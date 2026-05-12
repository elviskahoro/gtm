from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.attio.ops import UpsertMention
from src.octolens.webhook.mention import Webhook

SAMPLES_DIR = Path(__file__).resolve().parents[4] / "api" / "samples"

SAMPLE_FILES = [
    "octolens.mention.created.reddit.redacted.json",
    "octolens.mention.created.twitter.redacted.json",
    "octolens.mention.created.bluesky.redacted.json",
    "octolens.mention.created.hackernews.redacted.json",
    "octolens.mention.created.dev.redacted.json",
    "octolens.mention.created.podcasts.redacted.json",
]


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
