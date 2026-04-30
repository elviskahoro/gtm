# trunk-ignore-all(pyright/reportUntypedFunctionDecorator)
import json
import sys

import modal
import typer
from pydantic import ValidationError

from cli.json_validation import emit_json_payload_validation_telemetry
from src.modal_app import MODAL_APP
from src.parallel.extract import ExtractExcerptsQuery, ExtractFullContentQuery

app = typer.Typer(help="Extract content from URLs using Parallel API.")


@app.command()
def excerpts(
    url: str = typer.Argument("", help="URL to extract content from"),
    objective: str = typer.Argument("", help="Focus extraction on this objective"),
    json_input: str | None = typer.Option(
        None, "--json", help="JSON payload (overrides flags)"
    ),
    parallel_api_key_override: str | None = typer.Option(None, "--parallel-api-key"),
) -> None:
    """Extract focused excerpts from a URL matching an objective."""
    if json_input:
        try:
            q = ExtractExcerptsQuery.model_validate_json(json_input)
            payload = q.model_dump()
        except (ValidationError, json.JSONDecodeError) as e:
            emit_json_payload_validation_telemetry(
                "parallel.extract.excerpts", e, ExtractExcerptsQuery, json_input
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
        fn = modal.Function.from_name(MODAL_APP, "parallel_extract_excerpts")
        response = fn.remote(payload=payload, api_keys=api_keys or None)
        out = response.model_dump() if hasattr(response, "model_dump") else response
        print(json.dumps(out, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(code=1)


@app.command()
def full(
    url: str = typer.Argument("", help="URL to extract content from"),
    json_input: str | None = typer.Option(
        None, "--json", help="JSON payload (overrides flags)"
    ),
    parallel_api_key_override: str | None = typer.Option(None, "--parallel-api-key"),
) -> None:
    """Extract full content from a URL."""
    if json_input:
        try:
            q = ExtractFullContentQuery.model_validate_json(json_input)
            payload = q.model_dump()
        except (ValidationError, json.JSONDecodeError) as e:
            emit_json_payload_validation_telemetry(
                "parallel.extract.full", e, ExtractFullContentQuery, json_input
            )
            print(f"Error: {e}", file=sys.stderr)
            raise typer.Exit(code=1)
    else:
        if not url:
            print("Error: url is required when --json is not used", file=sys.stderr)
            raise typer.Exit(code=1)
        payload = {"url": url}

    api_keys = (
        {"parallel_api_key": parallel_api_key_override}
        if parallel_api_key_override
        else {}
    )
    try:
        fn = modal.Function.from_name(MODAL_APP, "parallel_extract_full_content")
        response = fn.remote(payload=payload, api_keys=api_keys or None)
        out = response.model_dump() if hasattr(response, "model_dump") else response
        print(json.dumps(out, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(code=1)
