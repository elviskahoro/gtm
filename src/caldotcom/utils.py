"""Utilities for Cal.com booking webhook pipeline."""

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


def flatten_booking(webhook_dict: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten webhook data using flatsplode."""
    flattened = flatsplode.flatsplode(webhook_dict)
    if isinstance(flattened, list):
        return flattened
    return list(flattened)


def generate_row_id(booking_id: str, index: int) -> str:
    """Generate unique row ID for flattened record."""
    return f"{booking_id}-{index:05d}"


def webhook_to_jsonl(webhook_dict: dict[str, Any], booking_id: str) -> str:
    """Convert webhook to JSONL with booking_id and per-row id injected."""
    flattened_rows = flatten_booking(webhook_dict)
    lines = []
    for i, row in enumerate(flattened_rows):
        row["booking_id"] = booking_id
        row["id"] = generate_row_id(booking_id, i)
        lines.append(orjson.dumps(row).decode("utf-8"))
    return "\n".join(lines) + "\n"


def generate_gcs_filename(
    created_at: datetime,
    trigger_event: str,
    booking_id: str,
) -> str:
    """Generate GCS filename: {clean_timestamp}-{trigger_slug}-{booking_id}.jsonl"""
    timestamp = clean_timestamp(created_at)
    trigger_slug = clean_string(trigger_event)
    safe_booking_id = clean_string(booking_id)
    return f"{timestamp}-{trigger_slug}-{safe_booking_id}.jsonl"
