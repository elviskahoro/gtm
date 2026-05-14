from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

from libs.attio.mentions import upsert_mention
from libs.attio.models import MentionInput


def _sample(action: str = "mention_created") -> MentionInput:
    return MentionInput(
        mention_url="https://reddit.com/r/x/comments/abc",
        last_action=action,  # type: ignore[arg-type]
        source_platform="reddit",
        source_id="abc",
        mention_body="hello",
        mention_timestamp=datetime(2026, 5, 10, 11, 55, 53),
        author_handle="u",
        primary_keyword="kw",
    )


def _mock_client_with_response(record_id: str) -> MagicMock:
    client = MagicMock()
    client.__enter__.return_value = client
    response = MagicMock()
    response.data = MagicMock()
    response.data.id.record_id = record_id
    client.records.put_v2_objects_object_records.return_value = response
    return client


def test_upsert_mention_calls_assert_endpoint() -> None:
    client = _mock_client_with_response("rec-1")
    with (
        patch("libs.attio.mentions.get_client", return_value=client),
        patch(
            "libs.attio.mentions.ensure_select_options",
        ),
    ):
        envelope = upsert_mention(_sample())
    client.records.put_v2_objects_object_records.assert_called_once()
    _, kwargs = client.records.put_v2_objects_object_records.call_args
    assert kwargs["object"] == "social_mention"
    assert kwargs["matching_attribute"] == "mention_url"
    assert envelope.success is True
    assert envelope.record_id == "rec-1"


def test_upsert_mention_update_path_omits_immutables() -> None:
    """The update value builder must omit source_platform / source_id."""
    client = _mock_client_with_response("rec-1")
    with (
        patch("libs.attio.mentions.get_client", return_value=client),
        patch(
            "libs.attio.mentions.ensure_select_options",
        ),
    ):
        upsert_mention(_sample(action="mention_updated"))
    _, kwargs = client.records.put_v2_objects_object_records.call_args
    data_obj = kwargs["data"]
    # data_obj is the assert-request Pydantic model from the Attio SDK;
    # `values` is accessible as a pydantic field.
    values = data_obj.values
    assert "source_platform" not in values
    assert "source_id" not in values
