# trunk-ignore-all(pyright/reportUntypedFunctionDecorator)
import json
import sys

import modal
import typer
from pydantic import ValidationError

from cli.json_encoder import dumps_with_datetime
from cli.json_validation import emit_json_payload_validation_telemetry
from src.apollo.people import PersonEnrichQuery, PersonSearchQuery
from src.modal_app import MODAL_APP

app = typer.Typer(help="People enrichment and search via Apollo.")


@app.command()
def enrich(
    email: str | None = typer.Option(None, "--email", "-e", help="Email address"),
    name: str | None = typer.Option(None, "--name", "-n", help="Full name"),
    first_name: str | None = typer.Option(None, "--first-name", help="First name"),
    last_name: str | None = typer.Option(None, "--last-name", help="Last name"),
    domain: str | None = typer.Option(None, "--domain", "-d", help="Company domain"),
    linkedin_url: str | None = typer.Option(
        None,
        "--linkedin",
        "-l",
        help="LinkedIn profile URL",
    ),
    organization_name: str | None = typer.Option(
        None,
        "--org",
        help="Organization name",
    ),
    json_input: str | None = typer.Option(
        None,
        "--json",
        help="JSON payload (overrides flags)",
    ),
    apollo_api_key_override: str | None = typer.Option(None, "--apollo-api-key"),
) -> None:
    """Enrich a person's data using Apollo."""
    if json_input:
        try:
            q = PersonEnrichQuery.model_validate_json(json_input)
            payload = q.model_dump()
        except (ValidationError, json.JSONDecodeError) as e:
            emit_json_payload_validation_telemetry(
                "apollo.people.enrich",
                e,
                PersonEnrichQuery,
                json_input,
            )
            print(f"Error: {e}", file=sys.stderr)
            raise typer.Exit(code=1)
    else:
        if not any([email, name, first_name, last_name, domain, linkedin_url]):
            print(
                "Error: at least one identifier is required (--email, --name, --domain, --linkedin)",
                file=sys.stderr,
            )
            raise typer.Exit(code=1)
        payload = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "name": name,
            "domain": domain,
            "linkedin_url": linkedin_url,
            "organization_name": organization_name,
        }

    api_keys = (
        {"apollo_api_key": apollo_api_key_override} if apollo_api_key_override else {}
    )
    try:
        fn = modal.Function.from_name(MODAL_APP, "apollo_enrich_person")
        response = fn.remote(payload=payload, api_keys=api_keys or None)
        out = response.model_dump() if hasattr(response, "model_dump") else response
        print(dumps_with_datetime(out, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(code=1)


@app.command()
def search(
    keywords: str = typer.Argument("", help="Keyword search"),
    titles: list[str] | None = typer.Option(
        None,
        "--title",
        "-t",
        help="Job titles to filter by (repeatable)",
    ),
    seniorities: list[str] | None = typer.Option(
        None,
        "--seniority",
        "-s",
        help="Seniority levels (repeatable)",
    ),
    locations: list[str] | None = typer.Option(
        None,
        "--location",
        help="Person locations (repeatable)",
    ),
    domains: list[str] | None = typer.Option(
        None,
        "--domain",
        "-d",
        help="Company domains (repeatable)",
    ),
    page: int = typer.Option(1, "--page", "-p", help="Page number"),
    per_page: int = typer.Option(10, "--per-page", "-n", help="Results per page"),
    json_input: str | None = typer.Option(
        None,
        "--json",
        help="JSON payload (overrides flags)",
    ),
    apollo_api_key_override: str | None = typer.Option(None, "--apollo-api-key"),
) -> None:
    """Search for people in Apollo's database."""
    if json_input:
        try:
            q = PersonSearchQuery.model_validate_json(json_input)
            payload = q.model_dump()
        except (ValidationError, json.JSONDecodeError) as e:
            emit_json_payload_validation_telemetry(
                "apollo.people.search",
                e,
                PersonSearchQuery,
                json_input,
            )
            print(f"Error: {e}", file=sys.stderr)
            raise typer.Exit(code=1)
    else:
        payload = {
            "q_keywords": keywords or None,
            "person_titles": titles or [],
            "person_seniorities": seniorities or [],
            "person_locations": locations or [],
            "q_organization_domains_list": domains or [],
            "page": page,
            "per_page": per_page,
        }

    api_keys = (
        {"apollo_api_key": apollo_api_key_override} if apollo_api_key_override else {}
    )
    try:
        fn = modal.Function.from_name(MODAL_APP, "apollo_search_people")
        response = fn.remote(payload=payload, api_keys=api_keys or None)
        out = response.model_dump() if hasattr(response, "model_dump") else response
        print(dumps_with_datetime(out, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(code=1)
