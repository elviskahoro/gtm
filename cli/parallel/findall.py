# trunk-ignore-all(pyright/reportUntypedFunctionDecorator)
import json
import sys

import modal
import typer
from pydantic import ValidationError

from cli.json_validation import emit_json_payload_validation_telemetry
from src.modal_app import MODAL_APP
from src.parallel.findall import (
    FindAllCreateQuery,
    FindAllResultQuery,
    FindAllStatusQuery,
)

app = typer.Typer(help="Discover entities using Parallel FindAll API.")


@app.command()
def create(
    objective: str = typer.Argument("", help="Natural language objective"),
    entity_type: str = typer.Argument("", help="Type of entity to find"),
    conditions: str = typer.Argument("[]", help="Match conditions as JSON array"),
    match_limit: int = typer.Option(10, "--limit", "-n", help="Max matches (5-1000)"),
    generator: str = typer.Option(
        "base", "--generator", "-g", help="Generator: base, core, pro, preview"
    ),
    json_input: str | None = typer.Option(
        None, "--json", help="JSON payload (overrides flags)"
    ),
    parallel_api_key_override: str | None = typer.Option(None, "--parallel-api-key"),
) -> None:
    """Start a FindAll entity discovery run."""
    if json_input:
        try:
            q = FindAllCreateQuery.model_validate_json(json_input)
            payload = q.model_dump()
        except (ValidationError, json.JSONDecodeError) as e:
            emit_json_payload_validation_telemetry(
                "parallel.findall.create", e, FindAllCreateQuery, json_input
            )
            print(f"Error: {e}", file=sys.stderr)
            raise typer.Exit(code=1)
    else:
        if not objective or not entity_type:
            print(
                "Error: objective and entity_type are required when --json is not used",
                file=sys.stderr,
            )
            raise typer.Exit(code=1)
        parsed = json.loads(conditions)
        match_conditions = [
            {"name": c["name"], "description": c["description"]} for c in parsed
        ]
        if not match_conditions:
            print(
                "Error: conditions must contain at least one match condition when --json is not used",
                file=sys.stderr,
            )
            raise typer.Exit(code=1)
        payload = {
            "objective": objective,
            "entity_type": entity_type,
            "match_conditions": match_conditions,
            "match_limit": match_limit,
            "generator": generator,
        }

    api_keys = (
        {"parallel_api_key": parallel_api_key_override}
        if parallel_api_key_override
        else {}
    )
    try:
        fn = modal.Function.from_name(MODAL_APP, "parallel_findall_create")
        run = fn.remote(payload=payload, api_keys=api_keys or None)
        out = run.model_dump() if hasattr(run, "model_dump") else run
        print(json.dumps(out, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(code=1)


@app.command()
def result(
    findall_id: str = typer.Argument("", help="FindAll run ID"),
    json_input: str | None = typer.Option(
        None, "--json", help="JSON payload (overrides flags)"
    ),
    parallel_api_key_override: str | None = typer.Option(None, "--parallel-api-key"),
) -> None:
    """Get results from a completed FindAll run."""
    if json_input:
        try:
            q = FindAllResultQuery.model_validate_json(json_input)
            payload = q.model_dump()
        except (ValidationError, json.JSONDecodeError) as e:
            emit_json_payload_validation_telemetry(
                "parallel.findall.result", e, FindAllResultQuery, json_input
            )
            print(f"Error: {e}", file=sys.stderr)
            raise typer.Exit(code=1)
    else:
        if not findall_id:
            print(
                "Error: findall_id is required when --json is not used", file=sys.stderr
            )
            raise typer.Exit(code=1)
        payload = {"findall_id": findall_id}

    api_keys = (
        {"parallel_api_key": parallel_api_key_override}
        if parallel_api_key_override
        else {}
    )
    try:
        fn = modal.Function.from_name(MODAL_APP, "parallel_findall_result")
        res = fn.remote(payload=payload, api_keys=api_keys or None)
        out = res.model_dump() if hasattr(res, "model_dump") else res
        print(json.dumps(out, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(code=1)


@app.command()
def status(
    findall_id: str = typer.Argument("", help="FindAll run ID"),
    json_input: str | None = typer.Option(
        None, "--json", help="JSON payload (overrides flags)"
    ),
    parallel_api_key_override: str | None = typer.Option(None, "--parallel-api-key"),
) -> None:
    """Check the status of a FindAll run."""
    if json_input:
        try:
            q = FindAllStatusQuery.model_validate_json(json_input)
            payload = q.model_dump()
        except (ValidationError, json.JSONDecodeError) as e:
            emit_json_payload_validation_telemetry(
                "parallel.findall.status", e, FindAllStatusQuery, json_input
            )
            print(f"Error: {e}", file=sys.stderr)
            raise typer.Exit(code=1)
    else:
        if not findall_id:
            print(
                "Error: findall_id is required when --json is not used", file=sys.stderr
            )
            raise typer.Exit(code=1)
        payload = {"findall_id": findall_id}

    api_keys = (
        {"parallel_api_key": parallel_api_key_override}
        if parallel_api_key_override
        else {}
    )
    try:
        fn = modal.Function.from_name(MODAL_APP, "parallel_findall_status")
        run = fn.remote(payload=payload, api_keys=api_keys or None)
        out = run.model_dump() if hasattr(run, "model_dump") else run
        print(json.dumps(out, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(code=1)
