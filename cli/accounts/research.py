from __future__ import annotations

import json
import sys

import modal
import typer
from pydantic import ValidationError

from cli.json_validation import emit_json_payload_validation_telemetry
from libs.parsers.normalization import normalize_mapping_payload
from src.accounts.research import EnrichQuery, ResearchQuery
from src.modal_app import MODAL_APP


def _print_json(value: object) -> None:
    out = normalize_mapping_payload(value)
    print(json.dumps(out))


def research_command(
    objective: str = typer.Argument("", help="Research objective"),
    json_input: str | None = typer.Option(
        None, "--json", help="JSON payload (overrides flags)"
    ),
    parallel_api_key_override: str | None = typer.Option(None, "--parallel-api-key"),
) -> None:
    """Run non-mutating research."""
    if json_input:
        try:
            q = ResearchQuery.model_validate_json(json_input)
            payload = q.model_dump()
        except (ValidationError, json.JSONDecodeError) as e:
            emit_json_payload_validation_telemetry(
                "gtm.research.research", e, ResearchQuery, json_input
            )
            print(f"Error: {e}", file=sys.stderr)
            raise typer.Exit(code=1)
    else:
        if not objective:
            print(
                "Error: objective is required when --json is not used", file=sys.stderr
            )
            raise typer.Exit(code=1)
        payload = {"objective": objective}

    api_keys = (
        {"parallel_api_key": parallel_api_key_override}
        if parallel_api_key_override
        else {}
    )
    try:
        fn = modal.Function.from_name(MODAL_APP, "gtm_research")
        response = fn.remote(payload=payload, api_keys=api_keys or None)
        _print_json(response)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise typer.Exit(code=1)


def enrich_command(
    url: str = typer.Argument("", help="URL to enrich"),
    objective: str = typer.Argument("", help="Enrichment objective"),
    json_input: str | None = typer.Option(
        None, "--json", help="JSON payload (overrides flags)"
    ),
    parallel_api_key_override: str | None = typer.Option(None, "--parallel-api-key"),
) -> None:
    """Run non-mutating enrichment."""
    if json_input:
        try:
            q = EnrichQuery.model_validate_json(json_input)
            payload = q.model_dump()
        except (ValidationError, json.JSONDecodeError) as e:
            emit_json_payload_validation_telemetry(
                "gtm.research.enrich", e, EnrichQuery, json_input
            )
            print(f"Error: {e}", file=sys.stderr)
            raise typer.Exit(code=1)
    else:
        if not url or not objective:
            print(
                "Error: url and objective are required when --json is not used",
                file=sys.stderr,
            )
            raise typer.Exit(code=1)
        payload = {"url": url, "objective": objective}

    api_keys = (
        {"parallel_api_key": parallel_api_key_override}
        if parallel_api_key_override
        else {}
    )
    try:
        fn = modal.Function.from_name(MODAL_APP, "gtm_enrich")
        response = fn.remote(payload=payload, api_keys=api_keys or None)
        _print_json(response)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise typer.Exit(code=1)
