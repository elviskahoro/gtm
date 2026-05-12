from __future__ import annotations

import json
from collections.abc import Mapping
from types import ModuleType
from typing import Any, Protocol, cast


class _ModelDumpLike(Protocol):
    def model_dump(self) -> dict[str, Any]: ...


def _import_attio_sdk_module() -> ModuleType:
    import attio

    return cast(ModuleType, attio)


def _import_attio_models_module() -> object:
    module = _import_attio_sdk_module()
    return getattr(module, "models")


def get_attio_sdk_client_class() -> type[Any]:
    module = _import_attio_sdk_module()
    return cast(type[Any], getattr(module, "SDK"))


def build_post_record_request(values: dict[str, Any]) -> object:
    models = _import_attio_models_module()
    constructor = getattr(models, "PostV2ObjectsObjectRecordsDataRequest")
    return constructor(values=values)


def build_patch_record_request(values: dict[str, Any]) -> object:
    models = _import_attio_models_module()
    constructor = getattr(models, "PatchV2ObjectsObjectRecordsRecordIDDataRequest")
    return constructor(values=values)


def build_post_note_request(
    *,
    parent_object: str,
    parent_record_id: str,
    title: str,
    format_: str,
    content: str,
) -> object:
    models = _import_attio_models_module()
    constructor = getattr(models, "PostV2NotesData")
    return constructor(
        parent_object=parent_object,
        parent_record_id=parent_record_id,
        title=title,
        format_=format_,
        content=content,
    )


def build_post_meeting_request(
    *,
    external_ref: dict[str, Any],
    title: str,
    description: str,
    start: dict[str, Any],
    end: dict[str, Any],
    is_all_day: bool,
    participants: list[dict[str, Any]],
    linked_records: list[dict[str, Any]],
) -> object:
    models = _import_attio_models_module()
    constructor = getattr(models, "PostV2MeetingsData")
    return constructor(
        external_ref=external_ref,
        title=title,
        description=description,
        start=start,
        end=end,
        is_all_day=is_all_day,
        participants=participants,
        linked_records=linked_records,
    )


def extract_exception_body_text(exc: BaseException) -> str:
    body = getattr(exc, "body", None)
    if body is None:
        return str(exc)
    if isinstance(body, bytes):
        return body.decode("utf-8", errors="replace")
    if isinstance(body, str):
        return body
    return str(body)


def _parse_json_object(text: str) -> Mapping[str, Any] | None:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None

    if isinstance(parsed, dict):
        return cast(Mapping[str, Any], parsed)
    return None


def extract_existing_record_id(exc: BaseException) -> str | None:
    payload = _parse_json_object(extract_exception_body_text(exc))
    if payload is None:
        return None

    data = payload.get("data")
    if not isinstance(data, Mapping):
        return None
    existing_record = data.get("existing_record")
    if not isinstance(existing_record, Mapping):
        return None
    record_id_obj = existing_record.get("id")
    if not isinstance(record_id_obj, Mapping):
        return None
    record_id = record_id_obj.get("record_id")
    if isinstance(record_id, str) and record_id:
        return record_id
    return None


def is_uniqueness_conflict(exc: BaseException) -> bool:
    return "uniqueness_conflict" in extract_exception_body_text(exc)


def model_dump_or_empty(value: object) -> dict[str, Any]:
    if hasattr(value, "model_dump") and callable(getattr(value, "model_dump")):
        return cast(_ModelDumpLike, value).model_dump()
    return {}
