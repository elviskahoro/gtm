from datetime import datetime, timezone
from typing import Any
from unittest.mock import patch

from libs.attio.models import (
    MeetingExternalRef,
    MeetingInput,
    MeetingParticipantInput,
)


def _input(**overrides: Any) -> MeetingInput:
    base: dict[str, Any] = dict(
        external_ref=MeetingExternalRef(
            ical_uid="fathom-call-1",
            provider="google",
            is_recurring=False,
        ),
        title="t",
        description="d",
        start=datetime(2026, 5, 12, 14, 0, tzinfo=timezone.utc),
        end=datetime(2026, 5, 12, 15, 0, tzinfo=timezone.utc),
        is_all_day=False,
        participants=[
            MeetingParticipantInput(email_address="a@example.com", is_organizer=True),
        ],
    )
    base.update(overrides)
    return MeetingInput(**base)


def test_find_or_create_meeting_returns_success_envelope(monkeypatch) -> None:
    monkeypatch.setenv("ATTIO_API_KEY", "test-token")
    from libs.attio.meetings import find_or_create_meeting
    from libs.attio.models import MeetingResult

    fake_result = MeetingResult(
        meeting_id="11111111-1111-1111-1111-111111111111",
        workspace_id="22222222-2222-2222-2222-222222222222",
        title="t",
        external_ref_ical_uid="fathom-call-1",
        created=True,
    )
    with patch("libs.attio.meetings._post_meeting", return_value=fake_result):
        envelope = find_or_create_meeting(_input())

    assert envelope.success is True
    assert envelope.record_id == "11111111-1111-1111-1111-111111111111"
    assert envelope.action == "created"
    assert envelope.meta["external_ref_ical_uid"] == "fathom-call-1"


def test_find_or_create_meeting_auth_missing(monkeypatch) -> None:
    monkeypatch.delenv("ATTIO_API_KEY", raising=False)
    from libs.attio.meetings import find_or_create_meeting

    envelope = find_or_create_meeting(_input())
    assert envelope.success is False
    assert envelope.action == "failed"
    assert envelope.errors
    assert envelope.errors[0].fatal is True


def test_find_or_create_meeting_classified_validation_error(monkeypatch) -> None:
    monkeypatch.setenv("ATTIO_API_KEY", "test-token")
    from libs.attio.errors import AttioValidationError
    from libs.attio.meetings import find_or_create_meeting

    with patch(
        "libs.attio.meetings._post_meeting",
        side_effect=AttioValidationError("invalid title"),
    ):
        envelope = find_or_create_meeting(_input())

    assert envelope.success is False
    assert envelope.action == "failed"
    assert envelope.errors[0].error_type == "AttioValidationError"
    assert "invalid title" in envelope.errors[0].message
