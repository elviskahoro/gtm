"""Webhook ETL contract for rb2b visit ingestion."""

from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel

from libs.dlt.bucket_naming import etl_bucket_name
from libs.rb2b import Webhook as Rb2bWebhook
from src.rb2b.utils import (
    event_to_jsonl,
    generate_gcs_filename,
)


def extract_domain(website: str | None) -> str | None:
    """Best-effort domain extraction from an rb2b Website field.

    rb2b emits values like ``https://example.com``, ``example.com/path``, or
    ``www.example.com``. Strip scheme, leading ``www.``, and any path/query so
    the result matches Attio's expected ``domains[].domain`` shape.
    """
    if not website:
        return None
    candidate = website.strip()
    if not candidate:
        return None
    if "://" not in candidate:
        candidate = f"//{candidate}"
    host = urlparse(candidate).hostname
    if not host:
        return None
    return host.removeprefix("www.")


class Webhook(Rb2bWebhook):
    """Webhook subclass implementing ETL contract for rb2b visits."""

    @staticmethod
    def modal_get_secret_collection_names() -> list[str]:
        return ["devx-gcp-202605111323"]

    @staticmethod
    def etl_get_bucket_name() -> str:
        return etl_bucket_name(source="rb2b", entity_plural="visits")

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

    # --- Attio export contract ---

    @staticmethod
    def attio_get_secret_collection_names() -> list[str]:
        return ["attio"]

    @staticmethod
    def attio_get_app_name() -> str:
        return "export-to-attio-from-rb2b-visits"

    def _attio_domain(self) -> str | None:
        return extract_domain(self.payload.website)

    def attio_is_valid_webhook(self) -> bool:
        # An rb2b visit is exportable if we have something to land in Attio —
        # either an identified person (business_email) or an identified company
        # (resolvable domain). Anonymous visits with neither are skipped.
        has_person = bool(self.payload.business_email)
        has_company = bool(self._attio_domain())
        return has_person or has_company

    def attio_get_invalid_webhook_error_msg(self) -> str:
        return "rb2b visit has neither business_email nor a resolvable company domain"

    def attio_get_operations(self) -> list[Any]:
        import json
        from datetime import datetime, timezone

        from src.attio.ops import (
            CompanyRef,
            PersonRef,
            UpsertCompany,
            UpsertPerson,
            UpsertTrackingEvent,
        )

        ops: list[Any] = []
        domain = self._attio_domain()
        email = self.payload.business_email
        linkedin = self.payload.linkedin_url

        if domain:
            ops.append(
                UpsertCompany(
                    domain=domain,
                    name=self.payload.company_name,
                    industry=self.payload.industry,
                    employee_count=self.payload.employee_count,
                    estimate_revenue=self.payload.estimate_revenue,
                    merge_only_if_empty=[
                        "industry",
                        "employee_count",
                        "estimate_revenue",
                    ],
                ),
            )

        if email:
            ops.append(
                UpsertPerson(
                    matching_attribute="email",
                    email=email,
                    first_name=self.payload.first_name,
                    last_name=self.payload.last_name,
                    linkedin=linkedin,
                    company_domain=domain,
                    title=self.payload.title,
                    city=self.payload.city,
                    state=self.payload.state,
                    zipcode=self.payload.zipcode,
                    merge_only_if_empty=["title", "city", "state", "zipcode"],
                ),
            )

        # tracking_events always emitted if validity gate passed (anonymous already rejected).
        subject_person = PersonRef(attribute="email", value=email) if email else None
        subject_company = CompanyRef(domain=domain) if domain else None

        tags_list = [
            t.strip() for t in (self.payload.tags or "").split(",") if t.strip()
        ]
        seen_at = self.payload.seen_at or self.timestamp or datetime.now(timezone.utc)

        ops.append(
            UpsertTrackingEvent(
                external_id=f"rb2b:{self.event_id}",
                name=self.payload.captured_url or "",
                event_type="rb2b_visit",
                event_timestamp=seen_at,
                body_json=json.dumps(self.model_dump(mode="json")),
                captured_url=self.payload.captured_url or "",
                referrer=self.payload.referrer,
                is_repeat_visit=self.payload.is_repeat_visit,
                tags=tags_list,
                city=self.payload.city,
                state=self.payload.state,
                zipcode=self.payload.zipcode,
                subject_person=subject_person,
                subject_company=subject_company,
            ),
        )

        return ops
