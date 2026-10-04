from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from kiekkokeskus.season import data_date, resolve_data_date, run_date_et


def test_run_date_et_before_midnight_et_is_still_prior_day() -> None:
    # 03:30 UTC on 2026-10-04 → 23:30 ET on 2026-10-03 (ET is UTC-4 in DST)
    now_utc = datetime(2026, 10, 4, 3, 30, tzinfo=UTC)
    assert run_date_et(now_utc) == date(2026, 10, 3)


def test_run_date_et_after_midnight_et() -> None:
    # 05:00 UTC on 2026-10-04 → 01:00 ET on 2026-10-04
    now_utc = datetime(2026, 10, 4, 5, 0, tzinfo=UTC)
    assert run_date_et(now_utc) == date(2026, 10, 4)


@pytest.mark.parametrize(
    ("now_utc", "expected"),
    [
        # 2026-11-01 is the DST change in US: 2am ET falls back to 1am ET (ET goes UTC-4 → UTC-5)
        # 10:00 ET pre-DST = 14:00 UTC; 10:00 ET post-DST = 15:00 UTC. Right before: Oct 31.
        (datetime(2026, 10, 31, 14, 0, tzinfo=UTC), date(2026, 10, 31)),  # ET -04:00
        (datetime(2026, 11, 1, 14, 0, tzinfo=UTC), date(2026, 11, 1)),  # DST day, still -04 pre-2am
        (datetime(2026, 11, 1, 15, 0, tzinfo=UTC), date(2026, 11, 1)),  # ET -05:00 after change
        (datetime(2026, 11, 2, 15, 0, tzinfo=UTC), date(2026, 11, 2)),  # standard time
    ],
)
def test_run_date_et_across_dst(now_utc: datetime, expected: date) -> None:
    assert run_date_et(now_utc) == expected


def test_data_date_is_prior_day() -> None:
    assert data_date(date(2026, 10, 3)) == date(2026, 10, 2)


def test_run_date_requires_tz_aware() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        run_date_et(datetime(2026, 10, 4, 3, 30))


def test_resolve_data_date_default() -> None:
    now_utc = datetime(2026, 10, 4, 14, 0, tzinfo=UTC)  # 10:00 ET on Oct 4
    assert resolve_data_date({}, now_utc) == date(2026, 10, 3)


def test_resolve_data_date_valid_override() -> None:
    now_utc = datetime(2026, 10, 4, 14, 0, tzinfo=UTC)
    assert resolve_data_date({"date": "2026-04-01"}, now_utc) == date(2026, 4, 1)


def test_resolve_data_date_today_override_ok() -> None:
    now_utc = datetime(2026, 10, 4, 14, 0, tzinfo=UTC)
    # today in ET is 2026-10-04 — override to today is allowed, only future rejected
    assert resolve_data_date({"date": "2026-10-04"}, now_utc) == date(2026, 10, 4)


@pytest.mark.parametrize("bad", ["4/1/26", "2026-13-01", "2026-01-32", "2026/01/01", ""])
def test_resolve_data_date_malformed(bad: str) -> None:
    now_utc = datetime(2026, 10, 4, 14, 0, tzinfo=UTC)
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        resolve_data_date({"date": bad}, now_utc)


def test_resolve_data_date_future_rejected() -> None:
    now_utc = datetime(2026, 10, 4, 14, 0, tzinfo=UTC)
    with pytest.raises(ValueError, match="future"):
        resolve_data_date({"date": "2026-10-05"}, now_utc)


def test_resolve_data_date_non_string_rejected() -> None:
    now_utc = datetime(2026, 10, 4, 14, 0, tzinfo=UTC)
    with pytest.raises(ValueError, match="must be a string"):
        resolve_data_date({"date": 20261004}, now_utc)
