"""Utilities for Fathom recording webhook pipeline."""

import re
from datetime import datetime
from typing import Any

import flatsplode
import orjson

from libs.fathom.models import ActionItem


def clean_timestamp(dt: datetime) -> str:
    """Convert datetime to clean timestamp format."""
    return dt.strftime("%Y%m%d%H%M%S")


def clean_string(s: str) -> str:
    """Clean string for use in filenames."""
    s = re.sub(r"[^a-zA-Z0-9\s-]", "", s)
    s = re.sub(r"[\s]+", "_", s)
    s = re.sub(r"-+", "-", s)
    return s.lower()


def flatten_recording(recording_dict: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten recording data using flatsplode."""
    flattened = flatsplode.flatsplode(recording_dict)
    if isinstance(flattened, list):
        return flattened
    return list(flattened)


def generate_row_id(recording_id: int, index: int) -> str:
    """Generate unique row ID for flattened record."""
    return f"{recording_id}-{index:05d}"


def recording_to_jsonl(recording_dict: dict[str, Any], recording_id: int) -> str:
    """Convert recording to JSONL with recording_id and per-row id injected."""
    flattened_rows = flatten_recording(recording_dict)
    lines = []
    for i, row in enumerate(flattened_rows):
        row["recording_id"] = recording_id
        row["id"] = generate_row_id(recording_id, i)
        lines.append(orjson.dumps(row).decode("utf-8"))
    return "\n".join(lines) + "\n"


def generate_gcs_filename(
    recording_start_time: datetime,
    recording_id: int,
    meeting_title: str,
) -> str:
    """Generate GCS filename: {clean_timestamp}-{recording_id}-{clean_title}.jsonl"""
    timestamp = clean_timestamp(recording_start_time)
    clean_title = clean_string(meeting_title)
    return f"{timestamp}-{recording_id}-{clean_title}.jsonl"


def _format_timestamp_label(timestamp: str | None) -> str | None:
    if not timestamp:
        return None
    parts = timestamp.split(":")
    if len(parts) not in (2, 3):
        return None
    if not all(p.isdigit() for p in parts):
        return None
    return timestamp


def _format_playback_link(url: str | None, timestamp: str | None) -> str | None:
    if not url or not url.startswith("https://"):
        return None
    label = _format_timestamp_label(timestamp)
    if label is None:
        return None
    return f"[▶ {label}]({url})"


def render_action_items_markdown(items: list[ActionItem]) -> str:
    """Render Fathom action items as a markdown checklist.

    Output shape::

        - [ ] **Alex Doe** — Send deck. [▶ 12:34](https://fathom.video/...)
        - [x] **Sarah Lee** (sarah@example.com) — Confirm budget.

    Rules:
    - ``[x]`` if completed, else ``[ ]``.
    - Bold the assignee name; append ``(email)`` when present.
    - Append a ``[▶ MM:SS](url)`` link only when the URL is https and the
      timestamp parses as ``HH:MM:SS`` or ``MM:SS``.
    - Drop items where both ``description`` and ``assignee.name`` are blank
      (defensive — Fathom occasionally emits empty rows).
    """
    rendered_lines: list[str] = []
    for item in items:
        description = (item.description or "").strip()
        name = (item.assignee.name or "").strip()
        if not description and not name:
            continue

        marker = "[x]" if item.completed else "[ ]"
        who = f"**{name}**" if name else "**(unassigned)**"
        if item.assignee.email:
            who = f"{who} ({item.assignee.email})"

        body = description or "(no description)"
        line = f"- {marker} {who} — {body}"

        link = _format_playback_link(
            item.recording_playback_url,
            item.recording_timestamp,
        )
        if link:
            line = f"{line} {link}"
        rendered_lines.append(line)

    return "\n".join(rendered_lines)


def fathom_summary_title(template_name: str | None) -> str:
    """Build the title used for the Fathom-summary AddNote.

    Fathom ships templates like "General", "Sales Discovery", etc. When
    present, surface the template in the title so a teammate scanning the
    Attio note list immediately recognises which summary template produced it.
    """
    name = (template_name or "").strip()
    if not name:
        return "Fathom summary"
    return f"Fathom summary — {name}"
