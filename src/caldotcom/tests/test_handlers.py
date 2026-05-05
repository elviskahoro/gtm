"""Integration tests for Cal.com webhook handlers with mocked GCS."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.caldotcom.handlers import _handle_etl_request, _handle_raw_request


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


def test_export_to_gcp_etl_success(booking_accepted):
    """Test ETL endpoint successfully processes booking."""
    with patch("src.caldotcom.handlers.write_to_gcs") as mock_write:
        result = _handle_etl_request(booking_accepted)

        assert result["status"] == "success"
        assert result["booking_uid"] == "booking-001-accepted"
        assert result["bucket"] == "devx-caldotcom-booking-etl"
        assert result["file"].endswith(".jsonl")

        # Verify GCS write was called
        mock_write.assert_called_once()
        call_args = mock_write.call_args
        assert call_args[0][0] == "devx-caldotcom-booking-etl"
        assert "booking-001-accepted" in call_args[0][1]


def test_export_to_gcp_etl_invalid_payload():
    """Test ETL endpoint rejects invalid payload."""
    from fastapi import HTTPException

    invalid_payload = {"invalid": "data"}

    with pytest.raises(HTTPException) as exc_info:
        _handle_etl_request(invalid_payload)

    assert exc_info.value.status_code == 422


def test_export_to_gcp_etl_gcs_failure(booking_accepted):
    """Test ETL endpoint handles GCS write failures."""
    from fastapi import HTTPException

    with patch(
        "src.caldotcom.handlers.write_to_gcs", side_effect=Exception("GCS error")
    ):
        with pytest.raises(HTTPException) as exc_info:
            _handle_etl_request(booking_accepted)

        assert exc_info.value.status_code == 500


def test_export_to_gcp_raw_success(booking_accepted):
    """Test raw endpoint successfully archives booking."""
    with patch("src.caldotcom.handlers.write_to_gcs") as mock_write:
        result = _handle_raw_request(booking_accepted)

        assert result["status"] == "success"
        assert result["bucket"] == "devx-caldotcom-booking-raw"
        assert result["file"].endswith(".jsonl")
        assert result["booking_uid"] == "booking-001-accepted"

        # Verify GCS write was called with raw content
        mock_write.assert_called_once()
        call_args = mock_write.call_args
        assert call_args[0][0] == "devx-caldotcom-booking-raw"
        # Raw content should be JSON
        content = call_args[0][2]
        parsed = json.loads(content.strip())
        assert parsed["uid"] == "booking-001-accepted"


def test_export_to_gcp_raw_with_cancelled_booking(booking_cancelled):
    """Test raw endpoint with cancelled booking."""
    with patch("src.caldotcom.handlers.write_to_gcs") as mock_write:
        result = _handle_raw_request(booking_cancelled)

        assert result["status"] == "success"
        assert result["booking_uid"] == "booking-002-cancelled"

        # Verify raw content includes cancellation fields
        call_args = mock_write.call_args
        content = call_args[0][2]
        parsed = json.loads(content.strip())
        assert parsed["cancellationReason"] == "Schedule conflict"


def test_export_to_gcp_raw_gcs_failure(booking_accepted):
    """Test raw endpoint handles GCS write failures."""
    from fastapi import HTTPException

    with patch(
        "src.caldotcom.handlers.write_to_gcs", side_effect=Exception("GCS error")
    ):
        with pytest.raises(HTTPException) as exc_info:
            _handle_raw_request(booking_accepted)

        assert exc_info.value.status_code == 500


def test_etl_output_format(booking_accepted):
    """Test ETL output is valid JSONL format."""
    with patch("src.caldotcom.handlers.write_to_gcs") as mock_write:
        _handle_etl_request(booking_accepted)

        call_args = mock_write.call_args
        content = call_args[0][2]

        # Parse JSONL
        lines = [line for line in content.strip().split("\n") if line]
        assert len(lines) > 0

        for line in lines:
            obj = json.loads(line)
            assert "booking_uid" in obj
            assert "id" in obj
            assert obj["booking_uid"] == "booking-001-accepted"
            # ID should be in format: uid-00000
            assert obj["id"].startswith("booking-001-accepted-")


def test_filename_format(booking_accepted):
    """Test filename follows correct convention."""
    with patch("src.caldotcom.handlers.write_to_gcs") as mock_write:
        _handle_etl_request(booking_accepted)

        call_args = mock_write.call_args
        filename = call_args[0][1]

        # Should be: YYYYMMDDHHMMSS-uid-clean_title.jsonl
        assert filename.endswith(".jsonl")
        assert "booking-001-accepted" in filename
        assert "customer" in filename.lower()  # From "Customer Discovery Call"
        parts = filename.split("-")
        # First part should be timestamp (14 digits)
        assert len(parts[0]) == 14
        assert parts[0].isdigit()
