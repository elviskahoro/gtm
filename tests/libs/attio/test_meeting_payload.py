from datetime import datetime, timezone

from libs.attio.models import (
    MeetingExternalRef,
    MeetingInput,
    MeetingLinkedRecord,
    MeetingParticipantInput,
)
from libs.attio.values import build_meeting_payload


def _ref(uid: str = "fathom-call-42") -> MeetingExternalRef:
    return MeetingExternalRef(ical_uid=uid, provider="google", is_recurring=False)


def test_build_meeting_payload_required_fields() -> None:
    input = MeetingInput(
        external_ref=_ref(),
        title="Onboarding",
        description="Customer kickoff",
        start=datetime(2026, 5, 12, 14, 0, tzinfo=timezone.utc),
        end=datetime(2026, 5, 12, 15, 0, tzinfo=timezone.utc),
        is_all_day=False,
        participants=[
            MeetingParticipantInput(email_address="a@example.com", is_organizer=True),
            MeetingParticipantInput(email_address="b@example.com", is_organizer=False),
        ],
    )
    payload = build_meeting_payload(input)
    data = payload["data"]
    assert data["external_ref"]["ical_uid"] == "fathom-call-42"
    assert data["external_ref"]["provider"] == "google"
    assert data["external_ref"]["is_recurring"] is False
    assert data["title"] == "Onboarding"
    assert data["is_all_day"] is False
    assert data["start"]["datetime"] == "2026-05-12T14:00:00+00:00"
    assert data["end"]["datetime"] == "2026-05-12T15:00:00+00:00"
    assert len(data["participants"]) == 2
    assert data["participants"][0] == {
        "email_address": "a@example.com",
        "is_organizer": True,
        "status": "accepted",
    }
    assert data["linked_records"] == []


def test_build_meeting_payload_with_linked_records() -> None:
    input = MeetingInput(
        external_ref=_ref("fathom-call-99"),
        title="Demo",
        description="x",
        start=datetime(2026, 5, 12, 14, 0, tzinfo=timezone.utc),
        end=datetime(2026, 5, 12, 14, 30, tzinfo=timezone.utc),
        is_all_day=False,
        participants=[
            MeetingParticipantInput(email_address="c@example.com", is_organizer=True),
        ],
        linked_records=[
            MeetingLinkedRecord(
                object="people",
                record_id="11111111-1111-1111-1111-111111111111",
            ),
        ],
    )
    payload = build_meeting_payload(input)
    assert payload["data"]["linked_records"] == [
        {"object": "people", "record_id": "11111111-1111-1111-1111-111111111111"},
    ]
