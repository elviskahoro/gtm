"""Utilities for Fathom recording webhook pipeline."""

import re
from datetime import datetime
from typing import Any

import flatsplode
import orjson


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
