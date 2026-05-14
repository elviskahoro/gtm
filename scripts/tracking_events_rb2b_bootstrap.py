"""Idempotent attribute bootstrap for tracking_events / rb2b_visit.

Adds:
  - event_type option: rb2b_visit
  - record-reference attribute: company (-> companies)
  - text attributes: captured_url, referrer, city, state, zipcode
  - checkbox attribute: is_repeat_visit
  - multiselect attribute: tags

Usage:
  uv run python scripts/tracking_events_rb2b_bootstrap.py --preview
  uv run python scripts/tracking_events_rb2b_bootstrap.py --apply
"""

from __future__ import annotations

import argparse
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

from libs.attio.attributes import create_attribute, ensure_select_options

TARGET = "tracking_events"


def main(apply: bool) -> int:
    results = []

    # event_type option
    added = ensure_select_options(
        target_object=TARGET,
        attribute_slug="event_type",
        options=["rb2b_visit"] if apply else [],
    )
    results.append(
        (
            "event_type:rb2b_visit option",
            "applied" if added else "would-apply" if not apply else "exists",
        ),
    )

    attrs = [
        ("company", "Company", "record-reference", {"allowed_objects": ["companies"]}),
        ("captured_url", "Captured URL", "text", None),
        ("referrer", "Referrer", "text", None),
        ("is_repeat_visit", "Is Repeat Visit", "checkbox", None),
        ("tags", "Tags", "select", None),
        ("city", "City", "text", None),
        ("state", "State", "text", None),
        ("zipcode", "Zipcode", "text", None),
    ]
    for slug, title, attr_type, extra in attrs:
        is_multi = slug == "tags"
        allowed = (extra or {}).get("allowed_objects")
        r = create_attribute(
            target_object=TARGET,
            title=title,
            api_slug=slug,
            attribute_type=attr_type,
            is_multiselect=is_multi,
            allowed_objects=allowed,
            apply=apply,
        )
        results.append(
            (
                slug,
                "created"
                if r.attribute_created
                else "exists"
                if r.attribute_exists
                else "would-create",
            ),
        )

    for slug, status in results:
        print(f"  {slug:30s} {status}")
    print(f"\nMode: {'apply' if apply else 'preview'}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--preview", action="store_true")
    g.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    raise SystemExit(main(apply=args.apply))
