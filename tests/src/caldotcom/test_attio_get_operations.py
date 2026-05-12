from __future__ import annotations

from datetime import datetime
from pathlib import Path

import orjson

from libs.meetings import canonical_meeting_uid
from src.attio.ops import MeetingExternalRef, UpsertMeeting
from src.caldotcom.webhook.booking import Webhook

FIXTURE = Path("api/samples/caldotcom/booking/redacted.json")


def _load() -> Webhook:
    payload = orjson.loads(FIXTURE.read_bytes())
    return Webhook.model_validate(payload)


def test_attio_get_secret_collection_names() -> None:
    assert Webhook.attio_get_secret_collection_names() == ["attio"]


def test_attio_is_valid_webhook_true_for_normal_payload() -> None:
    assert _load().attio_is_valid_webhook() is True


def test_attio_is_valid_webhook_false_with_no_attendees() -> None:
    w = _load()
    w.payload["attendees"] = []
    assert w.attio_is_valid_webhook() is False
    assert "attendees" in w.attio_get_invalid_webhook_error_msg()


def test_attio_get_operations_returns_single_upsert_meeting() -> None:
    plan = _load().attio_get_operations()

    assert len(plan) == 1
    op = plan[0]
    assert isinstance(op, UpsertMeeting)

    assert isinstance(op.external_ref, MeetingExternalRef)
    expected = canonical_meeting_uid(
        host_email="host@dlthub.com",
        start=datetime.fromisoformat("2026-05-20T15:00:00+00:00"),
    )
    assert op.external_ref.ical_uid == expected

    assert op.title == "Discovery call"
    assert op.description == "Customer would like to discuss pricing."
    assert op.is_all_day is False

    emails = [p.email_address for p in op.participants]
    assert "host@dlthub.com" in emails
    assert "external@example.com" in emails

    organizers = [p for p in op.participants if p.is_organizer]
    assert len(organizers) == 1
    assert organizers[0].email_address == "host@dlthub.com"

    external = next(
        p for p in op.participants if p.email_address == "external@example.com"
    )
    # Booking status="accepted" → attendee status="accepted"
    assert external.status == "accepted"


def test_attio_get_operations_ignores_icsUid_in_favor_of_canonical_uid() -> None:
    with_ics = _load()
    without_ics = _load()
    without_ics.payload.pop("icsUid", None)
    assert (
        with_ics.attio_get_operations()[0].external_ref.ical_uid
        == without_ics.attio_get_operations()[0].external_ref.ical_uid
    )


def test_attio_get_operations_falls_back_when_host_email_missing() -> None:
    w = _load()
    w.payload["hosts"] = []
    op = w.attio_get_operations()[0]
    assert isinstance(op, UpsertMeeting)
    assert op.external_ref.ical_uid == "caldotcom-booking-calcom-booking-abc123"


def test_attio_is_valid_webhook_false_when_host_email_missing() -> None:
    w = _load()
    w.payload["hosts"] = []
    assert w.attio_is_valid_webhook() is False


def test_attio_is_valid_webhook_false_when_start_missing() -> None:
    w = _load()
    w.payload.pop("start", None)
    assert w.attio_is_valid_webhook() is False


def test_attio_get_operations_marks_absent_attendee_declined() -> None:
    w = _load()
    w.payload["attendees"][0]["absent"] = True
    op = w.attio_get_operations()[0]
    external = next(
        p for p in op.participants if p.email_address == "external@example.com"
    )
    assert external.status == "declined"


def test_attio_get_operations_maps_cancelled_status_to_declined() -> None:
    w = _load()
    w.payload["status"] = "cancelled"
    op = w.attio_get_operations()[0]
    external = next(
        p for p in op.participants if p.email_address == "external@example.com"
    )
    assert external.status == "declined"
