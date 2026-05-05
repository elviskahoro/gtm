from __future__ import annotations

from libs.granola.models import TranscriptSegment
from libs.granola.normalize import normalize_meeting


def test_notes_markdown_preferred_over_plain() -> None:
    meeting = normalize_meeting(
        local_doc={
            "id": "m1",
            "title": "Sync",
            "notes_markdown": "**md**",
            "notes": "plain",
        },
        local_transcript=[{"text": "local"}],
        api_note=None,
        previous_export=None,
    )
    assert meeting.notes_markdown == "**md**"


def test_api_transcript_overrides_missing_local() -> None:
    meeting = normalize_meeting(
        local_doc={"id": "m1", "title": "Sync", "notes": "plain"},
        local_transcript=None,
        api_note={"transcript": [{"text": "api"}]},
        previous_export=None,
    )
    assert meeting.transcript_source == "api"
    assert meeting.transcript_status == "present"
    assert meeting.transcript_segments == [
        TranscriptSegment(text="api", start_ms=None, end_ms=None, speaker=None),
    ]


def test_previous_sidecar_transcript_restored_when_missing() -> None:
    meeting = normalize_meeting(
        local_doc={"id": "m1", "title": "Sync", "notes": "plain"},
        local_transcript=None,
        api_note=None,
        previous_export={"transcript_segments": [{"text": "old"}]},
    )
    assert meeting.transcript_source == "preserved"
    assert meeting.transcript_status == "present"


def test_transcript_deleted_status_without_preserved_content() -> None:
    meeting = normalize_meeting(
        local_doc={
            "id": "m1",
            "title": "Sync",
            "notes": "plain",
            "transcript_deleted_at": "2026-01-01T00:00:00Z",
        },
        local_transcript=None,
        api_note=None,
        previous_export=None,
    )
    assert meeting.transcript_status == "deleted_in_source"


def test_structured_notes_markdown_is_rendered_to_text() -> None:
    meeting = normalize_meeting(
        local_doc={
            "id": "m1",
            "title": "Sync",
            "notes_markdown": "{'type': 'doc', 'content': [{'type': 'heading', 'content': [{'type': 'text', 'text': 'Plan'}]}, {'type': 'paragraph', 'content': [{'type': 'text', 'text': 'Ship it'}]}]}",
        },
        local_transcript=None,
        api_note=None,
        previous_export=None,
    )
    assert "Plan" in meeting.notes_markdown
    assert "Ship it" in meeting.notes_markdown
    assert "{'type': 'doc'" not in meeting.notes_markdown


def test_plain_notes_markdown_is_preserved() -> None:
    meeting = normalize_meeting(
        local_doc={
            "id": "m1",
            "title": "Sync",
            "notes_markdown": "## Heading\n\nAlready markdown",
        },
        local_transcript=None,
        api_note=None,
        previous_export=None,
    )
    assert meeting.notes_markdown == "## Heading\n\nAlready markdown"
