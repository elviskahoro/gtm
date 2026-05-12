from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import TypeAdapter, ValidationError

from src.attio.ops import (
    AddNote,
    AttioOp,
    CompanyRef,
    MeetingExternalRef,
    MeetingParticipant,
    MeetingRef,
    PersonRef,
    Ref,
    UpsertCompany,
    UpsertMeeting,
    UpsertPerson,
)


def test_upsert_person_discriminator() -> None:
    op = UpsertPerson(email="a@example.com")
    assert op.op_type == "upsert_person"


def test_attio_op_union_dispatches_by_op_type() -> None:
    adapter: TypeAdapter[AttioOp] = TypeAdapter(AttioOp)
    parsed = adapter.validate_python(
        {"op_type": "upsert_company", "domain": "example.com"},
    )
    assert isinstance(parsed, UpsertCompany)
    assert parsed.domain == "example.com"


def test_ref_discriminator() -> None:
    adapter: TypeAdapter[Ref] = TypeAdapter(Ref)
    parsed = adapter.validate_python(
        {"ref_kind": "meeting", "ical_uid": "fathom-call-1"},
    )
    assert isinstance(parsed, MeetingRef)
    assert parsed.ical_uid == "fathom-call-1"


def test_ref_discriminator_person_and_company() -> None:
    adapter: TypeAdapter[Ref] = TypeAdapter(Ref)
    person = adapter.validate_python({"ref_kind": "person", "email": "a@b.com"})
    company = adapter.validate_python({"ref_kind": "company", "domain": "b.com"})
    assert isinstance(person, PersonRef)
    assert isinstance(company, CompanyRef)


def test_upsert_meeting_requires_participants() -> None:
    with pytest.raises(ValidationError):
        UpsertMeeting(  # type: ignore[call-arg]
            external_ref=MeetingExternalRef(ical_uid="x"),
            title="t",
            description="d",
            start=datetime(2026, 5, 12, tzinfo=timezone.utc),
            end=datetime(2026, 5, 12, 1, tzinfo=timezone.utc),
        )


def test_upsert_meeting_external_ref_structured_defaults() -> None:
    ref = MeetingExternalRef(ical_uid="fathom-call-42")
    assert ref.provider == "google"
    assert ref.is_recurring is False
    assert ref.original_start_time is None

    op = UpsertMeeting(
        external_ref=ref,
        title="t",
        description="d",
        start=datetime(2026, 5, 12, tzinfo=timezone.utc),
        end=datetime(2026, 5, 12, 1, tzinfo=timezone.utc),
        is_all_day=False,
        participants=[MeetingParticipant(email_address="a@b.com", is_organizer=True)],
    )
    assert op.external_ref.ical_uid == "fathom-call-42"
    assert op.linked_records == []


def test_add_note_carries_ref() -> None:
    op = AddNote(
        parent=PersonRef(email="a@b.com"),
        title="x",
        content="y",
    )
    assert isinstance(op.parent, PersonRef)
    assert op.op_type == "add_note"
