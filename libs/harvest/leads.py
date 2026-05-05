from __future__ import annotations

from typing import Any

from libs.harvest.client import HarvestClient, get_client
from libs.harvest.models import LeadSearchInput


def _bool_str(value: bool | None) -> str | None:
    if value is None:
        return None
    return "true" if value else "false"


def _csv(values: list[str]) -> str | None:
    return ",".join(values) or None


def search_leads(
    input: LeadSearchInput,
    client: HarvestClient | None = None,
) -> dict[str, Any]:
    client = client or get_client()
    params: dict[str, Any] = {
        "search": input.search,
        "currentCompanies": _csv(input.current_companies),
        "pastCompanies": _csv(input.past_companies),
        "locations": _csv(input.locations),
        "geoIds": _csv(input.geo_ids),
        "schools": _csv(input.schools),
        "currentJobTitles": _csv(input.current_job_titles),
        "pastJobTitles": _csv(input.past_job_titles),
        "firstNames": _csv(input.first_names),
        "lastNames": _csv(input.last_names),
        "industryIds": _csv(input.industry_ids),
        "yearsAtCurrentCompanyIds": _csv(input.years_at_current_company_ids),
        "yearsOfExperienceIds": _csv(input.years_of_experience_ids),
        "seniorityLevelIds": _csv(input.seniority_level_ids),
        "functionIds": _csv(input.function_ids),
        "recentlyChangedJobs": _bool_str(input.recently_changed_jobs),
        "postedOnLinkedin": _bool_str(input.posted_on_linkedin),
        "profileLanguages": _csv(input.profile_languages),
        "companyHeadcount": _csv(input.company_headcount),
        "companyHeadquarterLocations": _csv(input.company_headquarter_locations),
        "excludeLocations": _csv(input.exclude_locations),
        "excludeGeoIds": _csv(input.exclude_geo_ids),
        "excludeCurrentCompanies": _csv(input.exclude_current_companies),
        "excludePastCompanies": _csv(input.exclude_past_companies),
        "excludeSchools": _csv(input.exclude_schools),
        "excludeCurrentJobTitles": _csv(input.exclude_current_job_titles),
        "excludePastJobTitles": _csv(input.exclude_past_job_titles),
        "excludeIndustryIds": _csv(input.exclude_industry_ids),
        "excludeSeniorityLevelIds": _csv(input.exclude_seniority_level_ids),
        "excludeFunctionIds": _csv(input.exclude_function_ids),
        "excludeCompanyHeadquarterLocations": _csv(
            input.exclude_company_headquarter_locations,
        ),
        "salesNavUrl": input.sales_nav_url,
        "page": input.page,
        "sessionId": input.session_id,
        "usePrivatePool": _bool_str(input.use_private_pool),
        "requiredAccountId": input.required_account_id,
    }
    return client.get("/linkedin/lead-search", params)
