from __future__ import annotations

from unittest.mock import MagicMock, patch

from libs.attio.attributes import create_attribute
from libs.attio.models import AttributeCreateResult


def _mock_client_with_existing(existing_slugs: list[str]) -> MagicMock:
    client = MagicMock()
    client.__enter__.return_value = client
    attrs_response = MagicMock()
    attrs_response.data = [MagicMock(api_slug=s) for s in existing_slugs]
    client.attributes.get_v2_target_identifier_attributes.return_value = attrs_response
    return client


def test_create_attribute_routes_to_arbitrary_target() -> None:
    client = _mock_client_with_existing([])
    with patch("libs.attio.attributes.get_client", return_value=client):
        result = create_attribute(
            target_object="social_mention",
            title="Mention URL",
            api_slug="mention_url",
            attribute_type="text",
            is_unique=True,
            is_multiselect=False,
            apply=True,
        )
    client.attributes.get_v2_target_identifier_attributes.assert_called_once_with(
        target="objects",
        identifier="social_mention",
    )
    client.attributes.post_v2_target_identifier_attributes.assert_called_once()
    _, kwargs = client.attributes.post_v2_target_identifier_attributes.call_args
    assert kwargs["identifier"] == "social_mention"
    assert isinstance(result, AttributeCreateResult)
    assert result.attribute_created is True


def test_create_attribute_skips_when_exists() -> None:
    client = _mock_client_with_existing(["mention_url"])
    with patch("libs.attio.attributes.get_client", return_value=client):
        result = create_attribute(
            target_object="social_mention",
            title="Mention URL",
            api_slug="mention_url",
            attribute_type="text",
            is_multiselect=False,
            apply=True,
        )
    client.attributes.post_v2_target_identifier_attributes.assert_not_called()
    assert result.attribute_exists is True
    assert result.attribute_created is False
