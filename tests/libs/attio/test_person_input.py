from __future__ import annotations

import pytest
from pydantic import ValidationError

from libs.attio.models import PersonInput


def test_person_input_accepts_github_handle_only() -> None:
    pi = PersonInput(github_handle="elviskahoro")
    assert pi.github_handle == "elviskahoro"
    assert pi.email is None
    assert pi.linkedin is None


def test_person_input_accepts_github_handle_with_url() -> None:
    pi = PersonInput(
        github_handle="elviskahoro",
        github_url="https://github.com/elviskahoro",
    )
    assert pi.github_handle == "elviskahoro"
    assert pi.github_url == "https://github.com/elviskahoro"


def test_person_input_rejects_no_identity() -> None:
    with pytest.raises(ValidationError, match="At least one of"):
        PersonInput(first_name="someone")


def test_person_input_accepts_email_only_unchanged() -> None:
    pi = PersonInput(email="a@example.com")
    assert pi.email == "a@example.com"


def test_person_input_accepts_linkedin_only_unchanged() -> None:
    pi = PersonInput(linkedin="https://www.linkedin.com/in/foo")
    assert pi.linkedin == "https://www.linkedin.com/in/foo"
