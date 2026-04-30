# trunk-ignore-all(pyright/reportUntypedFunctionDecorator)
import json
import sys

import modal
import typer
from pydantic import ValidationError

from cli.json_encoder import dumps_with_datetime
from cli.json_validation import emit_json_payload_validation_telemetry
from src.apollo.organizations import OrgEnrichQuery, OrgSearchQuery
from src.modal_app import MODAL_APP

app = typer.Typer(help="Organization enrichment and search via Apollo.")


@app.command()
def enrich(
    domain: str = typer.Argument("", help="Company domain (e.g. apollo.io)"),
    json_input: str | None = typer.Option(
        None, "--json", help="JSON payload (overrides flags)"
    ),
    apollo_api_key_override: str | None = typer.Option(None, "--apollo-api-key"),
) -> None:
    """Enrich an organization's data by domain."""
    if json_input:
        try:
            q = OrgEnrichQuery.model_validate_json(json_input)
            payload = q.model_dump()
        except (ValidationError, json.JSONDecodeError) as e:
            emit_json_payload_validation_telemetry(
                "apollo.organizations.enrich", e, OrgEnrichQuery, json_input
            )
            print(f"Error: {e}", file=sys.stderr)
            raise typer.Exit(code=1)
    else:
        if not domain:
            print("Error: domain is required", file=sys.stderr)
            raise typer.Exit(code=1)
        payload = {"domain": domain}

    api_keys = (
        {"apollo_api_key": apollo_api_key_override} if apollo_api_key_override else {}
    )
    try:
        fn = modal.Function.from_name(MODAL_APP, "apollo_enrich_organization")
        response = fn.remote(payload=payload, api_keys=api_keys or None)
        out = response.model_dump() if hasattr(response, "model_dump") else response
        print(dumps_with_datetime(out, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(code=1)


@app.command()
def search(
    keywords: str = typer.Argument("", help="Organization name search"),
    locations: list[str] | None = typer.Option(
        None, "--location", help="HQ locations (repeatable)"
    ),
    employees: list[str] | None = typer.Option(
        None,
        "--employees",
        help="Employee count ranges like '1,10' or '501,1000' (repeatable)",
    ),
    page: int = typer.Option(1, "--page", "-p", help="Page number"),
    per_page: int = typer.Option(10, "--per-page", "-n", help="Results per page"),
    json_input: str | None = typer.Option(
        None, "--json", help="JSON payload (overrides flags)"
    ),
    apollo_api_key_override: str | None = typer.Option(None, "--apollo-api-key"),
) -> None:
    """Search for organizations in Apollo's database."""
    if json_input:
        try:
            q = OrgSearchQuery.model_validate_json(json_input)
            payload = q.model_dump()
        except (ValidationError, json.JSONDecodeError) as e:
            emit_json_payload_validation_telemetry(
                "apollo.organizations.search", e, OrgSearchQuery, json_input
            )
            print(f"Error: {e}", file=sys.stderr)
            raise typer.Exit(code=1)
    else:
        payload = {
            "q_keywords": keywords or None,
            "organization_locations": locations or [],
            "organization_num_employees_ranges": employees or [],
            "page": page,
            "per_page": per_page,
        }

    api_keys = (
        {"apollo_api_key": apollo_api_key_override} if apollo_api_key_override else {}
    )
    try:
        fn = modal.Function.from_name(MODAL_APP, "apollo_search_organizations")
        response = fn.remote(payload=payload, api_keys=api_keys or None)
        out = response.model_dump() if hasattr(response, "model_dump") else response
        print(dumps_with_datetime(out, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(code=1)
