"""Utilities for rb2b visit webhook pipeline."""

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


def flatten_event(event_dict: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten event data using flatsplode."""
    flattened = flatsplode.flatsplode(event_dict)
    if isinstance(flattened, list):
        return flattened
    return list(flattened)


def generate_row_id(event_id: str, index: int) -> str:
    """Generate unique row ID for flattened record."""
    return f"{event_id}-{index:05d}"


def event_to_jsonl(event_dict: dict[str, Any], event_id: str) -> str:
    """Convert event to JSONL with event_id and per-row id injected."""
    flattened_rows = flatten_event(event_dict)
    lines = []
    for i, row in enumerate(flattened_rows):
        row["event_id"] = event_id
        row["id"] = generate_row_id(event_id, i)
        lines.append(orjson.dumps(row).decode("utf-8"))
    return "\n".join(lines) + "\n"


def generate_gcs_filename(
    timestamp: datetime,
    event_id: str,
    company_name: str | None,
) -> str:
    """Generate GCS filename: {clean_timestamp}-{event_id}-{clean_company}.jsonl"""
    ts = clean_timestamp(timestamp)
    company = clean_string(company_name) if company_name else "unknown"
    return f"{ts}-{event_id}-{company}.jsonl"
