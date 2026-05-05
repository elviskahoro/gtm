from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest
from pydantic import ValidationError

from libs.attio.errors import (
    ConflictError,
    SchemaMismatchError,
    classify_error,
    translate_modal_signature_error,
)
from libs.attio.models import PersonInput, PersonSearchResult
from libs.attio.people import attempt_person_write_with_optional_fallback, upsert_person


def test_envelope_requires_warning_object_shape() -> None:
    from libs.attio.contracts import ReliabilityEnvelope

    with pytest.raises(ValidationError):
        ReliabilityEnvelope(
            success=True,
            partial_success=False,
            action="created",
            record_id="rec_123",
            warnings=[cast(Any, {"code": "x"})],
            skipped_fields=[],
            errors=[],
            meta={},
        )


def test_error_taxonomy_maps_schema_mismatch_as_nonfatal_by_default() -> None:
    err = SchemaMismatchError("missing field", field="notes")
    mapped = classify_error(err)

    assert mapped.code == "schema_mismatch"
    assert mapped.fatal is False
    assert mapped.error_type == "SchemaMismatchError"


def test_optional_field_degrades_with_warning_and_skipped_fields() -> None:
    class _Err(Exception):
        body = "associated_company field unavailable"

    calls: list[dict[str, Any]] = []

    def _write(values: dict[str, Any]) -> SimpleNamespace:
        calls.append(values)
        if "associated_company" in values or "company" in values:
            raise _Err("boom")
        return SimpleNamespace(
            data=SimpleNamespace(id=SimpleNamespace(record_id="rec_1"), values={}),
        )

    _, warnings, skipped = attempt_person_write_with_optional_fallback(
        write_func=_write,
        core_values={"email_addresses": ["a@example.com"]},
        optional_values={"associated_company": [{"domains": [{"domain": "acme.com"}]}]},
        strict=False,
    )

    assert len(calls) == 3
    assert "associated_company" in calls[0]
    assert "company" in calls[1]
    assert "associated_company" not in calls[2]
    assert "company" not in calls[2]
    assert warnings[0].code == "attio_associated_company_field_unavailable"
    assert skipped[0].field in {"associated_company", "company"}


def test_optional_field_schema_mismatch_raises_when_strict() -> None:
    class _Err(Exception):
        body = "notes field unavailable"

    def _write(_values: dict[str, Any]) -> None:
        raise _Err("boom")

    with pytest.raises(SchemaMismatchError):
        attempt_person_write_with_optional_fallback(
            write_func=_write,
            core_values={"email_addresses": ["a@example.com"]},
            optional_values={"notes": ["hello"]},
            strict=True,
        )


def test_company_optional_field_retries_with_alias_before_skipping() -> None:
    class _Err(Exception):
        body = "associated_company field unavailable"

    calls: list[dict[str, Any]] = []

    def _write(values: dict[str, Any]) -> SimpleNamespace:
        calls.append(values)
        if "associated_company" in values:
            raise _Err("boom")
        if "company" in values:
            return SimpleNamespace(
                data=SimpleNamespace(id=SimpleNamespace(record_id="rec_1"), values={}),
            )
        raise AssertionError("expected fallback to company alias")

    _, warnings, skipped = attempt_person_write_with_optional_fallback(
        write_func=_write,
        core_values={"email_addresses": ["a@example.com"]},
        optional_values={"associated_company": [{"domains": [{"domain": "acme.com"}]}]},
        strict=False,
    )

    assert len(calls) == 2
    assert "associated_company" in calls[0]
    assert "company" in calls[1]
    assert warnings == []
    assert skipped == []


def test_upsert_no_match_creates(monkeypatch) -> None:
    def _search_none(**_kwargs: object) -> list[PersonSearchResult]:
        return []

    monkeypatch.setattr("libs.attio.people._search_people_raw", _search_none)

    def _add(_input: PersonInput):
        from libs.attio.contracts import ReliabilityEnvelope

        return ReliabilityEnvelope(
            success=True,
            partial_success=False,
            action="created",
            record_id="rec_new",
            warnings=[],
            skipped_fields=[],
            errors=[],
            meta={"output_schema_version": "v1"},
        )

    monkeypatch.setattr("libs.attio.people.add_person", _add)

    result = upsert_person(PersonInput(email="a@example.com"))
    assert result.action == "created"


def test_upsert_single_match_updates(monkeypatch) -> None:
    def _search_single(**_kwargs: object) -> list[PersonSearchResult]:
        return [PersonSearchResult(record_id="rec_2")]

    monkeypatch.setattr("libs.attio.people._search_people_raw", _search_single)

    def _update(
        *,
        record_id: str | None,
        email: str | None,
        input: PersonInput,
    ):
        from libs.attio.contracts import ReliabilityEnvelope

        assert record_id == "rec_2"
        assert email is None
        _ = input
        return ReliabilityEnvelope(
            success=True,
            partial_success=False,
            action="updated",
            record_id="rec_2",
            warnings=[],
            skipped_fields=[],
            errors=[],
            meta={"output_schema_version": "v1"},
        )

    monkeypatch.setattr("libs.attio.people.update_person", _update)

    result = upsert_person(PersonInput(email="a@example.com"))
    assert result.action == "updated"


def test_upsert_multi_match_selects_lexicographically_smallest(monkeypatch) -> None:
    def _search_multi(**_kwargs: object) -> list[PersonSearchResult]:
        return [
            PersonSearchResult(record_id="rec_z"),
            PersonSearchResult(record_id="rec_a"),
        ]

    monkeypatch.setattr("libs.attio.people._search_people_raw", _search_multi)

    def _update(
        *,
        record_id: str | None,
        email: str | None,
        input: PersonInput,
    ):
        from libs.attio.contracts import ReliabilityEnvelope

        assert record_id == "rec_a"
        assert email is None
        _ = input
        return ReliabilityEnvelope(
            success=True,
            partial_success=False,
            action="updated",
            record_id="rec_a",
            warnings=[],
            skipped_fields=[],
            errors=[],
            meta={"output_schema_version": "v1"},
        )

    monkeypatch.setattr("libs.attio.people.update_person", _update)

    result = upsert_person(PersonInput(email="a@example.com"))
    warning_codes = {w.code for w in result.warnings}
    assert "upsert_multi_match_selected_record" in warning_codes


def test_upsert_multi_match_strict_raises_conflict(monkeypatch) -> None:
    def _search_multi(**_kwargs: object) -> list[PersonSearchResult]:
        return [
            PersonSearchResult(record_id="rec_z"),
            PersonSearchResult(record_id="rec_a"),
        ]

    monkeypatch.setattr("libs.attio.people._search_people_raw", _search_multi)

    with pytest.raises(ConflictError):
        upsert_person(PersonInput(email="a@example.com"), strict=True)


def test_classify_error_maps_modal_signature_mismatch_code() -> None:
    err = TypeError(
        "attio_upsert_person() got an unexpected keyword argument 'additional_emails'",
    )
    mapped = classify_error(translate_modal_signature_error(err))
    assert mapped.code == "modal_signature_mismatch"
