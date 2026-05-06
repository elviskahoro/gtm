# trunk-ignore-all(pyright/reportUntypedFunctionDecorator)
from __future__ import annotations

import json
import os
from typing import Annotated, Any

import modal
import typer
from pydantic import ValidationError

from cli.attio.preflight import run_people_preflight
from cli.json_validation import emit_json_payload_validation_telemetry
from libs.attio.contracts import ReliabilityEnvelope
from libs.attio.errors import ConnectivityError
from libs.attio.people import error_envelope
from src.attio.people import (
    PersonAddQuery,
    PersonSearchQuery,
    PersonUpdateQuery,
    PersonUpsertQuery,
)
from src.modal_app import MODAL_APP

app = typer.Typer(help="Manage people records in Attio.")

DEFAULT_REMOTE_TIMEOUT_SECONDS = 120


def _remote_timeout_seconds() -> int:
    try:
        value = os.environ.get("MODAL_REMOTE_TIMEOUT_SECONDS", "")
        if value:
            timeout = int(value)
            if timeout > 0:
                return timeout
    except (ValueError, TypeError):
        pass
    return DEFAULT_REMOTE_TIMEOUT_SECONDS


def _print_envelope_and_exit(envelope: ReliabilityEnvelope) -> None:
    print(json.dumps(envelope.model_dump(), indent=2))
    if envelope.success or envelope.partial_success:
        return
    raise typer.Exit(code=1)


def _envelope_from_remote_result(result) -> ReliabilityEnvelope:
    if hasattr(result, "model_dump"):
        payload = result.model_dump()
    else:
        payload = result

    if isinstance(payload, list):
        return ReliabilityEnvelope(
            success=True,
            partial_success=False,
            action="searched",
            record_id=None,
            warnings=[],
            skipped_fields=[],
            errors=[],
            meta={
                "output_schema_version": "v1",
                "results": payload,
                "count": len(payload),
            },
        )

    return ReliabilityEnvelope.model_validate(payload)


def _invoke_people_fn(
    function_name: str,
    payload: dict[str, Any],
    *,
    api_keys: dict[str, str] | None = None,
    no_connectivity_probe: bool,
    strict: bool,
    modal_sync: str = "check",
) -> None:
    parity_meta: dict[str, Any] = {}
    try:
        env_payload, preflight_warnings, parity_meta = run_people_preflight(
            connectivity_probe=not no_connectivity_probe,
            modal_app=MODAL_APP,
            function_name=function_name,
            modal_sync=modal_sync,
        )
        os.environ.update(env_payload)

        effective_keys = api_keys or {}
        if not effective_keys and "ATTIO_API_KEY" in env_payload:
            effective_keys = {"attio_api_key": env_payload["ATTIO_API_KEY"]}

        fn = modal.Function.from_name(
            MODAL_APP,
            function_name,
        )  # pyrefly: ignore[invalid-param-spec]
        call = fn.spawn(
            payload=payload,
            api_keys=effective_keys or None,
        )  # pyrefly: ignore[invalid-param-spec]  # pyright: ignore[reportFunctionMemberAccess,reportUnknownMemberType]
        timeout = _remote_timeout_seconds()
        try:
            result = call.get(timeout=timeout)
        except modal.exception.TimeoutError as exc:
            raise ConnectivityError(
                f"Modal function '{function_name}' did not return within "
                f"{timeout}s. The container may be failing to start "
                f"(check `modal app logs {MODAL_APP}`).",
            ) from exc
        envelope = _envelope_from_remote_result(result)
        envelope.warnings = [*preflight_warnings, *envelope.warnings]
        if parity_meta:
            envelope.meta["deployment_parity"] = parity_meta
        _print_envelope_and_exit(envelope)
    except Exception as exc:
        envelope = error_envelope(exc, strict=strict)
        if parity_meta:
            envelope.meta["deployment_parity"] = parity_meta
        _print_envelope_and_exit(envelope)


@app.command()
def add(
    email: str = typer.Argument(
        "",
        help="Email address (required when --json not used)",
    ),
    add_email: Annotated[
        list[str],
        typer.Option(
            "--add-email",
            help="Additional email for this person (repeat for multiple).",
        ),
    ] = [],
    first_name: str | None = typer.Option(None, "--first-name", help="First name"),
    last_name: str | None = typer.Option(None, "--last-name", help="Last name"),
    phone: str | None = typer.Option(None, "--phone", help="Phone number"),
    linkedin: str | None = typer.Option(
        None,
        "--linkedin",
        help="LinkedIn profile URL",
    ),
    location: str | None = typer.Option(None, "--location", help="Primary location"),
    company_domain: str | None = typer.Option(None, "--company", help="Company domain"),
    notes: str | None = typer.Option(None, "--notes", help="Intake notes"),
    strict: bool = typer.Option(
        False,
        "--strict",
        help="Fail fast on optional-field mismatches",
    ),
    location_mode: str = typer.Option(
        "city",
        "--location-mode",
        help="Location normalization mode: city|raw",
    ),
    no_connectivity_probe: bool = typer.Option(
        False,
        "--no-connectivity-probe",
        help="Skip Modal connectivity preflight",
    ),
    modal_sync: str = typer.Option(
        "check",
        "--modal-sync",
        help="Modal sync strategy for mutation commands: check|deploy|skip",
    ),
    json_input: str | None = typer.Option(
        None,
        "--json",
        help="JSON payload (overrides flags)",
    ),
    attio_api_key_override: str | None = typer.Option(
        None,
        "--attio-api-key",
        help="Override Attio API key",
    ),
) -> None:
    if json_input:
        try:
            query = PersonAddQuery.model_validate_json(json_input)
            payload = query.model_dump()
        except (ValidationError, json.JSONDecodeError) as exc:
            emit_json_payload_validation_telemetry(
                "attio.people.add",
                exc,
                PersonAddQuery,
                json_input,
            )
            _print_envelope_and_exit(error_envelope(exc))
            return
        except Exception as exc:
            _print_envelope_and_exit(error_envelope(exc))
            return
    else:
        if not email:
            _print_envelope_and_exit(
                error_envelope(ValueError("email is required when --json is not used")),
            )
            return
        payload = {
            "email": email,
            "additional_emails": add_email,
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
            "linkedin": linkedin,
            "location": location,
            "company_domain": company_domain,
            "notes": notes,
            "strict": strict,
            "location_mode": location_mode,
        }

    api_keys: dict[str, str] = {}
    if attio_api_key_override:
        api_keys["attio_api_key"] = attio_api_key_override

    _invoke_people_fn(
        "attio_add_person",
        payload,
        api_keys=api_keys or None,
        no_connectivity_probe=no_connectivity_probe,
        strict=bool(payload.get("strict", False)),
        modal_sync=modal_sync,
    )


@app.command()
def search(
    name: str | None = typer.Option(
        None,
        "--name",
        help="Search by name (fuzzy, case-insensitive)",
    ),
    email: str | None = typer.Option(
        None,
        "--email",
        help="Search by exact email address",
    ),
    email_domain: str | None = typer.Option(
        None,
        "--email-domain",
        help="Search by email domain (e.g. continue.dev)",
    ),
    phone: str | None = typer.Option(
        None,
        "--phone",
        help="Search by phone number (partial match)",
    ),
    company: str | None = typer.Option(
        None,
        "--company",
        help="Search by company name or domain",
    ),
    sample: bool = typer.Option(
        False,
        "--sample",
        help="Fetch recent records without filtering (overrides all search criteria)",
    ),
    limit: int = typer.Option(25, "--limit", help="Max results to return"),
    no_connectivity_probe: bool = typer.Option(
        False,
        "--no-connectivity-probe",
        help="Skip Modal connectivity preflight",
    ),
    json_input: str | None = typer.Option(
        None,
        "--json",
        help="JSON payload (overrides flags)",
    ),
    attio_api_key_override: str | None = typer.Option(
        None,
        "--attio-api-key",
        help="Override Attio API key",
    ),
) -> None:
    if json_input:
        try:
            query = PersonSearchQuery.model_validate_json(json_input)
            payload = query.model_dump()
        except (ValidationError, json.JSONDecodeError) as exc:
            emit_json_payload_validation_telemetry(
                "attio.people.search",
                exc,
                PersonSearchQuery,
                json_input,
            )
            _print_envelope_and_exit(error_envelope(exc))
            return
        except Exception as exc:
            _print_envelope_and_exit(error_envelope(exc))
            return
    else:
        if not sample and not any([name, email, email_domain, phone, company]):
            _print_envelope_and_exit(
                error_envelope(
                    ValueError(
                        "Provide at least one search criterion: --name, --email, --email-domain, --phone, --company. "
                        "Or use --sample to browse recent records without filtering.",
                    ),
                ),
            )
            return
        payload = {
            "name": name,
            "email": email,
            "email_domain": email_domain,
            "phone": phone,
            "company": company,
            "sample": sample,
            "limit": limit,
        }

    api_keys: dict[str, str] = {}
    if attio_api_key_override:
        api_keys["attio_api_key"] = attio_api_key_override

    _invoke_people_fn(
        "attio_search_people",
        payload,
        api_keys=api_keys or None,
        no_connectivity_probe=no_connectivity_probe,
        strict=False,
    )


@app.command()
def update(
    email: str | None = typer.Option(None, "--email", help="Email to look up person"),
    record_id: str | None = typer.Option(None, "--id", help="Attio record ID"),
    add_email: Annotated[
        list[str],
        typer.Option(
            "--add-email",
            help="Email to merge onto the person (repeat for multiple). "
            "Existing addresses are kept; duplicates are dropped.",
        ),
    ] = [],
    replace_emails: bool = typer.Option(
        False,
        "--replace-emails",
        help="Replace stored emails with lookup identity (--email) plus "
        "--add-email only (no merge with existing).",
    ),
    first_name: str | None = typer.Option(None, "--first-name", help="First name"),
    last_name: str | None = typer.Option(None, "--last-name", help="Last name"),
    phone: str | None = typer.Option(None, "--phone", help="Phone number"),
    linkedin: str | None = typer.Option(
        None,
        "--linkedin",
        help="LinkedIn profile URL",
    ),
    location: str | None = typer.Option(None, "--location", help="Primary location"),
    company_domain: str | None = typer.Option(None, "--company", help="Company domain"),
    notes: str | None = typer.Option(None, "--notes", help="Intake notes"),
    strict: bool = typer.Option(
        False,
        "--strict",
        help="Fail fast on optional-field mismatches",
    ),
    location_mode: str = typer.Option(
        "city",
        "--location-mode",
        help="Location normalization mode: city|raw",
    ),
    no_connectivity_probe: bool = typer.Option(
        False,
        "--no-connectivity-probe",
        help="Skip Modal connectivity preflight",
    ),
    modal_sync: str = typer.Option(
        "check",
        "--modal-sync",
        help="Modal sync strategy for mutation commands: check|deploy|skip",
    ),
    json_input: str | None = typer.Option(
        None,
        "--json",
        help="JSON payload (overrides flags)",
    ),
    attio_api_key_override: str | None = typer.Option(
        None,
        "--attio-api-key",
        help="Override Attio API key",
    ),
) -> None:
    if json_input:
        try:
            query = PersonUpdateQuery.model_validate_json(json_input)
            payload = query.model_dump()
        except (ValidationError, json.JSONDecodeError) as exc:
            emit_json_payload_validation_telemetry(
                "attio.people.update",
                exc,
                PersonUpdateQuery,
                json_input,
            )
            _print_envelope_and_exit(error_envelope(exc))
            return
        except Exception as exc:
            _print_envelope_and_exit(error_envelope(exc))
            return
    else:
        if not email and not record_id:
            _print_envelope_and_exit(
                error_envelope(
                    ValueError("provide --email or --id to identify the person."),
                ),
            )
            return
        payload = {
            "record_id": record_id,
            "email": email,
            "additional_emails": add_email,
            "replace_emails": replace_emails,
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
            "linkedin": linkedin,
            "location": location,
            "company_domain": company_domain,
            "notes": notes,
            "strict": strict,
            "location_mode": location_mode,
        }

    api_keys: dict[str, str] = {}
    if attio_api_key_override:
        api_keys["attio_api_key"] = attio_api_key_override

    _invoke_people_fn(
        "attio_update_person",
        payload,
        api_keys=api_keys or None,
        no_connectivity_probe=no_connectivity_probe,
        strict=bool(payload.get("strict", False)),
        modal_sync=modal_sync,
    )


@app.command()
def upsert(
    email: str = typer.Argument(
        "",
        help="Email address used as deterministic identity key",
    ),
    add_email: Annotated[
        list[str],
        typer.Option(
            "--add-email",
            help="Extra email to store (repeat for multiple). "
            "On update, merged with existing unless --replace-emails.",
        ),
    ] = [],
    replace_emails: bool = typer.Option(
        False,
        "--replace-emails",
        help="On update, set emails to identity email plus --add-email only.",
    ),
    first_name: str | None = typer.Option(None, "--first-name", help="First name"),
    last_name: str | None = typer.Option(None, "--last-name", help="Last name"),
    phone: str | None = typer.Option(None, "--phone", help="Phone number"),
    linkedin: str | None = typer.Option(
        None,
        "--linkedin",
        help="LinkedIn profile URL",
    ),
    location: str | None = typer.Option(None, "--location", help="Primary location"),
    company_domain: str | None = typer.Option(None, "--company", help="Company domain"),
    notes: str | None = typer.Option(None, "--notes", help="Intake notes"),
    strict: bool = typer.Option(
        False,
        "--strict",
        help="Fail fast on ambiguity or optional-field mismatches",
    ),
    location_mode: str = typer.Option(
        "city",
        "--location-mode",
        help="Location normalization mode: city|raw",
    ),
    no_connectivity_probe: bool = typer.Option(
        False,
        "--no-connectivity-probe",
        help="Skip Modal connectivity preflight",
    ),
    modal_sync: str = typer.Option(
        "check",
        "--modal-sync",
        help="Modal sync strategy for mutation commands: check|deploy|skip",
    ),
    json_input: str | None = typer.Option(
        None,
        "--json",
        help="JSON payload (overrides flags)",
    ),
    attio_api_key_override: str | None = typer.Option(
        None,
        "--attio-api-key",
        help="Override Attio API key",
    ),
) -> None:
    if json_input:
        try:
            query = PersonUpsertQuery.model_validate_json(json_input)
            payload = query.model_dump()
        except (ValidationError, json.JSONDecodeError) as exc:
            emit_json_payload_validation_telemetry(
                "attio.people.upsert",
                exc,
                PersonUpsertQuery,
                json_input,
            )
            _print_envelope_and_exit(error_envelope(exc))
            return
        except Exception as exc:
            _print_envelope_and_exit(error_envelope(exc))
            return
    else:
        if not email:
            _print_envelope_and_exit(
                error_envelope(ValueError("email is required when --json is not used")),
            )
            return
        payload = {
            "email": email,
            "additional_emails": add_email,
            "replace_emails": replace_emails,
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
            "linkedin": linkedin,
            "location": location,
            "company_domain": company_domain,
            "notes": notes,
            "strict": strict,
            "location_mode": location_mode,
        }

    api_keys: dict[str, str] = {}
    if attio_api_key_override:
        api_keys["attio_api_key"] = attio_api_key_override

    _invoke_people_fn(
        "attio_upsert_person",
        payload,
        api_keys=api_keys or None,
        no_connectivity_probe=no_connectivity_probe,
        strict=bool(payload.get("strict", False)),
        modal_sync=modal_sync,
    )
