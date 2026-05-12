"""Pydantic models for Octolens mention webhook payloads.

Hookdeck wraps deliveries in a ``{"body": "<json string>"}`` envelope. The
top-level ``Webhook`` model accepts either shape — if ``body`` is present and
the dict does not already look unwrapped, ``body`` is parsed and used as the
source dict; otherwise the dict is validated directly.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import orjson
from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class Mention(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    url: str = Field(validation_alias=AliasChoices("url", "URL"))
    title: str | None = Field(
        default=None,
        validation_alias=AliasChoices("title", "Title"),
    )
    body: str = Field(validation_alias=AliasChoices("body", "Body"))
    timestamp: datetime = Field(validation_alias=AliasChoices("timestamp", "Timestamp"))
    image_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("image_url", "Image URL", "imageUrl"),
    )
    source: str = Field(validation_alias=AliasChoices("source", "Source"))
    source_id: str = Field(
        validation_alias=AliasChoices("source_id", "Source ID", "sourceId"),
    )
    author: str = Field(validation_alias=AliasChoices("author", "Author"))
    author_avatar_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "author_avatar_url",
            "Author Avatar URL",
            "authorAvatarUrl",
        ),
    )
    author_profile_link: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "author_profile_link",
            "Author Profile Link",
            "authorProfileLink",
        ),
    )
    relevance_score: str = Field(
        validation_alias=AliasChoices(
            "relevance_score",
            "Relevance Score",
            "relevanceScore",
        ),
    )
    relevance_comment: str = Field(
        validation_alias=AliasChoices(
            "relevance_comment",
            "Relevance Comment",
            "relevanceComment",
        ),
    )
    language: str | None = Field(
        default=None,
        validation_alias=AliasChoices("language", "Language"),
    )
    keyword: str = Field(validation_alias=AliasChoices("keyword", "Keyword"))
    keywords: list[str] = Field(default_factory=list)
    sentiment_label: str | None = Field(
        default=None,
        validation_alias=AliasChoices("sentiment_label", "sentimentLabel"),
    )
    tags: list[Any] = Field(default_factory=list)
    view_id: int | None = Field(
        default=None,
        validation_alias=AliasChoices("view_id", "viewId"),
    )
    view_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices("view_name", "viewName"),
    )
    view_keywords: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("view_keywords", "viewKeywords"),
    )
    subreddit: str | None = None
    bookmarked: bool = False

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if not isinstance(value, str):
            error_msg: str = f"Invalid timestamp format: {value}"
            raise TypeError(error_msg)

        # Live Octolens form, e.g. "2026-05-10 11:55:53.000"
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            pass

        # Legacy GMT form, e.g. "Mon Jan 15 2024 10:30:00 GMT+0000"
        try:
            return datetime.strptime(value, "%a %b %d %Y %H:%M:%S GMT%z")
        except ValueError:
            pass

        # ISO 8601 fallback
        try:
            return datetime.fromisoformat(value)
        except ValueError as e:
            error_msg = f"Invalid timestamp format: {value}"
            raise ValueError(error_msg) from e


class Webhook(BaseModel):
    model_config = ConfigDict(extra="allow")

    action: str = "mention_created"
    data: Mention

    @model_validator(mode="before")
    @classmethod
    def _unwrap_body(cls, data: Any) -> Any:
        if isinstance(data, dict) and "body" in data and "action" not in data:
            body = data["body"]
            if isinstance(body, (bytes, bytearray, memoryview)):
                return orjson.loads(body)
            if isinstance(body, str):
                return orjson.loads(body)
        return data
