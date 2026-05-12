"""Webhook ETL contract for rb2b visit ingestion."""

from typing import Any

from libs.rb2b import Webhook as Rb2bWebhook
from src.rb2b.utils import (
    event_to_jsonl,
    generate_gcs_filename,
)


class Webhook(Rb2bWebhook):
    """Webhook subclass implementing ETL contract for rb2b visits."""

    @staticmethod
    def modal_get_secret_collection_names() -> list[str]:
        return ["devx-growth-gcp"]

    @staticmethod
    def etl_get_bucket_name() -> str:
        return "devx-rb2b-visit-etl"

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

    def etl_get_json(self, storage: Any = None) -> str:
        return event_to_jsonl(
            self.model_dump(mode="json", by_alias=False),
            self.event_id,
        )

    def etl_get_file_name(self) -> str:
        return generate_gcs_filename(
            self.timestamp,
            self.event_id,
            self.payload.company_name,
        )

    def etl_get_base_models(self, storage: Any) -> list[Any]:
        raise NotImplementedError("LanceDB integration is Phase 2+")
