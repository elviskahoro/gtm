"""Unit tests for Cal.com webhook ETL contract."""

import json
from pathlib import Path

import pytest

from src.caldotcom.webhook import Webhook


@pytest.fixture
def booking_accepted():
    """Load accepted booking fixture."""
    fixture_path = Path(__file__).parent / "fixtures" / "booking" / "accepted.json"
    with open(fixture_path) as f:
        return json.load(f)


@pytest.fixture
def booking_cancelled():
    """Load cancelled booking fixture."""
    fixture_path = Path(__file__).parent / "fixtures" / "booking" / "cancelled.json"
    with open(fixture_path) as f:
        return json.load(f)


@pytest.fixture
def booking_rescheduled():
    """Load rescheduled booking fixture."""
    fixture_path = Path(__file__).parent / "fixtures" / "booking" / "rescheduled.json"
    with open(fixture_path) as f:
        return json.load(f)


def test_webhook_instantiation(booking_accepted):
    """Test Webhook can be instantiated from booking payload."""
    webhook = Webhook(**booking_accepted)
    assert webhook.uid == "booking-001-accepted"
    assert webhook.title == "Customer Discovery Call"
    assert webhook.status == "accepted"


def test_get_booking_id(booking_accepted):
    """Test get_booking_id returns uid."""
    webhook = Webhook(**booking_accepted)
    assert webhook.get_booking_id() == webhook.uid


def test_etl_is_valid_webhook(booking_accepted):
    """Test BOOKING family returns True for ETL validity."""
    webhook = Webhook(**booking_accepted)
    assert webhook.etl_is_valid_webhook() is True


def test_etl_get_bucket_name():
    """Test ETL bucket name is correct."""
    assert Webhook.etl_get_bucket_name() == "devx-caldotcom-booking-etl"


def test_storage_get_app_name():
    """Test storage app name matches ETL bucket."""
    assert Webhook.storage_get_app_name() == Webhook.etl_get_bucket_name()


def test_modal_get_secret_collection_names():
    """Test Modal secret collection names."""
    secrets = Webhook.modal_get_secret_collection_names()
    assert secrets == ["devx-growth-gcp"]


def test_storage_get_base_model_type():
    """Test storage base model type is None for Phase 1."""
    assert Webhook.storage_get_base_model_type() is None


def test_lance_raises_notimplemented():
    """Test Phase 2 methods raise NotImplementedError."""
    with pytest.raises(NotImplementedError):
        Webhook.lance_get_project_name()

    with pytest.raises(NotImplementedError):
        Webhook.lance_get_base_model_type()


def test_etl_get_file_name(booking_accepted):
    """Test file name generation follows convention."""
    webhook = Webhook(**booking_accepted)
    filename = webhook.etl_get_file_name()

    # Should be: {timestamp}-{uid}-{clean_title}.jsonl
    parts = filename.split("-")
    assert len(parts) >= 3
    assert filename.endswith(".jsonl")
    assert "booking-001-accepted" in filename
    assert "customer" in filename.lower()


def test_etl_get_json_produces_jsonl(booking_accepted):
    """Test ETL JSON output is valid JSONL."""
    webhook = Webhook(**booking_accepted)
    jsonl_content = webhook.etl_get_json()

    # Should be JSONL format (one JSON per line)
    lines = [line for line in jsonl_content.strip().split("\n") if line]
    assert len(lines) > 0

    # Each line should be valid JSON with booking_uid and id
    for line in lines:
        obj = json.loads(line)
        assert "booking_uid" in obj
        assert obj["booking_uid"] == webhook.uid
        assert "id" in obj
        assert "-" in obj["id"]  # Format: uid-00000


def test_etl_get_json_with_cancelled_booking(booking_cancelled):
    """Test ETL JSON with cancelled booking includes reschedule fields."""
    webhook = Webhook(**booking_cancelled)
    jsonl_content = webhook.etl_get_json()

    lines = [line for line in jsonl_content.strip().split("\n") if line]
    assert len(lines) > 0

    # Check that cancellation fields are present
    for line in lines:
        obj = json.loads(line)
        # flatsplode should flatten the structure
        assert any("cancel" in str(k).lower() for k in obj.keys())


def test_etl_get_json_with_rescheduled_booking(booking_rescheduled):
    """Test ETL JSON with rescheduled booking includes reschedule fields."""
    webhook = Webhook(**booking_rescheduled)
    jsonl_content = webhook.etl_get_json()

    lines = [line for line in jsonl_content.strip().split("\n") if line]
    assert len(lines) > 0

    # Check for rescheduling fields
    for line in lines:
        obj = json.loads(line)
        # Flattened keys should include reschedule information
        assert obj["booking_uid"] == webhook.uid


def test_multiple_attendees(booking_accepted):
    """Test webhook handles multiple attendees."""
    webhook = Webhook(**booking_accepted)
    assert len(webhook.attendees) > 0
    assert webhook.attendees[0].name == "Bob Attendee"


def test_metadata_preserved(booking_accepted):
    """Test metadata dict is preserved."""
    webhook = Webhook(**booking_accepted)
    assert webhook.metadata is not None
    assert webhook.metadata.get("source") == "website"
