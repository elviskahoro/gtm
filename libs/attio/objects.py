from __future__ import annotations

from libs.attio.client import get_client
from libs.attio.models import ObjectCreateResult


def create_object(
    *,
    api_slug: str,
    singular_noun: str,
    plural_noun: str,
    apply: bool,
) -> ObjectCreateResult:
    """Idempotently create a custom object in Attio.

    Checks for an existing object with the given api_slug; if absent and
    ``apply`` is True, calls ``POST /v2/objects``. Re-runs are no-ops.
    """
    with get_client() as client:
        objects_response = client.objects.get_v2_objects()
        existing_slugs = {getattr(obj, "api_slug", "") for obj in objects_response.data}
        object_exists = api_slug in existing_slugs
        object_created = False

        if not object_exists and apply:
            client.objects.post_v2_objects(
                data={
                    "api_slug": api_slug,
                    "singular_noun": singular_noun,
                    "plural_noun": plural_noun,
                },
            )
            object_created = True

    return ObjectCreateResult(
        mode="apply" if apply else "preview",
        api_slug=api_slug,
        object_exists=object_exists,
        object_created=object_created,
    )
