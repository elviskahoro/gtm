from __future__ import annotations

from types import SimpleNamespace

from libs.parallel.models import (
    ExtractExcerptsInput,
    ExtractFullContentInput,
    FindAllCreateInput,
    FindAllLookupInput,
    MatchCondition,
    SearchInput,
)


def test_search_input_defaults():
    inp = SearchInput(objective="find acme")
    assert inp.mode == "one-shot"
    assert inp.max_results == 10


def test_findall_create_input_requires_fields():
    inp = FindAllCreateInput(
        objective="find",
        entity_type="company",
        match_conditions=[MatchCondition(name="rev", description="revenue > 1M")],
    )
    assert inp.match_limit == 10
    assert inp.generator == "base"


def test_extract_excerpts_input():
    inp = ExtractExcerptsInput(url="https://acme.com", objective="funding")
    assert inp.url == "https://acme.com"


def test_extract_full_content_input():
    inp = ExtractFullContentInput(url="https://acme.com")
    assert inp.url == "https://acme.com"


def test_findall_lookup_input():
    inp = FindAllLookupInput(findall_id="fa_123")
    assert inp.findall_id == "fa_123"


def test_search_handles_none_excerpts(monkeypatch) -> None:
    from libs.parallel.client import search

    response = SimpleNamespace(
        search_id="s_1",
        results=[
            SimpleNamespace(
                url="https://example.com",
                title=None,
                publish_date=None,
                excerpts=None,
            ),
        ],
    )

    def _search(**_: object) -> SimpleNamespace:
        return response

    fake_client = SimpleNamespace(beta=SimpleNamespace(search=_search))

    def _get_client() -> SimpleNamespace:
        return fake_client

    monkeypatch.setattr("libs.parallel.client._get_client", _get_client)

    parsed = search(SearchInput(objective="acme"))
    assert parsed.results[0].excerpts == []
