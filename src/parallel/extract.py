# trunk-ignore-all(pyright/reportUntypedFunctionDecorator)
from typing import Any

from pydantic import BaseModel, ConfigDict

from libs.parallel.client import extract_excerpts, extract_full_content
from libs.parallel.models import (
    ExtractExcerptsInput,
    ExtractFullContentInput,
    ExtractResponse,
)
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
def parallel_extract_excerpts(
    payload: dict[str, Any],
    api_keys: dict[str, str] | None = None,
) -> ExtractResponse:
    with inject_api_keys(api_keys or {}):
        query = ExtractExcerptsQuery.model_validate(payload)
        try:
            return extract_excerpts(
                ExtractExcerptsInput(url=query.url, objective=query.objective),
            )
        except ValueError as exc:
            raise _decorate_parallel_key_error(exc) from None
        except TypeError:
            raise
        except Exception as exc:
            raise ValueError(f"{type(exc).__name__}: {exc}") from None


@app.function(image=image, secrets=[secrets_parallel])
def parallel_extract_full_content(
    payload: dict[str, Any],
    api_keys: dict[str, str] | None = None,
) -> ExtractResponse:
    with inject_api_keys(api_keys or {}):
        query = ExtractFullContentQuery.model_validate(payload)
        try:
            return extract_full_content(ExtractFullContentInput(url=query.url))
        except ValueError as exc:
            raise _decorate_parallel_key_error(exc) from None
        except TypeError:
            raise
        except Exception as exc:
            raise ValueError(f"{type(exc).__name__}: {exc}") from None


# Query models


class ExtractExcerptsQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str
    objective: str


class ExtractFullContentQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str
