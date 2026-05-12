from __future__ import annotations

from datetime import datetime

from libs.attio.models import MentionInput, PersonInput
from libs.attio.values import (
    build_core_person_values,
    build_create_mention_values,
    build_optional_person_values,
    build_update_mention_values,
    format_location,
)


def test_format_location_city_mode_drops_street_granularity() -> None:
    value = format_location("123 Main St, San Francisco, CA", mode="city")
    assert value is not None
    assert value[0]["line_1"] is None
    assert value[0]["locality"] == "123 Main St"
    assert value[0]["region"] == "San Francisco"


def test_build_optional_person_values_serializes_notes_and_company() -> None:
    values = build_optional_person_values(
        company_domain="acme.com",
        notes="met at conference",
        location="San Francisco, CA",
        location_mode="city",
    )
    assert "associated_company" in values
    assert "notes" in values
    assert "primary_location" in values


def test_build_core_person_values_combines_primary_and_additional_emails() -> None:
    inp = PersonInput(
        email="a@example.com",
        additional_emails=["b@example.com", "a@example.com"],
    )
    values = build_core_person_values(inp)
    assert sorted(values["email_addresses"]) == ["a@example.com", "b@example.com"]


def test_build_core_person_values_partial_omits_emails_when_not_explicit() -> None:
    inp = PersonInput(email="lookup@example.com", first_name="X")
    values = build_core_person_values(inp, partial=True)
    assert "email_addresses" not in values


def test_location_mode_raw_retains_line_1() -> None:
    input_data = PersonInput(
        email="a@example.com",
        location="123 Main, SF, CA",
        location_mode="raw",
    )
    values = build_optional_person_values(
        company_domain=input_data.company_domain,
        notes=input_data.notes,
        location=input_data.location,
        location_mode=input_data.location_mode,
    )
    assert values["primary_location"][0]["line_1"] == "123 Main"


# ---------- Octolens mentions ----------


def _sample_mention() -> MentionInput:
    return MentionInput(
        mention_url="https://reddit.com/r/x/comments/abc",
        last_action="mention_created",
        source_platform="reddit",
        source_id="abc",
        mention_title=None,
        mention_body="hello",
        mention_timestamp=datetime(2026, 5, 10, 11, 55, 53),
        author_handle="someuser",
        author_profile_url="https://reddit.com/u/someuser",
        author_avatar_url=None,
        relevance_score="0.85",
        relevance_comment="strong relevance",
        primary_keyword="deepline",
        keywords=["gtm", "outbound"],
        octolens_tags=["competitor"],
        sentiment="Positive",
        language="en",
        subreddit="r/example",
        view_id=42,
        view_name="GTM watch",
        bookmarked=False,
        image_url=None,
    )


HUMAN_OWNED = {"triage_status", "related_person", "related_company"}


def test_create_builder_includes_all_writable_fields() -> None:
    values = build_create_mention_values(_sample_mention())
    assert "mention_url" in values
    assert "source_platform" in values
    assert "source_id" in values
    assert "relevance_score" in values
    assert "keywords" in values
    assert "octolens_tags" in values


def test_create_builder_never_includes_human_owned_fields() -> None:
    values = build_create_mention_values(_sample_mention())
    assert HUMAN_OWNED.isdisjoint(values.keys())


def test_update_builder_omits_immutable_fields() -> None:
    values = build_update_mention_values(_sample_mention())
    assert "source_platform" not in values
    assert "source_id" not in values


def test_update_builder_never_includes_human_owned_fields() -> None:
    values = build_update_mention_values(_sample_mention())
    assert HUMAN_OWNED.isdisjoint(values.keys())


def test_create_builder_handles_null_optionals() -> None:
    sample = _sample_mention()
    sample.mention_title = None
    sample.subreddit = None
    values = build_create_mention_values(sample)
    assert "mention_body" in values
