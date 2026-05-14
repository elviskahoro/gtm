from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.attio.ops import UpsertMention, UpsertPerson
from src.octolens.webhook.mention import (
    Webhook,
    normalize_linkedin_profile_url,
    split_author_name,
)

SAMPLES_DIR = Path(__file__).resolve().parents[4] / "api" / "samples"

SAMPLE_FILES = [
    "octolens.mention.created.reddit.redacted.json",
    "octolens.mention.created.twitter.redacted.json",
    "octolens.mention.created.bluesky.redacted.json",
    "octolens.mention.created.hackernews.redacted.json",
    "octolens.mention.created.dev.redacted.json",
    "octolens.mention.created.podcasts.redacted.json",
]

NON_LINKEDIN_SAMPLE_FILES = SAMPLE_FILES

LINKEDIN_SAMPLE_FILE = "octolens.mention.created.linkedin.redacted.json"


@pytest.mark.parametrize("filename", SAMPLE_FILES)
def test_sample_produces_single_upsert_mention_op(filename: str) -> None:
    payload = json.loads((SAMPLES_DIR / filename).read_text())
    webhook = Webhook.model_validate(payload)

    assert webhook.attio_is_valid_webhook() is True
    ops = webhook.attio_get_operations()
    assert len(ops) == 1
    op = ops[0]
    assert isinstance(op, UpsertMention)
    assert op.mention_url == webhook.data.url
    assert op.last_action == webhook.action
    assert op.source_platform == webhook.data.source
    assert op.source_id == webhook.data.source_id
    assert op.author_handle == webhook.data.author
    assert op.primary_keyword == webhook.data.keyword


def test_unknown_action_disables_attio_export() -> None:
    payload = json.loads((SAMPLES_DIR / SAMPLE_FILES[0]).read_text())
    payload["action"] = "mention_archived"
    webhook = Webhook.model_validate(payload)
    assert webhook.attio_is_valid_webhook() is False
    assert webhook.attio_get_operations() == []


def test_linkedin_sample_produces_upsert_person_and_mention() -> None:
    payload = json.loads((SAMPLES_DIR / LINKEDIN_SAMPLE_FILE).read_text())
    webhook = Webhook.model_validate(payload)

    assert webhook.attio_is_valid_webhook() is True
    ops = webhook.attio_get_operations()
    assert len(ops) == 2

    # First op: UpsertPerson
    person_op = ops[0]
    assert isinstance(person_op, UpsertPerson)
    assert person_op.linkedin == "https://www.linkedin.com/in/linkedin-user"
    assert person_op.first_name == "Linkedin"
    assert person_op.last_name == "User"

    # Second op: UpsertMention with related_person
    mention_op = ops[1]
    assert isinstance(mention_op, UpsertMention)
    assert mention_op.mention_url == webhook.data.url
    assert mention_op.source_platform == "linkedin"
    assert mention_op.author_handle == "Linkedin User"
    assert mention_op.related_person is not None
    assert mention_op.related_person.attribute == "linkedin"
    assert (
        mention_op.related_person.value
        == "https://www.linkedin.com/in/linkedin-user"
    )


@pytest.mark.parametrize("filename", NON_LINKEDIN_SAMPLE_FILES)
def test_non_linkedin_sample_produces_only_mention(filename: str) -> None:
    payload = json.loads((SAMPLES_DIR / filename).read_text())
    webhook = Webhook.model_validate(payload)

    ops = webhook.attio_get_operations()
    assert len(ops) == 1
    op = ops[0]
    assert isinstance(op, UpsertMention)
    assert op.related_person is None


def test_normalize_linkedin_profile_url_valid_urls() -> None:
    assert (
        normalize_linkedin_profile_url("https://www.linkedin.com/in/linkedin-user")
        == "https://www.linkedin.com/in/linkedin-user"
    )
    assert (
        normalize_linkedin_profile_url("https://linkedin.com/in/linkedin-user")
        == "https://www.linkedin.com/in/linkedin-user"
    )
    assert (
        normalize_linkedin_profile_url("http://www.linkedin.com/in/linkedin-user")
        == "https://www.linkedin.com/in/linkedin-user"
    )
    assert (
        normalize_linkedin_profile_url("https://www.linkedin.com/in/linkedin-user/")
        == "https://www.linkedin.com/in/linkedin-user"
    )
    assert (
        normalize_linkedin_profile_url(
            "https://www.linkedin.com/in/linkedin-user?utm=test",
        )
        == "https://www.linkedin.com/in/linkedin-user"
    )
    assert (
        normalize_linkedin_profile_url("https://www.linkedin.com/in/LinkedinUser")
        == "https://www.linkedin.com/in/LinkedinUser"
    )


def test_normalize_linkedin_profile_url_invalid_urls() -> None:
    assert (
        normalize_linkedin_profile_url("https://www.linkedin.com/company/example")
        is None
    )
    assert (
        normalize_linkedin_profile_url("https://www.linkedin.com/feed/update/123")
        is None
    )
    assert normalize_linkedin_profile_url("https://www.linkedin.com/posts/") is None
    assert normalize_linkedin_profile_url("not a url") is None
    assert normalize_linkedin_profile_url("") is None
    assert normalize_linkedin_profile_url(None) is None


def test_split_author_name() -> None:
    assert split_author_name("Linkedin User") == ("Linkedin", "User")
    assert split_author_name("Linkedin") == ("Linkedin", None)
    assert split_author_name("Linkedin A User") == ("Linkedin", "A User")
    assert split_author_name("") == (None, None)
    assert split_author_name(None) == (None, None)
    assert split_author_name("  ") == (None, None)
