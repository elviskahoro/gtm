"""Tests for libs/rb2b/models.py — covers PR #7 review feedback:

- direct (un-enveloped) RB2B webhook bodies
- numeric Employee Count values
- RB2B's documented `12:34:56:00.00+00.00` timestamp shape
"""

from __future__ import annotations

from libs.rb2b import Webhook


def test_webhook_accepts_flat_payload() -> None:
    """RB2B-direct deliveries put visit fields at the top level."""
    body = {
        "LinkedIn URL": "https://www.linkedin.com/company/example",
        "Company Name": "Example Inc",
        "Employee Count": "201-500",
        "Seen At": "2026-05-12T06:24:48.000+00:00",
        "Captured URL": "https://example.com/landing",
        "is_repeat_visit": False,
    }
    webhook = Webhook.model_validate(body)
    assert webhook.payload.company_name == "Example Inc"
    assert webhook.payload.captured_url == "https://example.com/landing"
    assert webhook.connection == "rb2b-direct"
    assert webhook.event_id.startswith("evt_")


def test_webhook_accepts_envelope_unchanged() -> None:
    """The pre-existing envelope shape must keep working."""
    body = {
        "event_id": "evt_known",
        "timestamp": "2026-05-12T06:24:48.000+00:00",
        "connection": "rb2b-visits",
        "payload": {
            "Company Name": "Example Inc",
            "Seen At": "2026-05-12T06:24:48.000+00:00",
        },
    }
    webhook = Webhook.model_validate(body)
    assert webhook.event_id == "evt_known"
    assert webhook.connection == "rb2b-visits"


def test_employee_count_accepts_integer() -> None:
    """RB2B documents Employee Count as integer | string | null."""
    body = {
        "event_id": "evt_1",
        "timestamp": "2026-05-12T06:24:48.000+00:00",
        "connection": "rb2b",
        "payload": {"Employee Count": 60},
    }
    webhook = Webhook.model_validate(body)
    assert webhook.payload.employee_count == "60"


def test_seen_at_normalizes_rb2b_documented_format() -> None:
    """RB2B docs sometimes use `12:34:56:00.00+00.00` separators."""
    body = {
        "event_id": "evt_1",
        "timestamp": "2026-05-12T06:24:48.000+00:00",
        "connection": "rb2b",
        "payload": {"Seen At": "2026-05-12T12:34:56:00.00+00.00"},
    }
    webhook = Webhook.model_validate(body)
    assert webhook.payload.seen_at is not None
    assert webhook.payload.seen_at.year == 2026
    assert webhook.payload.seen_at.hour == 12
    assert webhook.payload.seen_at.minute == 34
    assert webhook.payload.seen_at.second == 56
