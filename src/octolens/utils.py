"""Utilities for Octolens mention webhook pipeline."""

import re
from datetime import datetime


def clean_timestamp(dt: datetime) -> str:
    """Convert datetime to clean timestamp format."""
    return dt.strftime("%Y%m%d%H%M%S")


def clean_string(s: str) -> str:
    """Clean string for use in filenames."""
    s = re.sub(r"[^a-zA-Z0-9\s-]", "", s)
    s = re.sub(r"[\s]+", "_", s)
    s = re.sub(r"-+", "-", s)
    return s.lower()


def generate_gcs_filename(
    source: str,
    keyword: str,
    timestamp: datetime,
    author: str,
    source_id: str,
) -> str:
    """Generate GCS filename: {source}-{keyword}-{timestamp}-{author}-{source_id}.jsonl

    ``source_id`` is the Octolens-supplied stable mention identifier and is
    included to prevent collisions when two mentions share the same
    source/keyword/author/second-truncated timestamp (the GCS writer opens
    objects with ``mode="w"``, so collisions would overwrite earlier deliveries).
    """
    return (
        f"{clean_string(source)}-{clean_string(keyword)}-"
        f"{clean_timestamp(timestamp)}-{clean_string(author)}-"
        f"{clean_string(source_id)}.jsonl"
    )
