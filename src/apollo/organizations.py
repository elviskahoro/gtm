# trunk-ignore-all(pyright/reportUntypedFunctionDecorator)
from typing import Any

from pydantic import BaseModel, ConfigDict

from libs.apollo.models import OrgEnrichInput, OrgSearchInput
from libs.apollo.organizations import enrich_organization, search_organizations
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
def apollo_enrich_organization(
    payload: dict[str, Any],
    api_keys: dict[str, str] | None = None,
) -> dict[str, Any]:
    with inject_api_keys(api_keys or {}):
        query = OrgEnrichQuery.model_validate(payload)
        try:
            return enrich_organization(OrgEnrichInput(domain=query.domain))
        except ValueError as exc:
            raise _decorate_apollo_key_error(exc) from None
        except TypeError:
            raise
        except Exception as exc:
            raise ValueError(f"{type(exc).__name__}: {exc}") from None


@app.function(image=image, secrets=[secrets_apollo])
def apollo_search_organizations(
    payload: dict[str, Any],
    api_keys: dict[str, str] | None = None,
) -> dict[str, Any]:
    with inject_api_keys(api_keys or {}):
        query = OrgSearchQuery.model_validate(payload)
        try:
            return search_organizations(
                OrgSearchInput(
                    q_keywords=query.q_keywords,
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


class OrgEnrichQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain: str


class OrgSearchQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    q_keywords: str | None = None
    organization_locations: list[str] = []
    organization_num_employees_ranges: list[str] = []
    page: int = 1
    per_page: int = 10
