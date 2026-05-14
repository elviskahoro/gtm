from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.attio.ops import UpsertMention, UpsertPerson
from src.octolens.webhook.mention import (
    Webhook,
    _extract_github_handle,  # pyright: ignore[reportPrivateUsage]
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

GITHUB_SAMPLE_FILE = "octolens.mention.created.github.redacted.json"


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
        mention_op.related_person.value == "https://www.linkedin.com/in/linkedin-user"
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


# --- Task 5: _extract_github_handle tests ---


def test_extract_github_handle_profile_url_canonical() -> None:
    """Test extraction from canonical GitHub profile URL."""
    result = _extract_github_handle("GitHub User", "https://github.com/elviskahoro")
    assert result == "elviskahoro"


def test_extract_github_handle_profile_url_with_www() -> None:
    """Test extraction from GitHub profile URL with www."""
    result = _extract_github_handle("GitHub User", "https://www.github.com/elviskahoro")
    assert result == "elviskahoro"


def test_extract_github_handle_profile_url_trailing_slash() -> None:
    """Test extraction from GitHub profile URL with trailing slash."""
    result = _extract_github_handle("GitHub User", "https://github.com/elviskahoro/")
    assert result == "elviskahoro"


def test_extract_github_handle_bare_handle_simple() -> None:
    """Test extraction from bare GitHub handle (fallback when URL absent)."""
    result = _extract_github_handle("elviskahoro", None)
    assert result == "elviskahoro"


def test_extract_github_handle_bare_handle_with_hyphens() -> None:
    """Test extraction from bare handle with hyphens."""
    result = _extract_github_handle("john-doe-123", None)
    assert result == "john-doe-123"


def test_extract_github_handle_bare_handle_single_char() -> None:
    """Test extraction from single character handle."""
    result = _extract_github_handle("a", None)
    assert result == "a"


def test_extract_github_handle_bare_handle_max_length() -> None:
    """Test extraction from maximum length handle (39 chars)."""
    handle = "a" * 39
    result = _extract_github_handle(handle, None)
    assert result == handle


def test_extract_github_handle_rejects_display_name() -> None:
    """Test that display name without URL or matching pattern returns None."""
    result = _extract_github_handle("John Doe", None)
    assert result is None


def test_extract_github_handle_rejects_org_repo_path() -> None:
    """Test that GitHub org/repo paths are rejected."""
    result = _extract_github_handle("Random Name", "https://github.com/owner/repo")
    assert result is None


def test_extract_github_handle_rejects_non_github_url() -> None:
    """Test that non-GitHub URLs are rejected."""
    result = _extract_github_handle("Random Name", "https://gitlab.com/user")
    assert result is None


def test_extract_github_handle_rejects_trailing_hyphens() -> None:
    """Test that handles with trailing hyphens are rejected."""
    result = _extract_github_handle("user-", None)
    assert result is None


def test_extract_github_handle_rejects_leading_hyphens() -> None:
    """Test that handles with leading hyphens are rejected."""
    result = _extract_github_handle("-user", None)
    assert result is None


def test_extract_github_handle_rejects_too_long() -> None:
    """Test that handles over 39 chars are rejected."""
    handle = "a" * 40
    result = _extract_github_handle(handle, None)
    assert result is None


def test_extract_github_handle_rejects_special_chars() -> None:
    """Test that handles with special chars are rejected."""
    result = _extract_github_handle("user@name", None)
    assert result is None


def test_extract_github_handle_none_author() -> None:
    """Test that None author returns None."""
    result = _extract_github_handle(None, None)
    assert result is None


def test_extract_github_handle_empty_string() -> None:
    """Test that empty string author returns None."""
    result = _extract_github_handle("", None)
    assert result is None


def test_extract_github_handle_http_url() -> None:
    """Test extraction from GitHub profile URL with http (not https)."""
    result = _extract_github_handle("GitHub User", "http://github.com/elviskahoro")
    assert result == "elviskahoro"


# --- Task 6: GitHub branch in attio_get_operations tests ---


def test_github_sample_produces_upsert_person_and_mention() -> None:
    """Test that GitHub webhook with profile URL produces UpsertPerson and UpsertMention."""
    from src.octolens.webhook.mention import Webhook

    payload = {
        "action": "mention_created",
        "data": {
            "title": "GitHub Discussion",
            "body": "redacted",
            "url": "https://github.com/owner/repo/discussions/123",
            "timestamp": "2026-05-10 11:55:53.000",
            "imageUrl": "",
            "author": "GitHub User",
            "authorProfileLink": "https://github.com/elviskahoro",
            "source": "github",
            "sourceId": "gh-123",
            "relevanceScore": "high",
            "relevanceComment": "redacted",
            "keyword": "example_keyword",
            "keywords": ["example_keyword"],
            "language": "english",
            "sentimentLabel": "Positive",
            "tags": [],
            "viewId": 16485,
            "viewName": "Webhook",
            "viewKeywords": [],
        },
    }

    webhook = Webhook.model_validate(payload)
    assert webhook.attio_is_valid_webhook() is True
    ops = webhook.attio_get_operations()

    assert len(ops) == 2

    # First op: UpsertPerson with github_handle
    person_op = ops[0]
    assert isinstance(person_op, UpsertPerson)
    assert person_op.github_handle == "elviskahoro"
    assert person_op.github_url == "https://github.com/elviskahoro"
    assert person_op.matching_attribute == "github_handle"

    # Second op: UpsertMention with related_person
    mention_op = ops[1]
    assert isinstance(mention_op, UpsertMention)
    assert mention_op.source_platform == "github"
    assert mention_op.related_person is not None
    assert mention_op.related_person.attribute == "github_handle"
    assert mention_op.related_person.value == "elviskahoro"


def test_github_sample_bare_handle_fallback() -> None:
    """Test that GitHub webhook falls back to bare handle when URL unavailable."""
    from src.octolens.webhook.mention import Webhook

    payload = {
        "action": "mention_created",
        "data": {
            "title": "GitHub Issue",
            "body": "redacted",
            "url": "https://github.com/owner/repo/issues/123",
            "timestamp": "2026-05-10 11:55:53.000",
            "imageUrl": "",
            "author": "elvis-kahoro",
            "authorProfileLink": None,  # No URL fallback to author field
            "source": "github",
            "sourceId": "gh-456",
            "relevanceScore": "high",
            "relevanceComment": "redacted",
            "keyword": "example_keyword",
            "keywords": ["example_keyword"],
            "language": "english",
            "sentimentLabel": "Positive",
            "tags": [],
            "viewId": 16485,
            "viewName": "Webhook",
            "viewKeywords": [],
        },
    }

    webhook = Webhook.model_validate(payload)
    ops = webhook.attio_get_operations()

    assert len(ops) == 2

    person_op = ops[0]
    assert isinstance(person_op, UpsertPerson)
    assert person_op.github_handle == "elvis-kahoro"
    assert person_op.github_url == "https://github.com/elvis-kahoro"

    mention_op = ops[1]
    assert mention_op.related_person is not None
    assert mention_op.related_person.value == "elvis-kahoro"


def test_github_sample_no_extractable_handle() -> None:
    """Test that GitHub webhook with unextractable handle yields only mention op."""
    from src.octolens.webhook.mention import Webhook

    payload = {
        "action": "mention_created",
        "data": {
            "title": "GitHub Comment",
            "body": "redacted",
            "url": "https://github.com/owner/repo/issues/123#comment-456",
            "timestamp": "2026-05-10 11:55:53.000",
            "imageUrl": "",
            "author": "John Doe",  # Not a valid GitHub handle
            "authorProfileLink": None,  # No URL
            "source": "github",
            "sourceId": "gh-789",
            "relevanceScore": "high",
            "relevanceComment": "redacted",
            "keyword": "example_keyword",
            "keywords": ["example_keyword"],
            "language": "english",
            "sentimentLabel": "Positive",
            "tags": [],
            "viewId": 16485,
            "viewName": "Webhook",
            "viewKeywords": [],
        },
    }

    webhook = Webhook.model_validate(payload)
    ops = webhook.attio_get_operations()

    assert len(ops) == 1
    op = ops[0]
    assert isinstance(op, UpsertMention)
    assert op.related_person is None


def test_github_url_with_invalid_repo_path() -> None:
    """Test that GitHub URL with invalid repo path returns None."""
    from src.octolens.webhook.mention import Webhook

    payload = {
        "action": "mention_created",
        "data": {
            "title": "GitHub Comment",
            "body": "redacted",
            "url": "https://github.com/owner/repo",
            "timestamp": "2026-05-10 11:55:53.000",
            "imageUrl": "",
            "author": "Some Name",
            "authorProfileLink": "https://github.com/owner/repo",  # Org/repo path, not user
            "source": "github",
            "sourceId": "gh-999",
            "relevanceScore": "high",
            "relevanceComment": "redacted",
            "keyword": "example_keyword",
            "keywords": ["example_keyword"],
            "language": "english",
            "sentimentLabel": "Positive",
            "tags": [],
            "viewId": 16485,
            "viewName": "Webhook",
            "viewKeywords": [],
        },
    }

    webhook = Webhook.model_validate(payload)
    ops = webhook.attio_get_operations()

    # Should only have mention op since the author is not a valid handle
    assert len(ops) == 1
    op = ops[0]
    assert isinstance(op, UpsertMention)
    assert op.related_person is None


def test_github_real_fixture_produces_upsert_person_and_mention() -> None:
    """Test that real GitHub webhook fixture produces UpsertPerson and UpsertMention."""
    payload = json.loads((SAMPLES_DIR / GITHUB_SAMPLE_FILE).read_text())
    webhook = Webhook.model_validate(payload)

    assert webhook.attio_is_valid_webhook() is True
    ops = webhook.attio_get_operations()
    assert len(ops) == 2

    # First op: UpsertPerson with github_handle
    person_op = ops[0]
    assert isinstance(person_op, UpsertPerson)
    assert person_op.github_handle == "AxelEspinosa94"
    assert person_op.github_url == "https://github.com/AxelEspinosa94"
    assert person_op.matching_attribute == "github_handle"

    # Second op: UpsertMention with related_person
    mention_op = ops[1]
    assert isinstance(mention_op, UpsertMention)
    assert mention_op.source_platform == "github"
    assert mention_op.author_handle == "AxelEspinosa94"
    assert mention_op.related_person is not None
    assert mention_op.related_person.attribute == "github_handle"
    assert mention_op.related_person.value == "AxelEspinosa94"
