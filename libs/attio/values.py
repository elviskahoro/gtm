from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Literal

from libs.attio.models import MeetingInput, MentionInput, PersonInput, TrackingEventInput


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


def format_person_record_ref(record_id: str | None) -> list[dict[str, Any]] | None:
    if not record_id:
        return None
    return [{"target_object": "people", "target_record_id": record_id}]


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

    if input.github_handle:
        values["github_handle"] = input.github_handle
    if input.github_url:
        values["github_url"] = input.github_url

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


# ---------- Octolens mentions ----------

# Fields the webhook MUST NEVER write. Enforced both here (builder-level) and
# at the type level by MentionInput not declaring them. Belt-and-suspenders.
# related_person is excluded from this set because it's written programmatically
# by the dispatcher when linking LinkedIn mentions to Person records.
_HUMAN_OWNED_MENTION_FIELDS: frozenset[str] = frozenset(
    {"triage_status", "related_company"},
)

# Fields set at record creation that must never be overwritten by an update.
_IMMUTABLE_AFTER_CREATE: frozenset[str] = frozenset({"source_platform", "source_id"})


def _scalar_value(v: Any) -> list[dict[str, Any]]:
    """Wrap a scalar into Attio's standard ``[{"value": ...}]`` list shape."""
    return [{"value": v}]


def _select_value(option: str) -> list[dict[str, str]]:
    """Single-select attribute shape: ``[{"option": "<title>"}]``."""
    return [{"option": option}]


def _multiselect_values(options: list[str]) -> list[dict[str, str]]:
    return [{"option": opt} for opt in options]


def build_create_mention_values(input: MentionInput) -> dict[str, Any]:
    values: dict[str, Any] = {}

    values["mention_url"] = _scalar_value(input.mention_url)
    values["last_action"] = _select_value(input.last_action)
    values["source_platform"] = _select_value(input.source_platform)
    values["source_id"] = _scalar_value(input.source_id)
    values["mention_body"] = _scalar_value(input.mention_body)
    values["mention_timestamp"] = _scalar_value(input.mention_timestamp.isoformat())
    values["author_handle"] = _scalar_value(input.author_handle)
    values["primary_keyword"] = _scalar_value(input.primary_keyword)
    values["bookmarked"] = _scalar_value(input.bookmarked)

    if input.mention_title is not None:
        values["mention_title"] = _scalar_value(input.mention_title)
    if input.author_profile_url is not None:
        values["author_profile_url"] = _scalar_value(input.author_profile_url)
    if input.author_avatar_url is not None:
        values["author_avatar_url"] = _scalar_value(input.author_avatar_url)
    if input.relevance_score is not None:
        values["relevance_score"] = _select_value(input.relevance_score)
    if input.relevance_comment is not None:
        values["relevance_comment"] = _scalar_value(input.relevance_comment)
    if input.sentiment is not None:
        values["sentiment"] = _select_value(input.sentiment)
    if input.language is not None:
        values["language"] = _scalar_value(input.language)
    if input.subreddit is not None:
        values["subreddit"] = _scalar_value(input.subreddit)
    if input.view_id is not None:
        values["view_id"] = _scalar_value(input.view_id)
    if input.view_name is not None:
        values["view_name"] = _scalar_value(input.view_name)
    if input.image_url is not None:
        values["image_url"] = _scalar_value(input.image_url)

    if input.keywords:
        values["keywords"] = _multiselect_values(input.keywords)
    if input.octolens_tags:
        values["octolens_tags"] = _multiselect_values(input.octolens_tags)

    if input.related_person_record_id is not None:
        person_ref = format_person_record_ref(input.related_person_record_id)
        if person_ref:
            values["related_person"] = person_ref

    # Guard the invariant. Should be unreachable since MentionInput doesn't
    # declare these fields, but kept here in case the model grows.
    for forbidden in _HUMAN_OWNED_MENTION_FIELDS:
        assert forbidden not in values, f"Webhook tried to write {forbidden!r}"

    return values


def build_update_mention_values(input: MentionInput) -> dict[str, Any]:
    values = build_create_mention_values(input)
    for immutable in _IMMUTABLE_AFTER_CREATE:
        values.pop(immutable, None)
    return values


def build_tracking_event_values(input: TrackingEventInput) -> dict[str, list[dict]]:
    """Build the Attio values dict for a tracking_events record write.

    Omits optional slugs that are None / empty so we don't accidentally
    clobber existing values with a write of an empty payload.
    """
    values: dict[str, list[dict]] = {
        "name": _scalar_value(input.name),
        "event_type": _scalar_value(input.event_type),
        "external_id": _scalar_value(input.external_id),
        "captured_url": _scalar_value(input.captured_url),
        "body": _scalar_value(input.body_json),
        "timestamp": _scalar_value(input.event_timestamp.isoformat()),
    }
    if input.referrer is not None:
        values["referrer"] = _scalar_value(input.referrer)
    if input.is_repeat_visit is not None:
        values["is_repeat_visit"] = _scalar_value(input.is_repeat_visit)
    if input.tags:
        values["tags"] = _multiselect_values(input.tags)
    if input.city is not None:
        values["city"] = _scalar_value(input.city)
    if input.state is not None:
        values["state"] = _scalar_value(input.state)
    if input.zipcode is not None:
        values["zipcode"] = _scalar_value(input.zipcode)
    if input.related_person_record_id is not None:
        person_ref = format_person_record_ref(input.related_person_record_id)
        if person_ref:
            values["people"] = person_ref
    if input.related_company_record_id is not None:
        company_ref = _record_ref_companies(input.related_company_record_id)
        if company_ref:
            values["company"] = company_ref
    return values


def _record_ref_companies(record_id: str | None) -> list[dict[str, Any]] | None:
    """Format a company record reference."""
    if not record_id:
        return None
    return [{"target_object": "companies", "target_record_id": record_id}]
