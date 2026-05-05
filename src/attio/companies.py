# trunk-ignore-all(pyright/reportUntypedFunctionDecorator)
from typing import Any

import modal
from pydantic import BaseModel, ConfigDict

from libs.attio.attributes import create_companies_attribute
from libs.attio.companies import add_company, search_companies, update_company
from libs.attio.models import (
    AttributeCreateResult,
    CompanyInput,
    CompanyResult,
    CompanySearchResult,
)
from src.api_keys import inject_api_keys
from src.app import app, image, secrets_attio
from src.attio.http_responses import error_response_from_exception


@app.function(image=image, secrets=[secrets_attio])
def attio_add_company(
    payload: dict[str, Any],
    api_keys: dict[str, str] | None = None,
) -> CompanyResult:
    with inject_api_keys(api_keys or {}):
        query = CompanyAddQuery.model_validate(payload)
        return add_company(
            CompanyInput(
                name=query.name,
                domain=query.domain,
                description=query.description,
            ),
        )


@app.function(image=image, secrets=[secrets_attio])
def attio_search_companies(
    payload: dict[str, Any],
    api_keys: dict[str, str] | None = None,
) -> list[CompanySearchResult]:
    with inject_api_keys(api_keys or {}):
        query = CompanySearchQuery.model_validate(payload)
        return search_companies(name=query.name, domain=query.domain, limit=query.limit)


@app.function(image=image, secrets=[secrets_attio])
def attio_update_company(
    payload: dict[str, Any],
    api_keys: dict[str, str] | None = None,
) -> CompanyResult:
    with inject_api_keys(api_keys or {}):
        query = CompanyUpdateQuery.model_validate(payload)
        return update_company(
            record_id=query.record_id,
            domain=query.domain,
            input=CompanyInput(
                name=query.name or "",
                domain=query.domain,
                description=query.description,
            ),
        )


@app.function(image=image, secrets=[secrets_attio])
def attio_create_companies_attribute(
    payload: dict[str, Any],
    api_keys: dict[str, str] | None = None,
) -> AttributeCreateResult:
    with inject_api_keys(api_keys or {}):
        query = CompanyCreateAttributeQuery.model_validate(payload)
        return create_companies_attribute(
            title=query.title,
            api_slug=query.api_slug,
            attribute_type=query.attribute_type,
            description=query.description or None,
            is_multiselect=query.is_multiselect,
            is_required=query.is_required,
            is_unique=query.is_unique,
            apply=query.apply,
        )


# Query models


class CompanyAddQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    domain: str | None = None
    description: str | None = None


class CompanySearchQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    domain: str | None = None
    limit: int = 25


class CompanyUpdateQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str | None = None
    domain: str | None = None
    name: str | None = None
    description: str | None = None


class CompanyCreateAttributeQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    api_slug: str
    attribute_type: str = "select"
    description: str = ""
    is_multiselect: bool = True
    is_required: bool = False
    is_unique: bool = False
    apply: bool = False


# HTTP endpoint wrappers


@app.function(image=image, secrets=[secrets_attio])
@modal.fastapi_endpoint(method="POST", docs=True)
def attio_company_add_http(query: CompanyAddQuery) -> Any:
    try:
        result = attio_add_company.remote(
            payload=query.model_dump(),
        )  # pyright: ignore[reportFunctionMemberAccess]
        return result.model_dump()

    except Exception as exc:
        return error_response_from_exception(exc)


@app.function(image=image, secrets=[secrets_attio])
@modal.fastapi_endpoint(method="POST", docs=True)
def attio_companies_search_http(query: CompanySearchQuery) -> Any:
    try:
        results = attio_search_companies.remote(
            payload=query.model_dump(),
        )  # pyright: ignore[reportFunctionMemberAccess]
        return [r.model_dump() for r in results]

    except Exception as exc:
        return error_response_from_exception(exc)


@app.function(image=image, secrets=[secrets_attio])
@modal.fastapi_endpoint(method="POST", docs=True)
def attio_company_update_http(query: CompanyUpdateQuery) -> Any:
    try:
        result = attio_update_company.remote(
            payload=query.model_dump(),
        )  # pyright: ignore[reportFunctionMemberAccess]
        return result.model_dump()
    except Exception as exc:
        return error_response_from_exception(exc)
