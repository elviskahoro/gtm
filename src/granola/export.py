from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

from libs.granola.errors import ConfigError
from libs.granola.local_cache import (
    extract_local_records,
    find_latest_cache_file,
    load_local_cache,
)
from libs.granola.models import ExportRunOptions, ExportRunResult
from libs.granola.normalize import normalize_meeting
from libs.granola.state import (
    compute_meeting_hash,
    load_state,
    save_state,
    should_write,
)
from libs.granola.writer import append_manifest, write_meeting_export


def _load_previous_sidecar(output_root: Path, meeting_id: str) -> dict[str, Any] | None:
    for path in output_root.glob(f"notes/*/*_{meeting_id}.json"):
        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue
    return None


def run_export(options: ExportRunOptions) -> ExportRunResult:
    if options.source == "api" and not options.api_key:
        raise ConfigError("GRANOLA_API_KEY is required for --source api")

    cache_file = find_latest_cache_file(options.granola_dir)
    payload = load_local_cache(cache_file)
    documents, transcripts = extract_local_records(payload)

    state_path = options.output_root / "state.json"
    manifest_path = options.output_root / "manifest.jsonl"
    state = load_state(state_path)

    processed = 0
    written = 0
    skipped = 0
    errors = 0
    now = options.now or dt.datetime.now(dt.UTC)

    for key, doc in documents.items():
        processed += 1
        if not isinstance(doc, dict):
            errors += 1
            append_manifest(
                manifest_path,
                {"id": str(key), "status": "error", "error": "invalid document"},
            )
            continue

        try:
            meeting_id = str(doc.get("id", "")).strip()
            if not meeting_id:
                raise ConfigError("document id missing")
            local_transcript = transcripts.get(meeting_id)
            api_note = (options.api_notes or {}).get(meeting_id)
            previous_export = _load_previous_sidecar(options.output_root, meeting_id)
            meeting = normalize_meeting(
                doc,
                local_transcript,
                api_note,
                previous_export,
            )
            digest = compute_meeting_hash(meeting)

            if not should_write(meeting.id, digest, state):
                skipped += 1
                append_manifest(manifest_path, {"id": meeting.id, "status": "skipped"})
                continue

            written_paths = write_meeting_export(meeting, options.output_root, now)
            state.hashes[meeting.id] = digest
            written += 1
            append_manifest(
                manifest_path,
                {
                    "id": meeting.id,
                    "status": "written",
                    "markdown_path": str(written_paths.markdown_path),
                    "json_path": str(written_paths.json_path),
                },
            )
        except Exception as exc:  # noqa: BLE001
            errors += 1
            append_manifest(
                manifest_path,
                {"id": str(doc.get("id", key)), "status": "error", "error": str(exc)},
            )

    save_state(state_path, state)

    return ExportRunResult(
        source=options.source,
        processed=processed,
        written=written,
        skipped=skipped,
        errors=errors,
        manifest_path=str(manifest_path),
        state_path=str(state_path),
    )
