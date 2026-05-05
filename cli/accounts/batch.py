from __future__ import annotations

import json
import sys
from typing import Any

import modal
import typer
from pydantic import ValidationError

from cli.json_validation import emit_json_payload_validation_telemetry
from libs.parsers.normalization import normalize_mapping_payload
from src.accounts.batch import BatchAddCompaniesQuery, BatchAddPeopleQuery
from src.modal_app import MODAL_APP


def _parse_records(records: str) -> list[dict[str, Any]]:
    parsed = json.loads(records)
    if not isinstance(parsed, list):
        raise ValueError("--records must decode to a JSON array")
    if not parsed:
        raise ValueError("records must not be empty")
    if any(not isinstance(item, dict) for item in parsed):
        raise ValueError("records must contain JSON objects")
    return parsed


def _batch_exit_code(response: object, apply: bool) -> int:
    if not apply:
        return 0
    payload = normalize_mapping_payload(response)
    requested = int(payload.get("requested", 0))
    created = int(payload.get("created", 0))
    if requested > 0 and created == 0:
        return 1
    return 0


def batch_add_people_command(
    records: str = typer.Option("", "--records", help="JSON array of person records"),
    apply: bool = typer.Option(False, "--apply", help="Perform writes to Attio"),
    json_input: str | None = typer.Option(
        None,
        "--json",
        help="JSON payload (overrides flags)",
    ),
    attio_api_key_override: str | None = typer.Option(None, "--attio-api-key"),
) -> None:
    """Batch add people with explicit preview/apply behavior."""
    if json_input:
        try:
            q = BatchAddPeopleQuery.model_validate_json(json_input)
            payload = q.model_dump()
            apply = q.apply
        except (ValidationError, json.JSONDecodeError) as e:
            emit_json_payload_validation_telemetry(
                "gtm.batch.add-people",
                e,
                BatchAddPeopleQuery,
                json_input,
            )
            print(f"Error: {e}", file=sys.stderr)
            raise typer.Exit(code=1)
    else:
        if not records:
            print(
                "Error: --records is required when --json is not used",
                file=sys.stderr,
            )
            raise typer.Exit(code=1)
        try:
            parsed = _parse_records(records)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            raise typer.Exit(code=1)
        payload = {"records": parsed, "apply": apply}

    api_keys = (
        {"attio_api_key": attio_api_key_override} if attio_api_key_override else {}
    )
    try:
        fn = modal.Function.from_name(MODAL_APP, "gtm_batch_add_people")
        response = fn.remote(payload=payload, api_keys=api_keys or None)
        out = normalize_mapping_payload(response)
        print(json.dumps(out))
        if _batch_exit_code(response, apply=apply) != 0:
            raise typer.Exit(code=1)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise typer.Exit(code=1)


def batch_add_companies_command(
    records: str = typer.Option("", "--records", help="JSON array of company records"),
    apply: bool = typer.Option(False, "--apply", help="Perform writes to Attio"),
    json_input: str | None = typer.Option(
        None,
        "--json",
        help="JSON payload (overrides flags)",
    ),
    attio_api_key_override: str | None = typer.Option(None, "--attio-api-key"),
) -> None:
    """Batch add companies with explicit preview/apply behavior."""
    if json_input:
        try:
            q = BatchAddCompaniesQuery.model_validate_json(json_input)
            payload = q.model_dump()
            apply = q.apply
        except (ValidationError, json.JSONDecodeError) as e:
            emit_json_payload_validation_telemetry(
                "gtm.batch.add-companies",
                e,
                BatchAddCompaniesQuery,
                json_input,
            )
            print(f"Error: {e}", file=sys.stderr)
            raise typer.Exit(code=1)
    else:
        if not records:
            print(
                "Error: --records is required when --json is not used",
                file=sys.stderr,
            )
            raise typer.Exit(code=1)
        try:
            parsed = _parse_records(records)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            raise typer.Exit(code=1)
        payload = {"records": parsed, "apply": apply}

    api_keys = (
        {"attio_api_key": attio_api_key_override} if attio_api_key_override else {}
    )
    try:
        fn = modal.Function.from_name(MODAL_APP, "gtm_batch_add_companies")
        response = fn.remote(payload=payload, api_keys=api_keys or None)
        out = normalize_mapping_payload(response)
        print(json.dumps(out))
        if _batch_exit_code(response, apply=apply) != 0:
            raise typer.Exit(code=1)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise typer.Exit(code=1)
