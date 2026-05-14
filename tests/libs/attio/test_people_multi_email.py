from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

import pytest

from libs.attio.errors import AttioValidationError
from libs.attio.models import PersonInput
from libs.attio.people import update_person
from libs.attio.values import normalize_email_address_list


def test_normalize_email_address_list_dedupes_case_insensitive() -> None:
    assert normalize_email_address_list(
        ["A@x.com", "a@x.com", "  b@y.com ", "", None],
    ) == ["A@x.com", "b@y.com"]


def test_update_person_skips_email_addresses_when_not_merging(monkeypatch) -> None:
    patch_values: list[dict[str, Any]] = []

    class FakeRecords:
        def get_v2_objects_object_records_record_id_(self, object: str, record_id: str):
            _ = object
            return SimpleNamespace(
                data=SimpleNamespace(
                    values=SimpleNamespace(
                        email_addresses=[
                            SimpleNamespace(email_address="existing@example.com"),
                        ],
                    ),
                ),
            )

        def post_v2_objects_object_records_query(self, **_kwargs: object) -> None:
            raise AssertionError("unexpected query")

        def patch_v2_objects_object_records_record_id_(
            self,
            object: str,
            record_id: str,
            data: Any,
        ) -> SimpleNamespace:
            _ = object
            vals = getattr(data, "values", data)
            if vals is not None:
                patch_values.append(dict(vals))
            else:
                patch_values.append({})
            return SimpleNamespace(
                data=SimpleNamespace(
                    id=SimpleNamespace(record_id=record_id),
                    values={"email_addresses": []},
                ),
            )

    class FakeClient:
        records = FakeRecords()

    @contextmanager
    def fake_get_client():
        yield FakeClient()

    monkeypatch.setattr("libs.attio.people.get_client", fake_get_client)

    env = update_person(
        record_id="rec_1",
        email=None,
        input=PersonInput(
            email="a@example.com",
            first_name="Pat",
        ),
    )
    assert env.success is True
    assert len(patch_values) == 1
    assert "email_addresses" not in patch_values[0]
    assert patch_values[0]["name"]  # name patch present


def test_update_person_merges_additional_emails(monkeypatch) -> None:
    patch_values: list[dict[str, Any]] = []

    class FakeRecords:
        def get_v2_objects_object_records_record_id_(self, object: str, record_id: str):
            _ = object
            return SimpleNamespace(
                data=SimpleNamespace(
                    values=SimpleNamespace(
                        email_addresses=[
                            SimpleNamespace(email_address="a@example.com"),
                        ],
                    ),
                ),
            )

        def post_v2_objects_object_records_query(self, **_kwargs: object) -> None:
            raise AssertionError("unexpected query")

        def patch_v2_objects_object_records_record_id_(
            self,
            object: str,
            record_id: str,
            data: Any,
        ) -> SimpleNamespace:
            _ = object
            vals = getattr(data, "values", data)
            if vals is not None:
                patch_values.append(dict(vals))
            else:
                patch_values.append({})
            return SimpleNamespace(
                data=SimpleNamespace(
                    id=SimpleNamespace(record_id=record_id),
                    values={
                        "email_addresses": [
                            SimpleNamespace(email_address="a@example.com"),
                            SimpleNamespace(email_address="b@example.com"),
                        ],
                    },
                ),
            )

    class FakeClient:
        records = FakeRecords()

    @contextmanager
    def fake_get_client():
        yield FakeClient()

    monkeypatch.setattr("libs.attio.people.get_client", fake_get_client)

    env = update_person(
        record_id="rec_1",
        email=None,
        input=PersonInput(
            email="a@example.com",
            additional_emails=["b@example.com"],
        ),
    )
    assert env.success is True
    merged = patch_values[0]["email_addresses"]
    assert sorted(merged) == ["a@example.com", "b@example.com"]
    assert any(w.code == "multiple_emails_added" for w in env.warnings)


def test_update_person_replace_emails_requires_one_address(monkeypatch) -> None:
    class FakeRecords:
        def get_v2_objects_object_records_record_id_(self, object: str, record_id: str):
            _ = object
            return SimpleNamespace(
                data=SimpleNamespace(
                    values=SimpleNamespace(
                        email_addresses=[
                            SimpleNamespace(email_address="a@example.com"),
                        ],
                    ),
                ),
            )

        def patch_v2_objects_object_records_record_id_(
            self,
            **_kwargs: object,
        ) -> SimpleNamespace:
            raise AssertionError("unexpected patch")

    class FakeClient:
        records = FakeRecords()

    @contextmanager
    def fake_get_client():
        yield FakeClient()

    monkeypatch.setattr("libs.attio.people.get_client", fake_get_client)

    with pytest.raises(AttioValidationError):
        update_person(
            record_id="rec_1",
            email=None,
            input=PersonInput(
                linkedin="https://www.linkedin.com/in/foo",
                additional_emails=[],
                replace_emails=True,
            ),
        )
