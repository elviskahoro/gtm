from __future__ import annotations

from unittest.mock import MagicMock, patch

from libs.attio.objects import create_object


def _mock_client(existing_object_slugs: list[str]) -> MagicMock:
    client = MagicMock()
    client.__enter__.return_value = client
    objs_response = MagicMock()
    objs_response.data = [MagicMock(api_slug=s) for s in existing_object_slugs]
    client.objects.get_v2_objects.return_value = objs_response
    return client


def test_create_object_creates_when_missing() -> None:
    client = _mock_client([])
    with patch("libs.attio.objects.get_client", return_value=client):
        result = create_object(
            api_slug="social_mention",
            singular_noun="Social mention",
            plural_noun="Social mentions",
            apply=True,
        )
    client.objects.post_v2_objects.assert_called_once()
    assert result.object_created is True
    assert result.object_exists is False


def test_create_object_skips_when_present() -> None:
    client = _mock_client(["social_mention"])
    with patch("libs.attio.objects.get_client", return_value=client):
        result = create_object(
            api_slug="social_mention",
            singular_noun="Social mention",
            plural_noun="Social mentions",
            apply=True,
        )
    client.objects.post_v2_objects.assert_not_called()
    assert result.object_exists is True
    assert result.object_created is False
