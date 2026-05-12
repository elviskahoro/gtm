"""Webhook ETL contract for Cal.com booking ingestion."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel
from uuid_extensions import uuid7

from libs.caldotcom import Webhook as CalcomWebhook
from libs.meetings import canonical_meeting_uid
from src.caldotcom.utils import (
    generate_gcs_filename,
    webhook_to_jsonl,
)

# Cal.com Booking has a single top-level RSVP status that applies to the
# booking as a whole, plus a per-attendee `absent` boolean. Map to Attio's
# four-value enum: accepted | tentative | declined | pending.
_CALCOM_BOOKING_STATUS_TO_ATTIO: dict[
    str,
    Literal["accepted", "tentative", "declined", "pending"],
] = {
    "accepted": "accepted",
    "pending": "pending",
    "cancelled": "declined",
    "rejected": "declined",
}


def _caldotcom_status_to_attio(
    booking_status: str | None,
    *,
    absent: bool = False,
) -> Literal["accepted", "tentative", "declined", "pending"]:
    if absent:
        return "declined"
    if booking_status is None:
        return "accepted"
    return _CALCOM_BOOKING_STATUS_TO_ATTIO.get(booking_status, "accepted")


def _first_host_email(payload: dict[str, Any]) -> str | None:
    for h in payload.get("hosts") or []:
        email = h.get("email")
        if email:
            return str(email)
    return None


def _parse_start(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return None


class Webhook(CalcomWebhook):
    """Webhook subclass implementing ETL contract for Cal.com bookings."""

    @staticmethod
    def modal_get_secret_collection_names() -> list[str]:
        return ["devx-growth-gcp"]

    @staticmethod
    def etl_get_bucket_name() -> str:
        return "devx-caldotcom-booking-etl"

    @staticmethod
    def storage_get_app_name() -> str:
        return Webhook.etl_get_bucket_name()

    @staticmethod
    def storage_get_base_model_type() -> type[BaseModel] | None:
        return None

    @staticmethod
    def lance_get_project_name() -> str:
        raise NotImplementedError("LanceDB integration is Phase 2+")

    @staticmethod
    def lance_get_base_model_type() -> str:
        raise NotImplementedError("LanceDB integration is Phase 2+")

    def etl_is_valid_webhook(self) -> bool:
        return True

    def etl_get_invalid_webhook_error_msg(self) -> str:
        return "This webhook family does not support ETL output"

    def _booking_id(self) -> str:
        # Booking events nest the booking under `payload`; meeting events were
        # normalized into the same shape by the model validator. uid is the
        # stable string id; fall back to numeric ids, then uuid7 for PING.
        # Cached on the instance so filename and JSONL rows agree when we
        # have to synthesize a uuid.
        cached = getattr(self, "_cached_booking_id", None)
        if cached is not None:
            return cached
        payload = self.payload or {}
        uid = payload.get("uid") or payload.get("bookingUid")
        if not uid:
            for key in ("bookingId", "id"):
                if key in payload and payload[key] is not None:
                    uid = payload[key]
                    break
        if not uid:
            uid = uuid7()
        booking_id = str(uid)
        object.__setattr__(self, "_cached_booking_id", booking_id)
        return booking_id

    def etl_get_json(self, storage: Any = None) -> str:
        return webhook_to_jsonl(self.model_dump(mode="json"), self._booking_id())

    def etl_get_file_name(self) -> str:
        return generate_gcs_filename(
            self.createdAt,
            self.triggerEvent,
            self._booking_id(),
        )

    def etl_get_base_models(self, storage: Any) -> list[Any]:
        raise NotImplementedError("LanceDB integration is Phase 2+")

    # --- Attio export contract ---

    @staticmethod
    def attio_get_secret_collection_names() -> list[str]:
        return ["attio"]

    def attio_is_valid_webhook(self) -> bool:
        payload = self.payload or {}
        uid = payload.get("uid") or payload.get("bookingUid")
        attendees = payload.get("attendees") or []
        host_email = _first_host_email(payload)
        start = payload.get("start")
        return bool(uid) and bool(attendees) and bool(host_email) and bool(start)

    def attio_get_invalid_webhook_error_msg(self) -> str:
        return "Cal.com booking missing uid, attendees, host email, or start"

    def attio_get_operations(self) -> list[Any]:
        from src.attio.ops import (
            MeetingExternalRef,
            MeetingParticipant,
            UpsertMeeting,
        )

        payload = self.payload or {}
        uid = str(payload.get("uid") or payload.get("bookingUid") or "")
        host_email = _first_host_email(payload)
        start_dt = _parse_start(payload.get("start"))
        # Shared synthetic ical_uid lets Fathom's webhook write to the same Attio
        # record for the same meeting. Cal.com's icsUid is ignored on purpose:
        # Fathom does not see it, so using it would re-introduce duplicates.
        if host_email and start_dt is not None:
            ical_uid = canonical_meeting_uid(host_email=host_email, start=start_dt)
        else:
            ical_uid = f"caldotcom-booking-{uid}"

        title = payload.get("title") or "Cal.com booking"
        description = (
            payload.get("additionalNotes") or payload.get("description") or title
        )
        booking_status = payload.get("status")

        attendees: list[MeetingParticipant] = []
        for a in payload.get("attendees") or []:
            email = a.get("email")
            if not email:
                continue
            attendees.append(
                MeetingParticipant(
                    email_address=email,
                    is_organizer=False,
                    status=_caldotcom_status_to_attio(
                        booking_status,
                        absent=bool(a.get("absent")),
                    ),
                ),
            )

        for h in payload.get("hosts") or []:
            email = h.get("email")
            if not email:
                continue
            attendees.append(
                MeetingParticipant(
                    email_address=email,
                    is_organizer=True,
                    status="accepted",
                ),
            )

        return [
            UpsertMeeting(
                external_ref=MeetingExternalRef(
                    ical_uid=ical_uid,
                    provider="google",
                    is_recurring=False,
                ),
                title=title,
                description=description,
                start=payload["start"],
                end=payload["end"],
                is_all_day=False,
                participants=attendees,
            ),
        ]
