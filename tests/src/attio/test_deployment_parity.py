from __future__ import annotations

from src.attio.deployment_parity import (
    ParityStatus,
    ensure_modal_parity,
    evaluate_parity,
)


def test_evaluate_parity_returns_match_when_capability_present() -> None:
    status = evaluate_parity(
        {"attio_people_upsert.additional_emails": True},
        {
            "capabilities": {
                "attio_people_upsert.additional_emails": True,
            },
        },
    )
    assert status is ParityStatus.MATCH


def test_evaluate_parity_returns_mismatch_when_capability_missing() -> None:
    status = evaluate_parity(
        {"attio_people_upsert.additional_emails": True},
        {"capabilities": {}},
    )
    assert status is ParityStatus.MISMATCH


def test_sync_mode_deploy_attempts_single_redeploy_then_rechecks(
    monkeypatch,
) -> None:
    import src.attio.deployment_parity as parity

    fetch_calls = {"count": 0}
    deploy_calls = {"count": 0}

    def _fetch(_modal_app: str) -> dict[str, object]:
        fetch_calls["count"] += 1
        if fetch_calls["count"] == 1:
            return {"capabilities": {}}
        return {"capabilities": {"attio_people_upsert.additional_emails": True}}

    def _deploy(_cmd: list[str]) -> None:
        deploy_calls["count"] += 1

    monkeypatch.setattr(parity, "fetch_remote_metadata", _fetch)
    monkeypatch.setattr(parity, "run_deploy_command", _deploy)

    result = ensure_modal_parity(
        sync_mode="deploy",
        modal_app="elvis-ai",
        required_capabilities={"attio_people_upsert.additional_emails": True},
        deploy_cmd=["modal", "deploy", "deploy.py", "--name", "elvis-ai"],
    )

    assert result.status is ParityStatus.MATCH
    assert fetch_calls["count"] == 2
    assert deploy_calls["count"] == 1
