from __future__ import annotations

import datetime as dt
import json
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from libs.granola.errors import RateLimitError, SourceReadError


class GranolaApiClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.granola.ai/v1",
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _request(
        self,
        path: str,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        query = f"?{urlencode(params)}" if params else ""
        url = f"{self.base_url}{path}{query}"
        parsed_url = urlparse(url)
        if parsed_url.scheme != "https":
            raise SourceReadError("Granola API base URL must use https")
        if not parsed_url.netloc:
            raise SourceReadError("Granola API base URL must include a host")
        req = Request(
            url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json",
            },
        )
        try:
            with urlopen(
                req,
                timeout=30,
            ) as response:  # nosec B310  # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected  # noqa: S310
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            if exc.code == 429:
                raise RateLimitError("Granola API rate limited") from exc
            raise SourceReadError(f"Granola API error status: {exc.code}") from exc
        except OSError as exc:
            raise SourceReadError(f"Granola API request failed: {exc}") from exc

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SourceReadError("Granola API returned malformed JSON") from exc

        if not isinstance(parsed, dict):
            raise SourceReadError("Granola API returned non-object payload")
        return parsed

    def list_notes(self, *, since: dt.datetime | None = None) -> list[dict[str, Any]]:
        cursor: str | None = None
        notes: list[dict[str, Any]] = []

        while True:
            params: dict[str, str] = {}
            if cursor:
                params["cursor"] = cursor
            if since:
                params["since"] = since.isoformat()
            payload = self._request("/notes", params=params)
            page_notes = payload.get("notes", [])
            if not isinstance(page_notes, list):
                raise SourceReadError("Granola API notes list missing")
            notes.extend(note for note in page_notes if isinstance(note, dict))
            cursor = payload.get("next")
            if not cursor:
                return notes

    def get_note(
        self,
        note_id: str,
        *,
        include_transcript: bool = True,
    ) -> dict[str, Any]:
        params = {"include": "transcript"} if include_transcript else None
        return self._request(f"/notes/{note_id}", params=params)
