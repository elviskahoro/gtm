from __future__ import annotations

import os
from typing import cast

import modal

from libs.attio.models import AttributeCreateResult


def test_attio_create_companies_attribute_sets_and_clears_env_preview(
    monkeypatch,
) -> None:
    monkeypatch.delenv("ATTIO_API_KEY", raising=False)
    from src.attio.companies import attio_create_companies_attribute

    def _create(**kwargs):
        assert kwargs["title"] == "GTM Tool Type"
        assert kwargs["api_slug"] == "gtm_tool_type"
        assert kwargs["apply"] is False
        assert os.environ.get("ATTIO_API_KEY") == "ak_test"
        return AttributeCreateResult(
            mode="preview",
            attribute_title=kwargs["title"],
            attribute_slug=kwargs["api_slug"],
            attribute_type=kwargs["attribute_type"],
            attribute_exists=False,
            attribute_created=False,
        )

    monkeypatch.setattr("src.attio.companies.create_companies_attribute", _create)

    fn = cast(modal.Function, attio_create_companies_attribute)  # type: ignore
    result = fn.local(
        payload={
            "title": "GTM Tool Type",
            "api_slug": "gtm_tool_type",
            "attribute_type": "select",
            "description": "",
            "is_multiselect": True,
            "is_required": False,
            "is_unique": False,
            "apply": False,
        },
        api_keys={"attio_api_key": "ak_test"},
    )

    assert hasattr(result, "mode") and result.mode == "preview"
    assert "ATTIO_API_KEY" not in os.environ


def test_attio_create_companies_attribute_sets_and_clears_env_apply(
    monkeypatch,
) -> None:
    monkeypatch.delenv("ATTIO_API_KEY", raising=False)
    from src.attio.companies import attio_create_companies_attribute

    def _create(**kwargs):
        assert kwargs["title"] == "GTM Tool Type"
        assert kwargs["api_slug"] == "gtm_tool_type"
        assert kwargs["apply"] is True
        assert os.environ.get("ATTIO_API_KEY") == "ak_test"
        return AttributeCreateResult(
            mode="apply",
            attribute_title=kwargs["title"],
            attribute_slug=kwargs["api_slug"],
            attribute_type=kwargs["attribute_type"],
            attribute_exists=True,
            attribute_created=False,
        )

    monkeypatch.setattr("src.attio.companies.create_companies_attribute", _create)

    fn = cast(modal.Function, attio_create_companies_attribute)  # type: ignore
    result = fn.local(
        payload={
            "title": "GTM Tool Type",
            "api_slug": "gtm_tool_type",
            "attribute_type": "select",
            "description": "",
            "is_multiselect": True,
            "is_required": False,
            "is_unique": False,
            "apply": True,
        },
        api_keys={"attio_api_key": "ak_test"},
    )

    assert hasattr(result, "mode") and result.mode == "apply"
    assert (
        hasattr(result, "attribute_slug") and result.attribute_slug == "gtm_tool_type"
    )
    assert "ATTIO_API_KEY" not in os.environ
