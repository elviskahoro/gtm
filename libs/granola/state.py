from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, Field

from libs.granola.models import NormalizedMeeting


class ExportState(BaseModel):
    hashes: dict[str, str] = Field(default_factory=dict)


def compute_meeting_hash(meeting: NormalizedMeeting) -> str:
    body = json.dumps(
        meeting.model_dump(mode="json"),
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def should_write(meeting_id: str, digest: str, state: ExportState) -> bool:
    return state.hashes.get(meeting_id) != digest


def load_state(path: Path) -> ExportState:
    if not path.exists():
        return ExportState()
    return ExportState.model_validate_json(path.read_text(encoding="utf-8"))


def save_state(path: Path, state: ExportState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
