"""GCS bucket naming convention for raw ETL ingestion.

All webhook → GCS landing buckets follow a single format::

    dlthub-{workspace}-{source}-{entity_plural}-{stage}

Live examples (must match exactly — these are the real bucket names in GCS):

    dlthub-devx-calcom-bookings-raw
    dlthub-devx-fathom-recordings-raw
    dlthub-devx-octolens-mentions-raw
    dlthub-devx-rb2b-visits-raw

Field meanings:

    workspace      Modal workspace / GCP project tier — currently "devx".
    source         Vendor slug (lowercase). Note: caldotcom → "calcom".
    entity_plural  Plural noun for the event ("visits", "bookings",
                   "recordings", "mentions"). Always plural — singulars
                   like "visit" are wrong and will silently miss the
                   real bucket.
    stage          Ingestion stage. Raw landings (pre-transformation)
                   use "raw" via :func:`raw_bucket_name`; post-transform
                   ETL outputs use "etl" via :func:`etl_bucket_name`.

Why this exists: hard-coded strings drift from the actual GCS buckets
and cause 500s on upload. Centralizing the format here means future
contributors only choose ``source`` and ``entity_plural`` — they cannot
get the prefix, separators, or stage suffix wrong.
"""

from __future__ import annotations

WORKSPACE: str = "devx"
RAW_STAGE: str = "raw"
ETL_STAGE: str = "etl"


def raw_bucket_name(
    *,
    source: str,
    entity_plural: str,
) -> str:
    """Build the GCS bucket name for a raw webhook landing.

    Keyword-only to prevent positional mix-ups between ``source`` and
    ``entity_plural`` — they're both short lowercase strings and easy
    to swap.
    """
    return f"dlthub-{WORKSPACE}-{source}-{entity_plural}-{RAW_STAGE}"


def etl_bucket_name(
    *,
    source: str,
    entity_plural: str,
) -> str:
    """Build the GCS bucket name for post-transform ETL output."""
    return f"dlthub-{WORKSPACE}-{source}-{entity_plural}-{ETL_STAGE}"
