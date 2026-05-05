from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from libs.granola.errors import ConfigError, SchemaError
from libs.granola.local_cache import (
    extract_local_records,
    find_latest_cache_file,
    load_local_cache,
)


def _write_cache(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_picks_highest_cache_version(tmp_path: Path) -> None:
    _write_cache(
        tmp_path / "cache-v1.json",
        {"state": {"documents": {}, "transcripts": {}}},
    )
    _write_cache(
        tmp_path / "cache-v3.json",
        {"state": {"documents": {}, "transcripts": {}}},
    )
    assert find_latest_cache_file(tmp_path).name == "cache-v3.json"


def test_no_cache_file_raises_config_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        find_latest_cache_file(tmp_path)


def test_missing_state_keys_raises_schema_error(tmp_path: Path) -> None:
    cache = tmp_path / "cache-v2.json"
    _write_cache(cache, {"state": {"documents": {}}})
    with pytest.raises(SchemaError):
        payload = load_local_cache(cache)
        extract_local_records(payload)


def test_extract_documents_and_transcripts_maps(tmp_path: Path) -> None:
    cache = tmp_path / "cache-v2.json"
    _write_cache(
        cache,
        {
            "state": {
                "documents": {"a": {"id": "a", "title": "T"}},
                "transcripts": {"a": [{"text": "hello"}]},
            },
        },
    )
    payload = load_local_cache(cache)
    docs, transcripts = extract_local_records(payload)
    assert docs["a"]["title"] == "T"
    assert transcripts["a"][0]["text"] == "hello"


def test_extract_documents_and_transcripts_maps_from_nested_cache_state(
    tmp_path: Path,
) -> None:
    cache = tmp_path / "cache-v2.json"
    _write_cache(
        cache,
        {
            "cache": {
                "state": {
                    "documents": {"a": {"id": "a", "title": "T"}},
                    "transcripts": {"a": [{"text": "hello"}]},
                },
            },
        },
    )
    payload = load_local_cache(cache)
    docs, transcripts = extract_local_records(payload)
    assert docs["a"]["title"] == "T"
    assert transcripts["a"][0]["text"] == "hello"
