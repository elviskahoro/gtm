"""Webhook ETL contract for Octolens mention ingestion."""

from typing import Any, ClassVar

from pydantic import BaseModel

from libs.octolens import Webhook as OctolensWebhook
from src.octolens.utils import generate_gcs_filename


class Webhook(OctolensWebhook):
    """Webhook subclass implementing ETL contract for Octolens mentions."""

    @staticmethod
    def modal_get_secret_collection_names() -> list[str]:
        return ["devx-growth-gcp"]

    @staticmethod
    def etl_get_bucket_name() -> str:
        return "devx-octolens-mentions-etl"

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

    VALID_ACTIONS: ClassVar[frozenset[str]] = frozenset(
        {"mention_created", "mention_updated"},
    )

    def etl_is_valid_webhook(self) -> bool:
        return self.action in self.VALID_ACTIONS

    def etl_get_invalid_webhook_error_msg(self) -> str:
        return f"Invalid webhook: {self.action}"

    def etl_get_json(self, storage: Any = None) -> str:
        del storage
        return self.data.model_dump_json()

    def etl_get_file_name(self) -> str:
        return generate_gcs_filename(
            source=self.data.source,
            keyword=self.data.keyword,
            timestamp=self.data.timestamp,
            author=self.data.author,
            source_id=self.data.source_id,
        )

    def etl_get_base_models(self, storage: Any) -> list[Any]:
        del storage
        raise NotImplementedError("LanceDB integration is Phase 2+")

    # --- Attio export contract ---

    @staticmethod
    def attio_get_secret_collection_names() -> list[str]:
        return ["attio"]

    def attio_is_valid_webhook(self) -> bool:
        # Octolens mentions ship a platform-specific `author` username (Reddit,
        # Twitter, etc.) and an `author_profile_link`, but no email or company
        # domain — we cannot resolve a parent person/company without one of
        # those. Return False here so the webhook gracefully no-ops in Attio
        # while the rest of the export protocol stays uniform. A future change
        # could add LinkedIn-URL → Person resolution and flip this on.
        return False

    def attio_get_invalid_webhook_error_msg(self) -> str:
        return (
            "Octolens mentions do not currently map to Attio: no resolvable "
            "parent (no email or company domain on mention)."
        )

    def attio_get_operations(self) -> list[Any]:
        return []
