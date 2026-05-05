from __future__ import annotations

from typing import Any

from libs.harvest.client import HarvestClient, get_client
from libs.harvest.models import ProfileGetInput, ProfileSearchInput


def _bool_str(value: bool | None) -> str | None:
    if value is None:
        return None
    return "true" if value else "false"


def get_profile(
    input: ProfileGetInput,
    client: HarvestClient | None = None,
) -> dict[str, Any]:
    client = client or get_client()
    params: dict[str, Any] = {
        "url": input.url,
        "publicIdentifier": input.public_identifier,
        "profileId": input.profile_id,
        "main": _bool_str(input.main),
        "findEmail": _bool_str(input.find_email),
        "skipSmtp": _bool_str(input.skip_smtp),
        "includeAboutProfile": _bool_str(input.include_about_profile),
    }
    return client.get("/linkedin/profile", params)


def search_profiles(
    input: ProfileSearchInput,
    client: HarvestClient | None = None,
) -> dict[str, Any]:
    client = client or get_client()
    params: dict[str, Any] = {
        "search": input.search,
        "firstName": input.first_name,
        "lastName": input.last_name,
        "currentCompany": ",".join(input.current_company) or None,
        "pastCompany": ",".join(input.past_company) or None,
        "school": ",".join(input.school) or None,
        "title": input.title,
        "location": input.location,
        "geoId": input.geo_id,
        "industryId": ",".join(input.industry_id) or None,
        "keywordsCompany": input.keywords_company,
        "keywordsSchool": input.keywords_school,
        "followerOf": input.follower_of,
        "page": input.page,
    }
    return client.get("/linkedin/profile-search", params)
