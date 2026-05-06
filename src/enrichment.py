"""Harvest-powered LinkedIn enrichment for Attio CRM.

Orchestrates selective profile enrichment: filters records by missing
fields, fetches from Harvest API, and upserts only the target fields
to Attio to preserve existing data.

Workflow:
1. Load enrichment config (profiles, filters, field mappings)
2. Filter records by missing-field criteria
3. Create EnrichmentTask for each record+profile pair
4. Fetch from Harvest API for each task
5. Upsert to Attio with selective field updates
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from libs.attio import people as attio_people
from libs.attio.models import PersonInput
from libs.harvest import client as harvest_client

logger = logging.getLogger(__name__)


class HarvestProfile(BaseModel):
    """Harvest API profile payload — all fields optional for selective upsert.

    Only fields with non-None values will be upserted to the CRM. This lets us
    build targeted enrichment tasks where each task only updates the missing fields.
    """

    about: str | None = None
    causes: list | None = None
    certifications: list | None = None
    composeOptionType: str | None = None
    connectionsCount: int | None = None
    courses: list | None = None
    coverPicture: dict | None = None
    currentPosition: list | None = None
    education: list | None = None
    emails: list | None = None
    experience: list | None = None
    featured: Any | None = None
    firstName: str | None = None
    followerCount: int | None = None
    headline: str | None = None
    hiring: int | None = None
    honorsAndAwards: list | None = None
    id: str | None = None
    influencer: int | None = None
    languages: list | None = None
    lastName: str | None = None
    linkedinUrl: str | None = None
    location: dict | None = None
    memorialized: int | None = None
    moreProfiles: list | None = None
    multiLocaleHeadline: list | None = None
    objectUrn: str | None = None
    openToWork: int | None = None
    organizations: list | None = None
    patents: list | None = None
    photo: str | None = None
    premium: int | None = None
    primaryLocale: dict | None = None
    profileActions: list | None = None
    profileLocales: list | None = None
    profilePicture: dict | None = None
    profileTopEducation: list | None = None
    projects: list | None = None
    publicIdentifier: str | None = None
    publications: list | None = None
    receivedRecommendations: list | None = None
    registeredAt: str | None = None
    services: Any | None = None
    skills: list | None = None
    topSkills: Any | None = None
    verified: int | None = None
    volunteering: list | None = None

    def model_dump_non_none(self) -> dict:
        """Return only non-None fields for upsert operations."""
        return {k: v for k, v in self.model_dump().items() if v is not None}


class EnrichmentTask(BaseModel):
    """A single record's enrichment request — which fields to fill from Harvest."""

    record_id: str
    email: str
    linkedin_url: str
    enrichment_type: str
    target_fields: list[str]


class EnrichmentResult(BaseModel):
    """Result of enriching a single record."""

    task: EnrichmentTask
    success: bool
    error: str | None = None
    attio_record_id: str | None = None


def load_enrichment_config(config_path: Path | str) -> dict[str, Any]:
    """Load enrichment config mapping filters to Harvest fields and CRM targets."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Enrichment config not found: {config_path}")

    with open(path) as f:
        return json.load(f)


def build_enrichment_tasks(
    records: list[dict[str, Any]],
    enrichment_type: str,
    target_fields: list[str],
) -> list[EnrichmentTask]:
    """Build enrichment tasks from records.

    Args:
        records: List of records with 'record_id', 'email', 'linkedin_url'
        enrichment_type: Label (e.g., 'location', 'email', 'skills')
        target_fields: List of HarvestProfile field names to enrich

    Returns:
        List of EnrichmentTask ready for Harvest API calls.
    """
    tasks = []
    for row in records:
        linkedin_url = row.get("linkedin_url", "")
        if not linkedin_url and row.get("linkedin_slug"):
            linkedin_url = f"https://www.linkedin.com/in/{row['linkedin_slug']}"

        if not linkedin_url:
            logger.warning(f"Skipping record {row.get('record_id')}: no LinkedIn URL")
            continue

        task = EnrichmentTask(
            record_id=row["record_id"],
            email=row.get("email", ""),
            linkedin_url=linkedin_url,
            enrichment_type=enrichment_type,
            target_fields=target_fields,
        )
        tasks.append(task)

    return tasks


def harvest_profile_from_task(task: EnrichmentTask) -> HarvestProfile | None:
    """Fetch and construct selective HarvestProfile for a task.

    Calls Harvest API and returns a profile with only the target fields
    populated (others remain None for selective upsert).
    """
    raw = harvest_client.fetch_profile(task.linkedin_url)
    if not raw:
        logger.warning(f"Harvest API returned no data for {task.linkedin_url}")
        return None

    profile = HarvestProfile()
    for field in task.target_fields:
        if hasattr(profile, field) and field in raw:
            setattr(profile, field, raw[field])

    return profile


def enrich_record(task: EnrichmentTask) -> EnrichmentResult:
    """Enrich a single record: fetch from Harvest, update in Attio.

    Args:
        task: EnrichmentTask specifying record, LinkedIn URL, and target fields

    Returns:
        EnrichmentResult with success/error and Attio record ID if successful.
    """
    profile = harvest_profile_from_task(task)
    if not profile or not profile.model_dump_non_none():
        return EnrichmentResult(
            task=task,
            success=False,
            error="Harvest API returned no data or no target fields populated",
        )

    try:
        person_input = _profile_to_person_input(profile, task.email)
        result = attio_people.update_person(
            record_id=task.record_id,
            email=task.email,
            input=person_input,
        )

        return EnrichmentResult(
            task=task,
            success=True,
            attio_record_id=task.record_id,
        )

    except Exception as e:
        logger.error(f"Failed to enrich record {task.record_id}: {e}")
        return EnrichmentResult(
            task=task,
            success=False,
            error=str(e),
        )


def _profile_to_person_input(profile: HarvestProfile, email: str) -> PersonInput:
    """Convert selective HarvestProfile to Attio PersonInput.

    Only populated fields from the profile are included.
    """
    data = profile.model_dump_non_none()

    person_input = PersonInput(
        email=email,
    )

    if "firstName" in data:
        person_input.first_name = data["firstName"]

    if "lastName" in data:
        person_input.last_name = data["lastName"]

    if "emails" in data and data["emails"]:
        person_input.additional_emails = data["emails"]

    if "location" in data:
        loc = data["location"]
        if isinstance(loc, dict):
            parts = []
            if city := loc.get("city"):
                parts.append(city)
            if state := loc.get("state"):
                parts.append(state)
            if country := loc.get("country"):
                parts.append(country)
            if parts:
                person_input.location = ", ".join(parts)

    if "headline" in data and data["headline"]:
        person_input.notes = data["headline"]

    return person_input


async def enrich_batch(
    records: list[dict[str, Any]],
    enrichment_type: str,
    target_fields: list[str],
) -> list[EnrichmentResult]:
    """Enrich a batch of records.

    Args:
        records: List of records to enrich
        enrichment_type: Enrichment profile label
        target_fields: Target fields from Harvest to populate

    Returns:
        List of enrichment results (one per record, with success/error).
    """
    tasks = build_enrichment_tasks(records, enrichment_type, target_fields)
    results = []

    for task in tasks:
        result = enrich_record(task)
        results.append(result)
        logger.info(f"Enriched {task.record_id}: {result.success}")

    return results
