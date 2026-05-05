# trunk-ignore-all(pyright/reportUntypedFunctionDecorator)
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from src.accounts import tasks
from src.accounts.models import EnrichResult, ResearchResult
from src.api_keys import inject_api_keys
from src.app import app, image, secrets_parallel


class ResearchQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    objective: str


class EnrichQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str
    objective: str


@app.function(image=image, secrets=[secrets_parallel])
def gtm_research(
    payload: dict[str, Any],
    api_keys: dict[str, str] | None = None,
) -> ResearchResult:
    with inject_api_keys(api_keys or {}):
        query = ResearchQuery.model_validate(payload)
        return ResearchResult.model_validate(tasks.research(query.objective))


@app.function(image=image, secrets=[secrets_parallel])
def gtm_enrich(
    payload: dict[str, Any],
    api_keys: dict[str, str] | None = None,
) -> EnrichResult:
    with inject_api_keys(api_keys or {}):
        query = EnrichQuery.model_validate(payload)
        return EnrichResult.model_validate(tasks.enrich(query.url, query.objective))
