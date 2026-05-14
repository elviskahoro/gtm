from __future__ import annotations

from src.fathom.utils import _fathom_summary_title


def test_summary_title_with_template_name() -> None:
    assert _fathom_summary_title("General") == "Fathom summary — General"


def test_summary_title_empty_template_falls_back() -> None:
    assert _fathom_summary_title("") == "Fathom summary"


def test_summary_title_none_template_falls_back() -> None:
    assert _fathom_summary_title(None) == "Fathom summary"


def test_summary_title_strips_whitespace() -> None:
    assert _fathom_summary_title("   ") == "Fathom summary"


def test_summary_title_preserves_internal_whitespace() -> None:
    assert _fathom_summary_title("Sales Discovery") == "Fathom summary — Sales Discovery"
