from __future__ import annotations

from typing import Any

from libs.attio.client import get_client
from libs.attio.contracts import ErrorEntry, ReliabilityEnvelope
from libs.attio.errors import classify_error
from libs.attio.models import MentionInput
from libs.attio.sdk_boundary import build_assert_record_request
from libs.attio.values import (
    build_create_mention_values,
    build_update_mention_values,
)


def _build_values(input: MentionInput) -> dict[str, Any]:
    if input.last_action == "mention_created":
        return build_create_mention_values(input)
    return build_update_mention_values(input)


def upsert_mention(input: MentionInput) -> ReliabilityEnvelope:
    """Idempotent upsert against the ``octolens_mentions`` custom object.

    Uses Attio's assert endpoint with ``matching_attribute=mention_url``.
    The endpoint creates the record if no match exists, or updates the
    single match in place. ``mention_url`` is declared ``is_unique`` in
    the object schema, so multi-match is impossible by construction.
    """
    values = _build_values(input)
    try:
        with get_client() as client:
            response = client.records.put_v2_objects_object_records(
                object="octolens_mentions",
                matching_attribute="mention_url",
                data=build_assert_record_request(values),
            )
    except Exception as exc:  # noqa: BLE001 — classify and wrap any SDK exception
        return _error_envelope(exc)

    record_id: str = response.data.id.record_id
    # Different SDK versions name the create-vs-update signal differently
    # (`created`, `action`, ...). Default to "updated" when ambiguous — it's
    # the safer answer for downstream consumers.
    created_flag = getattr(response, "created", None)
    action = "created" if created_flag is True else "updated"

    return ReliabilityEnvelope(
        success=True,
        partial_success=False,
        action=action,  # type: ignore[arg-type]
        record_id=record_id,
        warnings=[],
        skipped_fields=[],
        errors=[],
        meta={
            "output_schema_version": "v1",
            "mention": input.model_dump(mode="json"),
        },
    )


def _error_envelope(error: Exception) -> ReliabilityEnvelope:
    classified = classify_error(error, strict=False)
    return ReliabilityEnvelope(
        success=False,
        partial_success=False,
        action="failed",
        record_id=None,
        warnings=[],
        skipped_fields=[],
        errors=[
            ErrorEntry(
                code=classified.code,
                message=classified.message,
                error_type=classified.error_type,
                fatal=classified.fatal,
                field=classified.field,
            ),
        ],
        meta={"output_schema_version": "v1"},
    )
