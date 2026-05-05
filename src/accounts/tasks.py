from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

from libs.attio import companies as attio_companies
from libs.attio import people as attio_people
from libs.attio.models import CompanyInput, PersonInput
from libs.parallel import client as parallel_client
from libs.parallel.models import ExtractExcerptsInput, SearchInput, SearchResponse
from libs.parsers.normalization import normalize_mapping_payload
from src.accounts.models import (
    BatchMutationResult,
    EnrichResult,
    FindPeopleResult,
    MapAccountHierarchyResult,
    ResearchResult,
)

MAX_BATCH_SIZE = 100


def _person_dedup_key(record: dict[str, Any]) -> str | None:
    email = str(record.get("email", "")).strip().lower()
    return f"email:{email}" if email else None


def _company_dedup_key(record: dict[str, Any]) -> str | None:
    domain = str(record.get("domain", "")).strip().lower()
    return f"domain:{domain}" if domain else None


def _validate_people_records(records: list[dict[str, Any]]) -> None:
    if not records:
        raise ValueError("records must not be empty")
    if len(records) > MAX_BATCH_SIZE:
        raise ValueError(f"maximum batch size is {MAX_BATCH_SIZE}")
    for record in records:
        if not str(record.get("email", "")).strip():
            raise ValueError("email is required for each person record")


def _validate_company_records(records: list[dict[str, Any]]) -> None:
    if not records:
        raise ValueError("records must not be empty")
    if len(records) > MAX_BATCH_SIZE:
        raise ValueError(f"maximum batch size is {MAX_BATCH_SIZE}")
    for record in records:
        if not str(record.get("domain", "")).strip():
            raise ValueError("domain is required for each company record")


def research(objective: str) -> ResearchResult:
    raw = cast(object, parallel_client.search(SearchInput(objective=objective)))
    if isinstance(raw, SearchResponse):
        results = [item.model_dump(mode="json") for item in raw.results]
    else:
        payload = normalize_mapping_payload(raw)
        results = list(payload.get("results", []))
    return ResearchResult(
        objective=objective,
        results=results,
    )


def find_people(query: str) -> FindPeopleResult:
    raw = cast(object, parallel_client.search(SearchInput(objective=query)))
    if isinstance(raw, SearchResponse):
        people = [item.model_dump(mode="json") for item in raw.results]
    else:
        payload = normalize_mapping_payload(raw)
        people = list(payload.get("results", []))
    return FindPeopleResult(
        query=query,
        people=people,
    )


def enrich(url: str, objective: str) -> EnrichResult:
    raw = parallel_client.extract_excerpts(
        ExtractExcerptsInput(url=url, objective=objective),
    )
    payload = normalize_mapping_payload(raw)
    return EnrichResult(url=url, objective=objective, data=payload)


def map_account_hierarchy(account: str) -> MapAccountHierarchyResult:
    raw = cast(
        object,
        parallel_client.search(
            SearchInput(objective=f"account hierarchy for {account}"),
        ),
    )
    if isinstance(raw, SearchResponse):
        hierarchy = [item.model_dump(mode="json") for item in raw.results]
    else:
        payload = normalize_mapping_payload(raw)
        hierarchy = list(payload.get("results", []))
    return MapAccountHierarchyResult(
        account=account,
        hierarchy=hierarchy,
    )


def batch_add_people(
    records: list[dict[str, Any]],
    apply: bool = False,
) -> BatchMutationResult:
    _validate_people_records(records)
    if not apply:
        results = [
            {"status": "would_create", "email": record.get("email")}
            for record in records
        ]
        return BatchMutationResult(
            mode="preview",
            requested=len(records),
            created=0,
            skipped=len(records),
            results=results,
            source="elvis.gtm.batch_add_people",
        )

    created = 0
    conflicts = 0
    errors = 0
    results: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for record in records:
        dedup_key = _person_dedup_key(record)
        if dedup_key and dedup_key in seen_keys:
            conflicts += 1
            results.append({"status": "conflict", "email": record.get("email")})
            continue
        if dedup_key:
            seen_keys.add(dedup_key)
        try:
            attio_people.add_person(PersonInput(**record))
            created += 1
            results.append({"status": "created", "email": record.get("email")})
        except Exception as exc:
            errors += 1
            results.append(
                {"status": "error", "email": record.get("email"), "error": str(exc)},
            )

    return BatchMutationResult(
        mode="apply",
        requested=len(records),
        created=created,
        skipped=len(records) - created,
        conflicts=conflicts,
        errors=errors,
        results=results,
        source="elvis.gtm.batch_add_people",
        applied_at=datetime.now(UTC).isoformat(),
    )


def batch_add_companies(
    records: list[dict[str, Any]],
    apply: bool = False,
) -> BatchMutationResult:
    _validate_company_records(records)
    if not apply:
        results = [
            {"status": "would_create", "domain": record.get("domain")}
            for record in records
        ]
        return BatchMutationResult(
            mode="preview",
            requested=len(records),
            created=0,
            skipped=len(records),
            results=results,
            source="elvis.gtm.batch_add_companies",
        )

    created = 0
    conflicts = 0
    errors = 0
    results: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for record in records:
        dedup_key = _company_dedup_key(record)
        if dedup_key and dedup_key in seen_keys:
            conflicts += 1
            results.append({"status": "conflict", "domain": record.get("domain")})
            continue
        if dedup_key:
            seen_keys.add(dedup_key)
        try:
            attio_companies.add_company(CompanyInput(**record))
            created += 1
            results.append({"status": "created", "domain": record.get("domain")})
        except Exception as exc:
            errors += 1
            results.append(
                {"status": "error", "domain": record.get("domain"), "error": str(exc)},
            )

    return BatchMutationResult(
        mode="apply",
        requested=len(records),
        created=created,
        skipped=len(records) - created,
        conflicts=conflicts,
        errors=errors,
        results=results,
        source="elvis.gtm.batch_add_companies",
        applied_at=datetime.now(UTC).isoformat(),
    )
