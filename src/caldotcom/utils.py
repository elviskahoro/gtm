"""Utilities for Cal.com webhook pipeline."""

import re
from datetime import datetime
from typing import Any

import flatsplode
import orjson
from gcsfs import GCSFileSystem


def clean_timestamp(dt: datetime) -> str:
    """Convert datetime to clean timestamp format."""
    return dt.strftime("%Y%m%d%H%M%S")


def clean_string(s: str) -> str:
    """Clean string for use in filenames."""
    # Remove special characters and replace spaces with underscores
    s = re.sub(r"[^a-zA-Z0-9\s-]", "", s)
    s = re.sub(r"[\s]+", "_", s)
    s = re.sub(r"-+", "-", s)
    return s.lower()


def flatten_booking(booking_dict: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten booking data using flatsplode."""
    flattened = flatsplode.flatsplode(booking_dict)
    # flatsplode returns a generator, convert to list
    if not isinstance(flattened, list):
        flattened = list(flattened)
    return flattened


def generate_row_id(uid: str, index: int) -> str:
    """Generate unique row ID for flattened record."""
    return f"{uid}-{index:05d}"


def booking_to_jsonl(booking_dict: dict[str, Any], uid: str) -> str:
    """Convert booking to JSONL format with booking_uid injected."""
    flattened_rows = flatten_booking(booking_dict)
    lines = []
    for i, row in enumerate(flattened_rows):
        if isinstance(row, dict):
            row["booking_uid"] = uid
            row["id"] = generate_row_id(uid, i)
            lines.append(orjson.dumps(row).decode("utf-8"))
    return "\n".join(lines) + "\n"


def generate_gcs_filename(start: datetime, uid: str, title: str) -> str:
    """Generate GCS filename following convention: {clean_timestamp}-{uid}-{clean_title}.jsonl"""
    timestamp = clean_timestamp(start)
    clean_title = clean_string(title)
    return f"{timestamp}-{uid}-{clean_title}.jsonl"


def write_to_gcs(bucket: str, key: str, data: str | bytes) -> None:
    """Write data to GCS bucket."""
    fs = GCSFileSystem()
    gcs_path = f"gs://{bucket}/{key}"
    binary_data: bytes = data.encode("utf-8") if isinstance(data, str) else data
    with fs.open(gcs_path, "wb") as f:
        f.write(binary_data)


def read_from_gcs(bucket: str, key: str) -> str:
    """Read data from GCS bucket."""
    fs = GCSFileSystem()
    gcs_path = f"gs://{bucket}/{key}"
    with fs.open(gcs_path, "rb") as f:
        data = f.read()
        return data.decode("utf-8") if isinstance(data, bytes) else data
