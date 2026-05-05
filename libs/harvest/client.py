from __future__ import annotations

import os
from typing import Any

import httpx

BASE_URL: str = "https://api.harvest-api.com"
TIMEOUT: int = 60


class HarvestClient:
    def __init__(
        self: HarvestClient,
        api_key: str,
        base_url: str = BASE_URL,
        timeout: int = TIMEOUT,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout

    def get(
        self: HarvestClient,
        path: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        clean: dict[str, Any] = {k: v for k, v in params.items() if v is not None}
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                url=f"{self.base_url}{path}",
                headers={"X-API-Key": self.api_key},
                params=clean,
            )
            response.raise_for_status()
        return response.json()


def get_client() -> HarvestClient:
    api_key = os.environ.get("HARVEST_API_KEY")
    if api_key is None:
        raise ValueError(
            "HARVEST_API_KEY is not present in the environment.",
        )
    if api_key == "":
        raise ValueError(
            "HARVEST_API_KEY is present but empty.",
        )
    return HarvestClient(api_key=api_key)
