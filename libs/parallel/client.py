from __future__ import annotations

import os

from .models import (
    ExtractErrorData,
    ExtractExcerptsInput,
    ExtractFullContentInput,
    ExtractResponse,
    ExtractResultData,
    FindAllCandidate,
    FindAllCreateInput,
    FindAllLookupInput,
    FindAllResultData,
    FindAllRunData,
    SearchInput,
    SearchResponse,
    SearchResultItem,
)


def _get_client():
    # Import here to avoid namespace collision with src/parallel
    import parallel as parallel_sdk

    api_key = os.environ.get("PARALLEL_API_KEY")
    if api_key is None:
        raise ValueError(
            "PARALLEL_API_KEY is not present in the environment.",
        )
    if api_key == "":
        raise ValueError(
            "PARALLEL_API_KEY is present but empty.",
        )
    parallel_client_class = getattr(parallel_sdk, "Parallel")
    return parallel_client_class(api_key=api_key)


def extract_full_content(input: ExtractFullContentInput) -> ExtractResponse:
    client = _get_client()
    response = client.beta.extract(
        urls=[input.url],
        excerpts=False,
        full_content=True,
    )
    return _parse_response(response)


def extract_excerpts(input: ExtractExcerptsInput) -> ExtractResponse:
    client = _get_client()
    response = client.beta.extract(
        urls=[input.url],
        objective=input.objective,
        excerpts=True,
        full_content=False,
    )
    return _parse_response(response)


def search(input: SearchInput) -> SearchResponse:
    client = _get_client()
    response = client.beta.search(
        objective=input.objective,
        mode=input.mode,
        max_results=input.max_results,
    )
    results: list[SearchResultItem] = []
    for r in response.results or []:
        excerpts_raw = getattr(r, "excerpts", None)
        excerpts = list(excerpts_raw) if excerpts_raw is not None else []
        results.append(
            SearchResultItem(
                url=r.url,
                title=getattr(r, "title", None),
                publish_date=getattr(r, "publish_date", None),
                excerpts=excerpts,
            ),
        )
    return SearchResponse(search_id=response.search_id, results=results)


def _parse_findall_run(response) -> FindAllRunData:
    return FindAllRunData(
        findall_id=response.findall_id,
        status=response.status.status,
        is_active=response.status.is_active,
        generated_count=response.status.metrics.generated_candidates_count or 0,
        matched_count=response.status.metrics.matched_candidates_count or 0,
    )


def findall_create(input: FindAllCreateInput) -> FindAllRunData:
    client = _get_client()
    response = client.beta.findall.create(
        objective=input.objective,
        entity_type=input.entity_type,
        match_conditions=[
            {"name": mc.name, "description": mc.description}
            for mc in input.match_conditions
        ],
        match_limit=input.match_limit,
        generator=input.generator,
    )
    return _parse_findall_run(response)


def findall_status(input: FindAllLookupInput) -> FindAllRunData:
    client = _get_client()
    response = client.beta.findall.retrieve(input.findall_id)
    return _parse_findall_run(response)


def findall_result(input: FindAllLookupInput) -> FindAllResultData:
    client = _get_client()
    response = client.beta.findall.result(input.findall_id)
    candidates = [
        FindAllCandidate(
            candidate_id=c.candidate_id,
            name=c.name,
            url=c.url,
            match_status=c.match_status,
            description=c.description,
            output=dict(c.output) if c.output else None,
        )
        for c in response.candidates
    ]
    return FindAllResultData(findall_id=input.findall_id, candidates=candidates)


def _parse_response(response) -> ExtractResponse:
    result: ExtractResultData | None = None
    if response.results:
        r = response.results[0]
        result = ExtractResultData(
            url=r.url,
            title=getattr(r, "title", None),
            publish_date=getattr(r, "publish_date", None),
            excerpts=list(r.excerpts) if getattr(r, "excerpts", None) else [],
            full_content=getattr(r, "full_content", None),
        )

    errors = [
        ExtractErrorData(
            url=e.url,
            error_type=e.error_type,
            http_status_code=getattr(e, "http_status_code", None),
            content=getattr(e, "content", None),
        )
        for e in (response.errors or [])
    ]

    return ExtractResponse(
        extract_id=response.extract_id,
        result=result,
        errors=errors,
    )
