from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

from libs.attio.contracts import ReliabilityEnvelope
from src.attio.export import execute
from src.attio.ops import UpsertMention


def _op() -> UpsertMention:
    return UpsertMention(
        mention_url="https://reddit.com/r/x/comments/abc",
        last_action="mention_created",
        source_platform="reddit",
        source_id="abc",
        mention_body="hello",
        mention_timestamp=datetime(2026, 5, 10, 11, 55, 53),
        author_handle="u",
        primary_keyword="kw",
    )


def _success(record_id: str) -> ReliabilityEnvelope:
    return ReliabilityEnvelope(
        success=True,
        partial_success=False,
        action="created",
        record_id=record_id,
        warnings=[],
        skipped_fields=[],
        errors=[],
        meta={"output_schema_version": "v1"},
    )


def test_execute_dispatches_upsert_mention() -> None:
    with patch(
        "src.attio.export.libs_upsert_mention",
        return_value=_success("rec-9"),
    ) as handler:
        result = execute([_op()])
    handler.assert_called_once()
    assert result.success is True
    assert result.outcomes[0].op_type == "UpsertMention"
    assert result.outcomes[0].record_id == "rec-9"
