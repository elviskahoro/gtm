# trunk-ignore-all(pyright/reportUntypedFunctionDecorator)
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from src.accounts import tasks
from src.accounts.models import MapAccountHierarchyResult
from src.api_keys import inject_api_keys
from src.app import app, image, secrets_parallel


class MapAccountHierarchyQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    account: str


@app.function(image=image, secrets=[secrets_parallel])
def gtm_map_account_hierarchy(
    payload: dict[str, Any],
    api_keys: dict[str, str] | None = None,
) -> MapAccountHierarchyResult:
    with inject_api_keys(api_keys or {}):
        query = MapAccountHierarchyQuery.model_validate(payload)
        return MapAccountHierarchyResult.model_validate(
            tasks.map_account_hierarchy(query.account),
        )
