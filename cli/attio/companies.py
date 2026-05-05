# trunk-ignore-all(pyright/reportUntypedFunctionDecorator)
import json
import sys

import modal
import typer
from pydantic import ValidationError

from cli.json_validation import emit_json_payload_validation_telemetry
from src.attio.companies import (
    CompanyAddQuery,
    CompanyCreateAttributeQuery,
    CompanySearchQuery,
    CompanyUpdateQuery,
)
from src.modal_app import MODAL_APP

app = typer.Typer(help="Manage company records in Attio.")


@app.command()
def add(
    name: str = typer.Argument("", help="Company name (required when --json not used)"),
    domain: str | None = typer.Option(None, "--domain", help="Company domain"),
    description: str | None = typer.Option(
        None,
        "--description",
        help="Company description",
    ),
    json_input: str | None = typer.Option(
        None,
        "--json",
        help="JSON payload (overrides flags)",
    ),
    attio_api_key_override: str | None = typer.Option(None, "--attio-api-key"),
) -> None:
    """Add a company to Attio."""
    if json_input:
        try:
            query = CompanyAddQuery.model_validate_json(json_input)
            payload = query.model_dump()

        except (ValidationError, json.JSONDecodeError) as e:
            emit_json_payload_validation_telemetry(
                "attio.companies.add",
                e,
                CompanyAddQuery,
                json_input,
            )
            print(f"Error: {e}", file=sys.stderr)
            raise typer.Exit(code=1)

    else:
        if not name:
            print("Error: name is required when --json is not used", file=sys.stderr)
            raise typer.Exit(code=1)

        payload = {"name": name, "domain": domain, "description": description}

    api_keys = (
        {"attio_api_key": attio_api_key_override} if attio_api_key_override else {}
    )
    try:
        fn = modal.Function.from_name(MODAL_APP, "attio_add_company")
        result = fn.remote(payload=payload, api_keys=api_keys or None)  # pyright: ignore[reportFunctionMemberAccess]
        out = (
            result.model_dump(mode="json") if hasattr(result, "model_dump") else result
        )
        print(json.dumps(out, indent=2))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(code=1)


@app.command()
def search(
    name: str | None = typer.Option(None, "--name", help="Search by company name"),
    domain: str | None = typer.Option(None, "--domain", help="Search by exact domain"),
    limit: int = typer.Option(25, "--limit", help="Max results to return"),
    json_input: str | None = typer.Option(
        None,
        "--json",
        help="JSON payload (overrides flags)",
    ),
    attio_api_key_override: str | None = typer.Option(None, "--attio-api-key"),
) -> None:
    """Search for companies in Attio."""
    if json_input:
        try:
            query = CompanySearchQuery.model_validate_json(json_input)
            payload = query.model_dump()
        except (ValidationError, json.JSONDecodeError) as e:
            emit_json_payload_validation_telemetry(
                "attio.companies.search",
                e,
                CompanySearchQuery,
                json_input,
            )
            print(f"Error: {e}", file=sys.stderr)
            raise typer.Exit(code=1)
    else:
        if not any([name, domain]):
            print("Error: provide at least one search option.", file=sys.stderr)
            raise typer.Exit(code=1)
        payload = {"name": name, "domain": domain, "limit": limit}

    api_keys = (
        {"attio_api_key": attio_api_key_override} if attio_api_key_override else {}
    )
    try:
        fn = modal.Function.from_name(MODAL_APP, "attio_search_companies")
        results = fn.remote(payload=payload, api_keys=api_keys or None)  # pyright: ignore[reportFunctionMemberAccess]
        out = [
            r.model_dump(mode="json") if hasattr(r, "model_dump") else r
            for r in results
        ]
        print(json.dumps(out, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(code=1)


@app.command()
def update(
    domain: str | None = typer.Option(
        None,
        "--domain",
        help="Domain to look up company",
    ),
    record_id: str | None = typer.Option(None, "--id", help="Attio record ID"),
    name: str | None = typer.Option(None, "--name", help="New company name"),
    description: str | None = typer.Option(
        None,
        "--description",
        help="New description",
    ),
    json_input: str | None = typer.Option(
        None,
        "--json",
        help="JSON payload (overrides flags)",
    ),
    attio_api_key_override: str | None = typer.Option(None, "--attio-api-key"),
) -> None:
    """Update an existing company in Attio."""
    if json_input:
        try:
            query = CompanyUpdateQuery.model_validate_json(json_input)
            payload = query.model_dump()
        except (ValidationError, json.JSONDecodeError) as e:
            emit_json_payload_validation_telemetry(
                "attio.companies.update",
                e,
                CompanyUpdateQuery,
                json_input,
            )
            print(f"Error: {e}", file=sys.stderr)
            raise typer.Exit(code=1)
    else:
        if not domain and not record_id:
            print(
                "Error: provide --domain or --id to identify the company.",
                file=sys.stderr,
            )
            raise typer.Exit(code=1)
        payload = {
            "record_id": record_id,
            "domain": domain,
            "name": name,
            "description": description,
        }

    api_keys = (
        {"attio_api_key": attio_api_key_override} if attio_api_key_override else {}
    )
    try:
        fn = modal.Function.from_name(MODAL_APP, "attio_update_company")
        result = fn.remote(payload=payload, api_keys=api_keys or None)  # pyright: ignore[reportFunctionMemberAccess]
        out = (
            result.model_dump(mode="json") if hasattr(result, "model_dump") else result
        )
        print(json.dumps(out, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(code=1)


@app.command("create-attribute-type")
def create_attribute_type(
    title: str | None = typer.Option(None, "--title"),
    api_slug: str | None = typer.Option(None, "--api-slug"),
    attribute_type: str = typer.Option("select", "--type"),
    description: str = typer.Option("", "--description"),
    is_multiselect: bool = typer.Option(True, "--is-multiselect/--no-is-multiselect"),
    is_required: bool = typer.Option(False, "--is-required/--no-is-required"),
    is_unique: bool = typer.Option(False, "--is-unique/--no-is-unique"),
    apply: bool = typer.Option(False, "--apply"),
    json_input: str | None = typer.Option(
        None,
        "--json",
        help="JSON payload (overrides flags)",
    ),
    attio_api_key_override: str | None = typer.Option(None, "--attio-api-key"),
) -> None:
    """Create an attribute on companies."""
    if json_input:
        try:
            query = CompanyCreateAttributeQuery.model_validate_json(json_input)
            payload = query.model_dump()
        except (ValidationError, json.JSONDecodeError) as e:
            emit_json_payload_validation_telemetry(
                "attio.companies.create-attribute-type",
                e,
                CompanyCreateAttributeQuery,
                json_input,
            )
            print(f"Error: {e}", file=sys.stderr)
            raise typer.Exit(code=1)
    else:
        if not title or not api_slug:
            print(
                "Error: --title and --api-slug are required when --json is not used",
                file=sys.stderr,
            )
            raise typer.Exit(code=1)
        payload = {
            "title": title,
            "api_slug": api_slug,
            "attribute_type": attribute_type,
            "description": description,
            "is_multiselect": is_multiselect,
            "is_required": is_required,
            "is_unique": is_unique,
            "apply": apply,
        }

    api_keys = (
        {"attio_api_key": attio_api_key_override} if attio_api_key_override else {}
    )
    try:
        fn = modal.Function.from_name(MODAL_APP, "attio_create_companies_attribute")
        result = fn.remote(payload=payload, api_keys=api_keys or None)  # pyright: ignore[reportFunctionMemberAccess]
        out = (
            result.model_dump(mode="json") if hasattr(result, "model_dump") else result
        )
        print(json.dumps(out, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(code=1)
