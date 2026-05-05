from __future__ import annotations

from libs.attio.models import PersonInput
from libs.attio.values import (
    build_core_person_values,
    build_optional_person_values,
    format_location,
)


def test_format_location_city_mode_drops_street_granularity() -> None:
    value = format_location("123 Main St, San Francisco, CA", mode="city")
    assert value is not None
    assert value[0]["line_1"] is None
    assert value[0]["locality"] == "123 Main St"
    assert value[0]["region"] == "San Francisco"


def test_build_optional_person_values_serializes_notes_and_company() -> None:
    values = build_optional_person_values(
        company_domain="acme.com",
        notes="met at conference",
        location="San Francisco, CA",
        location_mode="city",
    )
    assert "associated_company" in values
    assert "notes" in values
    assert "primary_location" in values


def test_build_core_person_values_combines_primary_and_additional_emails() -> None:
    inp = PersonInput(
        email="a@example.com",
        additional_emails=["b@example.com", "a@example.com"],
    )
    values = build_core_person_values(inp)
    assert sorted(values["email_addresses"]) == ["a@example.com", "b@example.com"]


def test_build_core_person_values_partial_omits_emails_when_not_explicit() -> None:
    inp = PersonInput(email="lookup@example.com", first_name="X")
    values = build_core_person_values(inp, partial=True)
    assert "email_addresses" not in values


def test_location_mode_raw_retains_line_1() -> None:
    input_data = PersonInput(
        email="a@example.com",
        location="123 Main, SF, CA",
        location_mode="raw",
    )
    values = build_optional_person_values(
        company_domain=input_data.company_domain,
        notes=input_data.notes,
        location=input_data.location,
        location_mode=input_data.location_mode,
    )
    assert values["primary_location"][0]["line_1"] == "123 Main"
