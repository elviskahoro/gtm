from __future__ import annotations

import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import Any

import modal


class ParityStatus(str, Enum):
    MATCH = "match"
    MISMATCH = "mismatch"
    UNKNOWN = "unknown"


@dataclass
class ParityResult:
    status: ParityStatus
    mismatch_reason: str | None = None
    deploy_attempted: bool = False
    local_build_sha: str | None = None
    remote_build_sha: str | None = None


def _normalize_payload(payload: Any) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump()
    if isinstance(payload, dict):
        return payload
    return {}


def fetch_remote_metadata(modal_app: str) -> dict[str, Any]:
    fn = modal.Function.from_name(modal_app, "attio_people_runtime_metadata")  # pyrefly: ignore[invalid-param-spec]
    payload = fn.remote()
    return _normalize_payload(payload)


def evaluate_parity(
    required_capabilities: dict[str, bool],
    remote_metadata: dict[str, Any],
    *,
    local_build_sha: str | None = None,
) -> ParityStatus:
    remote_caps = remote_metadata.get("capabilities")
    if isinstance(remote_caps, dict):
        for cap, required in required_capabilities.items():
            if bool(remote_caps.get(cap)) != required:
                return ParityStatus.MISMATCH
        return ParityStatus.MATCH

    remote_build_sha = remote_metadata.get("build_git_sha")
    if local_build_sha and isinstance(remote_build_sha, str) and remote_build_sha:
        return (
            ParityStatus.MATCH
            if remote_build_sha == local_build_sha
            else ParityStatus.MISMATCH
        )
    return ParityStatus.UNKNOWN


def run_deploy_command(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def ensure_modal_parity(
    *,
    sync_mode: str,
    modal_app: str,
    required_capabilities: dict[str, bool],
    deploy_cmd: list[str],
    local_build_sha: str | None = None,
) -> ParityResult:
    if sync_mode == "skip":
        return ParityResult(
            status=ParityStatus.UNKNOWN,
            mismatch_reason="parity_check_skipped",
            local_build_sha=local_build_sha,
        )

    try:
        remote = fetch_remote_metadata(modal_app)
    except Exception as exc:
        return ParityResult(
            status=ParityStatus.UNKNOWN,
            mismatch_reason=f"remote_metadata_unavailable: {exc}",
            local_build_sha=local_build_sha,
        )

    status = evaluate_parity(
        required_capabilities,
        remote,
        local_build_sha=local_build_sha,
    )
    remote_build_sha = remote.get("build_git_sha")
    result = ParityResult(
        status=status,
        local_build_sha=local_build_sha,
        remote_build_sha=(
            remote_build_sha if isinstance(remote_build_sha, str) else None
        ),
    )
    if status is not ParityStatus.MISMATCH:
        return result

    if sync_mode != "deploy":
        result.mismatch_reason = "modal_runtime_incompatible"
        return result

    try:
        run_deploy_command(deploy_cmd)
        remote_after = fetch_remote_metadata(modal_app)
    except Exception as exc:
        return ParityResult(
            status=ParityStatus.MISMATCH,
            mismatch_reason=f"redeploy_failed: {exc}",
            deploy_attempted=True,
            local_build_sha=local_build_sha,
            remote_build_sha=result.remote_build_sha,
        )

    status_after = evaluate_parity(
        required_capabilities,
        remote_after,
        local_build_sha=local_build_sha,
    )
    remote_after_sha = remote_after.get("build_git_sha")
    return ParityResult(
        status=status_after,
        mismatch_reason=(
            None if status_after is ParityStatus.MATCH else "modal_runtime_incompatible"
        ),
        deploy_attempted=True,
        local_build_sha=local_build_sha,
        remote_build_sha=(
            remote_after_sha
            if isinstance(remote_after_sha, str)
            else result.remote_build_sha
        ),
    )
