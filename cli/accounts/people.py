from __future__ import annotations

import json
import sys

import modal
import typer
from pydantic import ValidationError

from cli.json_validation import emit_json_payload_validation_telemetry
from src.accounts.people import FindPeopleQuery
from src.modal_app import MODAL_APP


def find_people_command(
    query: str = typer.Argument("", help="Search query for people"),
    json_input: str | None = typer.Option(
        None, "--json", help="JSON payload (overrides flags)"
    ),
    parallel_api_key_override: str | None = typer.Option(None, "--parallel-api-key"),
) -> None:
    """Run non-mutating people discovery."""
    if json_input:
        try:
            q = FindPeopleQuery.model_validate_json(json_input)
            payload = q.model_dump()
        except (ValidationError, json.JSONDecodeError) as e:
            emit_json_payload_validation_telemetry(
                "gtm.people.find", e, FindPeopleQuery, json_input
            )
            print(f"Error: {e}", file=sys.stderr)
            raise typer.Exit(code=1)
    else:
        if not query:
            print("Error: query is required when --json is not used", file=sys.stderr)
            raise typer.Exit(code=1)
        payload = {"query": query}

    api_keys = (
        {"parallel_api_key": parallel_api_key_override}
        if parallel_api_key_override
        else {}
    )
    try:
        fn = modal.Function.from_name(MODAL_APP, "gtm_find_people")
        response = fn.remote(payload=payload, api_keys=api_keys or None)
        out = response.model_dump() if hasattr(response, "model_dump") else response
        print(json.dumps(out))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise typer.Exit(code=1)
