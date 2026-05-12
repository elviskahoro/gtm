from __future__ import annotations

from src.fathom.webhook.message import Webhook


def test_attio_get_secret_collection_names() -> None:
    assert Webhook.attio_get_secret_collection_names() == ["attio"]


def test_attio_is_valid_webhook_always_false() -> None:
    # Construct via model_construct since the FathomMessage shape isn't
    # validated yet — we only care that the four attio_* hooks return the
    # documented stub values.
    w = Webhook.model_construct()
    assert w.attio_is_valid_webhook() is False
    assert "not currently exported" in w.attio_get_invalid_webhook_error_msg()
    assert w.attio_get_operations() == []
