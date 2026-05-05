# trunk-ignore-all(pyright/reportUntypedFunctionDecorator)
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from libs.parallel.client import findall_create, findall_result, findall_status
from libs.parallel.models import (
    FindAllCreateInput,
    FindAllLookupInput,
    FindAllResultData,
    FindAllRunData,
    MatchCondition,
)
from libs.parallel.types import FindAllGenerator
from src.api_keys import inject_api_keys
from src.app import app, image, secrets_parallel


def _decorate_parallel_key_error(exc: ValueError) -> ValueError:
    msg = str(exc)
    if "PARALLEL_API_KEY" not in msg:
        return exc
    return ValueError(
        f"{msg} Populate Modal secret 'parallel' with PARALLEL_API_KEY "
        "(modal secret create parallel PARALLEL_API_KEY=... --force).",
    )


@app.function(image=image, secrets=[secrets_parallel])
def parallel_findall_create(
    payload: dict[str, Any],
    api_keys: dict[str, str] | None = None,
) -> FindAllRunData:
    with inject_api_keys(api_keys or {}):
        query = FindAllCreateQuery.model_validate(payload)
        try:
            return findall_create(
                FindAllCreateInput(
                    objective=query.objective,
                    entity_type=query.entity_type,
                    match_conditions=query.match_conditions,
                    match_limit=query.match_limit,
                    generator=query.generator,
                ),
            )
        except ValueError as exc:
            raise _decorate_parallel_key_error(exc) from None
        except TypeError:
            raise
        except Exception as exc:
            raise ValueError(f"{type(exc).__name__}: {exc}") from None


@app.function(image=image, secrets=[secrets_parallel])
def parallel_findall_result(
    payload: dict[str, Any],
    api_keys: dict[str, str] | None = None,
) -> FindAllResultData:
    with inject_api_keys(api_keys or {}):
        query = FindAllResultQuery.model_validate(payload)
        try:
            return findall_result(FindAllLookupInput(findall_id=query.findall_id))
        except ValueError as exc:
            raise _decorate_parallel_key_error(exc) from None
        except TypeError:
            raise
        except Exception as exc:
            raise ValueError(f"{type(exc).__name__}: {exc}") from None


@app.function(image=image, secrets=[secrets_parallel])
def parallel_findall_status(
    payload: dict[str, Any],
    api_keys: dict[str, str] | None = None,
) -> FindAllRunData:
    with inject_api_keys(api_keys or {}):
        query = FindAllStatusQuery.model_validate(payload)
        try:
            return findall_status(FindAllLookupInput(findall_id=query.findall_id))
        except ValueError as exc:
            raise _decorate_parallel_key_error(exc) from None
        except TypeError:
            raise
        except Exception as exc:
            raise ValueError(f"{type(exc).__name__}: {exc}") from None


# Query models


class FindAllCreateQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objective: str
    entity_type: str
    match_conditions: list[MatchCondition] = Field(min_length=1)
    match_limit: int = 10
    generator: FindAllGenerator = "base"


class FindAllResultQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    findall_id: str


class FindAllStatusQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    findall_id: str
