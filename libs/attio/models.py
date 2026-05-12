from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class CompanyInput(BaseModel):
    name: str
    domain: str | None = None
    description: str | None = None


class CompanyResult(BaseModel):
    record_id: str
    name: str | None = None
    domains: list[str] = []
    created: bool = False
    raw: dict[str, Any] = {}


class CompanySearchResult(BaseModel):
    record_id: str
    name: str | None = None
    domains: list[str] = []
    description: str | None = None


class NoteInput(BaseModel):
    title: str
    content: str
    parent_object: str
    parent_record_id: str | None = None
    parent_email: str | None = None
    parent_domain: str | None = None
    format: str = "plaintext"


class NoteResult(BaseModel):
    note_id: str
    title: str
    parent_object: str
    parent_record_id: str
    content_plaintext: str
    created_at: str
    raw: dict[str, Any] = {}


class PersonInput(BaseModel):
    email: str
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    location: str | None = None
    company_domain: str | None = None
    notes: str | None = None
    strict: bool = False
    location_mode: Literal["raw", "city"] = "city"
    additional_emails: list[str] = Field(default_factory=list)
    replace_emails: bool = False


class PersonResult(BaseModel):
    record_id: str
    email_addresses: list[str] = []
    name: str | None = None
    created: bool = False
    raw: dict[str, Any] = {}


class PersonSearchResult(BaseModel):
    record_id: str
    name: str | None = None
    email_addresses: list[str] = []
    phone_numbers: list[str] = []
    linkedin: str | None = None
    location: str | None = None
    company: str | None = None


class MeetingExternalRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ical_uid: str
    provider: Literal["google", "outlook"] = "google"
    is_recurring: bool = False
    original_start_time: str | None = None


class MeetingParticipantInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email_address: str
    is_organizer: bool
    status: Literal["accepted", "tentative", "declined", "pending"] = "accepted"


class MeetingLinkedRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    object: str
    record_id: str


class MeetingInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    external_ref: MeetingExternalRef
    title: str
    description: str
    start: datetime
    end: datetime
    is_all_day: bool = False
    participants: list[MeetingParticipantInput]
    linked_records: list[MeetingLinkedRecord] = Field(default_factory=list)


class MeetingResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meeting_id: str
    workspace_id: str
    title: str
    external_ref_ical_uid: str | None = None
    created: bool = True


class AttributeCreateResult(BaseModel):
    mode: Literal["preview", "apply"]
    attribute_title: str
    attribute_slug: str
    attribute_type: str
    attribute_exists: bool
    attribute_created: bool


class ObjectCreateResult(BaseModel):
    mode: Literal["preview", "apply"]
    api_slug: str
    object_exists: bool
    object_created: bool


class MentionInput(BaseModel):
    """Input payload for the ``social_mention`` custom object.

    Unlike CompanyInput / PersonInput / MeetingInput which target Attio's
    built-in standard objects, this model targets a **custom** object that
    must be bootstrapped into the workspace via
    ``scripts/social_mention_bootstrap.py`` before any upsert succeeds.

    Fields here mirror the webhook-writable attributes only. The CRM-owned
    fields (triage_status, related_person, related_company) are intentionally
    absent so the webhook path cannot overwrite them.
    """

    mention_url: str
    last_action: Literal["mention_created", "mention_updated"]
    source_platform: str
    source_id: str
    mention_title: str | None = None
    mention_body: str
    mention_timestamp: datetime
    author_handle: str
    author_profile_url: str | None = None
    author_avatar_url: str | None = None
    relevance_score: str | None = None
    relevance_comment: str | None = None
    primary_keyword: str
    keywords: list[str] = Field(default_factory=list)
    octolens_tags: list[str] = Field(default_factory=list)
    sentiment: Literal["Positive", "Neutral", "Negative"] | None = None
    language: str | None = None
    subreddit: str | None = None
    view_id: int | None = None
    view_name: str | None = None
    bookmarked: bool = False
    image_url: str | None = None
