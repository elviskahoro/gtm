from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import TypeAdapter, ValidationError

from src.attio.ops import (
    AttioOp,
    CompanyRef,
    MeetingExternalRef,
    MeetingParticipant,
    MeetingRef,
    PersonRef,
    Ref,
    UpsertCompany,
    UpsertMeeting,
    UpsertNote,
    UpsertPerson,
)


def test_upsert_person_discriminator() -> None:
    op = UpsertPerson(matching_attribute="email", email="a@example.com")
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
    person = adapter.validate_python(
        {"ref_kind": "person", "attribute": "email", "value": "a@b.com"},
    )
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


def test_upsert_note_carries_ref() -> None:
    op = UpsertNote(
        parent=PersonRef(attribute="email", value="a@b.com"),
        title="x",
        content="y",
    )
    assert isinstance(op.parent, PersonRef)
    assert op.op_type == "upsert_note"


def test_person_ref_generalized_shape_email() -> None:
    ref = PersonRef(attribute="email", value="a@example.com")
    assert ref.attribute == "email"
    assert ref.value == "a@example.com"


def test_person_ref_generalized_shape_github_handle() -> None:
    ref = PersonRef(attribute="github_handle", value="elviskahoro")
    assert ref.attribute == "github_handle"
    assert ref.value == "elviskahoro"


def test_upsert_person_requires_matching_attribute_field_to_be_set() -> None:
    with pytest.raises(ValidationError):
        # matching_attribute="email" but email is None
        UpsertPerson(
            matching_attribute="email",
            linkedin="https://www.linkedin.com/in/foo",
        )


def test_upsert_person_github_handle_construction() -> None:
    op = UpsertPerson(
        matching_attribute="github_handle",
        github_handle="elviskahoro",
        github_url="https://github.com/elviskahoro",
    )
    assert op.matching_attribute == "github_handle"
    assert op.github_handle == "elviskahoro"
    assert op.github_url == "https://github.com/elviskahoro"


def _valid_tracking_event_kwargs() -> dict[str, object]:
    return dict(
        external_id="rb2b:abc123",
        name="https://example.test/pricing",
        event_type="rb2b_visit",
        event_timestamp=datetime(2026, 5, 14, tzinfo=timezone.utc),
        captured_url="https://example.test/pricing",
        body_json='{"raw": "payload"}',
    )


def test_upsert_tracking_event_minimal_valid() -> None:
    from src.attio.ops import UpsertTrackingEvent

    op = UpsertTrackingEvent(**_valid_tracking_event_kwargs())
    assert op.op_type == "upsert_tracking_event"
    assert op.tags == []
    assert op.subject_person is None and op.subject_company is None


def test_upsert_tracking_event_with_refs() -> None:
    from src.attio.ops import UpsertTrackingEvent

    op = UpsertTrackingEvent(
        **_valid_tracking_event_kwargs(),
        subject_person=PersonRef(attribute="email", value="alice@example.test"),
        subject_company=CompanyRef(domain="example.test"),
        tags=["pricing", "enterprise"],
    )
    assert op.subject_person.attribute == "email"
    assert op.subject_person.value == "alice@example.test"
    assert op.subject_company.domain == "example.test"
    assert op.tags == ["pricing", "enterprise"]


def test_upsert_tracking_event_forbids_extra_fields() -> None:
    from src.attio.ops import UpsertTrackingEvent

    with pytest.raises(ValidationError):
        UpsertTrackingEvent(**_valid_tracking_event_kwargs(), bogus="x")


def test_attio_op_union_discriminates_tracking_event() -> None:
    from src.attio.ops import UpsertTrackingEvent

    adapter = TypeAdapter(AttioOp)
    raw = {"op_type": "upsert_tracking_event", **_valid_tracking_event_kwargs()}
    raw["event_timestamp"] = raw["event_timestamp"].isoformat()
    op = adapter.validate_python(raw)
    assert isinstance(op, UpsertTrackingEvent)


def test_upsert_person_accepts_enrichment_fields() -> None:
    op = UpsertPerson(
        matching_attribute="email",
        email="alice@example.test",
        title="Head of Eng",
        city="Brooklyn",
        state="NY",
        zipcode="11201",
        merge_only_if_empty=["title", "city", "state", "zipcode"],
    )
    assert op.title == "Head of Eng"
    assert op.merge_only_if_empty == ["title", "city", "state", "zipcode"]


def test_upsert_person_defaults_preserve_existing_call_sites() -> None:
    op = UpsertPerson(matching_attribute="email", email="alice@example.test")
    assert op.title is None
    assert op.city is None
    assert op.merge_only_if_empty == []
