"""Placeholder ETL contract for a future Fathom message webhook.

Fathom currently only delivers recording webhooks (see ``call.py``). This
module exists so ``webhooks/export_to_gcp_etl.py``'s eager import resolves.
Selecting this class as the active provider raises immediately — there is
no validated payload shape to ingest yet.
"""

from typing import Any

from pydantic import BaseModel

from libs.fathom import Webhook as FathomWebhook


class Webhook(FathomWebhook):
    """Stub. Not implemented — see module docstring."""

    @staticmethod
    def modal_get_secret_collection_names() -> list[str]:
        return ["devx-growth-gcp"]

    @staticmethod
    def etl_get_bucket_name() -> str:
        return "devx-fathom-message-etl"

    @staticmethod
    def storage_get_app_name() -> str:
        return Webhook.etl_get_bucket_name()

    @staticmethod
    def storage_get_base_model_type() -> type[BaseModel] | None:
        return None

    @staticmethod
    def lance_get_project_name() -> str:
        raise NotImplementedError("Fathom message ETL is not implemented")

    @staticmethod
    def lance_get_base_model_type() -> str:
        raise NotImplementedError("Fathom message ETL is not implemented")

    def etl_is_valid_webhook(self) -> bool:
        return False

    def etl_get_invalid_webhook_error_msg(self) -> str:
        return "Fathom message webhook ETL is not implemented"

    def etl_get_json(self, storage: Any = None) -> str:
        raise NotImplementedError("Fathom message ETL is not implemented")

    def etl_get_file_name(self) -> str:
        raise NotImplementedError("Fathom message ETL is not implemented")

    def etl_get_base_models(self, storage: Any) -> list[Any]:
        raise NotImplementedError("Fathom message ETL is not implemented")

    # --- Attio export contract ---

    @staticmethod
    def attio_get_secret_collection_names() -> list[str]:
        return ["attio"]

    def attio_is_valid_webhook(self) -> bool:
        # Fathom "messages" are action-items / one-line follow-ups that don't
        # cleanly map to Attio yet. Returning False keeps the contract uniform
        # so the dispatcher can be pointed at this webhook without crashing,
        # but no Attio writes happen.
        return False

    def attio_get_invalid_webhook_error_msg(self) -> str:
        return (
            "Fathom messages are not currently exported to Attio "
            "(AddNote mapping deferred)"
        )

    def attio_get_operations(self) -> list[Any]:
        return []
