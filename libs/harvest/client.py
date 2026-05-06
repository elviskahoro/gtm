"""Harvest API client for LinkedIn profile enrichment.

Fetches full LinkedIn profile data including location, contact info,
education, experience, and skills.
"""

import os

import httpx


def fetch_profile(linkedin_url: str) -> dict | None:
    """Fetch complete LinkedIn profile from Harvest API.

    Args:
        linkedin_url: Full LinkedIn profile URL (e.g., https://www.linkedin.com/in/username)

    Returns:
        Full profile dict with all Harvest API fields (location, emails, experience, etc.)
        or None if the API call fails or returns 404.

    Raises:
        ValueError: If HARVEST_API_KEY environment variable is not set.
    """
    api_key = os.environ.get("HARVEST_API_KEY")
    if not api_key:
        raise ValueError("HARVEST_API_KEY not set in environment")

    try:
        resp = httpx.get(
            "https://api.harvest-api.com/linkedin/profile",
            params={"url": linkedin_url},
            headers={"X-API-Key": api_key},
            timeout=10,
        )

        if resp.status_code not in (200, 404):
            return None

        if resp.status_code == 404:
            return None

        data = resp.json()
        if data is None:
            return None

        element = data.get("element", {})
        return element if element else None

    except (httpx.RequestError, httpx.HTTPError):
        return None
    except Exception:
        return None
