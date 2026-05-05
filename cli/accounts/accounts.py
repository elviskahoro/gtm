from __future__ import annotations

import json
import sys

import modal
import typer
from pydantic import ValidationError

from cli.json_validation import emit_json_payload_validation_telemetry
from src.accounts.accounts import MapAccountHierarchyQuery
from src.modal_app import MODAL_APP


def map_account_hierarchy_command(
    account: str = typer.Argument("", help="Account domain or name"),
    json_input: str | None = typer.Option(
        None,
        "--json",
        help="JSON payload (overrides flags)",
    ),
    parallel_api_key_override: str | None = typer.Option(None, "--parallel-api-key"),
) -> None:
    """Run non-mutating account hierarchy mapping."""
    if json_input:
        try:
            q = MapAccountHierarchyQuery.model_validate_json(json_input)
            payload = q.model_dump()
        except (ValidationError, json.JSONDecodeError) as e:
            emit_json_payload_validation_telemetry(
                "gtm.accounts.map-account-hierarchy",
                e,
                MapAccountHierarchyQuery,
                json_input,
            )
            print(f"Error: {e}", file=sys.stderr)
            raise typer.Exit(code=1)
    else:
        if not account:
            print("Error: account is required when --json is not used", file=sys.stderr)
            raise typer.Exit(code=1)
        payload = {"account": account}

    api_keys = (
        {"parallel_api_key": parallel_api_key_override}
        if parallel_api_key_override
        else {}
    )
    try:
        fn = modal.Function.from_name(MODAL_APP, "gtm_map_account_hierarchy")
        response = fn.remote(payload=payload, api_keys=api_keys or None)
        out = response.model_dump() if hasattr(response, "model_dump") else response
        print(json.dumps(out))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise typer.Exit(code=1)
