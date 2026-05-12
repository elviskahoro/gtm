"""Pydantic models for Fathom recording webhook payloads.

Fathom posts the recording payload wrapped in a `{"body": "<json string>"}`
envelope. The top-level `Webhook` model accepts either shape — if `body` is
present, it is parsed and used as the source dict; otherwise the dict is
validated directly.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import orjson
from pydantic import BaseModel, ConfigDict, model_validator


class Assignee(BaseModel):
    email: str | None
    name: str
    team: str | None


class ActionItem(BaseModel):
    assignee: Assignee
    completed: bool
    description: str
    recording_playback_url: str
    recording_timestamp: str
    user_generated: bool


class CalendarInvitee(BaseModel):
    email: str
    email_domain: str
    is_external: bool
    matched_speaker_display_name: str | None
    name: str


class CrmCompany(BaseModel):
    name: str
    record_url: str


class CrmContact(BaseModel):
    email: str
    name: str
    record_url: str


class CrmMatches(BaseModel):
    companies: list[CrmCompany] = []
    contacts: list[CrmContact] = []
    deals: list[dict] = []
    error: str | None = None


class RecordedBy(BaseModel):
    email: str
    email_domain: str
    name: str
    team: str


class DefaultSummary(BaseModel):
    markdown_formatted: str
    template_name: str


class TranscriptSpeaker(BaseModel):
    display_name: str
    matched_calendar_invitee_email: str | None


class TranscriptMessage(BaseModel):
    speaker: TranscriptSpeaker
    text: str
    timestamp: str


class Webhook(BaseModel):
    model_config = ConfigDict(extra="allow")

    recording_id: int
    url: str
    share_url: str
    title: str
    meeting_title: str | None = None
    transcript_language: str
    created_at: datetime
    scheduled_start_time: datetime
    scheduled_end_time: datetime
    recording_start_time: datetime
    recording_end_time: datetime
    calendar_invitees_domains_type: str

    recorded_by: RecordedBy
    default_summary: DefaultSummary | None = None
    crm_matches: CrmMatches | None = None

    calendar_invitees: list[CalendarInvitee] = []
    action_items: list[ActionItem] | None = None
    transcript: list[TranscriptMessage] | None = None

    @model_validator(mode="before")
    @classmethod
    def _unwrap_body(cls, data: Any) -> Any:
        if isinstance(data, dict) and "body" in data and "recording_id" not in data:
            body = data["body"]
            if isinstance(body, (bytes, bytearray, memoryview)):
                return orjson.loads(body)
            if isinstance(body, str):
                return orjson.loads(body)
        return data
