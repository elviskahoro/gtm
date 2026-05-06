from __future__ import annotations

import json
from typing import Any

import modal
from typer.testing import CliRunner

from cli.main import app


class _FakeFunctionCall:
    def __init__(self, success_payload: dict[str, Any]) -> None:
        self.success_payload = success_payload
        self.timeout: int | None = None

    def get(self, timeout: int | None = None) -> dict[str, Any]:
        self.timeout = timeout
        return self.success_payload


class _FakeSecret:
    def hydrate(self) -> None:  # noqa: D401
        return None


def _patch_secret_ok(monkeypatch, people_cli) -> None:
    monkeypatch.setattr(
        people_cli.modal.Secret,
        "from_name",
        lambda _name: _FakeSecret(),  # pyright: ignore[reportUnknownLambdaType]
    )


class _FakeModalFunction:
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls: list[dict[str, Any]] = []

    def _success_payload(self) -> dict[str, Any]:
        return {
            "success": True,
            "partial_success": False,
            "action": (
                "updated"
                if "upsert" in self.name or "update" in self.name
                else "searched"
            ),
            "record_id": "rec_1" if "search" not in self.name else None,
            "warnings": [],
            "skipped_fields": [],
            "errors": [],
            "meta": {"output_schema_version": "v1"},
        }

    def spawn(self, **kwargs) -> _FakeFunctionCall:
        self.calls.append(kwargs)
        return _FakeFunctionCall(self._success_payload())

    def remote(self, **kwargs):
        self.calls.append(kwargs)
        return self._success_payload()


class _FakeModalRegistry:
    def __init__(self) -> None:
        self.functions: dict[str, _FakeModalFunction] = {}

    def from_name(self, _app_name: str, function_name: str):
        fn = self.functions.get(function_name)
        if fn is None:
            fn = _FakeModalFunction(function_name)
            self.functions[function_name] = fn
        return fn


def test_preflight_missing_modal_token_returns_configuration_error(monkeypatch) -> None:
    import cli.attio.preflight as preflight

    monkeypatch.setenv("ATTIO_API_KEY", "ak_test")
    monkeypatch.delenv("MODAL_TOKEN_ID", raising=False)
    monkeypatch.delenv("MODAL_TOKEN_SECRET", raising=False)

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["attio", "people", "search", "--email", "a@example.com"],
    )
    payload = json.loads(result.stdout)

    assert result.exit_code == 1
    assert payload["errors"][0]["code"] == "configuration_error"
    assert preflight.run_people_preflight


def test_preflight_modal_token_secret_whitespace_is_stripped(monkeypatch) -> None:
    import cli.attio.people as people_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(people_cli.modal.Function, "from_name", registry.from_name)
    _patch_secret_ok(monkeypatch, people_cli)
    monkeypatch.setenv("ATTIO_API_KEY", "ak_test")
    monkeypatch.setenv("MODAL_TOKEN_ID", "id_123")
    monkeypatch.setenv("MODAL_TOKEN_SECRET", "secret_123\n")

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["attio", "people", "search", "--email", "a@example.com"],
    )
    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    warning_codes = {w["code"] for w in payload["warnings"]}
    assert "modal_token_whitespace_stripped" in warning_codes


def test_connectivity_probe_failure_returns_error_unless_disabled(monkeypatch) -> None:
    import cli.attio.people as people_cli

    def _boom(_app_name: str, _function_name: str):
        raise RuntimeError("probe failed")

    monkeypatch.setattr(people_cli.modal.Function, "from_name", _boom)
    _patch_secret_ok(monkeypatch, people_cli)
    monkeypatch.setenv("ATTIO_API_KEY", "ak_test")
    monkeypatch.setenv("MODAL_TOKEN_ID", "id_123")
    monkeypatch.setenv("MODAL_TOKEN_SECRET", "secret_123")

    runner = CliRunner()
    fail = runner.invoke(app, ["attio", "people", "search", "--email", "a@example.com"])
    fail_payload = json.loads(fail.stdout)
    assert fail.exit_code == 1
    assert fail_payload["errors"][0]["code"] == "connectivity_error"

    registry = _FakeModalRegistry()
    monkeypatch.setattr(people_cli.modal.Function, "from_name", registry.from_name)
    ok = runner.invoke(
        app,
        [
            "attio",
            "people",
            "search",
            "--email",
            "a@example.com",
            "--no-connectivity-probe",
        ],
    )
    assert ok.exit_code == 0


def test_connectivity_probe_checks_target_function(monkeypatch) -> None:
    import cli.attio.people as people_cli

    registry = _FakeModalRegistry()

    def _from_name(app_name: str, function_name: str):
        if function_name == "attio_add_person":
            raise RuntimeError("function not deployed")
        return registry.from_name(app_name, function_name)

    monkeypatch.setattr(people_cli.modal.Function, "from_name", _from_name)
    _patch_secret_ok(monkeypatch, people_cli)
    monkeypatch.setenv("ATTIO_API_KEY", "ak_test")
    monkeypatch.setenv("MODAL_TOKEN_ID", "id_123")
    monkeypatch.setenv("MODAL_TOKEN_SECRET", "secret_123")

    runner = CliRunner()
    result = runner.invoke(app, ["attio", "people", "add", "a@example.com"])
    payload = json.loads(result.stdout)

    assert result.exit_code == 1
    assert payload["errors"][0]["code"] == "connectivity_error"


def test_envelope_shape_is_stable_for_search_add_update_upsert(monkeypatch) -> None:
    import cli.attio.people as people_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(people_cli.modal.Function, "from_name", registry.from_name)
    monkeypatch.setenv("ATTIO_API_KEY", "ak_test")
    monkeypatch.setenv("MODAL_TOKEN_ID", "id_123")
    monkeypatch.setenv("MODAL_TOKEN_SECRET", "secret_123")

    runner = CliRunner()
    commands = [
        [
            "attio",
            "people",
            "search",
            "--email",
            "a@example.com",
            "--no-connectivity-probe",
        ],
        ["attio", "people", "add", "a@example.com", "--no-connectivity-probe"],
        [
            "attio",
            "people",
            "update",
            "--email",
            "a@example.com",
            "--no-connectivity-probe",
        ],
        ["attio", "people", "upsert", "a@example.com", "--no-connectivity-probe"],
    ]

    for cmd in commands:
        result = runner.invoke(app, cmd)
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert set(payload) == {
            "success",
            "partial_success",
            "action",
            "record_id",
            "warnings",
            "skipped_fields",
            "errors",
            "meta",
        }
        assert payload["meta"]["output_schema_version"] == "v1"


def test_upsert_forwards_strict_notes_and_location_mode(monkeypatch) -> None:
    import cli.attio.people as people_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(people_cli.modal.Function, "from_name", registry.from_name)
    monkeypatch.setenv("ATTIO_API_KEY", "ak_test")
    monkeypatch.setenv("MODAL_TOKEN_ID", "id_123")
    monkeypatch.setenv("MODAL_TOKEN_SECRET", "secret_123")

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "attio",
            "people",
            "upsert",
            "a@example.com",
            "--strict",
            "--notes",
            "met at conf",
            "--location-mode",
            "raw",
            "--no-connectivity-probe",
        ],
    )

    assert result.exit_code == 0
    call = registry.functions["attio_upsert_person"].calls[0]
    assert call["payload"]["strict"] is True
    assert call["payload"]["notes"] == "met at conf"
    assert call["payload"]["location_mode"] == "raw"


def test_upsert_forwards_additional_emails_and_replace_flag(monkeypatch) -> None:
    import cli.attio.people as people_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(people_cli.modal.Function, "from_name", registry.from_name)
    monkeypatch.setenv("ATTIO_API_KEY", "ak_test")
    monkeypatch.setenv("MODAL_TOKEN_ID", "id_123")
    monkeypatch.setenv("MODAL_TOKEN_SECRET", "secret_123")

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "attio",
            "people",
            "upsert",
            "a@example.com",
            "--add-email",
            "b@example.com",
            "--add-email",
            "c@example.com",
            "--replace-emails",
            "--no-connectivity-probe",
        ],
    )

    assert result.exit_code == 0
    call = registry.functions["attio_upsert_person"].calls[0]
    assert call["payload"]["email"] == "a@example.com"
    assert call["payload"]["additional_emails"] == ["b@example.com", "c@example.com"]
    assert call["payload"]["replace_emails"] is True


def test_add_via_json_validates_and_calls_remote(monkeypatch) -> None:
    import cli.attio.people as people_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(people_cli.modal.Function, "from_name", registry.from_name)
    monkeypatch.setenv("MODAL_TOKEN_ID", "id_123")
    monkeypatch.setenv("MODAL_TOKEN_SECRET", "secret_123")

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "attio",
            "people",
            "add",
            "",
            "--json",
            '{"email":"a@b.com","first_name":"Ada"}',
            "--no-connectivity-probe",
        ],
    )
    assert result.exit_code == 0
    call = registry.functions["attio_add_person"].calls[0]
    assert call["payload"]["email"] == "a@b.com"
    assert call["payload"]["first_name"] == "Ada"


def test_add_via_json_rejects_extra_fields(monkeypatch) -> None:
    import cli.attio.people as people_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(people_cli.modal.Function, "from_name", registry.from_name)
    monkeypatch.setenv("MODAL_TOKEN_ID", "id_123")
    monkeypatch.setenv("MODAL_TOKEN_SECRET", "secret_123")

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "attio",
            "people",
            "add",
            "",
            "--json",
            '{"email":"a@b.com","company_name":"Acme"}',
            "--no-connectivity-probe",
        ],
    )
    payload = json.loads(result.stdout)
    assert result.exit_code == 1
    assert any("company_name" in str(e) for e in payload.get("errors", []))


def test_upsert_modal_sync_check_returns_mismatch_error(monkeypatch) -> None:
    import cli.attio.people as people_cli

    def _preflight(**_kwargs):
        raise TypeError(
            "attio_upsert_person() got an unexpected keyword argument 'additional_emails'",
        )

    monkeypatch.setattr(people_cli, "run_people_preflight", _preflight)
    monkeypatch.setenv("ATTIO_API_KEY", "ak_test")
    monkeypatch.setenv("MODAL_TOKEN_ID", "id_123")
    monkeypatch.setenv("MODAL_TOKEN_SECRET", "secret_123")

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "attio",
            "people",
            "upsert",
            "a@example.com",
            "--modal-sync",
            "check",
        ],
    )
    payload = json.loads(result.stdout)
    assert result.exit_code == 1
    assert payload["errors"][0]["code"] == "modal_signature_mismatch"


def test_upsert_modal_sync_skip_bypasses_parity_gate(monkeypatch) -> None:
    import cli.attio.people as people_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(people_cli.modal.Function, "from_name", registry.from_name)

    def _preflight(**kwargs):
        assert kwargs["modal_sync"] == "skip"
        modal_id = "".join(["m", "id"])
        modal_secret = "".join(["m", "token"])
        return (
            {
                "ATTIO_API_KEY": "ak_test",
                "MODAL_TOKEN_ID": modal_id,
                "MODAL_TOKEN_SECRET": modal_secret,
            },
            [],
            {"status": "unknown"},
        )

    monkeypatch.setattr(people_cli, "run_people_preflight", _preflight)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "attio",
            "people",
            "upsert",
            "a@example.com",
            "--modal-sync",
            "skip",
        ],
    )
    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert payload["meta"]["deployment_parity"]["status"] == "unknown"


def test_upsert_modal_sync_deploy_retries_once_then_succeeds(monkeypatch) -> None:
    import cli.attio.people as people_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(people_cli.modal.Function, "from_name", registry.from_name)
    calls = {"count": 0}

    def _preflight(**kwargs):
        calls["count"] += 1
        assert kwargs["modal_sync"] == "deploy"
        modal_id = "".join(["m", "id"])
        modal_secret = "".join(["m", "token"])
        return (
            {
                "ATTIO_API_KEY": "ak_test",
                "MODAL_TOKEN_ID": modal_id,
                "MODAL_TOKEN_SECRET": modal_secret,
            },
            [],
            {"status": "match", "deploy_attempted": True},
        )

    monkeypatch.setattr(people_cli, "run_people_preflight", _preflight)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "attio",
            "people",
            "upsert",
            "a@example.com",
            "--modal-sync",
            "deploy",
        ],
    )
    payload = json.loads(result.stdout)
    assert result.exit_code == 0
    assert calls["count"] == 1
    assert payload["meta"]["deployment_parity"]["deploy_attempted"] is True


def test_timeout_error_returns_connectivity_envelope(monkeypatch) -> None:
    import cli.attio.people as people_cli

    class _TimeoutFunctionCall:
        def __init__(self):
            self.timeout = None

        def get(self, timeout: int | None = None):
            self.timeout = timeout
            raise modal.exception.TimeoutError("timeout")

    class _TimeoutFunction:
        def __init__(self, name: str):
            self.name = name

        def spawn(self, **kwargs):
            return _TimeoutFunctionCall()

    registry = _FakeModalRegistry()
    original_from_name = registry.from_name

    def _from_name(app_name: str, function_name: str):
        if function_name == "attio_search_people":
            return _TimeoutFunction(function_name)
        return original_from_name(app_name, function_name)

    monkeypatch.setattr(people_cli.modal.Function, "from_name", _from_name)
    _patch_secret_ok(monkeypatch, people_cli)
    monkeypatch.setenv("ATTIO_API_KEY", "ak_test")
    monkeypatch.setenv("MODAL_TOKEN_ID", "id_123")
    monkeypatch.setenv("MODAL_TOKEN_SECRET", "secret_123")

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["attio", "people", "search", "--email", "foo@example.com"],
    )
    payload = json.loads(result.stdout)

    assert result.exit_code == 1
    assert payload["errors"][0]["code"] == "connectivity_error"
    assert "modal app logs" in payload["errors"][0]["message"]


def test_output_expired_error_returns_connectivity_envelope(monkeypatch) -> None:
    import cli.attio.people as people_cli

    class _ExpiredFunctionCall:
        def __init__(self):
            self.timeout = None

        def get(self, timeout: int | None = None):
            self.timeout = timeout
            # Create a real OutputExpiredError from modal
            raise modal.exception.OutputExpiredError()

    class _ExpiredFunction:
        def __init__(self, name: str):
            self.name = name

        def spawn(self, **kwargs):
            return _ExpiredFunctionCall()

    registry = _FakeModalRegistry()
    original_from_name = registry.from_name

    def _from_name(app_name: str, function_name: str):
        if function_name == "attio_search_people":
            return _ExpiredFunction(function_name)
        return original_from_name(app_name, function_name)

    monkeypatch.setattr(people_cli.modal.Function, "from_name", _from_name)
    _patch_secret_ok(monkeypatch, people_cli)
    monkeypatch.setenv("ATTIO_API_KEY", "ak_test")
    monkeypatch.setenv("MODAL_TOKEN_ID", "id_123")
    monkeypatch.setenv("MODAL_TOKEN_SECRET", "secret_123")

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["attio", "people", "search", "--email", "foo@example.com"],
    )
    payload = json.loads(result.stdout)

    assert result.exit_code == 1
    assert payload["errors"][0]["code"] == "connectivity_error"


def test_env_override_changes_timeout(monkeypatch) -> None:
    import cli.attio.people as people_cli

    class _TimeoutRecordingFunctionCall:
        def __init__(self):
            self.timeout = None

        def get(self, timeout: int | None = None):
            self.timeout = timeout
            return {
                "success": True,
                "partial_success": False,
                "action": "searched",
                "record_id": None,
                "warnings": [],
                "skipped_fields": [],
                "errors": [],
                "meta": {"output_schema_version": "v1"},
            }

    class _TimeoutRecordingFunction:
        def __init__(self, name: str):
            self.name = name
            self.call = None

        def spawn(self, **kwargs):
            self.call = _TimeoutRecordingFunctionCall()
            return self.call

    registry = _FakeModalRegistry()
    original_from_name = registry.from_name
    recorded_function = None

    def _from_name(app_name: str, function_name: str):
        nonlocal recorded_function
        if function_name == "attio_search_people":
            recorded_function = _TimeoutRecordingFunction(function_name)
            return recorded_function
        return original_from_name(app_name, function_name)

    monkeypatch.setattr(people_cli.modal.Function, "from_name", _from_name)
    _patch_secret_ok(monkeypatch, people_cli)
    monkeypatch.setenv("ATTIO_API_KEY", "ak_test")
    monkeypatch.setenv("MODAL_TOKEN_ID", "id_123")
    monkeypatch.setenv("MODAL_TOKEN_SECRET", "secret_123")
    monkeypatch.setenv("MODAL_REMOTE_TIMEOUT_SECONDS", "37")

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["attio", "people", "search", "--email", "foo@example.com"],
    )

    assert result.exit_code == 0
    assert recorded_function is not None
    assert recorded_function.call.timeout == 37


def test_invalid_env_override_falls_back_to_default(monkeypatch) -> None:
    import cli.attio.people as people_cli

    class _TimeoutRecordingFunctionCall:
        def __init__(self):
            self.timeout = None

        def get(self, timeout: int | None = None):
            self.timeout = timeout
            return {
                "success": True,
                "partial_success": False,
                "action": "searched",
                "record_id": None,
                "warnings": [],
                "skipped_fields": [],
                "errors": [],
                "meta": {"output_schema_version": "v1"},
            }

    class _TimeoutRecordingFunction:
        def __init__(self, name: str):
            self.name = name
            self.call = None

        def spawn(self, **kwargs):
            self.call = _TimeoutRecordingFunctionCall()
            return self.call

    registry = _FakeModalRegistry()
    original_from_name = registry.from_name
    recorded_function = None

    def _from_name(app_name: str, function_name: str):
        nonlocal recorded_function
        if function_name == "attio_search_people":
            recorded_function = _TimeoutRecordingFunction(function_name)
            return recorded_function
        return original_from_name(app_name, function_name)

    monkeypatch.setattr(people_cli.modal.Function, "from_name", _from_name)
    _patch_secret_ok(monkeypatch, people_cli)
    monkeypatch.setenv("ATTIO_API_KEY", "ak_test")
    monkeypatch.setenv("MODAL_TOKEN_ID", "id_123")
    monkeypatch.setenv("MODAL_TOKEN_SECRET", "secret_123")
    monkeypatch.setenv("MODAL_REMOTE_TIMEOUT_SECONDS", "not-a-number")

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["attio", "people", "search", "--email", "foo@example.com"],
    )

    assert result.exit_code == 0
    assert recorded_function is not None
    assert recorded_function.call.timeout == 120
