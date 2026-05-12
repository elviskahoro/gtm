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

from libs.attio.contracts import ErrorEntry, ReliabilityEnvelope
from libs.attio.meetings import find_or_create_meeting
from libs.attio.models import (
    MeetingExternalRef as LibMeetingExternalRef,
)
from libs.attio.models import (
    MeetingInput,
    MeetingParticipantInput,
    NoteInput,
    PersonInput,
)
from libs.attio.notes import add_note as libs_add_note
from libs.attio.people import upsert_person as libs_upsert_person
from src.attio.ops import (
    AddNote,
    AttioOp,
    CompanyRef,
    MeetingRef,
    PersonRef,
    UpsertCompany,
    UpsertMeeting,
    UpsertPerson,
)

logger = logging.getLogger(__name__)


# ---------- LookupTable ----------


@dataclass
class LookupTable:
    """In-plan registry mapping (kind, key) -> Attio record_id.

    Handlers consult the table to resolve ``Ref`` values (e.g. ``AddNote.parent``)
    against earlier ops in the same plan. Pass 3 wires ``_handle_add_note`` to
    use this.
    """

    _store: dict[tuple[str, str], str] = field(default_factory=dict)

    def record(self, op: AttioOp, record_id: str | None) -> None:
        if record_id is None:
            return
        key = self._key_for_op(op)
        if key is not None:
            self._store[key] = record_id

    def resolve(self, ref: PersonRef | CompanyRef | MeetingRef) -> str | None:
        return self._store.get(self._key_for_ref(ref))

    @staticmethod
    def _key_for_op(op: AttioOp) -> tuple[str, str] | None:
        if isinstance(op, UpsertPerson):
            return ("person", op.email)
        if isinstance(op, UpsertCompany):
            return ("company", op.domain)
        if isinstance(op, UpsertMeeting):
            return ("meeting", op.external_ref.ical_uid)
        return None

    @staticmethod
    def _key_for_ref(ref: PersonRef | CompanyRef | MeetingRef) -> tuple[str, str]:
        if isinstance(ref, PersonRef):
            return ("person", ref.email)
        if isinstance(ref, CompanyRef):
            return ("company", ref.domain)
        return ("meeting", ref.ical_uid)


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
            phone=op.phone,
            company_domain=op.company_domain,
            additional_emails=[],
            replace_emails=False,
        ),
    )


def _handle_upsert_company(
    op: UpsertCompany,
    table: LookupTable,
) -> ReliabilityEnvelope:
    # Pass 3 will either extend libs/attio/companies with upsert_company or
    # compose search+add inside this handler. The Fathom-call path never hits
    # this branch.
    raise NotImplementedError(
        "Pass 3 task: wire libs/attio/companies upsert path.",
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


def _handle_add_note(
    op: AddNote,
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


OP_HANDLERS: dict[type, Callable[[Any, LookupTable], ReliabilityEnvelope]] = {
    UpsertPerson: _handle_upsert_person,
    UpsertCompany: _handle_upsert_company,
    UpsertMeeting: _handle_upsert_meeting,
    AddNote: _handle_add_note,
}


# ---------- Dispatcher ----------


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
        envelope = handler(op, table)
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
