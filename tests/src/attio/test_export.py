from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

from libs.attio.contracts import ErrorEntry, ReliabilityEnvelope
from src.attio.export import LookupTable, execute
from src.attio.ops import (
    AddNote,
    MeetingExternalRef,
    MeetingParticipant,
    MeetingRef,
    PersonRef,
    UpsertCompany,
    UpsertMeeting,
    UpsertPerson,
)


def _ok(record_id: str) -> ReliabilityEnvelope:
    return ReliabilityEnvelope(
        success=True,
        partial_success=False,
        action="created",
        record_id=record_id,
        errors=[],
        warnings=[],
        skipped_fields=[],
        meta={"output_schema_version": "v1"},
    )


def _fail(msg: str) -> ReliabilityEnvelope:
    return ReliabilityEnvelope(
        success=False,
        partial_success=False,
        action="failed",
        record_id=None,
        errors=[
            ErrorEntry(
                code="test_failure",
                message=msg,
                error_type="TestError",
                fatal=True,
            ),
        ],
        warnings=[],
        skipped_fields=[],
        meta={"output_schema_version": "v1"},
    )


def _meeting(ical_uid: str = "fathom-call-1") -> UpsertMeeting:
    return UpsertMeeting(
        external_ref=MeetingExternalRef(ical_uid=ical_uid),
        title="t",
        description="d",
        start=datetime(2026, 5, 12, tzinfo=timezone.utc),
        end=datetime(2026, 5, 12, 1, tzinfo=timezone.utc),
        is_all_day=False,
        participants=[
            MeetingParticipant(email_address="a@example.com", is_organizer=True),
        ],
    )


def test_lookup_table_resolves_person_ref() -> None:
    table = LookupTable()
    table.record(
        UpsertPerson(matching_attribute="email", email="a@example.com"),
        "rec-1",
    )
    assert table.resolve(PersonRef(attribute="email", value="a@example.com")) == "rec-1"


def test_lookup_table_missing_returns_none() -> None:
    table = LookupTable()
    assert table.resolve(PersonRef(attribute="email", value="nope@example.com")) is None


def test_lookup_table_resolves_meeting_ref() -> None:
    table = LookupTable()
    table.record(_meeting("fathom-call-42"), "meet-42")
    assert table.resolve(MeetingRef(ical_uid="fathom-call-42")) == "meet-42"


def test_lookup_table_ignores_none_record_id() -> None:
    table = LookupTable()
    table.record(UpsertPerson(matching_attribute="email", email="a@example.com"), None)
    assert table.resolve(PersonRef(attribute="email", value="a@example.com")) is None


def test_execute_happy_single_op(monkeypatch) -> None:
    handler = MagicMock(return_value=_ok("meet-1"))
    monkeypatch.setattr("src.attio.export.OP_HANDLERS", {UpsertMeeting: handler})

    result = execute([_meeting()])

    assert result.success is True
    assert len(result.outcomes) == 1
    assert result.outcomes[0].record_id == "meet-1"
    assert result.outcomes[0].op_type == "UpsertMeeting"
    handler.assert_called_once()


def test_execute_fail_fast(monkeypatch) -> None:
    ok = MagicMock(return_value=_ok("p-1"))
    bad = MagicMock(return_value=_fail("validation"))
    never = MagicMock(return_value=_ok("never"))
    monkeypatch.setattr(
        "src.attio.export.OP_HANDLERS",
        {UpsertPerson: ok, UpsertCompany: bad, UpsertMeeting: never},
    )

    plan = [
        UpsertPerson(matching_attribute="email", email="a@example.com"),
        UpsertCompany(domain="example.com"),
        _meeting(),
    ]
    result = execute(plan)

    assert result.success is False
    assert result.fail_index == 1
    assert result.fail_reason == "op_failed"
    assert len(result.outcomes) == 2
    assert ok.call_count == 1
    assert bad.call_count == 1
    assert never.call_count == 0


def test_execute_unresolved_ref(monkeypatch) -> None:
    handler_note = MagicMock(
        return_value=_fail("unresolved_ref: meeting:not-yet-created"),
    )
    monkeypatch.setattr("src.attio.export.OP_HANDLERS", {AddNote: handler_note})

    plan = [
        AddNote(
            parent=MeetingRef(ical_uid="not-yet-created"),
            title="x",
            content="y",
        ),
    ]
    result = execute(plan)

    assert result.success is False
    assert result.fail_index == 0
    assert "unresolved_ref" in result.outcomes[0].envelope.errors[0].message


def test_execute_handler_exception_becomes_failed_outcome(monkeypatch) -> None:
    """Library exceptions must turn into a failed ExecutionResult, not propagate."""

    def boom(_op, _table):
        raise RuntimeError("attio api blew up")

    monkeypatch.setattr("src.attio.export.OP_HANDLERS", {UpsertPerson: boom})

    result = execute([UpsertPerson(matching_attribute="email", email="a@example.com")])

    assert result.success is False
    assert result.fail_index == 0
    assert result.fail_reason == "op_failed"
    assert len(result.outcomes) == 1
    envelope = result.outcomes[0].envelope
    assert envelope.success is False
    assert envelope.errors[0].code == "handler_exception"
    assert envelope.errors[0].error_type == "RuntimeError"
    assert "attio api blew up" in envelope.errors[0].message


def test_execute_unknown_op(monkeypatch) -> None:
    monkeypatch.setattr("src.attio.export.OP_HANDLERS", {})
    result = execute([UpsertPerson(matching_attribute="email", email="a@example.com")])
    assert result.success is False
    assert result.fail_reason is not None
    assert "unknown_op" in result.fail_reason


def test_execution_result_body_success(monkeypatch) -> None:
    import orjson

    handler = MagicMock(return_value=_ok("meet-1"))
    monkeypatch.setattr("src.attio.export.OP_HANDLERS", {UpsertMeeting: handler})
    result = execute([_meeting()])
    body = orjson.loads(result.body())

    assert body["success"] is True
    assert body["outcomes"] == [
        {
            "op_index": 0,
            "op_type": "UpsertMeeting",
            "success": True,
            "record_id": "meet-1",
        },
    ]
    assert "fail_index" not in body


def test_handle_add_note_happy_path(monkeypatch) -> None:
    from src.attio.export import OP_HANDLERS

    _handle_add_note = OP_HANDLERS[AddNote]

    person_op = UpsertPerson(matching_attribute="email", email="a@example.com")
    table = LookupTable()
    table.record(person_op, "person-rec-1")

    fake_result = MagicMock()
    fake_result.note_id = "note-1"
    add_note_mock = MagicMock(return_value=fake_result)
    monkeypatch.setattr("src.attio.export.libs_add_note", add_note_mock)

    envelope = _handle_add_note(
        AddNote(
            parent=PersonRef(attribute="email", value="a@example.com"),
            title="hi",
            content="body",
        ),
        table,
    )

    assert envelope.success is True
    assert envelope.record_id == "note-1"
    assert envelope.action == "created"
    call_input = add_note_mock.call_args.args[0]
    assert call_input.parent_object == "people"
    assert call_input.parent_record_id == "person-rec-1"
    assert call_input.title == "hi"
    assert call_input.content == "body"


def test_handle_add_note_maps_ref_kind_to_parent_object(monkeypatch) -> None:
    from src.attio.export import OP_HANDLERS

    _handle_add_note = OP_HANDLERS[AddNote]

    company_op = UpsertCompany(domain="example.com")
    meeting_op = _meeting("fathom-call-7")
    table = LookupTable()
    table.record(company_op, "company-rec-1")
    table.record(meeting_op, "meet-rec-7")

    fake_result = MagicMock()
    fake_result.note_id = "note-x"
    add_note_mock = MagicMock(return_value=fake_result)
    monkeypatch.setattr("src.attio.export.libs_add_note", add_note_mock)

    _handle_add_note(
        AddNote(
            parent=MeetingRef(ical_uid="fathom-call-7"),
            title="m",
            content="c",
        ),
        table,
    )
    assert add_note_mock.call_args.args[0].parent_object == "meetings"
    assert add_note_mock.call_args.args[0].parent_record_id == "meet-rec-7"

    from src.attio.ops import CompanyRef

    _handle_add_note(
        AddNote(
            parent=CompanyRef(domain="example.com"),
            title="m",
            content="c",
        ),
        table,
    )
    assert add_note_mock.call_args.args[0].parent_object == "companies"
    assert add_note_mock.call_args.args[0].parent_record_id == "company-rec-1"


def test_handle_add_note_unresolved_ref_returns_failed_envelope(monkeypatch) -> None:
    from src.attio.export import OP_HANDLERS

    _handle_add_note = OP_HANDLERS[AddNote]

    add_note_mock = MagicMock()
    monkeypatch.setattr("src.attio.export.libs_add_note", add_note_mock)

    envelope = _handle_add_note(
        AddNote(
            parent=PersonRef(attribute="email", value="missing@example.com"),
            title="hi",
            content="body",
        ),
        LookupTable(),
    )

    assert envelope.success is False
    assert envelope.action == "failed"
    assert envelope.record_id is None
    assert len(envelope.errors) == 1
    err = envelope.errors[0]
    assert err.code == "unresolved_ref"
    assert err.error_type == "UnresolvedRefError"
    assert err.fatal is True
    add_note_mock.assert_not_called()


def test_execution_result_body_failure(monkeypatch) -> None:
    import orjson

    monkeypatch.setattr("src.attio.export.OP_HANDLERS", {})
    result = execute([UpsertPerson(matching_attribute="email", email="a@example.com")])
    body = orjson.loads(result.body())

    assert body["success"] is False
    assert body["fail_index"] == 0
    assert body["fail_reason"].startswith("unknown_op")


def test_lookup_table_records_and_resolves_github_handle_person() -> None:
    table = LookupTable()
    op = UpsertPerson(
        matching_attribute="github_handle",
        github_handle="elviskahoro",
        github_url="https://github.com/elviskahoro",
    )
    table.record(op, "rec_gh_1")
    assert (
        table.resolve(PersonRef(attribute="github_handle", value="elviskahoro"))
        == "rec_gh_1"
    )


def test_lookup_table_records_and_resolves_email_person_generalized() -> None:
    table = LookupTable()
    op = UpsertPerson(matching_attribute="email", email="a@example.com")
    table.record(op, "rec_email_1")
    assert (
        table.resolve(PersonRef(attribute="email", value="a@example.com"))
        == "rec_email_1"
    )


def test_lookup_table_records_and_resolves_linkedin_person_generalized() -> None:
    table = LookupTable()
    op = UpsertPerson(
        matching_attribute="linkedin",
        linkedin="https://www.linkedin.com/in/foo",
    )
    table.record(op, "rec_li_1")
    assert (
        table.resolve(
            PersonRef(attribute="linkedin", value="https://www.linkedin.com/in/foo"),
        )
        == "rec_li_1"
    )
