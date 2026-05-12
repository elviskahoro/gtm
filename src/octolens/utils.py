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
) -> str:
    """Generate GCS filename: {source}-{keyword}-{timestamp}-{author}.jsonl"""
    return (
        f"{clean_string(source)}-{clean_string(keyword)}-"
        f"{clean_timestamp(timestamp)}-{clean_string(author)}.jsonl"
    )
