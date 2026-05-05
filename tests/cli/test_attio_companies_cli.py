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
        return {
            "mode": "apply" if p.get("apply") else "preview",
            "attribute_title": p.get("title", ""),
            "attribute_slug": p.get("api_slug", ""),
            "attribute_type": p.get("attribute_type", "select"),
            "attribute_exists": True,
            "attribute_created": False,
        }


class _FakeModalRegistry:
    def __init__(self) -> None:
        self.functions: dict[str, _FakeModalFunction] = {}

    def from_name(self, _app_name: str, function_name: str):
        fn = self.functions.get(function_name)
        if fn is None:
            fn = _FakeModalFunction(function_name)
            self.functions[function_name] = fn
        return fn


def test_attio_companies_help_includes_create_attribute_command() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["attio", "companies", "--help"])
    assert result.exit_code == 0
    assert "create-attribute-type" in result.stdout


def test_create_attribute_type_calls_modal_with_payload(monkeypatch) -> None:
    import cli.attio.companies as attio_companies

    registry = _FakeModalRegistry()
    monkeypatch.setattr(attio_companies.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "attio",
            "companies",
            "create-attribute-type",
            "--title",
            "GTM Tool Type",
            "--api-slug",
            "gtm_tool_type",
        ],
    )
    assert result.exit_code == 0
    call = registry.functions["attio_create_companies_attribute"].calls[0]
    assert "payload" in call


def test_create_attribute_type_defaults_to_preview(monkeypatch) -> None:
    import cli.attio.companies as attio_companies

    registry = _FakeModalRegistry()
    monkeypatch.setattr(attio_companies.modal.Function, "from_name", registry.from_name)
    monkeypatch.setenv("ATTIO_API_KEY", "ak_test")

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "attio",
            "companies",
            "create-attribute-type",
            "--title",
            "GTM Tool Type",
            "--api-slug",
            "gtm_tool_type",
            "--type",
            "select",
            "--is-multiselect",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["mode"] == "preview"
    call = registry.functions["attio_create_companies_attribute"].calls[0]
    assert call["payload"]["apply"] is False
    assert call["payload"]["title"] == "GTM Tool Type"
    assert call["payload"]["api_slug"] == "gtm_tool_type"


def test_create_attribute_type_json_only_without_title_flags(monkeypatch) -> None:
    """--json alone must work (no required --title/--api-slug flags)."""
    import cli.attio.companies as attio_companies

    registry = _FakeModalRegistry()
    monkeypatch.setattr(attio_companies.modal.Function, "from_name", registry.from_name)

    payload = json.dumps(
        {
            "title": "From JSON",
            "api_slug": "from_json_slug",
            "attribute_type": "select",
            "apply": False,
        },
    )
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "attio",
            "companies",
            "create-attribute-type",
            "--json",
            payload,
        ],
    )
    assert result.exit_code == 0
    call = registry.functions["attio_create_companies_attribute"].calls[0]
    assert call["payload"]["title"] == "From JSON"
    assert call["payload"]["api_slug"] == "from_json_slug"


def test_create_attribute_type_apply_when_flag_present(monkeypatch) -> None:
    import cli.attio.companies as attio_companies

    registry = _FakeModalRegistry()
    monkeypatch.setattr(attio_companies.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "attio",
            "companies",
            "create-attribute-type",
            "--title",
            "GTM Tool Type",
            "--api-slug",
            "gtm_tool_type",
            "--type",
            "select",
            "--is-multiselect",
            "--apply",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["mode"] == "apply"
    call = registry.functions["attio_create_companies_attribute"].calls[0]
    assert call["payload"]["apply"] is True
    assert call["payload"]["title"] == "GTM Tool Type"
    assert call["payload"]["api_slug"] == "gtm_tool_type"
