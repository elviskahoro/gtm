# trunk-ignore-all(pyright/reportUntypedFunctionDecorator)
import os
from typing import Any, Literal, cast

import modal
from pydantic import BaseModel, ConfigDict, Field

from libs.attio.contracts import ReliabilityEnvelope
from libs.attio.models import PersonInput
from libs.attio.people import (
    add_person,
    error_envelope,
    search_people,
    update_person,
    upsert_person,
)
from src.api_keys import inject_api_keys
from src.app import app, image, secrets_attio
from src.attio.http_responses import error_response_from_payload
from src.modal_app import MODAL_APP

ENABLE_ATTIO_PERSON_UPSERT_HTTP = (
    os.environ.get("ENABLE_ATTIO_PERSON_UPSERT_HTTP", "0") == "1"
)


@app.function(image=image)
def attio_people_runtime_metadata() -> dict[str, object]:
    return {
        "app": MODAL_APP,
        "build_git_sha": os.environ.get("AI_BUILD_GIT_SHA", "unknown"),
        "deployed_at": os.environ.get("AI_DEPLOYED_AT", "unknown"),
        "capabilities": {
            "attio_people_upsert.additional_emails": True,
        },
    }


@app.function(image=image, secrets=[secrets_attio])
def attio_add_person(
    payload: dict[str, Any],
    api_keys: dict[str, str] | None = None,
) -> ReliabilityEnvelope:
    query = None
    with inject_api_keys(api_keys or {}):
        try:
            query = PersonAddQuery.model_validate(payload)
            return add_person(
                PersonInput(
                    email=query.email,
                    additional_emails=list(query.additional_emails),
                    first_name=query.first_name,
                    last_name=query.last_name,
                    phone=query.phone,
                    linkedin=query.linkedin,
                    location=query.location,
                    company_domain=query.company_domain,
                    notes=query.notes,
                    strict=query.strict,
                    location_mode=cast(Literal["raw", "city"], query.location_mode),
                ),
            )
        except Exception as exc:
            return error_envelope(
                exc,
                strict=getattr(query, "strict", False) if query else False,
            )


@app.function(image=image, secrets=[secrets_attio])
def attio_search_people(
    payload: dict[str, Any],
    api_keys: dict[str, str] | None = None,
) -> ReliabilityEnvelope:
    with inject_api_keys(api_keys or {}):
        try:
            query = PersonSearchQuery.model_validate(payload)
            return search_people(
                name=query.name,
                email=query.email,
                email_domain=query.email_domain,
                phone=query.phone,
                company=query.company,
                sample=query.sample,
                limit=query.limit,
            )
        except Exception as exc:
            return error_envelope(exc)


@app.function(image=image, secrets=[secrets_attio])
def attio_update_person(
    payload: dict[str, Any],
    api_keys: dict[str, str] | None = None,
) -> ReliabilityEnvelope:
    query = None
    with inject_api_keys(api_keys or {}):
        try:
            query = PersonUpdateQuery.model_validate(payload)
            return update_person(
                record_id=query.record_id,
                email=query.email,
                input=PersonInput(
                    email=query.email or "",
                    additional_emails=list(query.additional_emails),
                    replace_emails=query.replace_emails,
                    first_name=query.first_name,
                    last_name=query.last_name,
                    phone=query.phone,
                    linkedin=query.linkedin,
                    location=query.location,
                    company_domain=query.company_domain,
                    notes=query.notes,
                    strict=query.strict,
                    location_mode=cast(Literal["raw", "city"], query.location_mode),
                ),
            )
        except Exception as exc:
            return error_envelope(
                exc,
                strict=getattr(query, "strict", False) if query else False,
            )


@app.function(image=image, secrets=[secrets_attio])
def attio_upsert_person(
    payload: dict[str, Any],
    api_keys: dict[str, str] | None = None,
) -> ReliabilityEnvelope:
    query = None
    with inject_api_keys(api_keys or {}):
        try:
            query = PersonUpsertQuery.model_validate(payload)
            return upsert_person(
                PersonInput(
                    email=query.email,
                    additional_emails=list(query.additional_emails),
                    replace_emails=query.replace_emails,
                    first_name=query.first_name,
                    last_name=query.last_name,
                    phone=query.phone,
                    linkedin=query.linkedin,
                    location=query.location,
                    company_domain=query.company_domain,
                    notes=query.notes,
                    strict=query.strict,
                    location_mode=cast(Literal["raw", "city"], query.location_mode),
                ),
                strict=query.strict,
            )
        except Exception as exc:
            return error_envelope(
                exc,
                strict=getattr(query, "strict", False) if query else False,
            )


# Query models


class PersonAddQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    additional_emails: list[str] = Field(default_factory=list)
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    location: str | None = None
    company_domain: str | None = None
    notes: str | None = None
    strict: bool = False
    location_mode: str = "city"


class PersonSearchQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    email: str | None = None
    email_domain: str | None = None
    phone: str | None = None
    company: str | None = None
    sample: bool = False
    limit: int = 25


class PersonUpdateQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str | None = None
    email: str | None = None
    additional_emails: list[str] = Field(default_factory=list)
    replace_emails: bool = False
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    location: str | None = None
    company_domain: str | None = None
    notes: str | None = None
    strict: bool = False
    location_mode: str = "city"


class PersonUpsertQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    additional_emails: list[str] = Field(default_factory=list)
    replace_emails: bool = False
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    location: str | None = None
    company_domain: str | None = None
    notes: str | None = None
    strict: bool = False
    location_mode: str = "city"


def _normalize_remote_payload(result: Any) -> Any:
    if hasattr(result, "model_dump"):
        return result.model_dump()
    return result


def _envelope_or_error_response(payload: Any) -> Any:
    if isinstance(payload, dict) and payload.get("success") is False:
        return error_response_from_payload(payload)
    return payload


@app.function(image=image, secrets=[secrets_attio])
@modal.fastapi_endpoint(method="POST", docs=True)
def attio_person_add_http(query: PersonAddQuery) -> Any:
    result = attio_add_person.remote(  # pyrefly: ignore[invalid-param-spec]
        payload=query.model_dump(),
    )  # pyright: ignore[reportFunctionMemberAccess]
    return _envelope_or_error_response(_normalize_remote_payload(result))


@app.function(image=image, secrets=[secrets_attio])
@modal.fastapi_endpoint(method="POST", docs=True)
def attio_people_search_http(query: PersonSearchQuery) -> Any:
    result = attio_search_people.remote(  # pyrefly: ignore[invalid-param-spec]
        payload=query.model_dump(),
    )  # pyright: ignore[reportFunctionMemberAccess]
    return _envelope_or_error_response(_normalize_remote_payload(result))


@app.function(image=image, secrets=[secrets_attio])
@modal.fastapi_endpoint(method="POST", docs=True)
def attio_person_update_http(query: PersonUpdateQuery) -> Any:
    result = attio_update_person.remote(  # pyrefly: ignore[invalid-param-spec]
        payload=query.model_dump(),
    )  # pyright: ignore[reportFunctionMemberAccess]
    return _envelope_or_error_response(_normalize_remote_payload(result))


if ENABLE_ATTIO_PERSON_UPSERT_HTTP:

    @app.function(image=image, secrets=[secrets_attio])
    @modal.fastapi_endpoint(method="POST", docs=True)
    def attio_person_upsert_http(query: PersonUpsertQuery) -> Any:
        result = attio_upsert_person.remote(  # pyrefly: ignore[invalid-param-spec]
            payload=query.model_dump(),
        )  # pyright: ignore[reportFunctionMemberAccess]
        return _envelope_or_error_response(_normalize_remote_payload(result))
