"""Pure date logic. `now` is always injected (CLAUDE.md). ADR-005: ET timezone matters."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")


def run_date_et(now_utc: datetime) -> date:
    """Today in America/New_York. `now_utc` must be timezone-aware UTC."""
    if now_utc.tzinfo is None:
        raise ValueError("now_utc must be timezone-aware UTC")
    return now_utc.astimezone(ET).date()


def data_date(run_date: date) -> date:
    """'Last night' in ET terms: run date minus one day."""
    return run_date - timedelta(days=1)


def resolve_data_date(event: dict[str, Any], now_utc: datetime) -> date:
    """Honor event['date'] (YYYY-MM-DD, not future) else data_date(run_date_et(now_utc))."""
    override = event.get("date")
    today_et = run_date_et(now_utc)
    if override is None:
        return data_date(today_et)
    if not isinstance(override, str):
        raise ValueError(f"event['date'] must be a string, got {type(override).__name__}")
    try:
        parsed = date.fromisoformat(override)
    except ValueError as e:
        raise ValueError(f"event['date'] not YYYY-MM-DD: {override!r}") from e
    if parsed > today_et:
        raise ValueError(f"event['date'] is in the future: {override}")
    return parsed
