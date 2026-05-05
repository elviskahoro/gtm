# trunk-ignore-all(pyright/reportUntypedFunctionDecorator)
from typing import Any

import modal
from pydantic import BaseModel, ConfigDict

from libs.attio.models import NoteInput, NoteResult
from libs.attio.notes import add_note, update_note
from src.api_keys import inject_api_keys
from src.app import app, image, secrets_attio
from src.attio.http_responses import error_response_from_exception


@app.function(image=image, secrets=[secrets_attio])
def attio_add_note(
    payload: dict[str, Any],
    api_keys: dict[str, str] | None = None,
) -> NoteResult:
    with inject_api_keys(api_keys or {}):
        query = NoteAddQuery.model_validate(payload)
        return add_note(
            NoteInput(
                title=query.title,
                content=query.content,
                parent_object=query.parent_object,
                parent_record_id=query.record_id,
                parent_email=query.email,
                parent_domain=query.domain,
                format=query.format,
            ),
        )


@app.function(image=image, secrets=[secrets_attio])
def attio_update_note(
    payload: dict[str, Any],
    api_keys: dict[str, str] | None = None,
) -> NoteResult:
    with inject_api_keys(api_keys or {}):
        query = NoteUpdateQuery.model_validate(payload)
        return update_note(
            query.note_id,
            input=NoteInput(
                title=query.title or "",
                content=query.content or "",
                parent_object="",
                format=query.format,
            ),
        )


# Query models


class NoteAddQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    content: str
    parent_object: str
    record_id: str | None = None
    email: str | None = None
    domain: str | None = None
    format: str = "plaintext"


class NoteUpdateQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note_id: str
    title: str | None = None
    content: str | None = None
    format: str = "plaintext"


# HTTP endpoint wrappers


@app.function(image=image, secrets=[secrets_attio])
@modal.fastapi_endpoint(method="POST", docs=True)
def attio_note_add_http(query: NoteAddQuery) -> Any:
    try:
        result = attio_add_note.remote(
            payload=query.model_dump(),
        )  # pyright: ignore[reportFunctionMemberAccess]
        return result.model_dump()
    except Exception as exc:
        return error_response_from_exception(exc)


@app.function(image=image, secrets=[secrets_attio])
@modal.fastapi_endpoint(method="POST", docs=True)
def attio_note_update_http(query: NoteUpdateQuery) -> Any:
    try:
        result = attio_update_note.remote(
            payload=query.model_dump(),
        )  # pyright: ignore[reportFunctionMemberAccess]
        return result.model_dump()
    except Exception as exc:
        return error_response_from_exception(exc)
