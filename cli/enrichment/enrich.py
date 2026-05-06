"""LinkedIn enrichment commands.

Two-stage pipeline: enrich (Harvest) >> output file >> upsert (Attio batch).
"""

import json
import logging
from pathlib import Path

import typer

from libs.attio import people as attio_people
from libs.attio.models import PersonInput
from src.enrichment import (
    HarvestProfile,
    build_enrichment_tasks,
    harvest_profile_from_task,
    _profile_to_person_input,
    load_enrichment_config,
)

app = typer.Typer(help="Enrich records from LinkedIn via Harvest API.")
logger = logging.getLogger(__name__)


@app.command()
def fetch(
    config_path: Path = typer.Option(
        ...,
        "--config",
        help="Path to enrichment_config.json",
    ),
    records_file: Path = typer.Option(
        ...,
        "--records",
        help="Path to JSON file with records (record_id, email, linkedin_url)",
    ),
    profile_id: str = typer.Option(
        ...,
        "--profile",
        help="Enrichment profile ID (e.g., 'location', 'email', 'skills')",
    ),
    output_file: Path = typer.Option(
        ...,
        "--output",
        help="Path to write enriched records JSON",
    ),
) -> None:
    """Fetch enrichment from Harvest API and write to file (no Attio changes).

    Example:

        gtm enrichment enrich fetch \\
            --config enrichment_config.json \\
            --records records.json \\
            --profile location \\
            --output enriched_output.json
    """
    try:
        config = load_enrichment_config(config_path)
    except FileNotFoundError:
        typer.echo(f"❌ Config file not found: {config_path}", err=True)
        raise typer.Exit(1)

    # Find the profile in config
    profiles = config.get("enrichment_profiles", [])
    profile = next((p for p in profiles if p["id"] == profile_id), None)
    if not profile:
        typer.echo(
            f"❌ Profile '{profile_id}' not found in config",
            err=True,
        )
        raise typer.Exit(1)

    # Load records
    try:
        with open(records_file) as f:
            records = json.load(f)
    except FileNotFoundError:
        typer.echo(f"❌ Records file not found: {records_file}", err=True)
        raise typer.Exit(1)
    except json.JSONDecodeError:
        typer.echo(f"❌ Invalid JSON in records file", err=True)
        raise typer.Exit(1)

    if not records:
        typer.echo("⚠️  No records to enrich")
        return

    # Build tasks
    target_fields = profile.get("harvest_fields", [])
    tasks = build_enrichment_tasks(
        records,
        enrichment_type=profile["id"],
        target_fields=target_fields,
    )

    if not tasks:
        typer.echo("⚠️  No valid tasks created from records")
        return

    typer.echo(
        f"📋 Enriching {len(tasks)} records from Harvest API...",
    )

    # Fetch enrichment for each task
    enriched = []
    success_count = 0
    error_count = 0

    with typer.progressbar(
        tasks,
        label="Fetching",
    ) as progress:
        for task in progress:
            profile_data = harvest_profile_from_task(task)
            if not profile_data:
                error_count += 1
                continue

            non_none = profile_data.model_dump_non_none()
            enriched.append(
                {
                    "record_id": task.record_id,
                    "email": task.email,
                    "enrichment_type": task.enrichment_type,
                    "harvested_fields": non_none,
                }
            )
            success_count += 1

    # Write output
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(enriched, f, indent=2)

    typer.echo()
    typer.echo(
        f"✅ Enrichment complete: {success_count} succeeded, {error_count} failed",
    )
    typer.echo(f"📝 Output written to: {output_file}")


@app.command()
def upsert(
    enriched_file: Path = typer.Option(
        ...,
        "--input",
        help="Path to enriched records JSON (from 'fetch' command)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview changes without updating Attio",
    ),
) -> None:
    """Batch upsert enriched records to Attio CRM.

    Example:

        gtm enrichment enrich upsert \\
            --input enriched_output.json

        gtm enrichment enrich upsert \\
            --input enriched_output.json \\
            --dry-run
    """
    try:
        with open(enriched_file) as f:
            enriched = json.load(f)
    except FileNotFoundError:
        typer.echo(f"❌ Enriched file not found: {enriched_file}", err=True)
        raise typer.Exit(1)
    except json.JSONDecodeError:
        typer.echo(f"❌ Invalid JSON in enriched file", err=True)
        raise typer.Exit(1)

    if not enriched:
        typer.echo("⚠️  No records to upsert")
        return

    typer.echo(f"📋 Upserting {len(enriched)} records to Attio...")
    typer.echo()

    if dry_run:
        for item in enriched:
            typer.echo(f"  [{item['record_id']}] {item['email']}")
            for field, value in item["harvested_fields"].items():
                typer.echo(f"    • {field}: {json.dumps(value)[:60]}...")
        typer.echo(f"\n✅ Dry run complete (0 records updated)")
        return

    # Execute upsert
    success_count = 0
    error_count = 0

    with typer.progressbar(
        enriched,
        label="Upserting",
    ) as progress:
        for item in progress:
            try:
                profile = HarvestProfile(**item["harvested_fields"])
                person_input = _profile_to_person_input(profile, item["email"])

                attio_people.update_person(
                    record_id=item["record_id"],
                    email=item["email"],
                    input=person_input,
                )
                success_count += 1
            except Exception as e:
                error_count += 1
                typer.echo(
                    f"  ❌ {item['record_id']}: {str(e)[:80]}",
                    err=True,
                )

    typer.echo()
    typer.echo(
        f"✅ Upsert complete: {success_count} succeeded, {error_count} failed",
    )
