from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from libs.granola.models import NormalizedMeeting
from libs.granola.writer import append_manifest, write_meeting_export


def _meeting() -> NormalizedMeeting:
    return NormalizedMeeting(
        id="m_123",
        title="Weekly Sync",
        notes_markdown="Hello",
        transcript_segments=[],
        transcript_source="local",
        transcript_status="missing",
        created_at="2026-03-29T00:00:00Z",
    )


def test_writer_path_and_sidecar_contract(tmp_path: Path) -> None:
    written = write_meeting_export(
        _meeting(),
        tmp_path,
        dt.datetime(2026, 3, 29, tzinfo=dt.UTC),
    )
    assert "notes/2026/2026-03-29_weekly-sync_m_123.md" in str(written.markdown_path)
    assert written.json_path.exists()
    sidecar = json.loads(written.json_path.read_text(encoding="utf-8"))
    assert sidecar["id"] == "m_123"


def test_manifest_appends_one_line_per_record(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.jsonl"
    append_manifest(manifest, {"id": "a"})
    append_manifest(manifest, {"id": "b"})
    assert len(manifest.read_text(encoding="utf-8").strip().splitlines()) == 2
