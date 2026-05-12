from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha1

UID_PREFIX = "dlt-mtg-"


def canonical_meeting_uid(*, host_email: str, start: datetime) -> str:
    """Deterministic Attio ical_uid shared across Cal.com and Fathom webhooks.

    Two webhooks for the same meeting must produce the same string so Attio's
    find_or_create_meeting collapses them. Inputs are normalized before hashing:
    host_email lowercased/stripped, start coerced to UTC and truncated to the
    minute.
    """
    email = (host_email or "").strip().casefold()
    if not email:
        raise ValueError("host_email required for canonical_meeting_uid")
    if start.tzinfo is None:
        raise ValueError("start must be timezone-aware")
    minute = start.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M")
    digest = sha1(  # noqa: S324 — identifier hash, not security
        f"{email}|{minute}".encode(),
        usedforsecurity=False,
    ).hexdigest()[:24]
    return f"{UID_PREFIX}{digest}"
