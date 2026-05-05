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


class _ModelLikeResponse:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def model_dump(self) -> dict[str, Any]:
        return self._data


def test_parallel_group_registered() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["parallel", "--help"])
    assert result.exit_code == 0
    assert "search" in result.stdout
    assert "extract" in result.stdout
    assert "findall" in result.stdout


def test_model_dump_response_handled(monkeypatch) -> None:
    import cli.parallel.search as search_cli

    class _ModelLikeFn:
        def remote(self, **_kwargs):
            return _ModelLikeResponse({"ok": True})

    monkeypatch.setattr(
        search_cli.modal.Function,
        "from_name",
        lambda _app, _fn: _ModelLikeFn(),  # pyright: ignore[reportUnknownLambdaType]
    )

    runner = CliRunner()
    result = runner.invoke(app, ["parallel", "search", "query", "test"])
    assert result.exit_code == 0
    assert json.loads(result.stdout) == {"ok": True}


def test_findall_create_empty_conditions_rejected(monkeypatch) -> None:
    import cli.parallel.findall as findall_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(findall_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    # conditions defaults to "[]" when omitted — should be rejected client-side
    result = runner.invoke(
        app,
        ["parallel", "findall", "create", "find saas", "company"],
    )
    assert result.exit_code == 1
    assert "conditions must contain at least one" in result.stderr


# --- search query ---


def test_search_query_help() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["parallel", "search", "query", "--help"])
    assert result.exit_code == 0
    assert "Search the web" in result.stdout


def test_search_query_missing_objective(monkeypatch) -> None:
    import cli.parallel.search as search_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(search_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(app, ["parallel", "search", "query"])
    assert result.exit_code == 1
    assert "objective is required" in result.stderr


def test_search_query_flags_forwarded(monkeypatch) -> None:
    import cli.parallel.search as search_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(search_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "parallel",
            "search",
            "query",
            "find saas companies",
            "--mode",
            "agentic",
            "--max",
            "5",
        ],
    )
    assert result.exit_code == 0
    call = registry.functions["parallel_search"].calls[0]
    assert call["payload"]["objective"] == "find saas companies"
    assert call["payload"]["mode"] == "agentic"
    assert call["payload"]["max_results"] == 5


def test_search_query_json_override(monkeypatch) -> None:
    import cli.parallel.search as search_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(search_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "parallel",
            "search",
            "query",
            "ignored",
            "--mode",
            "fast",
            "--json",
            '{"objective": "from json", "mode": "agentic", "max_results": 5}',
        ],
    )
    assert result.exit_code == 0
    call = registry.functions["parallel_search"].calls[0]
    assert call["payload"]["objective"] == "from json"
    assert call["payload"]["mode"] == "agentic"
    assert call["payload"]["max_results"] == 5


def test_search_query_json_malformed(monkeypatch) -> None:
    import cli.parallel.search as search_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(search_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["parallel", "search", "query", "test", "--json", "{bad json}"],
    )
    assert result.exit_code == 1
    assert "Error" in result.stderr


def test_search_query_api_key_override(monkeypatch) -> None:
    import cli.parallel.search as search_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(search_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "parallel",
            "search",
            "query",
            "test",
            "--parallel-api-key",
            "pk_override",
        ],
    )
    assert result.exit_code == 0
    call = registry.functions["parallel_search"].calls[0]
    assert call["api_keys"] == {"parallel_api_key": "pk_override"}


def test_search_query_json_stdout(monkeypatch) -> None:
    import cli.parallel.search as search_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(search_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(app, ["parallel", "search", "query", "test"])
    assert result.exit_code == 0
    parsed = json.loads(result.stdout)
    assert parsed["function"] == "parallel_search"


# --- extract excerpts ---


def test_extract_excerpts_help() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["parallel", "extract", "excerpts", "--help"])
    assert result.exit_code == 0
    assert "Extract focused excerpts" in result.stdout


def test_extract_excerpts_missing_args(monkeypatch) -> None:
    import cli.parallel.extract as extract_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(extract_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(app, ["parallel", "extract", "excerpts"])
    assert result.exit_code == 1
    assert "url and objective are required" in result.stderr


def test_extract_excerpts_flags_forwarded(monkeypatch) -> None:
    import cli.parallel.extract as extract_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(extract_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["parallel", "extract", "excerpts", "https://example.com", "pricing info"],
    )
    assert result.exit_code == 0
    call = registry.functions["parallel_extract_excerpts"].calls[0]
    assert call["payload"]["url"] == "https://example.com"
    assert call["payload"]["objective"] == "pricing info"


def test_extract_excerpts_json_override(monkeypatch) -> None:
    import cli.parallel.extract as extract_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(extract_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "parallel",
            "extract",
            "excerpts",
            "ignored",
            "ignored",
            "--json",
            '{"url": "https://real.com", "objective": "from json"}',
        ],
    )
    assert result.exit_code == 0
    call = registry.functions["parallel_extract_excerpts"].calls[0]
    assert call["payload"]["url"] == "https://real.com"
    assert call["payload"]["objective"] == "from json"


def test_extract_excerpts_json_malformed(monkeypatch) -> None:
    import cli.parallel.extract as extract_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(extract_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["parallel", "extract", "excerpts", "url", "obj", "--json", "{bad}"],
    )
    assert result.exit_code == 1
    assert "Error" in result.stderr


def test_extract_excerpts_api_key_override(monkeypatch) -> None:
    import cli.parallel.extract as extract_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(extract_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "parallel",
            "extract",
            "excerpts",
            "https://example.com",
            "info",
            "--parallel-api-key",
            "pk_override",
        ],
    )
    assert result.exit_code == 0
    call = registry.functions["parallel_extract_excerpts"].calls[0]
    assert call["api_keys"] == {"parallel_api_key": "pk_override"}


def test_extract_excerpts_json_stdout(monkeypatch) -> None:
    import cli.parallel.extract as extract_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(extract_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["parallel", "extract", "excerpts", "https://example.com", "info"],
    )
    assert result.exit_code == 0
    parsed = json.loads(result.stdout)
    assert parsed["function"] == "parallel_extract_excerpts"


# --- extract full ---


def test_extract_full_help() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["parallel", "extract", "full", "--help"])
    assert result.exit_code == 0
    assert "Extract full content" in result.stdout


def test_extract_full_missing_url(monkeypatch) -> None:
    import cli.parallel.extract as extract_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(extract_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(app, ["parallel", "extract", "full"])
    assert result.exit_code == 1
    assert "url is required" in result.stderr


def test_extract_full_flags_forwarded(monkeypatch) -> None:
    import cli.parallel.extract as extract_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(extract_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["parallel", "extract", "full", "https://example.com"],
    )
    assert result.exit_code == 0
    call = registry.functions["parallel_extract_full_content"].calls[0]
    assert call["payload"]["url"] == "https://example.com"


def test_extract_full_json_override(monkeypatch) -> None:
    import cli.parallel.extract as extract_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(extract_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "parallel",
            "extract",
            "full",
            "ignored",
            "--json",
            '{"url": "https://real.com"}',
        ],
    )
    assert result.exit_code == 0
    call = registry.functions["parallel_extract_full_content"].calls[0]
    assert call["payload"]["url"] == "https://real.com"


def test_extract_full_json_malformed(monkeypatch) -> None:
    import cli.parallel.extract as extract_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(extract_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["parallel", "extract", "full", "url", "--json", "{bad}"],
    )
    assert result.exit_code == 1
    assert "Error" in result.stderr


def test_extract_full_api_key_override(monkeypatch) -> None:
    import cli.parallel.extract as extract_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(extract_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "parallel",
            "extract",
            "full",
            "https://example.com",
            "--parallel-api-key",
            "pk_override",
        ],
    )
    assert result.exit_code == 0
    call = registry.functions["parallel_extract_full_content"].calls[0]
    assert call["api_keys"] == {"parallel_api_key": "pk_override"}


def test_extract_full_json_stdout(monkeypatch) -> None:
    import cli.parallel.extract as extract_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(extract_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["parallel", "extract", "full", "https://example.com"],
    )
    assert result.exit_code == 0
    parsed = json.loads(result.stdout)
    assert parsed["function"] == "parallel_extract_full_content"


# --- findall create ---


def test_findall_create_help() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["parallel", "findall", "create", "--help"])
    assert result.exit_code == 0
    assert "Start a FindAll" in result.stdout


def test_findall_create_missing_objective_or_entity_type(monkeypatch) -> None:
    import cli.parallel.findall as findall_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(findall_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(app, ["parallel", "findall", "create"])
    assert result.exit_code == 1
    assert "objective and entity_type are required" in result.stderr


def test_findall_create_flags_forwarded(monkeypatch) -> None:
    import cli.parallel.findall as findall_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(findall_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "parallel",
            "findall",
            "create",
            "find saas companies",
            "company",
            '[{"name": "revenue", "description": "annual revenue > 1M"}]',
            "--limit",
            "20",
            "--generator",
            "pro",
        ],
    )
    assert result.exit_code == 0
    call = registry.functions["parallel_findall_create"].calls[0]
    assert call["payload"]["objective"] == "find saas companies"
    assert call["payload"]["entity_type"] == "company"
    assert call["payload"]["match_conditions"] == [
        {"name": "revenue", "description": "annual revenue > 1M"},
    ]
    assert call["payload"]["match_limit"] == 20
    assert call["payload"]["generator"] == "pro"


def test_findall_create_json_override(monkeypatch) -> None:
    import cli.parallel.findall as findall_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(findall_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    json_payload = json.dumps(
        {
            "objective": "from json",
            "entity_type": "person",
            "match_conditions": [{"name": "role", "description": "VP or above"}],
            "match_limit": 50,
            "generator": "core",
        },
    )
    result = runner.invoke(
        app,
        [
            "parallel",
            "findall",
            "create",
            "ignored",
            "ignored",
            "--json",
            json_payload,
        ],
    )
    assert result.exit_code == 0
    call = registry.functions["parallel_findall_create"].calls[0]
    assert call["payload"]["objective"] == "from json"
    assert call["payload"]["entity_type"] == "person"
    assert call["payload"]["generator"] == "core"


def test_findall_create_json_empty_conditions_rejected(monkeypatch) -> None:
    import cli.parallel.findall as findall_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(findall_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    json_payload = json.dumps(
        {
            "objective": "find saas",
            "entity_type": "company",
            "match_conditions": [],
        },
    )
    result = runner.invoke(
        app,
        [
            "parallel",
            "findall",
            "create",
            "ignored",
            "ignored",
            "--json",
            json_payload,
        ],
    )
    assert result.exit_code == 1
    assert "Error" in result.stderr


def test_findall_create_json_malformed(monkeypatch) -> None:
    import cli.parallel.findall as findall_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(findall_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "parallel",
            "findall",
            "create",
            "obj",
            "type",
            "--json",
            "{bad json}",
        ],
    )
    assert result.exit_code == 1
    assert "Error" in result.stderr


def test_findall_create_api_key_override(monkeypatch) -> None:
    import cli.parallel.findall as findall_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(findall_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "parallel",
            "findall",
            "create",
            "find saas",
            "company",
            '[{"name": "rev", "description": "big"}]',
            "--parallel-api-key",
            "pk_override",
        ],
    )
    assert result.exit_code == 0
    call = registry.functions["parallel_findall_create"].calls[0]
    assert call["api_keys"] == {"parallel_api_key": "pk_override"}


def test_findall_create_json_stdout(monkeypatch) -> None:
    import cli.parallel.findall as findall_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(findall_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "parallel",
            "findall",
            "create",
            "find saas",
            "company",
            '[{"name": "rev", "description": "big"}]',
        ],
    )
    assert result.exit_code == 0
    parsed = json.loads(result.stdout)
    assert parsed["function"] == "parallel_findall_create"


# --- findall result ---


def test_findall_result_help() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["parallel", "findall", "result", "--help"])
    assert result.exit_code == 0
    assert "Get results from a completed" in result.stdout


def test_findall_result_missing_findall_id(monkeypatch) -> None:
    import cli.parallel.findall as findall_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(findall_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(app, ["parallel", "findall", "result"])
    assert result.exit_code == 1
    assert "findall_id is required" in result.stderr


def test_findall_result_flags_forwarded(monkeypatch) -> None:
    import cli.parallel.findall as findall_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(findall_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(app, ["parallel", "findall", "result", "fa_abc123"])
    assert result.exit_code == 0
    call = registry.functions["parallel_findall_result"].calls[0]
    assert call["payload"]["findall_id"] == "fa_abc123"


def test_findall_result_json_override(monkeypatch) -> None:
    import cli.parallel.findall as findall_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(findall_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "parallel",
            "findall",
            "result",
            "ignored",
            "--json",
            '{"findall_id": "fa_from_json"}',
        ],
    )
    assert result.exit_code == 0
    call = registry.functions["parallel_findall_result"].calls[0]
    assert call["payload"]["findall_id"] == "fa_from_json"


def test_findall_result_json_malformed(monkeypatch) -> None:
    import cli.parallel.findall as findall_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(findall_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["parallel", "findall", "result", "id", "--json", "{bad}"],
    )
    assert result.exit_code == 1
    assert "Error" in result.stderr


def test_findall_result_api_key_override(monkeypatch) -> None:
    import cli.parallel.findall as findall_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(findall_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "parallel",
            "findall",
            "result",
            "fa_abc123",
            "--parallel-api-key",
            "pk_override",
        ],
    )
    assert result.exit_code == 0
    call = registry.functions["parallel_findall_result"].calls[0]
    assert call["api_keys"] == {"parallel_api_key": "pk_override"}


def test_findall_result_json_stdout(monkeypatch) -> None:
    import cli.parallel.findall as findall_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(findall_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(app, ["parallel", "findall", "result", "fa_abc123"])
    assert result.exit_code == 0
    parsed = json.loads(result.stdout)
    assert parsed["function"] == "parallel_findall_result"


# --- findall status ---


def test_findall_status_help() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["parallel", "findall", "status", "--help"])
    assert result.exit_code == 0
    assert "Check the status" in result.stdout


def test_findall_status_missing_findall_id(monkeypatch) -> None:
    import cli.parallel.findall as findall_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(findall_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(app, ["parallel", "findall", "status"])
    assert result.exit_code == 1
    assert "findall_id is required" in result.stderr


def test_findall_status_flags_forwarded(monkeypatch) -> None:
    import cli.parallel.findall as findall_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(findall_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(app, ["parallel", "findall", "status", "fa_abc123"])
    assert result.exit_code == 0
    call = registry.functions["parallel_findall_status"].calls[0]
    assert call["payload"]["findall_id"] == "fa_abc123"


def test_findall_status_json_override(monkeypatch) -> None:
    import cli.parallel.findall as findall_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(findall_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "parallel",
            "findall",
            "status",
            "ignored",
            "--json",
            '{"findall_id": "fa_from_json"}',
        ],
    )
    assert result.exit_code == 0
    call = registry.functions["parallel_findall_status"].calls[0]
    assert call["payload"]["findall_id"] == "fa_from_json"


def test_findall_status_json_malformed(monkeypatch) -> None:
    import cli.parallel.findall as findall_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(findall_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["parallel", "findall", "status", "id", "--json", "{bad}"],
    )
    assert result.exit_code == 1
    assert "Error" in result.stderr


def test_findall_status_api_key_override(monkeypatch) -> None:
    import cli.parallel.findall as findall_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(findall_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "parallel",
            "findall",
            "status",
            "fa_abc123",
            "--parallel-api-key",
            "pk_override",
        ],
    )
    assert result.exit_code == 0
    call = registry.functions["parallel_findall_status"].calls[0]
    assert call["api_keys"] == {"parallel_api_key": "pk_override"}


def test_findall_status_json_stdout(monkeypatch) -> None:
    import cli.parallel.findall as findall_cli

    registry = _FakeModalRegistry()
    monkeypatch.setattr(findall_cli.modal.Function, "from_name", registry.from_name)

    runner = CliRunner()
    result = runner.invoke(app, ["parallel", "findall", "status", "fa_abc123"])
    assert result.exit_code == 0
    parsed = json.loads(result.stdout)
    assert parsed["function"] == "parallel_findall_status"
