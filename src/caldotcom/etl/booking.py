"""Webhook ETL contract for Cal.com booking ingestion."""

from typing import Any

from uuid_extensions import uuid7

from libs.caldotcom import Webhook as CalcomWebhook
from src.caldotcom.utils import (
    generate_gcs_filename,
    webhook_to_jsonl,
)


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
    def storage_get_base_model_type() -> None:
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
