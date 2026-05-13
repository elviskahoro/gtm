from __future__ import annotations

from attio.errors.sdkerror import SDKError

from libs.attio.client import get_client
from libs.attio.models import AttributeCreateResult


def create_attribute(
    *,
    target_object: str,
    title: str,
    api_slug: str,
    attribute_type: str = "select",
    description: str | None = None,
    is_multiselect: bool = True,
    is_required: bool = False,
    is_unique: bool = False,
    allowed_objects: list[str] | None = None,
    apply: bool,
) -> AttributeCreateResult:
    with get_client() as client:
        try:
            attributes_response = client.attributes.get_v2_target_identifier_attributes(
                target="objects",
                identifier=target_object,
            )
            existing_attribute_slugs = {
                getattr(attr, "api_slug", "") for attr in attributes_response.data
            }
        except SDKError as exc:
            # Parent object does not exist yet (e.g. preview run before bootstrap).
            # Treat as "no attributes exist" so the script can report would-create
            # instead of crashing.
            status = getattr(getattr(exc, "raw_response", None), "status_code", None)
            if status != 404:
                raise
            existing_attribute_slugs = set()
        attribute_exists = api_slug in existing_attribute_slugs
        attribute_created = False

        if not attribute_exists and apply:
            config: dict[str, object] = {}
            if attribute_type == "record-reference":
                # Attio requires record-reference attributes to declare which
                # object slugs they may point at. Default to ["people"] only if
                # the caller did not specify, to avoid silently mis-targeting.
                config["record_reference"] = {
                    "allowed_objects": allowed_objects or ["people"],
                }
            payload = {
                "title": title,
                "description": description or "",
                "api_slug": api_slug,
                "type": attribute_type,
                "is_required": is_required,
                "is_unique": is_unique,
                "is_multiselect": is_multiselect,
                "config": config,
            }
            client.attributes.post_v2_target_identifier_attributes(
                target="objects",
                identifier=target_object,
                data=payload,
            )
            attribute_created = True

    return AttributeCreateResult(
        mode="apply" if apply else "preview",
        attribute_title=title,
        attribute_slug=api_slug,
        attribute_type=attribute_type,
        attribute_exists=attribute_exists,
        attribute_created=attribute_created,
    )


def ensure_select_options(
    *,
    target_object: str,
    attribute_slug: str,
    options: list[str],
) -> list[str]:
    """Idempotently ensure each option title exists on a select attribute.

    Returns the list of titles that were newly created. No-op for options that
    already exist. Used both at bootstrap time (closed vocabularies) and at
    write time (open vocabularies like keywords/tags).
    """
    if not options:
        return []
    created: list[str] = []
    with get_client() as client:
        existing_resp = (
            client.attributes.get_v2_target_identifier_attributes_attribute_options(
                target="objects",
                identifier=target_object,
                attribute=attribute_slug,
            )
        )
        existing_titles = {getattr(o, "title", "") for o in existing_resp.data}
        for title in options:
            if title in existing_titles:
                continue
            client.attributes.post_v2_target_identifier_attributes_attribute_options(
                target="objects",
                identifier=target_object,
                attribute=attribute_slug,
                data={"title": title},
            )
            created.append(title)
    return created


def create_companies_attribute(
    *,
    title: str,
    api_slug: str,
    attribute_type: str = "select",
    description: str | None = None,
    is_multiselect: bool = True,
    is_required: bool = False,
    is_unique: bool = False,
    apply: bool,
) -> AttributeCreateResult:
    """Backward-compatible wrapper. Prefer ``create_attribute(target_object=...)`` for new code."""
    return create_attribute(
        target_object="companies",
        title=title,
        api_slug=api_slug,
        attribute_type=attribute_type,
        description=description,
        is_multiselect=is_multiselect,
        is_required=is_required,
        is_unique=is_unique,
        apply=apply,
    )
