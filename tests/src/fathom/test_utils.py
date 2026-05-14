from __future__ import annotations

from libs.fathom.models import ActionItem, Assignee
from src.fathom.utils import (
    fathom_summary_title,
    render_action_items_markdown,
)


def _item(
    *,
    name: str = "Alex",
    email: str | None = None,
    description: str = "Send deck",
    completed: bool = False,
    playback_url: str = "https://fathom.video/calls/1/?t=754",
    timestamp: str = "12:34",
) -> ActionItem:
    return ActionItem(
        assignee=Assignee(name=name, email=email, team=None),
        completed=completed,
        description=description,
        recording_playback_url=playback_url,
        recording_timestamp=timestamp,
        user_generated=False,
    )


def test_summary_title_with_template_name() -> None:
    assert fathom_summary_title("General") == "Fathom summary — General"


def test_summary_title_empty_template_falls_back() -> None:
    assert fathom_summary_title("") == "Fathom summary"


def test_summary_title_none_template_falls_back() -> None:
    assert fathom_summary_title(None) == "Fathom summary"


def test_summary_title_strips_whitespace() -> None:
    assert fathom_summary_title("   ") == "Fathom summary"


def test_summary_title_preserves_internal_whitespace() -> None:
    assert fathom_summary_title("Sales Discovery") == "Fathom summary — Sales Discovery"


def test_action_items_renders_unchecked_box() -> None:
    rendered = render_action_items_markdown([_item(completed=False)])
    assert rendered.startswith("- [ ] **Alex** — Send deck")


def test_action_items_renders_checked_box() -> None:
    rendered = render_action_items_markdown([_item(completed=True)])
    assert rendered.startswith("- [x] **Alex** — Send deck")


def test_action_items_appends_email_when_present() -> None:
    rendered = render_action_items_markdown([_item(email="alex@x.com")])
    assert "**Alex** (alex@x.com)" in rendered


def test_action_items_appends_playback_link_when_valid() -> None:
    rendered = render_action_items_markdown(
        [_item(playback_url="https://fathom.video/calls/1/?t=754", timestamp="12:34")],
    )
    assert rendered.endswith(" [▶ 12:34](https://fathom.video/calls/1/?t=754)")


def test_action_items_skips_link_for_non_https_url() -> None:
    rendered = render_action_items_markdown(
        [_item(playback_url="http://fathom.video/calls/1/?t=754", timestamp="12:34")],
    )
    assert "[▶" not in rendered


def test_action_items_skips_link_for_bad_timestamp() -> None:
    rendered = render_action_items_markdown(
        [_item(playback_url="https://fathom.video/calls/1/?t=754", timestamp="abc")],
    )
    assert "[▶" not in rendered


def test_action_items_omits_blank_items() -> None:
    rendered = render_action_items_markdown(
        [
            _item(name="Alex", description="Send deck"),
            _item(name="", description=""),
            _item(name="Sarah", description="Confirm budget"),
        ],
    )
    lines = rendered.splitlines()
    assert len(lines) == 2
    assert "**Alex**" in lines[0]
    assert "**Sarah**" in lines[1]


def test_action_items_empty_list_returns_empty_string() -> None:
    assert render_action_items_markdown([]) == ""
