"""Webhook ETL contract for Octolens mention ingestion."""

import re
from typing import Any, ClassVar, Literal, cast

from pydantic import BaseModel

from libs.dlt.bucket_naming import etl_bucket_name
from libs.octolens import Webhook as OctolensMentionWebhook
from src.octolens.utils import generate_gcs_filename


def normalize_linkedin_profile_url(url: str | None) -> str | None:
    """Parse and normalize a LinkedIn profile URL.

    Accepts only https?://(www.)?linkedin.com/in/<handle> URLs (reject company/feed/posts).
    Returns canonical form: https://www.linkedin.com/in/<handle> (lowercase host, no trailing slash).
    """
    if not url:
        return None

    url = url.strip()
    pattern = r"^https?://(?:www\.)?linkedin\.com/in/([^/?#]+)"
    match = re.match(pattern, url, re.IGNORECASE)

    if not match:
        return None

    handle = match.group(1)
    return f"https://www.linkedin.com/in/{handle}"


def split_author_name(full: str | None) -> tuple[str | None, str | None]:
    """Split author name into first and last name (best-effort).

    Single token → first_name only. Two+ tokens → first and last.
    """
    if not full:
        return None, None

    parts = full.strip().split(None, 1)
    if len(parts) == 0:
        return None, None
    if len(parts) == 1:
        return parts[0], None
    return parts[0], parts[1]


class Webhook(OctolensMentionWebhook):
    """Webhook subclass implementing ETL contract for Octolens mentions."""

    @staticmethod
    def modal_get_secret_collection_names() -> list[str]:
        return ["devx-gcp-202605111323"]

    @staticmethod
    def etl_get_bucket_name() -> str:
        return etl_bucket_name(source="octolens", entity_plural="mentions")

    @staticmethod
    def storage_get_app_name() -> str:
        return Webhook.etl_get_bucket_name()

    @staticmethod
    def storage_get_base_model_type() -> type[BaseModel] | None:
        return None

    @staticmethod
    def lance_get_project_name() -> str:
        raise NotImplementedError("LanceDB integration is Phase 2+")

    @staticmethod
    def lance_get_base_model_type() -> str:
        raise NotImplementedError("LanceDB integration is Phase 2+")

    VALID_ACTIONS: ClassVar[frozenset[str]] = frozenset(
        {"mention_created", "mention_updated"},
    )

    def etl_is_valid_webhook(self) -> bool:
        return self.action in self.VALID_ACTIONS

    def etl_get_invalid_webhook_error_msg(self) -> str:
        return f"Invalid webhook: {self.action}"

    def etl_get_json(self, storage: Any = None) -> str:
        del storage
        return self.data.model_dump_json()

    def etl_get_file_name(self) -> str:
        return generate_gcs_filename(
            source=self.data.source,
            keyword=self.data.keyword,
            timestamp=self.data.timestamp,
            author=self.data.author,
            source_id=self.data.source_id,
        )

    def etl_get_base_models(self, storage: Any) -> list[Any]:
        del storage
        raise NotImplementedError("LanceDB integration is Phase 2+")

    # --- Attio export contract ---

    @staticmethod
    def attio_get_secret_collection_names() -> list[str]:
        return ["attio"]

    @staticmethod
    def attio_get_app_name() -> str:
        return "export-to-attio-from-octolens-mentions"

    def attio_is_valid_webhook(self) -> bool:
        return self.action in self.VALID_ACTIONS

    def attio_get_invalid_webhook_error_msg(self) -> str:
        return f"Octolens action not eligible for Attio export: {self.action}"

    def attio_get_operations(self) -> list[Any]:
        if not self.attio_is_valid_webhook():
            return []
        # Local import to keep `libs/octolens/*` free of `src/attio/*` cycles
        # and to honor the no-cross-lib-import rule between adapters.
        from src.attio.ops import PersonRef, UpsertMention, UpsertPerson

        m = self.data
        ops: list[Any] = []

        # Emit UpsertPerson for LinkedIn mentions.
        linkedin_url = None
        related_person_ref = None
        if m.source == "linkedin":
            linkedin_url = normalize_linkedin_profile_url(m.author_profile_link)
            if linkedin_url:
                first_name, last_name = split_author_name(m.author)
                ops.append(
                    UpsertPerson(
                        linkedin=linkedin_url,
                        first_name=first_name,
                        last_name=last_name,
                    ),
                )
                related_person_ref = PersonRef(linkedin=linkedin_url)

        ops.append(
            UpsertMention(
                mention_url=m.url,
                last_action=self.action,  # type: ignore[arg-type]
                source_platform=m.source,
                source_id=m.source_id,
                mention_title=m.title,
                mention_body=m.body,
                mention_timestamp=m.timestamp,
                author_handle=m.author,
                author_profile_url=m.author_profile_link,
                author_avatar_url=m.author_avatar_url,
                relevance_score=m.relevance_score,
                relevance_comment=m.relevance_comment,
                primary_keyword=m.keyword,
                keywords=list(m.keywords),
                octolens_tags=[str(t) for t in m.tags],
                sentiment=_sentiment_or_none(m.sentiment_label),
                language=m.language,
                subreddit=m.subreddit,
                view_id=m.view_id,
                view_name=m.view_name,
                bookmarked=m.bookmarked,
                image_url=m.image_url,
                related_person=related_person_ref,
            ),
        )
        return ops


_SENTIMENT_VALUES: frozenset[str] = frozenset({"Positive", "Neutral", "Negative"})


def _sentiment_or_none(
    value: str | None,
) -> Literal["Positive", "Neutral", "Negative"] | None:
    if value in _SENTIMENT_VALUES:
        return cast(Literal["Positive", "Neutral", "Negative"], value)
    return None
