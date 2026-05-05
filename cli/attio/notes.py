# trunk-ignore-all(pyright/reportUntypedFunctionDecorator)
import json
import sys

import modal
import typer
from pydantic import ValidationError

from cli.json_validation import emit_json_payload_validation_telemetry
from src.attio.notes import NoteAddQuery, NoteUpdateQuery
from src.modal_app import MODAL_APP

app = typer.Typer(help="Manage notes in Attio.")


@app.command()
def add(
    title: str = typer.Argument("", help="Note title (required when --json not used)"),
    content: str = typer.Argument("", help="Note content"),
    parent_object: str = typer.Option(
        "",
        "--object",
        help="Parent object: 'people' or 'companies'",
    ),
    record_id: str | None = typer.Option(None, "--record-id", help="Parent record ID"),
    email: str | None = typer.Option(None, "--email", help="Look up person by email"),
    domain: str | None = typer.Option(
        None,
        "--domain",
        help="Look up company by domain",
    ),
    format: str = typer.Option(
        "plaintext",
        "--format",
        help="Content format: plaintext or markdown",
    ),
    json_input: str | None = typer.Option(
        None,
        "--json",
        help="JSON payload (overrides flags)",
    ),
    attio_api_key_override: str | None = typer.Option(None, "--attio-api-key"),
) -> None:
    """Add a note to a person or company in Attio."""
    if json_input:
        try:
            query = NoteAddQuery.model_validate_json(json_input)
            payload = query.model_dump()
        except (ValidationError, json.JSONDecodeError) as e:
            emit_json_payload_validation_telemetry(
                "attio.notes.add",
                e,
                NoteAddQuery,
                json_input,
            )
            print(f"Error: {e}", file=sys.stderr)
            raise typer.Exit(code=1)
    else:
        if not title or not parent_object:
            print(
                "Error: title and --object are required when --json is not used",
                file=sys.stderr,
            )
            raise typer.Exit(code=1)
        payload = {
            "title": title,
            "content": content,
            "parent_object": parent_object,
            "record_id": record_id,
            "email": email,
            "domain": domain,
            "format": format,
        }

    api_keys = (
        {"attio_api_key": attio_api_key_override} if attio_api_key_override else {}
    )
    try:
        fn = modal.Function.from_name(MODAL_APP, "attio_add_note")
        result = fn.remote(payload=payload, api_keys=api_keys or None)
        out = result.model_dump() if hasattr(result, "model_dump") else result
        print(json.dumps(out, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(code=1)


@app.command()
def update(
    note_id: str = typer.Argument("", help="ID of the note to update"),
    title: str | None = typer.Option(None, "--title", help="New title"),
    content: str | None = typer.Option(None, "--content", help="New content"),
    format: str = typer.Option(
        "plaintext",
        "--format",
        help="Content format: plaintext or markdown",
    ),
    json_input: str | None = typer.Option(
        None,
        "--json",
        help="JSON payload (overrides flags)",
    ),
    attio_api_key_override: str | None = typer.Option(None, "--attio-api-key"),
) -> None:
    """Update an existing note in Attio (replaces via delete + create)."""
    if json_input:
        try:
            query = NoteUpdateQuery.model_validate_json(json_input)
            payload = query.model_dump()
        except (ValidationError, json.JSONDecodeError) as e:
            emit_json_payload_validation_telemetry(
                "attio.notes.update",
                e,
                NoteUpdateQuery,
                json_input,
            )
            print(f"Error: {e}", file=sys.stderr)
            raise typer.Exit(code=1)
    else:
        if not note_id:
            print("Error: note_id is required when --json is not used", file=sys.stderr)
            raise typer.Exit(code=1)
        payload = {
            "note_id": note_id,
            "title": title,
            "content": content,
            "format": format,
        }

    api_keys = (
        {"attio_api_key": attio_api_key_override} if attio_api_key_override else {}
    )
    try:
        fn = modal.Function.from_name(MODAL_APP, "attio_update_note")
        result = fn.remote(payload=payload, api_keys=api_keys or None)
        out = result.model_dump() if hasattr(result, "model_dump") else result
        print(json.dumps(out, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(code=1)
