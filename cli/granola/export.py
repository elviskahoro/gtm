from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Literal

import typer
from pydantic import ValidationError

from cli.json_validation import emit_json_payload_validation_telemetry
from libs.granola.errors import GranolaError
from libs.granola.models import ExportCliJsonPayload, ExportRunOptions
from src.granola.export import run_export


def export_command(
    source: Literal["local", "api", "hybrid"] = typer.Option(
        "hybrid",
        "--source",
        help="Export source strategy",
    ),
    output: Path = typer.Option(
        Path("/Users/elvis/Documents/elviskahoro/zotero/zotero-granola"),
        "--output",
        help="Output root",
    ),
    since: str | None = typer.Option(
        None,
        "--since",
        help="Optional ISO timestamp filter",
    ),
    debug: bool = typer.Option(False, "--debug", help="Print debug output"),
    json_input: str | None = typer.Option(
        None,
        "--json",
        help="JSON payload (overrides flags)",
    ),
) -> None:
    if json_input:
        try:
            q = ExportCliJsonPayload.model_validate_json(json_input)
        except (ValidationError, json.JSONDecodeError) as e:
            emit_json_payload_validation_telemetry(
                "granola.export",
                e,
                ExportCliJsonPayload,
                json_input,
            )
            print(f"Error: {e}", file=sys.stderr)
            raise typer.Exit(code=1)
        if q.source is not None:
            source = q.source
        if q.output is not None:
            output = Path(q.output)
        if q.since is not None:
            since = q.since
        if q.debug is not None:
            debug = q.debug

    api_key = os.environ.get("GRANOLA_API_KEY", "").strip() or None

    if source == "api" and not api_key:
        print("Error: GRANOLA_API_KEY environment variable not set", file=sys.stderr)
        raise typer.Exit(code=1)

    since_dt = dt.datetime.fromisoformat(since) if since else None
    options = ExportRunOptions(
        source=source,
        output_root=output,
        since=since_dt,
        debug=debug,
        api_key=api_key,
    )

    try:
        result = run_export(options)
    except GranolaError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise typer.Exit(code=1)
    except ValueError as exc:
        print(f"Error: invalid --since value: {exc}", file=sys.stderr)
        raise typer.Exit(code=1)

    print(json.dumps(result.model_dump(mode="json")))
