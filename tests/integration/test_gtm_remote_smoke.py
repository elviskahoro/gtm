from __future__ import annotations

import os

import modal
import pytest

from src.modal_app import MODAL_APP

REQUIRED_ENV_VARS = [
    "MODAL_TOKEN_ID",
    "MODAL_TOKEN_SECRET",
    "MODAL_ENVIRONMENT",
    "PARALLEL_API_KEY",
]


def _missing_env_vars() -> list[str]:
    return [name for name in REQUIRED_ENV_VARS if not os.environ.get(name)]


def _skip_if_missing_env() -> None:
    missing = _missing_env_vars()
    if missing:
        pytest.skip(
            "Remote smoke tests gated by credentials preflight failure in this module",
        )


# --- Metadata / Capability Tests ---


def test_gtm_remote_metadata_attio_people_runtime() -> None:
    _skip_if_missing_env()
    fn = modal.Function.from_name(MODAL_APP, "attio_people_runtime_metadata")
    payload = fn.remote()  # pyrefly: ignore[invalid-param-spec]
    assert isinstance(payload, dict)
    assert payload.get("app") == MODAL_APP
    assert "build_git_sha" in payload
    assert "deployed_at" in payload
    capabilities = payload.get("capabilities", {})
    assert capabilities.get("attio_people_upsert.additional_emails") is True


# --- Research and Search Tests ---


def test_gtm_remote_smoke_non_mutating_research() -> None:
    _skip_if_missing_env()
    fn = modal.Function.from_name(MODAL_APP, "gtm_research")
    response = fn.remote(
        payload={"objective": "acme ai startup"},
        api_keys={"parallel": os.environ["PARALLEL_API_KEY"]},
    )
    payload = response.model_dump() if hasattr(response, "model_dump") else response
    assert isinstance(payload, dict)
    assert payload.get("objective") == "acme ai startup"
    assert isinstance(payload.get("results"), list)


def test_gtm_remote_smoke_enrich() -> None:
    _skip_if_missing_env()
    fn = modal.Function.from_name(MODAL_APP, "gtm_enrich")
    response = fn.remote(
        payload={"url": "https://example.com", "objective": "company info"},
        api_keys={"parallel": os.environ["PARALLEL_API_KEY"]},
    )
    payload = response.model_dump() if hasattr(response, "model_dump") else response
    assert isinstance(payload, dict)
    assert payload.get("url") == "https://example.com"
    assert payload.get("objective") == "company info"
    assert "data" in payload


def test_gtm_remote_parallel_search() -> None:
    _skip_if_missing_env()
    fn = modal.Function.from_name(MODAL_APP, "parallel_search")
    response = fn.remote(
        payload={"objective": "python web framework best practices", "max_results": 5},
        api_keys={"parallel": os.environ["PARALLEL_API_KEY"]},
    )
    payload = response.model_dump() if hasattr(response, "model_dump") else response
    assert isinstance(payload, dict)
    assert "search_id" in payload
    assert isinstance(payload.get("results"), list)


# --- Attio People Search (Read-Only) ---


def test_gtm_remote_attio_search_people_by_email() -> None:
    _skip_if_missing_env()
    fn = modal.Function.from_name(MODAL_APP, "attio_search_people")
    response = fn.remote(
        payload={"email": "nonexistent-smoke-test@example.com"},
        api_keys={"attio_api_key": os.environ.get("ATTIO_API_KEY", "")},
    )
    payload = response.model_dump() if hasattr(response, "model_dump") else response
    assert isinstance(payload, dict)
    assert "success" in payload
    # May return empty results for nonexistent email; just validate structure
    assert "record_id" in payload or "warnings" in payload or "errors" in payload


def test_gtm_remote_attio_search_people_by_domain() -> None:
    _skip_if_missing_env()
    fn = modal.Function.from_name(MODAL_APP, "attio_search_people")
    response = fn.remote(
        payload={"email_domain": "example.com", "limit": 5},
        api_keys={"attio_api_key": os.environ.get("ATTIO_API_KEY", "")},
    )
    payload = response.model_dump() if hasattr(response, "model_dump") else response
    assert isinstance(payload, dict)
    assert "success" in payload


# --- Batch Operations (Preview Mode) ---


def test_gtm_remote_smoke_mutating_preview_batch_people() -> None:
    _skip_if_missing_env()
    fn = modal.Function.from_name(MODAL_APP, "gtm_batch_add_people")
    response = fn.remote(
        payload={
            "records": [{"email": "remote-smoke@example.com"}],
            "apply": False,
        },
        api_keys={"attio_api_key": os.environ.get("ATTIO_API_KEY", "")},
    )
    payload = response.model_dump() if hasattr(response, "model_dump") else response
    assert isinstance(payload, dict)
    assert payload.get("mode") == "preview"
    assert payload.get("created") == 0
    assert isinstance(payload.get("requested"), int)


def test_gtm_remote_smoke_mutating_preview_batch_companies() -> None:
    _skip_if_missing_env()
    fn = modal.Function.from_name(MODAL_APP, "gtm_batch_add_companies")
    response = fn.remote(
        payload={
            "records": [{"domain": "example.com"}],
            "apply": False,
        },
        api_keys={"attio_api_key": os.environ.get("ATTIO_API_KEY", "")},
    )
    payload = response.model_dump() if hasattr(response, "model_dump") else response
    assert isinstance(payload, dict)
    assert payload.get("mode") == "preview"
    assert isinstance(payload.get("requested"), int)
