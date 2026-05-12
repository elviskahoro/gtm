from __future__ import annotations

import json
from pathlib import Path

from src.octolens.webhook import Webhook

REPO_ROOT = Path(__file__).resolve().parents[3]
EVENTS_PATH = REPO_ROOT / "tests" / "libs" / "octolens" / "fixtures" / "events.json"


def _load() -> Webhook:
    return Webhook.model_validate(json.loads(EVENTS_PATH.read_text()))


def test_attio_get_secret_collection_names() -> None:
    assert Webhook.attio_get_secret_collection_names() == ["attio"]


def test_attio_is_valid_webhook_false_for_octolens() -> None:
    # Octolens mentions have no email/domain — no resolvable Attio parent yet.
    assert _load().attio_is_valid_webhook() is False


def test_attio_get_invalid_webhook_error_msg_mentions_no_email_or_domain() -> None:
    msg = _load().attio_get_invalid_webhook_error_msg()
    assert "email" in msg
    assert "domain" in msg


def test_attio_get_operations_returns_empty_list() -> None:
    assert _load().attio_get_operations() == []
