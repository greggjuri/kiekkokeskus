"""Pure parser for the club-schedule-season payload.

Filters to regular season (ADR-014) and normalizes each game. The home/away flip is relative
to a chosen team (passed by the builder). OT/SO comes from `gameOutcome.lastPeriodType`.
"""

from __future__ import annotations

from datetime import date
from typing import Any

REGULAR_SEASON = 2  # ADR-014
COMPLETED_STATES = frozenset({"OFF", "FINAL"})  # ADR-013


def _normalize(game: dict[str, Any], team: str) -> dict[str, Any]:
    """Normalize one game relative to `team`. Returns a flat dict."""
    home = game.get("homeTeam") or {}
    away = game.get("awayTeam") or {}
    is_home = home.get("abbrev") == team
    me, opp = (home, away) if is_home else (away, home)
    outcome = game.get("gameOutcome") or {}
    return {
        "gameId": game.get("id"),
        "date": game.get("gameDate"),
        "startTimeUTC": game.get("startTimeUTC"),
        "home": is_home,
        "opponent": {"abbrev": opp.get("abbrev"), "name": opp.get("commonName")},
        "teamScore": me.get("score"),
        "oppScore": opp.get("score"),
        "state": game.get("gameState"),
        "decidedIn": outcome.get("lastPeriodType"),  # REG / OT / SO or None
    }


def games_regular_season(payload: dict[str, Any], team: str) -> list[dict[str, Any]]:
    """Return every regular-season game normalized, in payload order."""
    return [
        _normalize(g, team)
        for g in payload.get("games") or []
        if g.get("gameType") == REGULAR_SEASON
    ]


def last_completed_before(games: list[dict[str, Any]], data_date: date) -> dict[str, Any] | None:
    """Latest game with `state ∈ {OFF, FINAL}` and `date <= data_date` (string compare)."""
    cutoff = data_date.isoformat()
    completed = [
        g for g in games if g.get("state") in COMPLETED_STATES and (g.get("date") or "") <= cutoff
    ]
    if not completed:
        return None
    # Sort by date ascending; latest is the last entry.
    completed.sort(key=lambda g: g["date"])
    g = completed[-1]
    # Derive W/L/OTL result (ADR-036 for lastGame.result):
    me = g["teamScore"]
    opp = g["oppScore"]
    if me is None or opp is None:
        result = None
    elif me > opp:
        result = "W"
    elif g["decidedIn"] in ("OT", "SO"):
        result = "OTL"
    else:
        result = "L"
    return {**g, "result": result}


def next_games_after(
    games: list[dict[str, Any]], data_date: date, limit: int = 3
) -> list[dict[str, Any]]:
    """Up to `limit` games strictly after `data_date`, ascending by date."""
    cutoff = data_date.isoformat()
    upcoming = [g for g in games if (g.get("date") or "") > cutoff]
    upcoming.sort(key=lambda g: g["date"])
    return upcoming[:limit]
