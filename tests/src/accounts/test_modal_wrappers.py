from __future__ import annotations

import os
from typing import Any, cast

import modal


def test_gtm_research_sets_and_clears_env(monkeypatch) -> None:
    monkeypatch.delenv("PARALLEL_API_KEY", raising=False)
    from src.accounts.research import gtm_research

    called = {"ok": False}

    def _research(objective):
        called["ok"] = True
        assert os.environ.get("PARALLEL_API_KEY") == "pk_test"
        return {"objective": objective, "results": []}

    monkeypatch.setattr("src.accounts.tasks.research", _research)

    fn = cast(modal.Function, gtm_research)  # type: ignore
    result: dict[str, Any] = fn.local(
        payload={"objective": "find acme"},
        api_keys={"parallel_api_key": "pk_test"},
    )
    assert called["ok"] is True
    assert result["objective"] == "find acme"
    assert "PARALLEL_API_KEY" not in os.environ


def test_gtm_enrich_sets_and_clears_env(monkeypatch) -> None:
    monkeypatch.delenv("PARALLEL_API_KEY", raising=False)
    from src.accounts.research import gtm_enrich

    def _enrich(url, objective):
        assert os.environ.get("PARALLEL_API_KEY") == "pk_test"
        return {"url": url, "objective": objective, "data": {}}

    monkeypatch.setattr("src.accounts.tasks.enrich", _enrich)

    fn = cast(modal.Function, gtm_enrich)  # type: ignore
    result: dict[str, Any] = fn.local(
        payload={"url": "https://acme.com", "objective": "funding"},
        api_keys={"parallel_api_key": "pk_test"},
    )
    assert result["url"] == "https://acme.com"
    assert "PARALLEL_API_KEY" not in os.environ


def test_gtm_find_people_sets_and_clears_env(monkeypatch) -> None:
    monkeypatch.delenv("PARALLEL_API_KEY", raising=False)
    from src.accounts.people import gtm_find_people

    def _find_people(query):
        assert os.environ.get("PARALLEL_API_KEY") == "pk_test"
        return {"query": query, "people": []}

    monkeypatch.setattr("src.accounts.tasks.find_people", _find_people)

    fn = cast(modal.Function, gtm_find_people)  # type: ignore
    result: dict[str, Any] = fn.local(
        payload={"query": "vp sales"},
        api_keys={"parallel_api_key": "pk_test"},
    )
    assert result["query"] == "vp sales"
    assert "PARALLEL_API_KEY" not in os.environ


def test_gtm_map_account_hierarchy_sets_and_clears_env(monkeypatch) -> None:
    monkeypatch.delenv("PARALLEL_API_KEY", raising=False)
    from src.accounts.accounts import gtm_map_account_hierarchy

    def _map_account(account):
        assert os.environ.get("PARALLEL_API_KEY") == "pk_test"
        return {"account": account, "hierarchy": []}

    monkeypatch.setattr("src.accounts.tasks.map_account_hierarchy", _map_account)

    fn = cast(modal.Function, gtm_map_account_hierarchy)  # type: ignore
    result: dict[str, Any] = fn.local(
        payload={"account": "acme"},
        api_keys={"parallel_api_key": "pk_test"},
    )
    assert result["account"] == "acme"
    assert "PARALLEL_API_KEY" not in os.environ


def test_gtm_batch_add_people_sets_and_clears_env(monkeypatch) -> None:
    monkeypatch.delenv("ATTIO_API_KEY", raising=False)
    from src.accounts.batch import gtm_batch_add_people

    def _batch(records, apply=False):
        assert os.environ.get("ATTIO_API_KEY") == "ak_test"
        return {
            "mode": "apply" if apply else "preview",
            "requested": len(records),
            "created": len(records) if apply else 0,
            "skipped": 0 if apply else len(records),
            "conflicts": 0,
            "errors": 0,
            "results": [{"status": "created" if apply else "would_create"}],
        }

    monkeypatch.setattr("src.accounts.tasks.batch_add_people", _batch)

    fn = cast(modal.Function, gtm_batch_add_people)  # type: ignore
    result: dict[str, Any] = fn.local(
        payload={"records": [{"email": "ada@example.com"}], "apply": True},
        api_keys={"attio_api_key": "ak_test"},
    )
    assert result["mode"] == "apply"
    assert result["results"][0]["status"] == "created"
    assert "ATTIO_API_KEY" not in os.environ


def test_gtm_batch_add_companies_sets_and_clears_env(monkeypatch) -> None:
    monkeypatch.delenv("ATTIO_API_KEY", raising=False)
    from src.accounts.batch import gtm_batch_add_companies

    def _batch(records, apply=False):
        assert os.environ.get("ATTIO_API_KEY") == "ak_test"
        return {
            "mode": "apply" if apply else "preview",
            "requested": len(records),
            "created": len(records) if apply else 0,
            "skipped": 0 if apply else len(records),
        }

    monkeypatch.setattr("src.accounts.tasks.batch_add_companies", _batch)

    fn = cast(modal.Function, gtm_batch_add_companies)  # type: ignore
    result: dict[str, Any] = fn.local(
        payload={
            "records": [{"name": "Acme", "domain": "acme.com"}],
            "apply": True,
        },
        api_keys={"attio_api_key": "ak_test"},
    )
    assert result["mode"] == "apply"
    assert "ATTIO_API_KEY" not in os.environ
