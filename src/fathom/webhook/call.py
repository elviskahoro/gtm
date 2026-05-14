"""Webhook ETL contract for Fathom recording ingestion."""

from typing import Any

from pydantic import BaseModel

from libs.dlt.bucket_naming import etl_bucket_name
from libs.fathom import Webhook as FathomWebhook
from libs.meetings import canonical_meeting_uid
from src.fathom.utils import (
    fathom_summary_title,
    render_action_items_markdown,
    generate_gcs_filename,
    recording_to_jsonl,
)


class Webhook(FathomWebhook):
    """Webhook subclass implementing ETL contract for Fathom recordings."""

    @staticmethod
    def modal_get_secret_collection_names() -> list[str]:
        return ["devx-gcp-202605111323"]

    @staticmethod
    def etl_get_bucket_name() -> str:
        return etl_bucket_name(source="fathom", entity_plural="recordings")

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
        return recording_to_jsonl(self.model_dump(mode="json"), self.recording_id)

    def etl_get_file_name(self) -> str:
        return generate_gcs_filename(
            self.recording_start_time,
            self.recording_id,
            self.meeting_title or self.title,
        )

    def etl_get_base_models(self, storage: Any) -> list[Any]:
        raise NotImplementedError("LanceDB integration is Phase 2+")

    # --- Attio export contract ---

    @staticmethod
    def attio_get_secret_collection_names() -> list[str]:
        return ["attio"]

    @staticmethod
    def attio_get_app_name() -> str:
        return "export-to-attio-from-fathom-recordings"

    def attio_is_valid_webhook(self) -> bool:
        # Ad-hoc Fathom recordings have no calendar invitees but still carry a
        # recorder we can attribute the meeting to. Only reject payloads we
        # truly can't anchor (missing recording_id or recorder email).
        return bool(self.recording_id) and bool(self.recorded_by.email)

    def attio_get_invalid_webhook_error_msg(self) -> str:
        return (
            "Fathom call payload is not exportable to Attio "
            "(missing recording_id or recorder email)"
        )

    def attio_get_operations(self) -> list[Any]:
        from src.attio.ops import (
            AddNote,
            MeetingExternalRef,
            MeetingParticipant,
            MeetingRef,
            UpsertMeeting,
        )

        description: str = (
            self.default_summary.markdown_formatted
            if self.default_summary
            else (self.meeting_title or self.title)
        )
        # Fall back to the recorder as the sole participant for ad-hoc Fathom
        # recordings that aren't tied to a calendar invite.
        participants = [
            MeetingParticipant(
                email_address=inv.email,
                is_organizer=(inv.email == self.recorded_by.email),
            )
            for inv in self.calendar_invitees
        ] or [
            MeetingParticipant(
                email_address=self.recorded_by.email,
                is_organizer=True,
            ),
        ]
        ical_uid = canonical_meeting_uid(
            host_email=self.recorded_by.email,
            start=self.scheduled_start_time,
        )
        ops: list[Any] = [
            UpsertMeeting(
                external_ref=MeetingExternalRef(
                    ical_uid=ical_uid,
                    provider="google",
                    is_recurring=False,
                ),
                title=self.meeting_title or self.title,
                description=description,
                start=self.scheduled_start_time,
                end=self.scheduled_end_time,
                is_all_day=False,
                participants=participants,
            ),
        ]

        if self.default_summary and self.default_summary.markdown_formatted.strip():
            ops.append(
                AddNote(
                    parent=MeetingRef(ical_uid=ical_uid),
                    title=fathom_summary_title(self.default_summary.template_name),
                    content=self.default_summary.markdown_formatted,
                ),
            )

        if self.action_items:
            rendered = render_action_items_markdown(self.action_items)
            if rendered.strip():
                ops.append(
                    AddNote(
                        parent=MeetingRef(ical_uid=ical_uid),
                        title="Action items",
                        content=rendered,
                    ),
                )

        return ops
