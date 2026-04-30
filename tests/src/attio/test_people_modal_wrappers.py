from __future__ import annotations

from typing import Any, cast

import modal

from src.attio import people as modal_people
from src.modal_app import MODAL_APP


def test_runtime_metadata_includes_fingerprint_and_capabilities() -> None:
    fn = cast(modal.Function, modal_people.attio_people_runtime_metadata)
    payload = cast(dict[str, Any], fn.local())
    assert payload["app"] == MODAL_APP
    assert "build_git_sha" in payload
    assert "deployed_at" in payload
    capabilities = cast(dict[str, Any], payload["capabilities"])
    assert capabilities["attio_people_upsert.additional_emails"] is True


def test_attio_upsert_person_wrapper_forwards_flags(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def _fake_upsert(input_obj, *, strict: bool):
        captured["strict"] = strict
        captured["location_mode"] = input_obj.location_mode
        captured["notes"] = input_obj.notes
        from libs.attio.contracts import ReliabilityEnvelope

        return ReliabilityEnvelope(
            success=True,
            partial_success=False,
            action="updated",
            record_id="rec_1",
            warnings=[],
            skipped_fields=[],
            errors=[],
            meta={"output_schema_version": "v1"},
        )

    monkeypatch.setattr(modal_people, "upsert_person", _fake_upsert)

    fn = cast(modal.Function, modal_people.attio_upsert_person)
    result = fn.local(
        payload={
            "email": "a@example.com",
            "notes": "hello",
            "strict": True,
            "location_mode": "raw",
        },
        api_keys={"attio_api_key": "ak"},
    )

    assert result.success is True
    assert captured["strict"] is True
    assert captured["location_mode"] == "raw"
    assert captured["notes"] == "hello"


def test_attio_add_person_wrapper_cleans_env(monkeypatch) -> None:
    import os

    monkeypatch.delenv("ATTIO_API_KEY", raising=False)

    def _fake_add(_input_obj):
        from libs.attio.contracts import ReliabilityEnvelope

        return ReliabilityEnvelope(
            success=True,
            partial_success=False,
            action="created",
            record_id="rec_2",
            warnings=[],
            skipped_fields=[],
            errors=[],
            meta={"output_schema_version": "v1"},
        )

    monkeypatch.setattr(modal_people, "add_person", _fake_add)

    fn = cast(modal.Function, modal_people.attio_add_person)
    _ = fn.local(
        payload={"email": "a@example.com"},
        api_keys={"attio_api_key": "ak"},
    )

    assert "ATTIO_API_KEY" not in os.environ
