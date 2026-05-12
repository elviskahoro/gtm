from __future__ import annotations

from pathlib import Path

import orjson

from src.attio.ops import UpsertMeeting
from src.caldotcom.webhook.booking import Webhook as CalcomBookingWebhook
from src.fathom.webhook.call import Webhook as FathomCallWebhook

CALCOM_FIXTURE = Path("api/samples/caldotcom/booking/redacted.json")
FATHOM_FIXTURE = Path("api/samples/fathom/call/redacted.json")

HOST_EMAIL = "host@dlthub.com"
SHARED_START = "2026-06-01T15:00:00.000Z"
SHARED_END = "2026-06-01T15:30:00.000Z"


def _calcom_webhook() -> CalcomBookingWebhook:
    payload = orjson.loads(CALCOM_FIXTURE.read_bytes())
    payload["payload"]["start"] = SHARED_START
    payload["payload"]["end"] = SHARED_END
    payload["payload"]["hosts"] = [
        {
            "id": 1,
            "name": "Host",
            "email": HOST_EMAIL,
            "displayEmail": HOST_EMAIL,
            "username": "host",
            "timeZone": "UTC",
        },
    ]
    return CalcomBookingWebhook.model_validate(payload)


def _fathom_webhook() -> FathomCallWebhook:
    payload = orjson.loads(FATHOM_FIXTURE.read_bytes())
    payload["scheduled_start_time"] = SHARED_START
    payload["scheduled_end_time"] = SHARED_END
    payload["recorded_by"]["email"] = HOST_EMAIL
    return FathomCallWebhook.model_validate(payload)


def test_same_meeting_from_both_providers_collapses_to_one_ical_uid() -> None:
    calcom_op = _calcom_webhook().attio_get_operations()[0]
    fathom_op = _fathom_webhook().attio_get_operations()[0]
    assert isinstance(calcom_op, UpsertMeeting)
    assert isinstance(fathom_op, UpsertMeeting)
    assert calcom_op.external_ref.ical_uid == fathom_op.external_ref.ical_uid


def test_different_start_times_diverge() -> None:
    calcom = _calcom_webhook()
    fathom = _fathom_webhook()
    fathom.scheduled_start_time = fathom.scheduled_start_time.replace(minute=30)
    calcom_op = calcom.attio_get_operations()[0]
    fathom_op = fathom.attio_get_operations()[0]
    assert calcom_op.external_ref.ical_uid != fathom_op.external_ref.ical_uid


def test_host_email_case_does_not_diverge() -> None:
    calcom = _calcom_webhook()
    fathom = _fathom_webhook()
    fathom.recorded_by.email = HOST_EMAIL.upper()
    calcom_op = calcom.attio_get_operations()[0]
    fathom_op = fathom.attio_get_operations()[0]
    assert calcom_op.external_ref.ical_uid == fathom_op.external_ref.ical_uid
