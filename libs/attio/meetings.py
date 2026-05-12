from __future__ import annotations

import logging
from typing import Any

from libs.attio.client import get_client
from libs.attio.contracts import ErrorEntry, ReliabilityEnvelope
from libs.attio.errors import classify_error
from libs.attio.models import MeetingInput, MeetingResult
from libs.attio.sdk_boundary import build_post_meeting_request
from libs.attio.values import build_meeting_payload

logger = logging.getLogger(__name__)


def _extract_result(data: Any) -> MeetingResult:
    ident = data.id
    ical_uid: str | None = None
    ref = getattr(data, "external_ref", None)
    if ref is not None:
        ical_uid = getattr(ref, "ical_uid", None)
    return MeetingResult(
        meeting_id=ident.meeting_id,
        workspace_id=ident.workspace_id,
        title=getattr(data, "title", ""),
        external_ref_ical_uid=ical_uid,
        created=True,
    )


def _post_meeting(input: MeetingInput) -> MeetingResult:
    payload = build_meeting_payload(input)["data"]
    with get_client() as client:
        response = client.meetings.post_v2_meetings(
            data=build_post_meeting_request(
                external_ref=payload["external_ref"],
                title=payload["title"],
                description=payload["description"],
                start=payload["start"],
                end=payload["end"],
                is_all_day=payload["is_all_day"],
                participants=payload["participants"],
                linked_records=payload["linked_records"],
            ),
        )
        return _extract_result(response.data)


def find_or_create_meeting(input: MeetingInput) -> ReliabilityEnvelope:
    """POST /v2/meetings.

    Attio's endpoint is 'Find or create a meeting' — repeat POSTs that share
    the same `external_ref.ical_uid` return the existing record.
    """
    try:
        result = _post_meeting(input)
    except Exception as exc:  # noqa: BLE001 — boundary
        classified = classify_error(exc)
        logger.warning("attio_meeting_failed", extra={"code": classified.code})
        return ReliabilityEnvelope(
            success=False,
            partial_success=False,
            action="failed",
            record_id=None,
            errors=[
                ErrorEntry(
                    code=classified.code,
                    message=classified.message,
                    error_type=classified.error_type,
                    fatal=classified.fatal,
                    field=classified.field,
                ),
            ],
            warnings=[],
            skipped_fields=[],
            meta={"output_schema_version": "v1"},
        )

    return ReliabilityEnvelope(
        success=True,
        partial_success=False,
        action="created",
        record_id=result.meeting_id,
        errors=[],
        warnings=[],
        skipped_fields=[],
        meta={
            "output_schema_version": "v1",
            "external_ref_ical_uid": result.external_ref_ical_uid,
        },
    )
