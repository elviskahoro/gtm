from __future__ import annotations

import pytest


def test_research_supports_search_response_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from libs.parallel.models import SearchResponse, SearchResultItem
    from src.accounts.tasks import research

    monkeypatch.setattr(
        "libs.parallel.client.search",
        lambda input: SearchResponse(  # pyright: ignore[reportUnknownLambdaType]
            search_id="s_model_1",
            results=[SearchResultItem(title="Acme", url="https://acme.com")],
        ),
    )

    result = research("acme buyers")
    assert result.objective == "acme buyers"
    assert result.results[0]["url"] == "https://acme.com"


def test_map_account_hierarchy_supports_search_response_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from libs.parallel.models import SearchResponse, SearchResultItem
    from src.accounts.tasks import map_account_hierarchy

    monkeypatch.setattr(
        "libs.parallel.client.search",
        lambda input: SearchResponse(  # pyright: ignore[reportUnknownLambdaType]
            search_id="s_model_2",
            results=[
                SearchResultItem(title="Acme Parent", url="https://parent.example.com"),
            ],
        ),
    )

    result = map_account_hierarchy("acme")
    assert result.account == "acme"
    assert result.hierarchy[0]["title"] == "Acme Parent"


def test_enrich_raises_type_error_for_unsupported_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.accounts.tasks import enrich

    monkeypatch.setattr(
        "libs.parallel.client.extract_excerpts",
        lambda input: [
            "not",
            "a",
            "mapping",
        ],  # pyright: ignore[reportUnknownLambdaType]
    )

    with pytest.raises(TypeError, match="Expected mapping-like payload"):
        enrich("https://acme.com", "funding and market")


def test_model_batch_mutation_mode_is_required() -> None:
    from src.accounts.models import BatchMutationResult

    result = BatchMutationResult(mode="preview", requested=2, created=0, skipped=2)
    assert result.mode == "preview"

    with pytest.raises(Exception):
        BatchMutationResult(
            requested=1,
            created=0,
            skipped=1,
        )  # pyright: ignore[reportCallIssue]


def test_model_batch_mutation_mode_is_restricted() -> None:
    from src.accounts.models import BatchMutationResult

    with pytest.raises(Exception):
        BatchMutationResult(
            mode="invalid",  # pyright: ignore[reportArgumentType]
            requested=1,
            created=0,
            skipped=1,
        )


def test_model_json_dump_is_dict_compatible() -> None:
    from src.accounts.models import ResearchResult

    model = ResearchResult(
        objective="find companies",
        results=[{"url": "https://example.com"}],
    )
    dumped = model.model_dump(mode="json")
    assert isinstance(dumped, dict)
    assert dumped["objective"] == "find companies"


def test_research_returns_structured_result(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.accounts.tasks import research

    monkeypatch.setattr(
        "libs.parallel.client.search",
        lambda input: {  # pyright: ignore[reportUnknownLambdaType]
            "search_id": "s_1",
            "results": [{"title": "Acme", "url": "https://acme.com"}],
        },
    )

    result = research("acme buyers")
    dumped = result.model_dump(mode="json")
    assert dumped["objective"] == "acme buyers"
    assert dumped["results"][0]["url"] == "https://acme.com"


def test_find_people_returns_structured_result(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.accounts.tasks import find_people

    monkeypatch.setattr(
        "libs.parallel.client.search",
        lambda input: {  # pyright: ignore[reportUnknownLambdaType]
            "search_id": "s_2",
            "results": [{"name": "Ada", "email": "ada@example.com"}],
        },
    )

    result = find_people("eng leader at acme")
    assert result.query == "eng leader at acme"
    assert result.people[0]["name"] == "Ada"


def test_enrich_returns_structured_result(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.accounts.tasks import enrich

    monkeypatch.setattr(
        "libs.parallel.client.extract_excerpts",
        lambda input: {  # pyright: ignore[reportUnknownLambdaType]
            "extract_id": "e_1",
            "result": {"url": input.url, "excerpts": ["founded 2021"]},
            "errors": [],
        },
    )

    result = enrich("https://acme.com", "funding and market")
    assert result.url == "https://acme.com"
    assert result.data["extract_id"] == "e_1"


def test_map_account_hierarchy_returns_structured_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.accounts.tasks import map_account_hierarchy

    monkeypatch.setattr(
        "libs.parallel.client.search",
        lambda input: {  # pyright: ignore[reportUnknownLambdaType]
            "search_id": "s_3",
            "results": [{"company": "Acme", "parent": "Acme Holdings"}],
        },
    )

    result = map_account_hierarchy("acme")
    assert result.account == "acme"
    assert result.hierarchy[0]["parent"] == "Acme Holdings"


def test_batch_add_people_preview_by_default_has_no_writes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.accounts.tasks import batch_add_people

    writes = {"count": 0}

    def _add_person(_payload):
        writes["count"] += 1
        return {"record_id": "p_1"}

    monkeypatch.setattr("libs.attio.people.add_person", _add_person)

    result = batch_add_people([{"email": "ada@example.com"}])
    assert result.mode == "preview"
    assert result.created == 0
    assert writes["count"] == 0


def test_batch_add_people_apply_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.accounts.tasks import batch_add_people

    writes = {"count": 0}

    def _add_person(_payload):
        writes["count"] += 1
        return {"record_id": "p_1"}

    monkeypatch.setattr("libs.attio.people.add_person", _add_person)

    result = batch_add_people([{"email": "ada@example.com"}], apply=True)
    assert result.mode == "apply"
    assert result.created == 1
    assert writes["count"] == 1
    assert isinstance(result.applied_at, str)
    assert result.source == "elvis.gtm.batch_add_people"


def test_batch_add_companies_preview_by_default_has_no_writes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.accounts.tasks import batch_add_companies

    writes = {"count": 0}

    def _add_company(_payload):
        writes["count"] += 1
        return {"record_id": "c_1"}

    monkeypatch.setattr("libs.attio.companies.add_company", _add_company)

    result = batch_add_companies([{"name": "Acme", "domain": "acme.com"}])
    assert result.mode == "preview"
    assert result.created == 0
    assert writes["count"] == 0


def test_batch_add_companies_apply_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.accounts.tasks import batch_add_companies

    writes = {"count": 0}

    def _add_company(_payload):
        writes["count"] += 1
        return {"record_id": "c_1"}

    monkeypatch.setattr("libs.attio.companies.add_company", _add_company)

    result = batch_add_companies([{"name": "Acme", "domain": "acme.com"}], apply=True)
    assert result.mode == "apply"
    assert result.created == 1
    assert writes["count"] == 1
    assert result.source == "elvis.gtm.batch_add_companies"


def test_non_mutating_tasks_do_not_accept_apply() -> None:
    from src.accounts.tasks import enrich, find_people, map_account_hierarchy, research

    with pytest.raises(TypeError):
        research("x", apply=True)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        find_people("x", apply=True)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        enrich("https://example.com", "x", apply=True)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        map_account_hierarchy("x", apply=True)  # type: ignore[call-arg]


def test_batch_failure_all_success_statuses_are_stable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.accounts.tasks import batch_add_people

    monkeypatch.setattr(
        "libs.attio.people.add_person",
        lambda _payload: {
            "record_id": "p_1",
        },  # pyright: ignore[reportUnknownLambdaType]
    )

    result = batch_add_people([{"email": "ada@example.com"}], apply=True)
    dumped = result.model_dump(mode="json")
    assert dumped["created"] == 1
    assert dumped["conflicts"] == 0
    assert dumped["errors"] == 0
    assert dumped["results"][0]["status"] == "created"


def test_batch_failure_partial_success_summary_is_deterministic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.accounts.tasks import batch_add_people

    calls = {"count": 0}

    def _add_person(_payload):
        calls["count"] += 1
        if calls["count"] == 1:
            return {"record_id": "p_1"}
        raise RuntimeError("duplicate")

    monkeypatch.setattr("libs.attio.people.add_person", _add_person)

    result = batch_add_people(
        [{"email": "ada@example.com"}, {"email": "ada@example.com"}],
        apply=True,
    )
    dumped = result.model_dump(mode="json")
    assert dumped["created"] == 1
    assert dumped["errors"] == 0
    assert dumped["conflicts"] == 1
    assert dumped["results"][0]["status"] == "created"
    assert dumped["results"][1]["status"] == "conflict"


def test_batch_failure_all_failed_summary_is_deterministic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.accounts.tasks import batch_add_people

    monkeypatch.setattr(
        "libs.attio.people.add_person",
        lambda _payload: (_ for _ in ()).throw(
            RuntimeError("boom"),
        ),  # pyright: ignore[reportUnknownLambdaType]
    )

    result = batch_add_people([{"email": "ada@example.com"}], apply=True)
    dumped = result.model_dump(mode="json")
    assert dumped["created"] == 0
    assert dumped["errors"] == 1
    assert dumped["results"][0]["status"] == "error"


def test_idempotency_batch_people_marks_duplicate_keys_as_conflicts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.accounts.tasks import batch_add_people

    writes = {"count": 0}

    def _add_person(_payload):
        writes["count"] += 1
        return {"record_id": f"p_{writes['count']}"}

    monkeypatch.setattr("libs.attio.people.add_person", _add_person)

    result = batch_add_people(
        [{"email": "ada@example.com"}, {"email": "ada@example.com"}],
        apply=True,
    )
    dumped = result.model_dump(mode="json")
    assert dumped["created"] == 1
    assert dumped["conflicts"] == 1
    assert writes["count"] == 1
    assert dumped["results"][1]["status"] == "conflict"


def test_idempotency_batch_companies_marks_duplicate_keys_as_conflicts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.accounts.tasks import batch_add_companies

    writes = {"count": 0}

    def _add_company(_payload):
        writes["count"] += 1
        return {"record_id": f"c_{writes['count']}"}

    monkeypatch.setattr("libs.attio.companies.add_company", _add_company)

    result = batch_add_companies(
        [
            {"name": "Acme", "domain": "acme.com"},
            {"name": "Acme", "domain": "acme.com"},
        ],
        apply=True,
    )
    dumped = result.model_dump(mode="json")
    assert dumped["created"] == 1
    assert dumped["conflicts"] == 1
    assert writes["count"] == 1
    assert dumped["results"][1]["status"] == "conflict"


def test_validation_limits_reject_empty_people_payload() -> None:
    from src.accounts.tasks import batch_add_people

    with pytest.raises(ValueError, match="records must not be empty"):
        batch_add_people([], apply=False)


def test_validation_limits_reject_empty_company_payload() -> None:
    from src.accounts.tasks import batch_add_companies

    with pytest.raises(ValueError, match="records must not be empty"):
        batch_add_companies([], apply=False)


def test_validation_limits_reject_people_missing_email() -> None:
    from src.accounts.tasks import batch_add_people

    with pytest.raises(ValueError, match="email is required"):
        batch_add_people([{"first_name": "Ada"}], apply=False)


def test_validation_limits_reject_companies_missing_domain() -> None:
    from src.accounts.tasks import batch_add_companies

    with pytest.raises(ValueError, match="domain is required"):
        batch_add_companies([{"name": "Acme"}], apply=False)


def test_validation_limits_reject_batch_over_limit() -> None:
    from src.accounts.tasks import batch_add_people

    too_many = [{"email": f"p{i}@example.com"} for i in range(101)]
    with pytest.raises(ValueError, match="maximum batch size is 100"):
        batch_add_people(too_many, apply=False)
