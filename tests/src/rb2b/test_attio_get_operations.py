from __future__ import annotations

import json
from pathlib import Path

from src.rb2b.webhook.visit import Webhook, extract_domain

SAMPLES = Path(__file__).resolve().parents[3] / "api" / "samples"


def _load(name: str) -> Webhook:
    import orjson

    return Webhook.model_validate(orjson.loads((SAMPLES / name).read_text()))


def test_attio_get_secret_collection_names() -> None:
    assert Webhook.attio_get_secret_collection_names() == ["attio"]


def test_extract_domain_strips_scheme_path_and_www() -> None:
    assert extract_domain("https://example.com") == "example.com"
    assert extract_domain("https://www.example.com/path?x=1") == "example.com"
    assert extract_domain("example.com") == "example.com"
    assert extract_domain("www.example.com") == "example.com"
    assert extract_domain(None) is None
    assert extract_domain("") is None


def test_attio_get_operations_anonymous_visit_is_rejected() -> None:
    w = _load("rb2b.visit.anonymous.redacted.json")
    assert w.attio_is_valid_webhook() is False


def test_attio_get_operations_company_only_emits_two_ops() -> None:
    w = _load("rb2b.visit.company_only.redacted.json")
    ops = w.attio_get_operations()
    assert [type(o).__name__ for o in ops] == ["UpsertCompany", "UpsertTrackingEvent"]
    te = ops[1]
    assert te.subject_company is not None
    assert te.subject_person is None


def test_attio_get_operations_person_only_emits_two_ops() -> None:
    w = _load("rb2b.visit.person_only.redacted.json")
    ops = w.attio_get_operations()
    assert [type(o).__name__ for o in ops] == ["UpsertPerson", "UpsertTrackingEvent"]
    te = ops[1]
    assert te.subject_person is not None
    assert te.subject_company is None


def test_attio_get_operations_person_and_company_emits_three_ops_in_order() -> None:
    w = _load("rb2b.visit.person_and_company.redacted.json")
    ops = w.attio_get_operations()
    assert [type(o).__name__ for o in ops] == [
        "UpsertCompany",
        "UpsertPerson",
        "UpsertTrackingEvent",
    ]
    assert ops[0].merge_only_if_empty == [
        "industry",
        "employee_count",
        "estimate_revenue",
    ]
    assert ops[1].merge_only_if_empty == ["title", "city", "state", "zipcode"]
    te = ops[2]
    assert te.external_id.startswith("rb2b:")
    assert te.event_type == "rb2b_visit"
    assert te.captured_url == w.payload.captured_url
    assert te.name == w.payload.captured_url


def test_attio_get_operations_tracking_event_carries_full_mapping() -> None:
    w = _load("rb2b.visit.person_and_company.redacted.json")
    te = w.attio_get_operations()[-1]
    # Dedicated columns
    assert te.referrer == w.payload.referrer
    assert te.is_repeat_visit == w.payload.is_repeat_visit
    assert te.city == w.payload.city
    # Tags parsing
    assert isinstance(te.tags, list)
    assert all(isinstance(t, str) and t and t == t.strip() for t in te.tags)
    # body_json round-trips (uses snake_case in mode="json")
    assert json.loads(te.body_json)["payload"]["captured_url"] == w.payload.captured_url


def test_attio_get_operations_repeat_visit_sets_flag() -> None:
    w = _load("rb2b.visit.repeat_visit.redacted.json")
    te = [
        o for o in w.attio_get_operations() if type(o).__name__ == "UpsertTrackingEvent"
    ][0]
    assert te.is_repeat_visit is True


def test_attio_get_operations_flat_envelope_normalizes() -> None:
    w = _load("rb2b.visit.flat_envelope.redacted.json")
    # _wrap_flat_payload should have normalized this into the envelope shape.
    assert w.event_id  # generated if missing
    ops = w.attio_get_operations()
    # Exact op makeup depends on the fixture's fields — assert ordering invariant.
    types = [type(o).__name__ for o in ops]
    assert types[-1] == "UpsertTrackingEvent"
    assert types[0] in ("UpsertCompany", "UpsertPerson")
