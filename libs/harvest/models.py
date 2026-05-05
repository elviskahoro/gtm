from __future__ import annotations

from pydantic import BaseModel, model_validator

# --- Profile (GET /linkedin/profile) ---


class ProfileGetInput(BaseModel):
    url: str | None = None
    public_identifier: str | None = None
    profile_id: str | None = None
    main: bool | None = None
    find_email: bool | None = None
    skip_smtp: bool | None = None
    include_about_profile: bool | None = None

    @model_validator(mode="after")
    def _at_least_one_identifier(self: ProfileGetInput) -> ProfileGetInput:
        if not (self.url or self.public_identifier or self.profile_id):
            raise ValueError(
                "One of url, public_identifier, or profile_id is required.",
            )
        return self


# --- Profile search (GET /linkedin/profile-search) ---


class ProfileSearchInput(BaseModel):
    search: str
    first_name: str | None = None
    last_name: str | None = None
    current_company: list[str] = []
    past_company: list[str] = []
    school: list[str] = []
    title: str | None = None
    location: str | None = None
    geo_id: str | None = None
    industry_id: list[str] = []
    keywords_company: str | None = None
    keywords_school: str | None = None
    follower_of: str | None = None
    page: int = 1


# --- Lead search (GET /linkedin/lead-search) ---


class LeadSearchInput(BaseModel):
    search: str | None = None
    current_companies: list[str] = []
    past_companies: list[str] = []
    locations: list[str] = []
    geo_ids: list[str] = []
    schools: list[str] = []
    current_job_titles: list[str] = []
    past_job_titles: list[str] = []
    first_names: list[str] = []
    last_names: list[str] = []
    industry_ids: list[str] = []
    years_at_current_company_ids: list[str] = []
    years_of_experience_ids: list[str] = []
    seniority_level_ids: list[str] = []
    function_ids: list[str] = []
    recently_changed_jobs: bool | None = None
    posted_on_linkedin: bool | None = None
    profile_languages: list[str] = []
    company_headcount: list[str] = []
    company_headquarter_locations: list[str] = []
    exclude_locations: list[str] = []
    exclude_geo_ids: list[str] = []
    exclude_current_companies: list[str] = []
    exclude_past_companies: list[str] = []
    exclude_schools: list[str] = []
    exclude_current_job_titles: list[str] = []
    exclude_past_job_titles: list[str] = []
    exclude_industry_ids: list[str] = []
    exclude_seniority_level_ids: list[str] = []
    exclude_function_ids: list[str] = []
    exclude_company_headquarter_locations: list[str] = []
    sales_nav_url: str | None = None
    page: int = 1
    session_id: str | None = None
    use_private_pool: bool | None = None
    required_account_id: str | None = None
