from __future__ import annotations

import pytest

import modal

from cli.attio.preflight import run_people_preflight
from libs.attio.errors import ConfigurationError, ConnectivityError


class _FakeSecret:
    def __init__(self, hydrate_impl):
        self.hydrate_impl = hydrate_impl

    def hydrate(self) -> None:
        self.hydrate_impl()


def test_missing_secret_raises_configuration_error(monkeypatch) -> None:
    monkeypatch.setenv("MODAL_TOKEN_ID", "id_123")
    monkeypatch.setenv("MODAL_TOKEN_SECRET", "secret_123")

    def _secret_not_found(_name: str) -> _FakeSecret:
        raise modal.exception.NotFoundError("nope")

    monkeypatch.setattr(modal.Secret, "from_name", _secret_not_found)

    with pytest.raises(ConfigurationError) as exc_info:
        run_people_preflight(
            connectivity_probe=True,
            function_name="attio_search_people",
        )

    assert "attio" in str(exc_info.value)
    assert "modal secret create attio" in str(exc_info.value)


def test_transient_hydrate_error_raises_connectivity_error(monkeypatch) -> None:
    monkeypatch.setenv("MODAL_TOKEN_ID", "id_123")
    monkeypatch.setenv("MODAL_TOKEN_SECRET", "secret_123")

    def _secret_fails(_name: str) -> _FakeSecret:
        def _hydrate_fails():
            raise RuntimeError("grpc transport down")

        return _FakeSecret(_hydrate_fails)

    monkeypatch.setattr(modal.Secret, "from_name", _secret_fails)

    with pytest.raises(ConnectivityError):
        run_people_preflight(
            connectivity_probe=True,
            function_name="attio_search_people",
        )


def test_happy_path(monkeypatch) -> None:
    monkeypatch.setenv("MODAL_TOKEN_ID", "id_123")
    monkeypatch.setenv("MODAL_TOKEN_SECRET", "secret_123")

    def _secret_ok(_name: str) -> _FakeSecret:
        return _FakeSecret(lambda: None)

    monkeypatch.setattr(modal.Secret, "from_name", _secret_ok)

    def _from_name(_app: str, _fn: str):
        return object()

    monkeypatch.setattr(modal.Function, "from_name", _from_name)

    env_payload, warnings, parity_meta = run_people_preflight(
        connectivity_probe=True,
        function_name="attio_search_people",
    )

    assert env_payload["MODAL_TOKEN_ID"] == "id_123"
    assert isinstance(warnings, list)
    assert isinstance(parity_meta, dict)


def test_token_check_still_wins(monkeypatch) -> None:
    monkeypatch.delenv("MODAL_TOKEN_ID", raising=False)

    def _secret_fails(_name: str) -> _FakeSecret:
        pytest.fail("should not call hydrate if token is missing")

    monkeypatch.setattr(modal.Secret, "from_name", _secret_fails)

    with pytest.raises(ConfigurationError) as exc_info:
        run_people_preflight(
            connectivity_probe=True,
            function_name="attio_search_people",
        )

    assert "MODAL_TOKEN" in str(exc_info.value)


def test_connectivity_probe_false_skips_secret_check(monkeypatch) -> None:
    monkeypatch.setenv("MODAL_TOKEN_ID", "id_123")
    monkeypatch.setenv("MODAL_TOKEN_SECRET", "secret_123")

    hydrate_called = {"count": 0}

    def _secret_fails(_name: str) -> _FakeSecret:
        def _hydrate():
            hydrate_called["count"] += 1
            raise RuntimeError("should not be called")

        return _FakeSecret(_hydrate)

    monkeypatch.setattr(modal.Secret, "from_name", _secret_fails)

    env_payload, _, _ = run_people_preflight(
        connectivity_probe=False,
        function_name="attio_search_people",
    )

    assert hydrate_called["count"] == 0
    assert env_payload["MODAL_TOKEN_ID"] == "id_123"
