# trunk-ignore-all(pyright/reportUntypedFunctionDecorator)
from typing import Any

from pydantic import BaseModel, ConfigDict

from libs.apollo.models import PersonEnrichInput, PersonSearchInput
from libs.apollo.people import enrich_person, search_people
from src.api_keys import inject_api_keys
from src.app import app, image, secrets_apollo


def _decorate_apollo_key_error(exc: ValueError) -> ValueError:
    msg = str(exc)
    if "APOLLO_API_KEY" not in msg:
        return exc
    return ValueError(
        f"{msg} Populate Modal secret 'apollo' with APOLLO_API_KEY "
        "(modal secret create apollo APOLLO_API_KEY=... --force).",
    )


@app.function(image=image, secrets=[secrets_apollo])
def apollo_enrich_person(
    payload: dict[str, Any],
    api_keys: dict[str, str] | None = None,
) -> dict[str, Any]:
    with inject_api_keys(api_keys or {}):
        query = PersonEnrichQuery.model_validate(payload)
        try:
            return enrich_person(
                PersonEnrichInput(
                    email=query.email,
                    first_name=query.first_name,
                    last_name=query.last_name,
                    name=query.name,
                    domain=query.domain,
                    linkedin_url=query.linkedin_url,
                    organization_name=query.organization_name,
                ),
            )
        except ValueError as exc:
            raise _decorate_apollo_key_error(exc) from None
        except TypeError:
            raise
        except Exception as exc:
            raise ValueError(f"{type(exc).__name__}: {exc}") from None


@app.function(image=image, secrets=[secrets_apollo])
def apollo_search_people(
    payload: dict[str, Any],
    api_keys: dict[str, str] | None = None,
) -> dict[str, Any]:
    with inject_api_keys(api_keys or {}):
        query = PersonSearchQuery.model_validate(payload)
        try:
            return search_people(
                PersonSearchInput(
                    q_keywords=query.q_keywords,
                    person_titles=query.person_titles,
                    person_seniorities=query.person_seniorities,
                    person_locations=query.person_locations,
                    q_organization_domains_list=query.q_organization_domains_list,
                    organization_locations=query.organization_locations,
                    organization_num_employees_ranges=query.organization_num_employees_ranges,
                    page=query.page,
                    per_page=query.per_page,
                ),
            )
        except ValueError as exc:
            raise _decorate_apollo_key_error(exc) from None
        except TypeError:
            raise
        except Exception as exc:
            raise ValueError(f"{type(exc).__name__}: {exc}") from None


class PersonEnrichQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    name: str | None = None
    domain: str | None = None
    linkedin_url: str | None = None
    organization_name: str | None = None


class PersonSearchQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    q_keywords: str | None = None
    person_titles: list[str] = []
    person_seniorities: list[str] = []
    person_locations: list[str] = []
    q_organization_domains_list: list[str] = []
    organization_locations: list[str] = []
    organization_num_employees_ranges: list[str] = []
    page: int = 1
    per_page: int = 10
