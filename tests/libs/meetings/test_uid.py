from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from libs.meetings import UID_PREFIX, canonical_meeting_uid


def test_canonical_uid_is_deterministic() -> None:
    start = datetime(2026, 5, 20, 15, 0, tzinfo=timezone.utc)
    first = canonical_meeting_uid(host_email="host@dlthub.com", start=start)
    second = canonical_meeting_uid(host_email="host@dlthub.com", start=start)
    assert first == second
    assert first.startswith(UID_PREFIX)


def test_canonical_uid_normalizes_email_case_and_whitespace() -> None:
    start = datetime(2026, 5, 20, 15, 0, tzinfo=timezone.utc)
    lower = canonical_meeting_uid(host_email="host@dlthub.com", start=start)
    upper = canonical_meeting_uid(host_email="  HOST@DLTHUB.COM  ", start=start)
    assert lower == upper


def test_canonical_uid_normalizes_timezone_to_utc_minute() -> None:
    utc_start = datetime(2026, 5, 20, 15, 0, tzinfo=timezone.utc)
    pst = timezone(timedelta(hours=-8))
    pst_start = datetime(2026, 5, 20, 7, 0, tzinfo=pst)
    assert canonical_meeting_uid(
        host_email="host@dlthub.com",
        start=utc_start,
    ) == canonical_meeting_uid(host_email="host@dlthub.com", start=pst_start)


def test_canonical_uid_truncates_seconds() -> None:
    minute_start = datetime(2026, 5, 20, 15, 0, 0, tzinfo=timezone.utc)
    seconds_start = datetime(2026, 5, 20, 15, 0, 45, tzinfo=timezone.utc)
    assert canonical_meeting_uid(
        host_email="host@dlthub.com",
        start=minute_start,
    ) == canonical_meeting_uid(host_email="host@dlthub.com", start=seconds_start)


def test_canonical_uid_differs_when_start_minute_differs() -> None:
    a = canonical_meeting_uid(
        host_email="host@dlthub.com",
        start=datetime(2026, 5, 20, 15, 0, tzinfo=timezone.utc),
    )
    b = canonical_meeting_uid(
        host_email="host@dlthub.com",
        start=datetime(2026, 5, 20, 15, 1, tzinfo=timezone.utc),
    )
    assert a != b


def test_canonical_uid_differs_when_host_differs() -> None:
    start = datetime(2026, 5, 20, 15, 0, tzinfo=timezone.utc)
    a = canonical_meeting_uid(host_email="host@dlthub.com", start=start)
    b = canonical_meeting_uid(host_email="other@dlthub.com", start=start)
    assert a != b


def test_canonical_uid_requires_email() -> None:
    start = datetime(2026, 5, 20, 15, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        canonical_meeting_uid(host_email="", start=start)
    with pytest.raises(ValueError):
        canonical_meeting_uid(host_email="   ", start=start)


def test_canonical_uid_requires_tzaware_start() -> None:
    naive = datetime(2026, 5, 20, 15, 0)
    with pytest.raises(ValueError):
        canonical_meeting_uid(host_email="host@dlthub.com", start=naive)
