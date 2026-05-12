"""Pydantic models for rb2b visit webhook payloads.

rb2b posts an envelope of the shape:

    {
        "event_id": "evt_...",
        "timestamp": "<iso8601>",
        "connection": "<connection name>",
        "payload": {"LinkedIn URL": "...", "Company Name": "...", ...}
    }

The inner payload uses PascalCase-with-spaces keys. Each field aliases the
original key while exposing an idiomatic snake_case Python attribute.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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


class Webhook(BaseModel):
    model_config = ConfigDict(extra="allow")

    event_id: str
    timestamp: datetime
    connection: str
    payload: Payload
