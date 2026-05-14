"""Source-agnostic Attio operation dispatcher.

Source webhooks return ``list[AttioOp]`` via their ``attio_get_operations``
method; this module turns that into Attio SDK calls. The dispatcher imports
only from ``libs.attio.*`` and ``src.attio.ops`` — adding a new source webhook
should require no change here.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

from libs.attio.companies import upsert_company as libs_upsert_company
from libs.attio.contracts import ErrorEntry, ReliabilityEnvelope
from libs.attio.meetings import find_or_create_meeting
from libs.attio.mentions import upsert_mention as libs_upsert_mention
from libs.attio.models import (
    CompanyInput,
)
from libs.attio.models import (
    MeetingExternalRef as LibMeetingExternalRef,
)
from libs.attio.models import (
    MeetingInput,
    MeetingParticipantInput,
    MentionInput,
    NoteInput,
    PersonInput,
    TrackingEventInput,
)
from libs.attio.notes import (
    add_note as libs_add_note,
)
from libs.attio.notes import (
    list_notes_for_parent as libs_list_notes_for_parent,
)
from libs.attio.people import upsert_person as libs_upsert_person
from libs.attio.tracking_events import find_or_create_tracking_event
from src.attio.ops import (
    AttioOp,
    CompanyRef,
    MeetingRef,
    PersonRef,
    UpsertCompany,
    UpsertMeeting,
    UpsertMention,
    UpsertNote,
    UpsertPerson,
    UpsertTrackingEvent,
)

logger = logging.getLogger(__name__)


# ---------- LookupTable ----------


@dataclass
class LookupTable:
    """In-plan registry mapping (kind, attribute, value) -> Attio record_id.

    Handlers consult the table to resolve ``Ref`` values (e.g. ``UpsertNote.parent``)
    against earlier ops in the same plan. Pass 3 wires ``_handle_upsert_note`` to
    use this.
    """

    _store: dict[tuple[str, str, str], str] = field(default_factory=dict)

    def record(self, op: AttioOp, record_id: str | None) -> None:
        if record_id is None:
            return
        keys = self._key_for_op(op)
        if keys is not None:
            for key in keys:
                self._store[key] = record_id

    def resolve(self, ref: PersonRef | CompanyRef | MeetingRef) -> str | None:
        return self._store.get(self._key_for_ref(ref))

    @staticmethod
    def _key_for_op(op: AttioOp) -> list[tuple[str, str, str]] | None:
        if isinstance(op, UpsertPerson):
            value = getattr(op, op.matching_attribute)
            if value is None:
                return None
            return [("person", op.matching_attribute, value)]
        if isinstance(op, UpsertCompany):
            return [("company", "domain", op.domain)]
        if isinstance(op, UpsertMeeting):
            return [("meeting", "ical_uid", op.external_ref.ical_uid)]
        return None

    @staticmethod
    def _key_for_ref(ref: PersonRef | CompanyRef | MeetingRef) -> tuple[str, str, str]:
        if isinstance(ref, PersonRef):
            return ("person", ref.attribute, ref.value)
        if isinstance(ref, CompanyRef):
            return ("company", "domain", ref.domain)
        return ("meeting", "ical_uid", ref.ical_uid)


# ---------- Outcomes ----------


@dataclass
class OpOutcome:
    op_index: int
    op_type: str
    success: bool
    record_id: str | None
    envelope: ReliabilityEnvelope


@dataclass
class ExecutionResult:
    success: bool
    outcomes: list[OpOutcome]
    fail_index: int | None = None
    fail_reason: str | None = None

    def body(self) -> str:
        import orjson

        payload: dict[str, Any] = {
            "success": self.success,
            "outcomes": [
                {
                    "op_index": o.op_index,
                    "op_type": o.op_type,
                    "success": o.success,
                    "record_id": o.record_id,
                    **(
                        {"errors": [e.model_dump() for e in o.envelope.errors]}
                        if not o.success
                        else {}
                    ),
                }
                for o in self.outcomes
            ],
        }
        if not self.success:
            payload["fail_index"] = self.fail_index
            payload["fail_reason"] = self.fail_reason
        return orjson.dumps(payload).decode()


# ---------- Handlers ----------


def _handle_upsert_person(
    op: UpsertPerson,
    table: LookupTable,  # noqa: ARG001 — kept for handler signature parity
) -> ReliabilityEnvelope:
    return libs_upsert_person(
        PersonInput(
            email=op.email,
            first_name=op.first_name,
            last_name=op.last_name,
            linkedin=op.linkedin,
            github_handle=op.github_handle,
            github_url=op.github_url,
            phone=op.phone,
            company_domain=op.company_domain,
            title=op.title,
            city=op.city,
            state=op.state,
            zipcode=op.zipcode,
            additional_emails=[],
            replace_emails=False,
        ),
        matching_attribute=op.matching_attribute,
    )


def _handle_upsert_company(
    op: UpsertCompany,
    table: LookupTable,  # noqa: ARG001 — kept for handler signature parity
) -> ReliabilityEnvelope:
    return libs_upsert_company(
        CompanyInput(
            name=op.name or op.domain,
            domain=op.domain,
            industry=op.industry,
            employee_count=op.employee_count,
            estimate_revenue=op.estimate_revenue,
        ),
    )


def _handle_upsert_meeting(
    op: UpsertMeeting,
    table: LookupTable,  # noqa: ARG001 — Fathom path does not need linked_records
) -> ReliabilityEnvelope:
    return find_or_create_meeting(
        MeetingInput(
            external_ref=LibMeetingExternalRef(
                ical_uid=op.external_ref.ical_uid,
                provider=op.external_ref.provider,
                is_recurring=op.external_ref.is_recurring,
                original_start_time=op.external_ref.original_start_time,
            ),
            title=op.title,
            description=op.description,
            start=op.start,
            end=op.end,
            is_all_day=op.is_all_day,
            participants=[
                MeetingParticipantInput(
                    email_address=p.email_address,
                    is_organizer=p.is_organizer,
                    status=p.status,
                )
                for p in op.participants
            ],
            # Pass 3 will resolve op.linked_records through `table`; the Fathom
            # path uses /v2/meetings' implicit person/company auto-creation from
            # participants[].
            linked_records=[],
        ),
    )


_REF_KIND_TO_PARENT_OBJECT: dict[str, str] = {
    "person": "people",
    "company": "companies",
    "meeting": "meetings",
}


def _handle_upsert_note(
    op: UpsertNote,
    table: LookupTable,
) -> ReliabilityEnvelope:
    parent_record_id = table.resolve(op.parent)
    if parent_record_id is None:
        return ReliabilityEnvelope(
            success=False,
            partial_success=False,
            action="failed",
            record_id=None,
            errors=[
                ErrorEntry(
                    code="unresolved_ref",
                    message=(
                        f"could not resolve {op.parent.ref_kind}:"
                        f"{op.parent.model_dump()}"
                    ),
                    error_type="UnresolvedRefError",
                    fatal=True,
                ),
            ],
            warnings=[],
            skipped_fields=[],
            meta={"output_schema_version": "v1"},
        )

    parent_object = _REF_KIND_TO_PARENT_OBJECT[op.parent.ref_kind]

    # Idempotency: Attio has no native upsert for notes and no natural key,
    # so skip creation when a note with the same title already exists on the
    # parent. Titles emitted by webhook producers are deterministic per note
    # kind (e.g. "Fathom summary — Sales Discovery", "Action items"), so an
    # exact-title match is a reliable replay signal.
    existing = libs_list_notes_for_parent(
        parent_object=parent_object,
        parent_record_id=parent_record_id,
    )
    for note in existing:
        if note.title == op.title:
            return ReliabilityEnvelope(
                success=True,
                partial_success=False,
                action="noop",
                record_id=note.note_id,
                errors=[],
                warnings=[],
                skipped_fields=[],
                meta={"output_schema_version": "v1"},
            )

    result = libs_add_note(
        NoteInput(
            title=op.title,
            content=op.content,
            parent_object=parent_object,
            parent_record_id=parent_record_id,
        ),
    )
    return ReliabilityEnvelope(
        success=True,
        partial_success=False,
        action="created",
        record_id=result.note_id,
        errors=[],
        warnings=[],
        skipped_fields=[],
        meta={"output_schema_version": "v1"},
    )


def _handle_upsert_mention(
    op: UpsertMention,
    table: LookupTable,
) -> ReliabilityEnvelope:
    related_person_record_id = None
    if op.related_person:
        related_person_record_id = table.resolve(op.related_person)
        if related_person_record_id is None:
            return ReliabilityEnvelope(
                success=False,
                partial_success=False,
                action="failed",
                record_id=None,
                errors=[
                    ErrorEntry(
                        code="unresolved_ref",
                        message=(
                            f"could not resolve {op.related_person.ref_kind}:"
                            f"{op.related_person.model_dump()}"
                        ),
                        error_type="UnresolvedRefError",
                        fatal=True,
                    ),
                ],
                warnings=[],
                skipped_fields=[],
                meta={"output_schema_version": "v1"},
            )

    return libs_upsert_mention(
        MentionInput(
            mention_url=op.mention_url,
            last_action=op.last_action,
            source_platform=op.source_platform,
            source_id=op.source_id,
            mention_title=op.mention_title,
            mention_body=op.mention_body,
            mention_timestamp=op.mention_timestamp,
            author_handle=op.author_handle,
            author_profile_url=op.author_profile_url,
            author_avatar_url=op.author_avatar_url,
            relevance_score=op.relevance_score,
            relevance_comment=op.relevance_comment,
            primary_keyword=op.primary_keyword,
            keywords=op.keywords,
            octolens_tags=op.octolens_tags,
            sentiment=op.sentiment,
            language=op.language,
            subreddit=op.subreddit,
            view_id=op.view_id,
            view_name=op.view_name,
            bookmarked=op.bookmarked,
            image_url=op.image_url,
            related_person_record_id=related_person_record_id,
        ),
    )


def _handle_upsert_tracking_event(
    op: UpsertTrackingEvent,
    table: LookupTable,
) -> ReliabilityEnvelope:
    person_id: str | None = None
    company_id: str | None = None
    if op.subject_person is not None:
        person_id = table.resolve(op.subject_person)
        if person_id is None:
            return ReliabilityEnvelope(
                success=False,
                partial_success=False,
                action="failed",
                record_id=None,
                errors=[
                    ErrorEntry(
                        code="unresolved_ref",
                        message=(
                            f"could not resolve {op.subject_person.ref_kind}:"
                            f"{op.subject_person.model_dump()}"
                        ),
                        error_type="UnresolvedRefError",
                        fatal=True,
                    ),
                ],
                warnings=[],
                skipped_fields=[],
                meta={"output_schema_version": "v1"},
            )
    if op.subject_company is not None:
        company_id = table.resolve(op.subject_company)
        if company_id is None:
            return ReliabilityEnvelope(
                success=False,
                partial_success=False,
                action="failed",
                record_id=None,
                errors=[
                    ErrorEntry(
                        code="unresolved_ref",
                        message=(
                            f"could not resolve {op.subject_company.ref_kind}:"
                            f"{op.subject_company.model_dump()}"
                        ),
                        error_type="UnresolvedRefError",
                        fatal=True,
                    ),
                ],
                warnings=[],
                skipped_fields=[],
                meta={"output_schema_version": "v1"},
            )

    return find_or_create_tracking_event(
        TrackingEventInput(
            external_id=op.external_id,
            name=op.name,
            event_type=op.event_type,
            event_timestamp=op.event_timestamp,
            body_json=op.body_json,
            captured_url=op.captured_url,
            referrer=op.referrer,
            is_repeat_visit=op.is_repeat_visit,
            tags=op.tags,
            city=op.city,
            state=op.state,
            zipcode=op.zipcode,
            related_person_record_id=person_id,
            related_company_record_id=company_id,
        ),
    )


OP_HANDLERS: dict[type, Callable[[Any, LookupTable], ReliabilityEnvelope]] = {
    UpsertPerson: _handle_upsert_person,
    UpsertCompany: _handle_upsert_company,
    UpsertMeeting: _handle_upsert_meeting,
    UpsertNote: _handle_upsert_note,
    UpsertMention: _handle_upsert_mention,
    UpsertTrackingEvent: _handle_upsert_tracking_event,
}


# ---------- Dispatcher ----------


def _exception_envelope(error: Exception) -> ReliabilityEnvelope:
    """Wrap an uncaught handler exception as a failed envelope.

    Matches the shape Attio Modal wrappers produce via ``error_envelope`` so
    webhook callers always see a dispatcher result body, not a 500.
    """
    return ReliabilityEnvelope(
        success=False,
        partial_success=False,
        action="failed",
        record_id=None,
        errors=[
            ErrorEntry(
                code="handler_exception",
                message=f"{type(error).__name__}: {error}",
                error_type=type(error).__name__,
                fatal=True,
            ),
        ],
        warnings=[],
        skipped_fields=[],
        meta={"output_schema_version": "v1"},
    )


def execute(plan: Iterable[AttioOp]) -> ExecutionResult:
    """Execute a plan op-by-op. Fail-fast on the first failing envelope."""
    table = LookupTable()
    outcomes: list[OpOutcome] = []
    for i, op in enumerate(plan):
        handler = OP_HANDLERS.get(type(op))
        if handler is None:
            return ExecutionResult(
                success=False,
                outcomes=outcomes,
                fail_index=i,
                fail_reason=f"unknown_op: {type(op).__name__}",
            )
        try:
            envelope = handler(op, table)
        except Exception as exc:  # noqa: BLE001 — turn any handler crash into a failed outcome
            logger.exception(
                "attio handler raised for op_index=%d op_type=%s",
                i,
                type(op).__name__,
            )
            envelope = _exception_envelope(exc)
        outcomes.append(
            OpOutcome(
                op_index=i,
                op_type=type(op).__name__,
                success=envelope.success,
                record_id=envelope.record_id,
                envelope=envelope,
            ),
        )
        if not envelope.success:
            return ExecutionResult(
                success=False,
                outcomes=outcomes,
                fail_index=i,
                fail_reason="op_failed",
            )
        table.record(op, envelope.record_id)
    return ExecutionResult(success=True, outcomes=outcomes)
