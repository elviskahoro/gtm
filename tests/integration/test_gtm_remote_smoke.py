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
            "Remote smoke tests gated by credentials preflight failure in this module"
        )


def test_gtm_remote_smoke_non_mutating_research() -> None:
    _skip_if_missing_env()
    fn = modal.Function.from_name(MODAL_APP, "gtm_research")
    response = fn.remote(
        objective="acme ai startup",
        parallel_api_key=os.environ["PARALLEL_API_KEY"],
    )
    payload = response.model_dump() if hasattr(response, "model_dump") else response
    assert isinstance(payload, dict)
    assert payload.get("objective") == "acme ai startup"
    assert isinstance(payload.get("results"), list)


def test_gtm_remote_smoke_mutating_preview_batch_people() -> None:
    _skip_if_missing_env()
    fn = modal.Function.from_name(MODAL_APP, "gtm_batch_add_people")
    response = fn.remote(
        records=[{"email": "remote-smoke@example.com"}],
        apply=False,
        attio_api_key=os.environ.get("ATTIO_API_KEY", ""),
    )
    payload = response.model_dump() if hasattr(response, "model_dump") else response
    assert isinstance(payload, dict)
    assert payload.get("mode") == "preview"
    assert payload.get("created") == 0
