from __future__ import annotations

import os
from typing import Any

import modal

from libs.attio.contracts import WarningEntry
from libs.attio.errors import (
    ConfigurationError,
    ConnectivityError,
    DeploymentMismatchError,
)
from src.attio.deployment_parity import ParityStatus, ensure_modal_parity
from src.modal_app import MODAL_APP


def run_people_preflight(
    *,
    connectivity_probe: bool,
    modal_app: str = MODAL_APP,
    function_name: str = "attio_search_people",
    modal_sync: str = "check",
) -> tuple[dict[str, str], list[WarningEntry], dict[str, Any]]:
    warnings: list[WarningEntry] = []

    raw_token_id = os.environ.get("MODAL_TOKEN_ID", "")
    raw_token_secret = os.environ.get("MODAL_TOKEN_SECRET", "")
    attio_api_key = os.environ.get("ATTIO_API_KEY", "")

    token_id = raw_token_id.strip()
    token_secret = raw_token_secret.strip()

    if token_id != raw_token_id or token_secret != raw_token_secret:
        warnings.append(
            WarningEntry(
                code="modal_token_whitespace_stripped",
                message="Modal token values contained leading/trailing whitespace and were normalized.",
                retryable=False,
            ),
        )

    if not token_id or not token_secret:
        raise ConfigurationError("Missing MODAL_TOKEN_ID or MODAL_TOKEN_SECRET.")

    parity_meta: dict[str, Any] = {"status": "not_applicable"}
    if function_name in {
        "attio_add_person",
        "attio_update_person",
        "attio_upsert_person",
    }:
        local_build_sha = os.environ.get("AI_BUILD_GIT_SHA")
        parity = ensure_modal_parity(
            sync_mode=modal_sync,
            modal_app=modal_app,
            required_capabilities={"attio_people_upsert.additional_emails": True},
            deploy_cmd=["modal", "deploy", "deploy.py", "--name", modal_app],
            local_build_sha=local_build_sha,
        )
        parity_meta = {
            "status": parity.status.value,
            "mismatch_reason": parity.mismatch_reason,
            "deploy_attempted": parity.deploy_attempted,
            "local_build_sha": parity.local_build_sha,
            "remote_build_sha": parity.remote_build_sha,
        }
        if parity.status is ParityStatus.MISMATCH:
            raise DeploymentMismatchError(
                "Modal runtime is incompatible with current CLI payload. "
                f"Redeploy with: modal app stop {modal_app} && modal deploy deploy.py --name {modal_app}",
            )

    if connectivity_probe:
        try:
            modal.Function.from_name(modal_app, function_name)
        except Exception as exc:
            raise ConnectivityError(
                f"Modal connectivity probe failed for function '{function_name}'. "
                f"Deploy app '{modal_app}' with `uv run modal deploy deploy.py`.",
            ) from exc

    env_payload: dict[str, str] = {
        "MODAL_TOKEN_ID": token_id,
        "MODAL_TOKEN_SECRET": token_secret,
    }
    if attio_api_key:
        env_payload["ATTIO_API_KEY"] = attio_api_key

    return (env_payload, warnings, parity_meta)
