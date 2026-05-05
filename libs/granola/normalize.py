from __future__ import annotations

import ast
import json
from typing import Any

from libs.granola.models import NormalizedMeeting, TranscriptSegment


def _segments_from_raw(raw: list[dict[str, Any]] | None) -> list[TranscriptSegment]:
    if not raw:
        return []
    return [
        TranscriptSegment(
            start_ms=segment.get("start_ms"),
            end_ms=segment.get("end_ms"),
            speaker=segment.get("speaker"),
            text=str(segment.get("text", "")),
        )
        for segment in raw
        if str(segment.get("text", "")).strip()
    ]


def _parse_structured_notes(raw: Any) -> dict[str, Any] | None:
    if isinstance(raw, dict) and raw.get("type") == "doc":
        return raw
    if not isinstance(raw, str):
        return None

    text = raw.strip()
    if not text.startswith("{") and not text.startswith("["):
        return None

    candidates: list[Any] = []
    try:
        candidates.append(json.loads(text))
    except json.JSONDecodeError:
        pass
    try:
        candidates.append(ast.literal_eval(text))
    except (SyntaxError, ValueError):
        pass

    for candidate in candidates:
        if isinstance(candidate, dict) and candidate.get("type") == "doc":
            return candidate
    return None


def _extract_inline_text(node: dict[str, Any]) -> str:
    node_type = node.get("type")
    if node_type == "text":
        return str(node.get("text", ""))
    if node_type == "hardBreak":
        return "\n"

    attrs = node.get("attrs")
    if node_type == "mention" and isinstance(attrs, dict):
        label = attrs.get("label") or attrs.get("name")
        if isinstance(label, str):
            return label

    parts: list[str] = []
    for child in node.get("content", []):
        if isinstance(child, dict):
            parts.append(_extract_inline_text(child))
    return "".join(parts)


def _render_structured_notes(doc: dict[str, Any]) -> str:
    blocks: list[str] = []
    for node in doc.get("content", []):
        if not isinstance(node, dict):
            continue
        node_type = node.get("type")
        if node_type in {"paragraph", "heading", "blockquote"}:
            text = _extract_inline_text(node).strip()
            if text:
                blocks.append(text)
            continue
        if node_type in {"bulletList", "orderedList"}:
            marker = "- " if node_type == "bulletList" else "1. "
            for child in node.get("content", []):
                if isinstance(child, dict):
                    item_text = _extract_inline_text(child).strip()
                    if item_text:
                        blocks.append(f"{marker}{item_text}")
            continue
        text = _extract_inline_text(node).strip()
        if text:
            blocks.append(text)
    return "\n\n".join(blocks).strip()


def _notes_to_markdown(local_doc: dict[str, Any]) -> str:
    raw_notes = local_doc.get("notes_markdown") or local_doc.get("notes") or ""
    structured = _parse_structured_notes(raw_notes)
    if structured is None:
        return str(raw_notes)
    rendered = _render_structured_notes(structured)
    return rendered or str(raw_notes)


def normalize_meeting(
    local_doc: dict[str, Any],
    local_transcript: list[dict[str, Any]] | None,
    api_note: dict[str, Any] | None,
    previous_export: dict[str, Any] | None,
) -> NormalizedMeeting:
    meeting_id = str(local_doc.get("id", "")).strip()
    title = str(local_doc.get("title") or "Untitled Meeting")
    notes_markdown = _notes_to_markdown(local_doc)

    local_segments = _segments_from_raw(local_transcript)
    api_segments = _segments_from_raw((api_note or {}).get("transcript"))
    previous_segments = _segments_from_raw(
        (previous_export or {}).get("transcript_segments"),
    )

    if local_segments:
        segments = local_segments
        source = "local"
        status = "present"
    elif api_segments:
        segments = api_segments
        source = "api"
        status = "present"
    elif previous_segments:
        segments = previous_segments
        source = "preserved"
        status = "present"
    else:
        segments = []
        source = "local"
        status = (
            "deleted_in_source" if local_doc.get("transcript_deleted_at") else "missing"
        )

    return NormalizedMeeting(
        id=meeting_id,
        title=title,
        notes_markdown=notes_markdown,
        transcript_segments=segments,
        transcript_source=source,
        transcript_status=status,
        created_at=local_doc.get("created_at"),
    )
