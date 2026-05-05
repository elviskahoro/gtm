from __future__ import annotations

import os
from typing import cast

import modal


def test_parallel_search_sets_and_clears_env_and_forwards_mode(monkeypatch) -> None:
    monkeypatch.delenv("PARALLEL_API_KEY", raising=False)
    from libs.parallel.models import SearchResponse
    from src.parallel.search import parallel_search

    captured: dict[str, object] = {}

    def _search(input):
        assert os.environ.get("PARALLEL_API_KEY") == "pk_test"
        captured["objective"] = input.objective
        captured["mode"] = input.mode
        captured["max_results"] = input.max_results
        return SearchResponse(search_id="s_1", results=[])

    monkeypatch.setattr("src.parallel.search.search", _search)

    fn = cast(modal.Function, parallel_search)
    result = cast(
        SearchResponse,
        fn.local(
            payload={"objective": "find acme", "mode": "agentic", "max_results": 5},
            api_keys={"parallel_api_key": "pk_test"},
        ),
    )

    assert captured == {
        "objective": "find acme",
        "mode": "agentic",
        "max_results": 5,
    }
    assert result.search_id == "s_1"
    assert "PARALLEL_API_KEY" not in os.environ


def test_parallel_findall_create_sets_and_clears_env_and_forwards_generator(
    monkeypatch,
) -> None:
    monkeypatch.delenv("PARALLEL_API_KEY", raising=False)
    from libs.parallel.models import FindAllRunData
    from src.parallel.findall import parallel_findall_create

    captured: dict[str, object] = {}

    def _findall_create(input) -> FindAllRunData:
        assert os.environ.get("PARALLEL_API_KEY") == "pk_test"
        captured["objective"] = input.objective
        captured["entity_type"] = input.entity_type
        captured["match_limit"] = input.match_limit
        captured["generator"] = input.generator
        return FindAllRunData(
            findall_id="f_1",
            status="running",
            is_active=True,
            generated_count=0,
            matched_count=0,
        )

    monkeypatch.setattr("src.parallel.findall.findall_create", _findall_create)

    fn = cast(modal.Function, parallel_findall_create)
    result = cast(
        FindAllRunData,
        fn.local(
            payload={
                "objective": "find sales leaders",
                "entity_type": "person",
                "match_conditions": [{"name": "title", "description": "VP Sales"}],
                "match_limit": 7,
                "generator": "preview",
            },
            api_keys={"parallel_api_key": "pk_test"},
        ),
    )

    assert captured["objective"] == "find sales leaders"
    assert captured["match_limit"] == 7
    assert captured["generator"] == "preview"
    assert result.findall_id == "f_1"
    assert "PARALLEL_API_KEY" not in os.environ
