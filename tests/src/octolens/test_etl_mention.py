"""Tests for src/octolens/webhook/mention.py — Webhook contract."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.octolens.webhook import Webhook

REPO_ROOT = Path(__file__).resolve().parents[3]
EVENTS_PATH = REPO_ROOT / "tests" / "libs" / "octolens" / "fixtures" / "events.json"


def _load_webhook() -> Webhook:
    return Webhook.model_validate(json.loads(EVENTS_PATH.read_text()))


def test_etl_get_bucket_name() -> None:
    assert Webhook.etl_get_bucket_name() == "dlthub-devx-octolens-mentions-etl"


def test_modal_secret_collection_names() -> None:
    assert Webhook.modal_get_secret_collection_names() == ["devx-gcp-202605111323"]


def test_storage_get_base_model_type_returns_none() -> None:
    assert Webhook.storage_get_base_model_type() is None


def test_storage_get_app_name_matches_bucket() -> None:
    assert Webhook.storage_get_app_name() == Webhook.etl_get_bucket_name()


def test_etl_is_valid_webhook_true_for_mention_created() -> None:
    webhook = _load_webhook()
    assert webhook.etl_is_valid_webhook() is True


def test_etl_is_valid_webhook_false_for_other_action() -> None:
    payload = json.loads(EVENTS_PATH.read_text())
    payload["action"] = "mention_deleted"
    webhook = Webhook.model_validate(payload)
    assert webhook.etl_is_valid_webhook() is False
    assert (
        webhook.etl_get_invalid_webhook_error_msg()
        == "Invalid webhook: mention_deleted"
    )


def test_etl_get_json_serializes_data() -> None:
    webhook = _load_webhook()
    result = webhook.etl_get_json()
    parsed = json.loads(result)
    assert parsed["source"] == "reddit"
    assert parsed["keyword"] == "snowflake"
    assert parsed["author"] == "Sensitive_Pianist777"


def test_etl_get_file_name_format() -> None:
    webhook = _load_webhook()
    filename = webhook.etl_get_file_name()
    # Live payload timestamp: 2026-05-10 11:55:53.000 → 20260510115553
    # clean_string strips underscores (matches src/fathom/utils.py:16 behavior)
    # sourceId is appended to disambiguate same-second deliveries.
    assert (
        filename
        == "reddit-snowflake-20260510115553-sensitivepianist777-t3example1.jsonl"
    )


def test_etl_is_valid_webhook_true_for_mention_updated() -> None:
    payload = json.loads(EVENTS_PATH.read_text())
    payload["action"] = "mention_updated"
    webhook = Webhook.model_validate(payload)
    assert webhook.etl_is_valid_webhook() is True


def test_lance_methods_raise_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        Webhook.lance_get_project_name()
    with pytest.raises(NotImplementedError):
        Webhook.lance_get_base_model_type()


def test_etl_get_base_models_raises_not_implemented() -> None:
    webhook = _load_webhook()
    with pytest.raises(NotImplementedError):
        webhook.etl_get_base_models(storage=None)
