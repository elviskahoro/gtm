# trunk-ignore-all(pyright/reportUntypedFunctionDecorator)
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from src.accounts import tasks
from src.accounts.models import FindPeopleResult
from src.api_keys import inject_api_keys
from src.app import app, image, secrets_parallel


class FindPeopleQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str


@app.function(image=image, secrets=[secrets_parallel])
def gtm_find_people(
    payload: dict[str, Any],
    api_keys: dict[str, str] | None = None,
) -> FindPeopleResult:
    with inject_api_keys(api_keys or {}):
        q = FindPeopleQuery.model_validate(payload)
        return FindPeopleResult.model_validate(tasks.find_people(q.query))
