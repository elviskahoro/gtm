from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Literal

from libs.attio.models import MeetingInput, PersonInput


def normalize_email_address_list(candidates: Iterable[str | None]) -> list[str]:
    """Strip, drop empties, dedupe case-insensitively; keep first-seen spelling."""
    out: list[str] = []
    seen_set: set[str] = set()
    for raw in candidates:
        if raw is None:
            continue
        e = str(raw).strip()
        if not e:
            continue
        key = e.casefold()
        if key in seen_set:
            continue
        seen_set.add(key)
        out.append(e)
    return out


def format_email(email: str) -> list[str] | None:
    if not email:
        return None
    return [email]


def format_name(
    first_name: str | None,
    last_name: str | None,
) -> list[dict[str, str]] | None:
    if not first_name and not last_name:
        return None

    full_name_parts: list[str] = []
    if first_name:
        full_name_parts.append(first_name)
    if last_name:
        full_name_parts.append(last_name)

    name_data: dict[str, str] = {
        "first_name": first_name or "",
        "last_name": last_name or "",
        "full_name": " ".join(full_name_parts),
    }

    return [name_data]


def format_phone(phone: str | None) -> list[dict[str, str]] | None:
    if not phone:
        return None

    phone_str: str = str(phone)
    phone_data: dict[str, str] = {"original_phone_number": phone_str}

    match True:
        case _ if phone_str.startswith(("+1", "1")):
            phone_data["country_code"] = "US"
        case _ if phone_str.startswith("+44"):
            phone_data["country_code"] = "GB"
        case _ if phone_str.startswith("+33"):
            phone_data["country_code"] = "FR"
        case _:
            phone_data["country_code"] = "US"

    return [phone_data]


def format_linkedin(url: str | None) -> list[str] | None:
    if not url:
        return None
    if not url.startswith("http"):
        url = f"https://linkedin.com/in/{url}"
    return [url]


def format_location(
    location: str | None,
    mode: Literal["raw", "city"] = "city",
) -> list[dict[str, Any]] | None:
    if not location:
        return None

    parts: list[str] = str(location).split(",")

    if mode == "raw":
        line_1 = parts[0].strip() if len(parts) > 0 else None
        locality = parts[1].strip() if len(parts) > 1 else None
        region = parts[2].strip() if len(parts) > 2 else None
    else:
        line_1 = None
        locality = parts[0].strip() if len(parts) > 0 else None
        region = parts[1].strip() if len(parts) > 1 else None

    location_data: dict[str, Any] = {
        "line_1": line_1,
        "line_2": None,
        "line_3": None,
        "line_4": None,
        "locality": locality,
        "region": region,
        "postcode": None,
        "country_code": "US",
        "latitude": None,
        "longitude": None,
    }
    return [location_data]


def format_company_ref(domain: str | None) -> list[dict[str, Any]] | None:
    if not domain:
        return None
    return [{"target_object": "companies", "domains": [{"domain": domain}]}]


def format_notes(notes: str | None) -> list[str] | None:
    if not notes:
        return None
    return [notes]


def format_company_name(name: str) -> list[dict[str, str]]:
    return [{"value": name}]


def format_company_domains(domain: str | None) -> list[dict[str, str]] | None:
    if not domain:
        return None
    return [{"domain": domain}]


def format_company_description(description: str | None) -> list[str] | None:
    if not description:
        return None
    return [description]


def build_core_person_values(
    input: PersonInput,
    *,
    partial: bool = False,
    email_addresses: list[str] | None = None,
) -> dict[str, Any]:
    values: dict[str, Any] = {}

    if email_addresses is not None:
        values["email_addresses"] = email_addresses
    elif not partial:
        combined = normalize_email_address_list([input.email, *input.additional_emails])
        values["email_addresses"] = combined

    name = format_name(input.first_name, input.last_name)
    if name:
        values["name"] = name

    phone = format_phone(input.phone)
    if phone:
        values["phone_numbers"] = phone

    linkedin = format_linkedin(input.linkedin)
    if linkedin:
        values["linkedin"] = linkedin

    return values


def build_optional_person_values(
    *,
    company_domain: str | None,
    notes: str | None,
    location: str | None,
    location_mode: Literal["raw", "city"] = "city",
) -> dict[str, Any]:
    values: dict[str, Any] = {}

    company = format_company_ref(company_domain)
    if company:
        values["associated_company"] = company

    location_value = format_location(location, mode=location_mode)
    if location_value:
        values["primary_location"] = location_value

    notes_value = format_notes(notes)
    if notes_value:
        values["notes"] = notes_value

    return values


def build_meeting_payload(input: MeetingInput) -> dict[str, Any]:
    """Build the JSON body for POST /v2/meetings.

    `external_ref` is a structured object per Attio's SDK: `{ical_uid, provider,
    is_recurring, original_start_time}`. Idempotency is keyed off `ical_uid`.
    Datetimes serialize as `{"datetime": <iso8601>}`; the iso8601 offset carries
    timezone info so no separate `timezone` key is emitted.
    """
    ref = input.external_ref
    data: dict[str, Any] = {
        "external_ref": {
            "ical_uid": ref.ical_uid,
            "provider": ref.provider,
            "is_recurring": ref.is_recurring,
            "original_start_time": ref.original_start_time,
        },
        "title": input.title,
        "description": input.description,
        "is_all_day": input.is_all_day,
        "start": {"datetime": input.start.isoformat()},
        "end": {"datetime": input.end.isoformat()},
        "participants": [
            {
                "email_address": p.email_address,
                "is_organizer": p.is_organizer,
                "status": p.status,
            }
            for p in input.participants
        ],
        "linked_records": [
            {"object": lr.object, "record_id": lr.record_id}
            for lr in input.linked_records
        ],
    }
    return {"data": data}
