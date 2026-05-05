from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from libs.granola.errors import WriteError
from libs.granola.models import NormalizedMeeting, WrittenPaths

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(value: str) -> str:
    slug = _SLUG_RE.sub("-", value.lower()).strip("-")
    return slug or "untitled"


def _meeting_date(meeting: NormalizedMeeting, exported_at: dt.datetime) -> dt.date:
    raw = meeting.created_at
    if raw:
        try:
            return dt.datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
        except ValueError:
            pass
    return exported_at.date()


def write_meeting_export(
    meeting: NormalizedMeeting,
    output_root: Path,
    exported_at: dt.datetime,
) -> WrittenPaths:
    try:
        meeting_date = _meeting_date(meeting, exported_at)
        year = str(meeting_date.year)
        slug = _slugify(meeting.title)
        stem = f"{meeting_date.isoformat()}_{slug}_{meeting.id}"
        base = output_root / "notes" / year
        markdown_path = base / f"{stem}.md"
        json_path = base / f"{stem}.json"
        base.mkdir(parents=True, exist_ok=True)

        markdown = (
            "\n".join(
                [
                    f"# {meeting.title}",
                    "",
                    meeting.notes_markdown,
                    "",
                    "## Transcript",
                    "",
                    *[
                        f"- {segment.speaker + ': ' if segment.speaker else ''}{segment.text}"
                        for segment in meeting.transcript_segments
                    ],
                ],
            ).rstrip()
            + "\n"
        )

        markdown_path.write_text(markdown, encoding="utf-8")
        json_path.write_text(
            json.dumps(meeting.model_dump(mode="json"), ensure_ascii=False, indent=2)
            + "\n",
            encoding="utf-8",
        )
        return WrittenPaths(markdown_path=markdown_path, json_path=json_path)
    except OSError as exc:
        raise WriteError(str(exc)) from exc


def append_manifest(manifest_path: Path, entry: dict[str, Any]) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.open("a", encoding="utf-8").write(
        json.dumps(entry, ensure_ascii=False) + "\n",
    )
