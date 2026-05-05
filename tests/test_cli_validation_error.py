import os
import subprocess
import sys

import pytest


def _run_cli(
    *args: str,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    # Ensure Modal credentials are not malformed or empty strings
    # (test isolation can sometimes leave empty strings instead of unset)
    for token_key in ("MODAL_TOKEN_ID", "MODAL_TOKEN_SECRET"):
        if token_key in env and not env[token_key].strip():
            del env[token_key]
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def test_cli_help_works() -> None:
    result = _run_cli("--help")
    assert result.returncode == 0
    assert "gtm" in result.stdout.lower()


def _missing_modal_credentials() -> list[str]:
    required = ["MODAL_TOKEN_ID", "MODAL_TOKEN_SECRET"]
    return [name for name in required if not os.environ.get(name, "").strip()]


def _skip_if_missing_modal_credentials() -> None:
    if _missing_modal_credentials():
        pytest.skip(
            "CLI integration tests gated by credentials preflight failure in this module",
        )


def test_cli_add_person_with_validation_error() -> None:
    _skip_if_missing_modal_credentials()
    result = _run_cli(
        "attio",
        "people",
        "add",
        "invalid-email-format",
        "--first-name",
        "CLI",
        "--last-name",
        "Invalid",
    )

    assert result.returncode != 0
    error_output = (result.stderr or "") + (result.stdout or "")
    assert "literal_error" not in error_output
    assert "pydantic" not in error_output.lower()


def test_cli_add_person_with_valid_data() -> None:
    _skip_if_missing_modal_credentials()
    email = f"attio-cli-validation-{os.urandom(3).hex()}@example.com"
    result = _run_cli(
        "attio",
        "people",
        "add",
        email,
        "--first-name",
        "CLI",
        "--last-name",
        "Valid",
    )

    # Skip if auth error occurs (can happen if other tests modify credentials)
    if result.returncode != 0 and "Token ID is malformed" in result.stdout:
        pytest.skip(
            "Skipping due to malformed Modal token (likely from test isolation issue)",
        )

    assert result.returncode == 0
