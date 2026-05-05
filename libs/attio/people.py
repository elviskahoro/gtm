from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, Literal

from libs.attio.client import get_client
from libs.attio.contracts import (
    ErrorEntry,
    ReliabilityEnvelope,
    SkippedField,
    WarningEntry,
)
from libs.attio.errors import (
    AttioConflictError,
    AttioNotFoundError,
    AttioValidationError,
    ConflictError,
    SchemaMismatchError,
    classify_error,
    translate_modal_signature_error,
)
from libs.attio.models import PersonInput, PersonResult, PersonSearchResult
from libs.attio.sdk_boundary import (
    build_patch_record_request,
    build_post_record_request,
    extract_exception_body_text,
    is_uniqueness_conflict,
)
from libs.attio.values import (
    build_core_person_values,
    build_optional_person_values,
    normalize_email_address_list,
)

OPTIONAL_FIELD_WARNING_CODES = {
    "associated_company": "attio_associated_company_field_unavailable",
    "company": "attio_associated_company_field_unavailable",
    "notes": "attio_notes_field_unavailable",
    "primary_location": "attio_location_field_unavailable",
}

OPTIONAL_FIELD_ALIASES = {
    "associated_company": "company",
    "company": "associated_company",
}

logger = logging.getLogger(__name__)


def _result_envelope(
    *,
    success: bool,
    partial_success: bool,
    action: Literal["searched", "created", "updated", "noop", "failed"],
    record_id: str | None,
    warnings: list[WarningEntry] | None = None,
    skipped_fields: list[SkippedField] | None = None,
    errors: list[ErrorEntry] | None = None,
    meta: dict[str, Any] | None = None,
) -> ReliabilityEnvelope:
    merged_meta = {"output_schema_version": "v1"}
    if meta:
        merged_meta.update(meta)
    return ReliabilityEnvelope(
        success=success,
        partial_success=partial_success,
        action=action,
        record_id=record_id,
        warnings=warnings or [],
        skipped_fields=skipped_fields or [],
        errors=errors or [],
        meta=merged_meta,
    )


def _extract_email_addresses_from_record_values(values: Any) -> list[str]:
    if isinstance(values, dict):
        email_values = values.get("email_addresses", [])
    else:
        email_values = getattr(values, "email_addresses", []) or []
    out: list[str] = []
    for ev in email_values:
        if hasattr(ev, "email_address"):
            out.append(ev.email_address)
    return out


def _extract_result(data: Any) -> PersonResult:
    record_id: str = data.id.record_id

    email_addresses: list[str] = []
    name: str | None = None

    email_values = data.values.get("email_addresses", [])
    for ev in email_values:
        if hasattr(ev, "email_address"):
            email_addresses.append(ev.email_address)

    name_values = data.values.get("name", [])
    for nv in name_values:
        if hasattr(nv, "full_name"):
            name = nv.full_name
            break

    return PersonResult(
        record_id=record_id,
        email_addresses=email_addresses,
        name=name,
        raw={},
    )


def _extract_search_result(data: Any) -> PersonSearchResult:
    record_id: str = data.id.record_id

    name: str | None = None
    for nv in data.values.get("name", []):
        if hasattr(nv, "full_name"):
            name = nv.full_name
            break

    email_addresses: list[str] = []
    for ev in data.values.get("email_addresses", []):
        if hasattr(ev, "email_address"):
            email_addresses.append(ev.email_address)

    phone_numbers: list[str] = []
    for pv in data.values.get("phone_numbers", []):
        if hasattr(pv, "original_phone_number"):
            phone_numbers.append(pv.original_phone_number)
        elif hasattr(pv, "phone_number"):
            phone_numbers.append(pv.phone_number)

    linkedin: str | None = None
    for lv in data.values.get("linkedin", []):
        if hasattr(lv, "value"):
            linkedin = lv.value
            break

    location: str | None = None
    for loc in data.values.get("primary_location", []):
        if hasattr(loc, "locality"):
            parts = [
                getattr(loc, "locality", None),
                getattr(loc, "region", None),
                getattr(loc, "country_code", None),
            ]
            location = ", ".join(p for p in parts if p)
            break

    company_record_id: str | None = None
    for cv in data.values.get("company", []):
        if hasattr(cv, "target_record_id"):
            company_record_id = cv.target_record_id
            break

    return PersonSearchResult(
        record_id=record_id,
        name=name,
        email_addresses=email_addresses,
        phone_numbers=phone_numbers,
        linkedin=linkedin,
        location=location,
        company=company_record_id,
    )


def _search_people_raw(
    name: str | None = None,
    email: str | None = None,
    email_domain: str | None = None,
    phone: str | None = None,
    company: str | None = None,
    sample: bool = False,
    limit: int = 25,
) -> list[PersonSearchResult]:
    conditions: list[dict[str, Any]] = []
    if name:
        conditions.append({"name": {"$contains": name}})
    if email:
        conditions.append({"email_addresses": email})
    if email_domain:
        domain = email_domain.lstrip("@")
        conditions.append(
            {"email_addresses": {"email_address": {"$ends_with": f"@{domain}"}}},
        )
    if phone:
        conditions.append({"phone_numbers": {"$contains": phone}})

    if not sample and not conditions and not company:
        raise AttioValidationError(
            "Provide at least one search criterion or use --sample to browse recent records.",
        )

    with get_client() as client:
        if company:
            company_filter: dict[str, Any]
            if "." in company:
                company_filter = {
                    "$or": [
                        {"name": {"$contains": company}},
                        {"domains": {"domain": {"$eq": company}}},
                    ],
                }
            else:
                company_filter = {"name": {"$contains": company}}
            company_response = client.records.post_v2_objects_object_records_query(
                object="companies",
                filter_=company_filter,
                limit=10,
            )
            if not company_response.data:
                return []
            company_ids = [r.id.record_id for r in company_response.data]
            company_or = [{"company": {"target_record_id": cid}} for cid in company_ids]
            if len(company_or) == 1:
                conditions.append(company_or[0])
            else:
                conditions.append({"$or": company_or})

        if len(conditions) == 0:
            filter_: dict[str, Any] = {}
        elif len(conditions) == 1:
            filter_ = conditions[0]
        else:
            filter_ = {"$and": conditions}

        response = client.records.post_v2_objects_object_records_query(
            object="people",
            filter_=filter_,
            limit=limit,
        )
        results = [_extract_search_result(record) for record in response.data]

        company_ids = {r.company for r in results if r.company}
        if company_ids:
            name_map: dict[str, str] = {}
            for cid in company_ids:
                try:
                    cr = client.records.get_v2_objects_object_records_record_id_(
                        object="companies",
                        record_id=cid,
                    )
                    for nv in cr.data.values.get("name", []):
                        if hasattr(nv, "value"):
                            name_map[cid] = nv.value
                            break
                except Exception as exc:
                    logger.debug(
                        "Failed to resolve company name for company id %s: %s",
                        cid,
                        exc,
                    )
            for r in results:
                if r.company and r.company in name_map:
                    r.company = name_map[r.company]

        return results


def _detect_optional_field_from_exception(error: Exception) -> str | None:
    text = extract_exception_body_text(error)
    for field in OPTIONAL_FIELD_WARNING_CODES:
        if field in text:
            return field
    return None


def _attempt_person_write_with_optional_fallback(
    *,
    write_func: Callable[[dict[str, Any]], Any],
    core_values: dict[str, Any],
    optional_values: dict[str, Any],
    strict: bool,
) -> tuple[Any, list[WarningEntry], list[SkippedField]]:
    active_optional = dict(optional_values)
    alias_pairs_attempted: set[tuple[str, str]] = set()
    warnings: list[WarningEntry] = []
    skipped_fields: list[SkippedField] = []

    while True:
        values = {**core_values, **active_optional}
        try:
            response = write_func(values)
            return response, warnings, skipped_fields
        except Exception as exc:
            optional_field = _detect_optional_field_from_exception(exc)
            if not optional_field:
                raise

            alias_field = OPTIONAL_FIELD_ALIASES.get(optional_field)
            if optional_field not in active_optional and alias_field in active_optional:
                optional_field = alias_field
                alias_field = OPTIONAL_FIELD_ALIASES.get(optional_field)

            if strict:
                raise SchemaMismatchError(
                    f"Optional field unavailable: {optional_field}",
                    field=optional_field,
                ) from exc

            if (
                alias_field
                and optional_field in active_optional
                and alias_field not in active_optional
            ):
                alias_pair = (
                    (optional_field, alias_field)
                    if optional_field <= alias_field
                    else (alias_field, optional_field)
                )
                if alias_pair not in alias_pairs_attempted:
                    alias_pairs_attempted.add(alias_pair)
                    active_optional[alias_field] = active_optional.pop(optional_field)
                    continue

            if optional_field not in active_optional:
                raise

            del active_optional[optional_field]
            code = OPTIONAL_FIELD_WARNING_CODES[optional_field]
            warnings.append(
                WarningEntry(
                    code=code,
                    message=f"Skipped optional field '{optional_field}' due to schema mismatch.",
                    field=optional_field,
                    retryable=False,
                ),
            )
            skipped_fields.append(
                SkippedField(
                    field=optional_field,
                    reason="schema_mismatch",
                ),
            )


# Public alias for test and integration reliability checks.
attempt_person_write_with_optional_fallback = (
    _attempt_person_write_with_optional_fallback
)


def search_people(
    name: str | None = None,
    email: str | None = None,
    email_domain: str | None = None,
    phone: str | None = None,
    company: str | None = None,
    sample: bool = False,
    limit: int = 25,
) -> ReliabilityEnvelope:
    results = _search_people_raw(
        name=name,
        email=email,
        email_domain=email_domain,
        phone=phone,
        company=company,
        sample=sample,
        limit=limit,
    )
    return _result_envelope(
        success=True,
        partial_success=False,
        action="searched",
        record_id=None,
        meta={"results": [r.model_dump() for r in results], "count": len(results)},
    )


def add_person(input: PersonInput) -> ReliabilityEnvelope:
    core_values = build_core_person_values(input)
    optional_values = build_optional_person_values(
        company_domain=input.company_domain,
        notes=input.notes,
        location=input.location,
        location_mode=input.location_mode,
    )

    with get_client() as client:

        def _create_person(values: dict[str, Any]) -> Any:
            return client.records.post_v2_objects_object_records(
                object="people",
                data=build_post_record_request(values),
            )

        try:
            response, warnings, skipped_fields = (
                _attempt_person_write_with_optional_fallback(
                    write_func=_create_person,
                    core_values=core_values,
                    optional_values=optional_values,
                    strict=input.strict,
                )
            )
        except Exception as e:
            if is_uniqueness_conflict(e):
                raise AttioConflictError(
                    "Person already exists. Use 'update' instead.",
                ) from e
            raise

        person = _extract_result(response.data)
        return _result_envelope(
            success=True,
            partial_success=bool(skipped_fields),
            action="created",
            record_id=person.record_id,
            warnings=warnings,
            skipped_fields=skipped_fields,
            meta={"person": person.model_dump()},
        )


def update_person(
    record_id: str | None,
    email: str | None,
    input: PersonInput,
) -> ReliabilityEnvelope:
    with get_client() as client:
        if not record_id:
            if not email:
                raise AttioNotFoundError(
                    "Provide --id or --email to identify the person.",
                )
            query_response = client.records.post_v2_objects_object_records_query(
                object="people",
                filter_={"email_addresses": email},
                limit=2,
            )
            if not query_response.data:
                raise AttioNotFoundError(f"No person found with email: {email}")
            record_id = query_response.data[0].id.record_id

        get_resp = client.records.get_v2_objects_object_records_record_id_(
            object="people",
            record_id=record_id,
        )
        existing_emails = _extract_email_addresses_from_record_values(
            get_resp.data.values,
        )

        email_write: list[str] | None = None
        merge_warnings: list[WarningEntry] = []

        if input.replace_emails:
            seeds = [
                e
                for e in [input.email, *input.additional_emails]
                if e and str(e).strip()
            ]
            email_write = normalize_email_address_list(seeds)
            if not email_write:
                raise AttioValidationError(
                    "--replace-emails requires at least one email "
                    "(identity or --add-email).",
                )
            if {e.casefold() for e in email_write} != {
                e.casefold() for e in existing_emails
            }:
                merge_warnings.append(
                    WarningEntry(
                        code="multiple_emails_added",
                        message="Email addresses updated (--replace-emails).",
                        field="email_addresses",
                        retryable=False,
                    ),
                )
        elif input.additional_emails:
            email_write = normalize_email_address_list(
                [*existing_emails, input.email, *input.additional_emails],
            )
            new_keys = {e.casefold() for e in email_write} - {
                e.casefold() for e in existing_emails
            }
            if new_keys:
                merge_warnings.append(
                    WarningEntry(
                        code="multiple_emails_added",
                        message="New email address(es) merged onto existing person.",
                        field="email_addresses",
                        retryable=False,
                    ),
                )

        core_values = build_core_person_values(
            input,
            partial=True,
            email_addresses=email_write,
        )
        optional_values = build_optional_person_values(
            company_domain=input.company_domain,
            notes=input.notes,
            location=input.location,
            location_mode=input.location_mode,
        )

        def _update_person(values: dict[str, Any]) -> Any:
            return client.records.patch_v2_objects_object_records_record_id_(
                object="people",
                record_id=record_id,
                data=build_patch_record_request(values),
            )

        response, warnings, skipped_fields = (
            _attempt_person_write_with_optional_fallback(
                write_func=_update_person,
                core_values=core_values,
                optional_values=optional_values,
                strict=input.strict,
            )
        )
        warnings = [*merge_warnings, *warnings]

        person = _extract_result(response.data)
        return _result_envelope(
            success=True,
            partial_success=bool(skipped_fields),
            action="updated",
            record_id=person.record_id,
            warnings=warnings,
            skipped_fields=skipped_fields,
            meta={"person": person.model_dump()},
        )


def upsert_person(input: PersonInput, *, strict: bool = False) -> ReliabilityEnvelope:
    matches = _search_people_raw(email=input.email, limit=50)

    if len(matches) == 0:
        return add_person(input)

    if len(matches) == 1:
        return update_person(record_id=matches[0].record_id, email=None, input=input)

    if strict:
        raise ConflictError(
            f"Multiple people matched email {input.email}; strict mode rejects ambiguity.",
        )

    selected = sorted(m.record_id for m in matches)[0]
    envelope = update_person(record_id=selected, email=None, input=input)
    envelope.warnings.append(
        WarningEntry(
            code="upsert_multi_match_selected_record",
            message="Multiple records matched; selected lexicographically smallest record_id.",
            field="record_id",
            retryable=False,
        ),
    )
    envelope.partial_success = True
    return envelope


def error_envelope(error: Exception, *, strict: bool = False) -> ReliabilityEnvelope:
    classified = classify_error(
        translate_modal_signature_error(error),
        strict=strict,
    )
    return _result_envelope(
        success=False,
        partial_success=False,
        action="failed",
        record_id=None,
        errors=[
            ErrorEntry(
                code=classified.code,
                message=classified.message,
                error_type=classified.error_type,
                fatal=classified.fatal,
                field=classified.field,
            ),
        ],
    )
