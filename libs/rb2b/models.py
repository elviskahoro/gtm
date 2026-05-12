"""Pydantic models for rb2b visit webhook payloads.

rb2b can deliver visits in two shapes:

1. The internal envelope used by saved samples / Hookdeck replays::

       {
           "event_id": "evt_...",
           "timestamp": "<iso8601>",
           "connection": "<connection name>",
           "payload": {"LinkedIn URL": "...", "Company Name": "...", ...}
       }

2. The direct-from-rb2b shape documented at
   https://support.rb2b.com/en/articles/8976614-setup-guide-webhook —
   the visit fields are flat at the top level with no envelope.

``Webhook`` accepts either shape via a ``model_validator(mode="before")``
that synthesizes an envelope when one is missing. The inner payload uses
PascalCase-with-spaces keys, aliased to snake_case Python attributes.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

_RB2B_DOC_TS_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})[T ]"
    r"(?P<h>\d{2}):(?P<m>\d{2}):(?P<s>\d{2}):(?P<frac>\d+(?:\.\d+)?)"
    r"(?P<tzsign>[+-])(?P<tzh>\d{2})\.(?P<tzm>\d{2})$",
)


def _normalize_rb2b_timestamp(value: Any) -> Any:
    """Normalize rb2b's documented `12:34:56:00.00+00.00` shape to ISO 8601.

    rb2b's own webhook docs sometimes emit timestamps where the
    sub-second separator is ``:`` instead of ``.`` and the tz offset is
    dot-separated (e.g. ``12:34:56:00.00+00.00``). Pydantic v2 rejects
    that form. We rewrite it to a valid ISO 8601 string; other formats
    pass through unchanged so pydantic can apply its built-in parsing.
    """
    if not isinstance(value, str):
        return value
    match = _RB2B_DOC_TS_RE.match(value)
    if match is None:
        return value
    g = match.groupdict()
    frac = g["frac"].replace(".", "")
    return (
        f"{g['date']}T{g['h']}:{g['m']}:{g['s']}.{frac}"
        f"{g['tzsign']}{g['tzh']}:{g['tzm']}"
    )


class Payload(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    linkedin_url: str | None = Field(default=None, alias="LinkedIn URL")
    first_name: str | None = Field(default=None, alias="First Name")
    last_name: str | None = Field(default=None, alias="Last Name")
    title: str | None = Field(default=None, alias="Title")
    company_name: str | None = Field(default=None, alias="Company Name")
    business_email: str | None = Field(default=None, alias="Business Email")
    website: str | None = Field(default=None, alias="Website")
    industry: str | None = Field(default=None, alias="Industry")
    employee_count: str | None = Field(default=None, alias="Employee Count")
    estimate_revenue: str | None = Field(default=None, alias="Estimate Revenue")
    city: str | None = Field(default=None, alias="City")
    state: str | None = Field(default=None, alias="State")
    zipcode: str | None = Field(default=None, alias="Zipcode")
    seen_at: datetime | None = Field(default=None, alias="Seen At")
    referrer: str | None = Field(default=None, alias="Referrer")
    tags: str | None = Field(default=None, alias="Tags")
    captured_url: str | None = Field(default=None, alias="Captured URL")
    is_repeat_visit: bool | None = None

    @field_validator("employee_count", mode="before")
    @classmethod
    def _coerce_employee_count(cls, value: Any) -> Any:
        """rb2b documents Employee Count as `integer, string, null`."""
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return str(value)
        return value

    @field_validator("seen_at", mode="before")
    @classmethod
    def _normalize_seen_at(cls, value: Any) -> Any:
        return _normalize_rb2b_timestamp(value)


_ENVELOPE_KEYS = frozenset({"event_id", "timestamp", "connection", "payload"})


class Webhook(BaseModel):
    model_config = ConfigDict(extra="allow")

    event_id: str
    timestamp: datetime
    connection: str
    payload: Payload

    @model_validator(mode="before")
    @classmethod
    def _wrap_flat_payload(cls, data: Any) -> Any:
        """Synthesize an envelope when rb2b posts the visit flat.

        Direct rb2b webhook deliveries put visit fields at the top level
        without an envelope. Detect that shape (no envelope keys + a
        recognizable visit key) and wrap it so the rest of the model
        sees the canonical structure. ``seen_at`` is also normalized
        here so the synthesized envelope timestamp is parseable.
        """
        if not isinstance(data, dict):
            return data
        if "payload" in data or _ENVELOPE_KEYS.issubset(data.keys()):
            return data
        looks_flat = any(
            key in data
            for key in ("LinkedIn URL", "Company Name", "Seen At", "Captured URL")
        )
        if not looks_flat:
            return data

        seen_at = _normalize_rb2b_timestamp(data.get("Seen At"))
        envelope_ts = (
            seen_at
            if isinstance(seen_at, str)
            else datetime.now(timezone.utc).isoformat()
        )
        flat_payload = dict(data)
        if seen_at is not None:
            flat_payload["Seen At"] = seen_at
        return {
            "event_id": data.get("event_id") or f"evt_{uuid.uuid4().hex}",
            "timestamp": envelope_ts,
            "connection": data.get("connection") or "rb2b-direct",
            "payload": flat_payload,
        }
