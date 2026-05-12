"""Tests for libs/octolens/models.py — Mention + Webhook validation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from libs.octolens import Mention, Webhook

FIXTURES_DIR = Path(__file__).parent / "fixtures"
EVENTS_PATH = FIXTURES_DIR / "events.json"
ALL_PAYLOADS_PATH = FIXTURES_DIR / "all_payloads.txt"


def _parse_all_payloads(path: Path) -> list[dict[str, object]]:
    """Split all_payloads.txt on '=== Event:' delimiter and parse each envelope."""
    text = path.read_text()
    chunks = text.split("=== Event:")
    envelopes: list[dict[str, object]] = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        # Drop the "evt_xxx ===" header line; the rest is JSON.
        _, _, body = chunk.partition("===")
        body = body.strip()
        if not body:
            continue
        envelopes.append(json.loads(body))
    return envelopes


def test_webhook_unwrapped_form_validates() -> None:
    payload = json.loads(EVENTS_PATH.read_text())
    webhook = Webhook.model_validate(payload)
    assert webhook.action == "mention_created"
    assert isinstance(webhook.data, Mention)
    assert webhook.data.source == "reddit"
    assert webhook.data.keyword == "snowflake"
    assert webhook.data.author == "Sensitive_Pianist777"
    assert "snowflake" in webhook.data.keywords
    assert "snowflake" in webhook.data.view_keywords
    assert webhook.data.subreddit == "r/generationology"


def test_webhook_wrapped_hookdeck_form_validates() -> None:
    """Real Hookdeck deliveries arrive as {'body': '<json string>'}."""
    envelopes = _parse_all_payloads(ALL_PAYLOADS_PATH)
    assert len(envelopes) > 0, "expected at least one event in all_payloads.txt"

    success = 0
    failures: list[tuple[int, str]] = []
    for i, env in enumerate(envelopes):
        try:
            webhook = Webhook.model_validate(env)
            assert webhook.action in {"mention_created", "mention_updated"}
            assert isinstance(webhook.data, Mention)
            success += 1
        except ValidationError as exc:
            failures.append((i, str(exc)))

    assert not failures, (
        f"{len(failures)}/{len(envelopes)} payloads failed validation. "
        f"First failure (index {failures[0][0]}): {failures[0][1][:500]}"
    )
    assert success == len(envelopes)


def test_unwrap_body_with_bytes() -> None:
    payload = json.loads(EVENTS_PATH.read_text())
    raw = json.dumps(payload).encode("utf-8")
    webhook = Webhook.model_validate({"body": raw})
    assert webhook.action == "mention_created"
    assert webhook.data.source == "reddit"


def test_timestamp_live_format() -> None:
    mention = Mention.model_validate(
        {
            "url": "https://test.com",
            "body": "x",
            "timestamp": "2026-05-10 11:55:53.000",
            "source": "reddit",
            "sourceId": "abc",
            "author": "user",
            "relevanceScore": "low",
            "relevanceComment": "n/a",
            "language": "english",
            "keyword": "snowflake",
        },
    )
    assert mention.timestamp.year == 2026
    assert mention.timestamp.month == 5
    assert mention.timestamp.day == 10
    assert mention.timestamp.hour == 11
    assert mention.timestamp.minute == 55
    assert mention.timestamp.second == 53


def test_timestamp_legacy_gmt_format() -> None:
    mention = Mention.model_validate(
        {
            "url": "https://test.com",
            "body": "x",
            "timestamp": "Mon Jan 15 2024 10:30:00 GMT+0000",
            "source": "twitter",
            "sourceId": "abc",
            "author": "user",
            "relevanceScore": "high",
            "relevanceComment": "n/a",
            "language": "en",
            "keyword": "test",
        },
    )
    assert mention.timestamp.year == 2024
    assert mention.timestamp.tzinfo == timezone.utc


def test_timestamp_iso_format() -> None:
    mention = Mention.model_validate(
        {
            "url": "https://test.com",
            "body": "x",
            "timestamp": "2024-01-15T10:30:00+00:00",
            "source": "twitter",
            "sourceId": "abc",
            "author": "user",
            "relevanceScore": "high",
            "relevanceComment": "n/a",
            "language": "en",
            "keyword": "test",
        },
    )
    assert mention.timestamp == datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)


def test_timestamp_rejects_non_string() -> None:
    with pytest.raises((TypeError, ValidationError)):
        Mention.model_validate(
            {
                "url": "https://test.com",
                "body": "x",
                "timestamp": 1705315800,
                "source": "twitter",
                "sourceId": "abc",
                "author": "user",
                "relevanceScore": "high",
                "relevanceComment": "n/a",
                "language": "en",
                "keyword": "test",
            },
        )


def test_timestamp_rejects_garbage_string() -> None:
    with pytest.raises(ValidationError):
        Mention.model_validate(
            {
                "url": "https://test.com",
                "body": "x",
                "timestamp": "not-a-date",
                "source": "twitter",
                "sourceId": "abc",
                "author": "user",
                "relevanceScore": "high",
                "relevanceComment": "n/a",
                "language": "en",
                "keyword": "test",
            },
        )


def test_camel_case_aliases() -> None:
    mention = Mention.model_validate(
        {
            "url": "https://test.com",
            "body": "x",
            "timestamp": "2024-01-15T10:30:00+00:00",
            "source": "twitter",
            "sourceId": "tweet_1",
            "author": "u",
            "authorAvatarUrl": "https://a",
            "authorProfileLink": "https://p",
            "relevanceScore": "high",
            "relevanceComment": "n/a",
            "language": "en",
            "keyword": "test",
        },
    )
    assert mention.source_id == "tweet_1"
    assert mention.author_avatar_url == "https://a"
    assert mention.author_profile_link == "https://p"
