# trunk-ignore-all(pyright/reportUntypedFunctionDecorator)
import json
import sys

import modal
import typer
from pydantic import ValidationError

from cli.json_validation import emit_json_payload_validation_telemetry
from src.modal_app import MODAL_APP
from src.parallel.search import SearchQuery

app = typer.Typer(help="Search the web using Parallel API.")


@app.command()
def query(
    objective: str = typer.Argument("", help="What to search for"),
    mode: str = typer.Option(
        "one-shot",
        "--mode",
        "-m",
        help="Search mode: one-shot, agentic, fast",
    ),
    max_results: int = typer.Option(10, "--max", "-n", help="Max results (1-20)"),
    json_input: str | None = typer.Option(
        None,
        "--json",
        help="JSON payload (overrides flags)",
    ),
    parallel_api_key_override: str | None = typer.Option(None, "--parallel-api-key"),
) -> None:
    """Search the web for a given objective."""
    if json_input:
        try:
            q = SearchQuery.model_validate_json(json_input)
            payload = q.model_dump()
        except (ValidationError, json.JSONDecodeError) as e:
            emit_json_payload_validation_telemetry(
                "parallel.search.query",
                e,
                SearchQuery,
                json_input,
            )
            print(f"Error: {e}", file=sys.stderr)
            raise typer.Exit(code=1)
    else:
        if not objective:
            print(
                "Error: objective is required when --json is not used",
                file=sys.stderr,
            )
            raise typer.Exit(code=1)
        payload = {"objective": objective, "mode": mode, "max_results": max_results}

    api_keys = (
        {"parallel_api_key": parallel_api_key_override}
        if parallel_api_key_override
        else {}
    )
    try:
        fn = modal.Function.from_name(MODAL_APP, "parallel_search")
        response = fn.remote(payload=payload, api_keys=api_keys or None)
        out = response.model_dump() if hasattr(response, "model_dump") else response
        print(json.dumps(out, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(code=1)
