"""Attio operation vocabulary.

Source-agnostic Pydantic models that describe what to write to Attio. Each
source webhook produces a list of ``AttioOp`` values; the dispatcher in
``src.attio.export`` turns them into Attio SDK calls.

This module imports only from ``pydantic``. It does NOT import from
``libs.attio.*`` so the vocabulary stays a pure data definition. Conversion
between ops and lib-side input types lives in the dispatcher.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field


class PersonRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ref_kind: Literal["person"] = "person"
    email: str


class CompanyRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ref_kind: Literal["company"] = "company"
    domain: str


class MeetingRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ref_kind: Literal["meeting"] = "meeting"
    # Matches libs.attio.models.MeetingExternalRef.ical_uid — the key the
    # dispatcher's LookupTable uses to resolve meetings already created earlier
    # in the same plan.
    ical_uid: str


Ref = Annotated[
    Union[PersonRef, CompanyRef, MeetingRef],
    Field(discriminator="ref_kind"),
]


class MeetingExternalRef(BaseModel):
    """Mirror of ``libs.attio.models.MeetingExternalRef``.

    Duplicated so this module can stay free of ``libs/*`` imports. The
    dispatcher copies field-by-field into the lib-side type.
    """

    model_config = ConfigDict(extra="forbid")

    ical_uid: str
    provider: Literal["google", "outlook"] = "google"
    is_recurring: bool = False
    original_start_time: str | None = None


class MeetingParticipant(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email_address: str
    is_organizer: bool
    # Sources without a real RSVP signal (e.g. Fathom) should leave the default;
    # Cal.com and other sources with actual status should pass it through.
    status: Literal["accepted", "tentative", "declined", "pending"] = "accepted"


class UpsertPerson(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op_type: Literal["upsert_person"] = "upsert_person"
    email: str
    first_name: str | None = None
    last_name: str | None = None
    linkedin: str | None = None
    phone: str | None = None
    company_domain: str | None = None


class UpsertCompany(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op_type: Literal["upsert_company"] = "upsert_company"
    domain: str
    name: str | None = None


class UpsertMeeting(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op_type: Literal["upsert_meeting"] = "upsert_meeting"
    external_ref: MeetingExternalRef
    title: str
    description: str
    start: datetime
    end: datetime
    is_all_day: bool = False
    participants: list[MeetingParticipant]
    linked_records: list[Ref] = Field(default_factory=list)


class AddNote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op_type: Literal["add_note"] = "add_note"
    parent: Ref
    title: str
    content: str


class UpsertMention(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op_type: Literal["upsert_mention"] = "upsert_mention"
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


AttioOp = Annotated[
    Union[UpsertPerson, UpsertCompany, UpsertMeeting, AddNote, UpsertMention],
    Field(discriminator="op_type"),
]
