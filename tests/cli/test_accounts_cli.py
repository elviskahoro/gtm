from __future__ import annotations

import json
from typing import Any

from typer.testing import CliRunner

from cli.main import app


class _FakeModalFunction:
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls: list[dict[str, Any]] = []

    def remote(self, **kwargs):
        self.calls.append(kwargs)
        p = kwargs.get("payload", {})
        if self.name in {
            "gtm_batch_add_people",
            "gtm_batch_add_companies",
        }:
            mode = "apply" if p.get("apply") else "preview"
            records = p.get("records", [])
            return {
                "mode": mode,
                "requested": len(records),
                "created": len(records) if mode == "apply" else 0,
                "skipped": 0 if mode == "apply" else len(records),
            }

        return {"ok": True, "function": self.name}


class _FakeModalRegistry:
    def __init__(self) -> None:
        self.functions: dict[str, _FakeModalFunction] = {}

    def from_name(self, _app_name: str, function_name: str):
        fn = self.functions.get(function_name)
        if fn is None:
            fn = _FakeModalFunction(function_name)
            self.functions[function_name] = fn
        return fn


class _StrictModelLikeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def model_dump(self, *, mode: str) -> dict[str, Any]:
        assert mode == "json"
        return self.payload


def test_gtm_command_group_registered() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["accounts", "--help"])
    assert result.exit_code == 0
    assert "research" in result.stdout
    assert "find-people" in result.stdout
    assert "batch-add-people" in result.stdout


def test_non_mutating_reject_apply() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["accounts", "research", "find acme", "--apply"])
    assert result.exit_code != 0
    assert "No such option" in result.stderr


def test_batch_add_people_defaults_to_preview(monkeypatch) -> None:
    import cli.accounts.batch as gtm_batch

    registry = _FakeModalRegistry()
    monkeypatch.setattr(gtm_batch.modal.Function, "from_name", registry.from_name)
    monkeypatch.setenv("ATTIO_API_KEY", "ak_test")

    runner = CliRunner()
    payload = json.dumps([{"email": "ada@example.com"}])
    result = runner.invoke(app, ["accounts", "batch-add-people", "--records", payload])
    assert result.exit_code == 0
    out = json.loads(result.stdout)
    assert out["mode"] == "preview"
    assert (
        registry.functions["gtm_batch_add_people"].calls[0]["payload"]["apply"] is False
    )


def test_batch_add_people_apply_true_when_flag_present(monkeypatch) -> None:
    import cli.accounts.batch as gtm_batch

    registry = _FakeModalRegistry()
    monkeypatch.setattr(gtm_batch.modal.Function, "from_name", registry.from_name)
    monkeypatch.setenv("ATTIO_API_KEY", "ak_test")

    runner = CliRunner()
    payload = json.dumps([{"email": "ada@example.com"}])
    result = runner.invoke(
        app,
        ["accounts", "batch-add-people", "--records", payload, "--apply"],
    )
    assert result.exit_code == 0
    out = json.loads(result.stdout)
    assert out["mode"] == "apply"
    assert (
        registry.functions["gtm_batch_add_people"].calls[0]["payload"]["apply"] is True
    )


def test_json_stdout_on_success(monkeypatch) -> None:
    import cli.accounts.research as gtm_research

    registry = _FakeModalRegistry()
    monkeypatch.setattr(gtm_research.modal.Function, "from_name", registry.from_name)
    monkeypatch.setenv("PARALLEL_API_KEY", "pk_test")

    runner = CliRunner()
    result = runner.invoke(app, ["accounts", "research", "find acme"])
    assert result.exit_code == 0
    parsed = json.loads(result.stdout)
    assert parsed["function"] == "gtm_research"


def test_contract_matrix_research_modal_binding_and_env(monkeypatch) -> None:
    import cli.accounts.research as gtm_research

    registry = _FakeModalRegistry()
    monkeypatch.setattr(gtm_research.modal.Function, "from_name", registry.from_name)
    monkeypatch.setenv("PARALLEL_API_KEY", "pk_test")

    runner = CliRunner()
    result = runner.invoke(app, ["accounts", "research", "find acme"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["function"] == "gtm_research"
    call = registry.functions["gtm_research"].calls[0]
    assert call["payload"]["objective"] == "find acme"


def test_contract_matrix_find_people_modal_binding_and_env(monkeypatch) -> None:
    import cli.accounts.people as gtm_people

    registry = _FakeModalRegistry()
    monkeypatch.setattr(gtm_people.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(app, ["accounts", "find-people", "vp sales acme"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["function"] == "gtm_find_people"
    call = registry.functions["gtm_find_people"].calls[0]
    assert call["payload"]["query"] == "vp sales acme"


def test_contract_matrix_enrich_modal_binding_and_env(monkeypatch) -> None:
    import cli.accounts.research as gtm_research

    registry = _FakeModalRegistry()
    monkeypatch.setattr(gtm_research.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(app, ["accounts", "enrich", "https://acme.com", "funding"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["function"] == "gtm_enrich"
    call = registry.functions["gtm_enrich"].calls[0]
    assert call["payload"]["url"] == "https://acme.com"


def test_contract_matrix_map_account_hierarchy_modal_binding_and_env(
    monkeypatch,
) -> None:
    import cli.accounts.accounts as gtm_accounts

    registry = _FakeModalRegistry()
    monkeypatch.setattr(gtm_accounts.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(app, ["accounts", "map-account-hierarchy", "acme"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["function"] == "gtm_map_account_hierarchy"
    call = registry.functions["gtm_map_account_hierarchy"].calls[0]
    assert call["payload"]["account"] == "acme"


def test_contract_matrix_batch_add_companies_modal_binding_and_env(monkeypatch) -> None:
    import cli.accounts.batch as gtm_batch

    registry = _FakeModalRegistry()
    monkeypatch.setattr(gtm_batch.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    payload = json.dumps([{"name": "Acme", "domain": "acme.com"}])
    result = runner.invoke(
        app,
        ["accounts", "batch-add-companies", "--records", payload],
    )

    assert result.exit_code == 0
    output = json.loads(result.stdout)
    assert output["mode"] == "preview"
    call = registry.functions["gtm_batch_add_companies"].calls[0]
    assert call["payload"]["apply"] is False


def test_contract_matrix_non_mutating_commands_reject_apply() -> None:
    runner = CliRunner()
    assert (
        runner.invoke(app, ["accounts", "research", "find acme", "--apply"]).exit_code
        != 0
    )
    assert (
        runner.invoke(app, ["accounts", "find-people", "vp sales", "--apply"]).exit_code
        != 0
    )
    assert (
        runner.invoke(
            app,
            ["accounts", "enrich", "https://acme.com", "funding", "--apply"],
        ).exit_code
        != 0
    )
    assert (
        runner.invoke(
            app,
            ["accounts", "map-account-hierarchy", "acme", "--apply"],
        ).exit_code
        != 0
    )


def test_batch_failure_cli_exit_zero_for_partial_success(monkeypatch) -> None:
    import cli.accounts.batch as gtm_batch

    class _PartialSuccessFn:
        def remote(self, **_kwargs):
            return {
                "mode": "apply",
                "requested": 2,
                "created": 1,
                "conflicts": 0,
                "errors": 1,
                "results": [
                    {"status": "created", "email": "ada@example.com"},
                    {"status": "error", "email": "grace@example.com"},
                ],
            }

    monkeypatch.setattr(
        gtm_batch.modal.Function,
        "from_name",
        lambda _app, _fn: _PartialSuccessFn(),  # pyright: ignore[reportUnknownLambdaType]
    )
    monkeypatch.setenv("ATTIO_API_KEY", "ak_test")

    runner = CliRunner()
    payload = json.dumps([{"email": "ada@example.com"}, {"email": "grace@example.com"}])
    result = runner.invoke(
        app,
        ["accounts", "batch-add-people", "--records", payload, "--apply"],
    )
    assert result.exit_code == 0
    assert json.loads(result.stdout)["errors"] == 1


def test_batch_failure_cli_exit_one_for_all_failed(monkeypatch) -> None:
    import cli.accounts.batch as gtm_batch

    class _AllFailedFn:
        def remote(self, **_kwargs):
            return {
                "mode": "apply",
                "requested": 2,
                "created": 0,
                "conflicts": 0,
                "errors": 2,
                "results": [
                    {"status": "error", "email": "ada@example.com"},
                    {"status": "error", "email": "grace@example.com"},
                ],
            }

    monkeypatch.setattr(
        gtm_batch.modal.Function,
        "from_name",
        lambda _app, _fn: _AllFailedFn(),  # pyright: ignore[reportUnknownLambdaType]
    )
    monkeypatch.setenv("ATTIO_API_KEY", "ak_test")

    runner = CliRunner()
    payload = json.dumps([{"email": "ada@example.com"}, {"email": "grace@example.com"}])
    result = runner.invoke(
        app,
        ["accounts", "batch-add-people", "--records", payload, "--apply"],
    )
    assert result.exit_code == 1


def test_batch_add_people_accepts_model_like_response(monkeypatch) -> None:
    import cli.accounts.batch as gtm_batch

    class _ModelLikeFn:
        def remote(self, **_kwargs):
            return _StrictModelLikeResponse(
                {
                    "mode": "apply",
                    "requested": 1,
                    "created": 1,
                    "skipped": 0,
                    "errors": 0,
                },
            )

    monkeypatch.setattr(
        gtm_batch.modal.Function,
        "from_name",
        lambda _app, _fn: _ModelLikeFn(),  # pyright: ignore[reportUnknownLambdaType]
    )
    monkeypatch.setenv("ATTIO_API_KEY", "ak_test")

    runner = CliRunner()
    payload = json.dumps([{"email": "ada@example.com"}])
    result = runner.invoke(
        app,
        ["accounts", "batch-add-people", "--records", payload, "--apply"],
    )
    assert result.exit_code == 0
    assert json.loads(result.stdout)["created"] == 1


def test_research_prints_json_for_model_like_response(monkeypatch) -> None:
    import cli.accounts.research as gtm_research

    class _ModelLikeFn:
        def remote(self, **_kwargs):
            return _StrictModelLikeResponse({"ok": True, "function": "gtm_research"})

    monkeypatch.setattr(
        gtm_research.modal.Function,
        "from_name",
        lambda _app, _fn: _ModelLikeFn(),  # pyright: ignore[reportUnknownLambdaType]
    )
    monkeypatch.setenv("PARALLEL_API_KEY", "pk_test")

    runner = CliRunner()
    result = runner.invoke(app, ["accounts", "research", "find acme"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["function"] == "gtm_research"


def test_validation_limits_cli_rejects_empty_records(monkeypatch) -> None:
    monkeypatch.setenv("ATTIO_API_KEY", "ak_test")
    runner = CliRunner()
    result = runner.invoke(app, ["accounts", "batch-add-people", "--records", "[]"])
    assert result.exit_code == 1
    assert "records must not be empty" in result.stderr


def test_validation_limits_cli_rejects_non_array_records(monkeypatch) -> None:
    monkeypatch.setenv("ATTIO_API_KEY", "ak_test")
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["accounts", "batch-add-people", "--records", '{"email":"a@b.com"}'],
    )
    assert result.exit_code == 1
    assert "--records must decode to a JSON array" in result.stderr


def test_validation_limits_cli_rejects_non_object_record_items(monkeypatch) -> None:
    monkeypatch.setenv("ATTIO_API_KEY", "ak_test")
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["accounts", "batch-add-people", "--records", '["not-an-object"]'],
    )
    assert result.exit_code == 1
    assert "records must contain JSON objects" in result.stderr
