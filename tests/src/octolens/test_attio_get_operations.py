from __future__ import annotations

from src.octolens.webhook import Webhook


def test_attio_get_secret_collection_names() -> None:
    assert Webhook.attio_get_secret_collection_names() == ["attio"]
