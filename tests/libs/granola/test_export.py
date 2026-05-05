from __future__ import annotations

import datetime as dt
from pathlib import Path

from libs.granola.models import ExportRunOptions
from src.granola.export import run_export


def _seed_cache(path: Path) -> None:
    path.write_text(
        '{"state": {"documents": {"m1": {"id": "m1", "title": "A", "notes": "n"}}, "transcripts": {}}}',
        encoding="utf-8",
    )


def test_local_source_exports(tmp_path: Path) -> None:
    granola_home = tmp_path / "Library/Application Support/Granola"
    granola_home.mkdir(parents=True)
    _seed_cache(granola_home / "cache-v1.json")

    result = run_export(
        ExportRunOptions(
            source="local",
            output_root=tmp_path / "out",
            granola_dir=granola_home,
            now=dt.datetime(2026, 3, 29, tzinfo=dt.UTC),
        ),
    )
    assert result.processed == 1
    assert result.written == 1


def test_hybrid_can_use_api_transcript(tmp_path: Path) -> None:
    granola_home = tmp_path / "Library/Application Support/Granola"
    granola_home.mkdir(parents=True)
    _seed_cache(granola_home / "cache-v1.json")

    result = run_export(
        ExportRunOptions(
            source="hybrid",
            output_root=tmp_path / "out",
            granola_dir=granola_home,
            api_key="k",
            api_notes={"m1": {"id": "m1", "transcript": [{"text": "api"}]}},
            now=dt.datetime(2026, 3, 29, tzinfo=dt.UTC),
        ),
    )
    assert result.processed == 1


def test_record_error_accumulates_and_continues(tmp_path: Path) -> None:
    granola_home = tmp_path / "Library/Application Support/Granola"
    granola_home.mkdir(parents=True)
    (granola_home / "cache-v1.json").write_text(
        '{"state": {"documents": {"ok": {"id": "ok", "title": "A", "notes": "n"}, "bad": {"title": "missing id"}}, "transcripts": {}}}',
        encoding="utf-8",
    )

    result = run_export(
        ExportRunOptions(
            source="local",
            output_root=tmp_path / "out",
            granola_dir=granola_home,
            now=dt.datetime(2026, 3, 29, tzinfo=dt.UTC),
        ),
    )
    assert result.processed == 2
    assert result.errors == 1


def test_fatal_preflight_raises(tmp_path: Path) -> None:
    bad = tmp_path / "missing"
    try:
        run_export(
            ExportRunOptions(
                source="local",
                output_root=tmp_path / "out",
                granola_dir=bad,
            ),
        )
    except Exception as exc:  # noqa: BLE001
        assert "cache" in str(exc).lower() or "granola" in str(exc).lower()
    else:
        raise AssertionError("expected failure")
