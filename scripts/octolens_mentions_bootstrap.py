"""One-off bootstrap for the octolens_mentions custom object.

Usage:
    infisical run -- uv run python scripts/octolens_mentions_bootstrap.py --preview
    infisical run -- uv run python scripts/octolens_mentions_bootstrap.py --apply

Idempotent. Safe to re-run. Adding a new attribute = edit ATTRIBUTES below
and re-run.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# Anchor on the script's own directory so the script runs correctly regardless
# of CWD (per repo CLAUDE.md path-anchoring rule). `uv run path/to/script.py`
# does NOT chdir into the script's folder.
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from libs.attio.attributes import create_attribute  # noqa: E402
from libs.attio.objects import create_object  # noqa: E402

OBJECT_API_SLUG = "octolens_mentions"
OBJECT_SINGULAR = "Octolens mention"
OBJECT_PLURAL = "Octolens mentions"


AttrType = Literal[
    "text",
    "select",
    "multiselect",
    "checkbox",
    "number",
    "timestamp",
    "status",
    "record-reference",
]


@dataclass(frozen=True)
class AttrSpec:
    title: str
    api_slug: str
    attribute_type: AttrType
    is_multiselect: bool = False
    is_unique: bool = False
    description: str = ""


ATTRIBUTES: tuple[AttrSpec, ...] = (
    AttrSpec("Mention URL", "mention_url", "text", is_unique=True),
    AttrSpec("Source platform", "source_platform", "select"),
    AttrSpec("Source ID", "source_id", "text"),
    AttrSpec("Mention title", "mention_title", "text"),
    AttrSpec("Mention body", "mention_body", "text"),
    AttrSpec("Mention timestamp", "mention_timestamp", "timestamp"),
    AttrSpec("Author handle", "author_handle", "text"),
    AttrSpec("Author profile URL", "author_profile_url", "text"),
    AttrSpec("Author avatar URL", "author_avatar_url", "text"),
    AttrSpec("Relevance score", "relevance_score", "select"),
    AttrSpec("Relevance comment", "relevance_comment", "text"),
    AttrSpec("Primary keyword", "primary_keyword", "text"),
    AttrSpec("Keywords", "keywords", "multiselect", is_multiselect=True),
    AttrSpec("Octolens tags", "octolens_tags", "multiselect", is_multiselect=True),
    AttrSpec("Sentiment", "sentiment", "select"),
    AttrSpec("Language", "language", "text"),
    AttrSpec("Subreddit", "subreddit", "text"),
    AttrSpec("View ID", "view_id", "number"),
    AttrSpec("View name", "view_name", "text"),
    AttrSpec("Bookmarked", "bookmarked", "checkbox"),
    AttrSpec("Image URL", "image_url", "text"),
    AttrSpec("Last action", "last_action", "select"),
    AttrSpec("Triage status", "triage_status", "status"),
    AttrSpec("Related person", "related_person", "record-reference"),
    AttrSpec("Related company", "related_company", "record-reference"),
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--preview",
        action="store_true",
        help="Print what would happen; no writes.",
    )
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Create missing object + attributes.",
    )
    args = parser.parse_args()
    apply = bool(args.apply)

    print(f"[object]      {OBJECT_API_SLUG}")
    obj_result = create_object(
        api_slug=OBJECT_API_SLUG,
        singular_noun=OBJECT_SINGULAR,
        plural_noun=OBJECT_PLURAL,
        apply=apply,
    )
    if obj_result.object_created:
        obj_action = "created"
    elif obj_result.object_exists:
        obj_action = "exists"
    else:
        obj_action = "would-create"
    print(f"              {obj_action}")

    pending = 0
    for spec in ATTRIBUTES:
        attr_result = create_attribute(
            target_object=OBJECT_API_SLUG,
            title=spec.title,
            api_slug=spec.api_slug,
            attribute_type=spec.attribute_type,
            description=spec.description,
            is_multiselect=spec.is_multiselect,
            is_unique=spec.is_unique,
            apply=apply,
        )
        if attr_result.attribute_created:
            status = "created"
        elif attr_result.attribute_exists:
            status = "exists (skip)"
        else:
            status = "would-create"
            pending += 1
        print(
            f"[attribute]   {spec.api_slug:25s}  {spec.attribute_type:14s}  {status}",
        )

    if not apply:
        print(f"{pending} creates pending. Run with --apply to execute.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
