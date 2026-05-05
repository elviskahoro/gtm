from __future__ import annotations

import json
from typing import cast

import modal

from libs.attio.errors import ConflictError
from src.attio import companies as modal_companies
from src.attio import notes as modal_notes
from src.attio import people as modal_people


def test_company_add_http_returns_structured_409_on_conflict(monkeypatch) -> None:
    def _raise_conflict(**_kwargs):
        raise ConflictError("already exists")

    monkeypatch.setattr(modal_companies.attio_add_company, "remote", _raise_conflict)

    fn = cast(modal.Function, modal_companies.attio_company_add_http)
    response = fn.local(
        modal_companies.CompanyAddQuery(
            name="Acme",
            domain="acme.com",
            description=None,
        ),
    )

    assert hasattr(response, "status_code")
    assert hasattr(response, "body")
    assert response.status_code == 409
    body = json.loads(response.body.decode("utf-8"))
    assert body["errors"][0]["code"] == "conflict"


def test_note_update_http_infers_401_from_error_message(monkeypatch) -> None:
    def _raise_auth(**_kwargs):
        raise RuntimeError(
            "API error occurred: Status 401 Content-Type application/json",
        )

    monkeypatch.setattr(modal_notes.attio_update_note, "remote", _raise_auth)

    fn = cast(modal.Function, modal_notes.attio_note_update_http)
    response = fn.local(
        modal_notes.NoteUpdateQuery(
            note_id="note_123",
            title="x",
            content="y",
        ),
    )

    assert hasattr(response, "status_code")
    assert hasattr(response, "body")
    assert response.status_code == 401
    body = json.loads(response.body.decode("utf-8"))
    assert body["errors"][0]["code"] == "unknown_error"


def test_person_add_http_returns_non_2xx_when_envelope_failed(monkeypatch) -> None:
    def _failed_envelope(**_kwargs):
        return {
            "success": False,
            "partial_success": False,
            "action": "failed",
            "record_id": None,
            "warnings": [],
            "skipped_fields": [],
            "errors": [
                {
                    "code": "validation_error",
                    "message": "bad input",
                    "error_type": "ValidationError",
                    "fatal": True,
                    "field": None,
                    "details": {},
                },
            ],
            "meta": {"output_schema_version": "v1"},
        }

    monkeypatch.setattr(modal_people.attio_add_person, "remote", _failed_envelope)

    fn = cast(modal.Function, modal_people.attio_person_add_http)
    response = fn.local(
        modal_people.PersonAddQuery(
            email="a@example.com",
        ),
    )

    assert hasattr(response, "status_code")
    assert hasattr(response, "body")
    assert response.status_code == 400
    body = json.loads(response.body.decode("utf-8"))
    assert body["success"] is False
