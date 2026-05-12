from __future__ import annotations

from pathlib import Path

import orjson

from src.attio.ops import UpsertCompany, UpsertPerson
from src.rb2b.webhook.visit import Webhook, extract_domain

FIXTURE = Path("api/samples/rb2b/visit/redacted.json")


def _load() -> Webhook:
    payload = orjson.loads(FIXTURE.read_bytes())
    return Webhook.model_validate(payload)


def test_attio_get_secret_collection_names() -> None:
    assert Webhook.attio_get_secret_collection_names() == ["attio"]


def testextract_domain_strips_scheme_path_and_www() -> None:
    assert extract_domain("https://example.com") == "example.com"
    assert extract_domain("https://www.example.com/path?x=1") == "example.com"
    assert extract_domain("example.com") == "example.com"
    assert extract_domain("www.example.com") == "example.com"
    assert extract_domain(None) is None
    assert extract_domain("") is None


def test_attio_is_valid_webhook_true_for_company_only_fixture() -> None:
    # The redacted fixture has Website but no Business Email — still valid.
    assert _load().attio_is_valid_webhook() is True


def test_attio_get_operations_returns_company_only_when_no_email() -> None:
    plan = _load().attio_get_operations()

    assert len(plan) == 1
    assert isinstance(plan[0], UpsertCompany)
    assert plan[0].domain == "example.com"
    assert plan[0].name == "Example Corp"


def test_attio_get_operations_returns_person_and_company_when_both_present() -> None:
    payload = orjson.loads(FIXTURE.read_bytes())
    payload["payload"]["Business Email"] = "buyer@example.com"
    payload["payload"]["First Name"] = "Pat"
    payload["payload"]["Last Name"] = "Buyer"
    webhook = Webhook.model_validate(payload)

    plan = webhook.attio_get_operations()

    # Company op runs before person op so the person's company_domain
    # reference resolves to an already-upserted record.
    assert len(plan) == 2
    assert isinstance(plan[0], UpsertCompany)
    assert plan[0].domain == "example.com"
    assert isinstance(plan[1], UpsertPerson)
    assert plan[1].email == "buyer@example.com"
    assert plan[1].first_name == "Pat"
    assert plan[1].last_name == "Buyer"
    assert plan[1].company_domain == "example.com"
    assert plan[1].linkedin == "https://www.linkedin.com/company/example"


def test_attio_is_valid_webhook_false_when_no_email_and_no_domain() -> None:
    payload = orjson.loads(FIXTURE.read_bytes())
    payload["payload"]["Website"] = None
    payload["payload"]["Business Email"] = None
    webhook = Webhook.model_validate(payload)

    assert webhook.attio_is_valid_webhook() is False
    assert "domain" in webhook.attio_get_invalid_webhook_error_msg()
