from __future__ import annotations

from unittest.mock import MagicMock, patch

from libs.attio.models import PersonInput
from libs.attio.people import upsert_person


@patch("libs.attio.people._search_people_raw")
@patch("libs.attio.people.add_person")
def test_upsert_person_routes_github_handle_match(mock_add, mock_search) -> None:
    mock_search.return_value = []
    mock_add.return_value = MagicMock()

    upsert_person(
        PersonInput(github_handle="elviskahoro"),
        matching_attribute="github_handle",
    )

    mock_search.assert_called_once()
    kwargs = mock_search.call_args.kwargs
    assert kwargs.get("github_handle") == "elviskahoro"
    # Must NOT pass email or linkedin
    assert kwargs.get("email") is None
    assert kwargs.get("linkedin") is None


@patch("libs.attio.people._search_people_raw")
@patch("libs.attio.people.add_person")
def test_upsert_person_email_match_unchanged(mock_add, mock_search) -> None:
    mock_search.return_value = []
    mock_add.return_value = MagicMock()

    upsert_person(PersonInput(email="a@example.com"), matching_attribute="email")

    kwargs = mock_search.call_args.kwargs
    assert kwargs.get("email") == "a@example.com"
