"""Pure parser for the NHL schedule payload. Dict in, tuple out. No I/O, no clock."""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

log = logging.getLogger(__name__)

COMPLETED_STATES = frozenset({"OFF", "FINAL"})  # ADR-013
REGULAR_SEASON = 2  # ADR-014


def _games_on(payload: dict[str, Any], data_date: date) -> list[dict[str, Any]]:
    """Return the games in the gameWeek entry whose date == data_date (empty if absent)."""
    want = data_date.isoformat()
    for week in payload.get("gameWeek", []):
        if week.get("date") == want:
            return list(week.get("games", []))
    return []


def extract(payload: dict[str, Any], data_date: date) -> tuple[str | None, list[int]]:
    """Return (season, completed_regular_season_game_ids_on_data_date).

    Season is read from any game on `data_date` (ADR-033). It is `None` when the gameWeek has no
    entry for `data_date` or when that entry has no games. The caller is responsible for the
    standings fallback.

    Game IDs are filtered to `gameType == 2` and `gameState in {OFF, FINAL}` on `data_date`.
    Unknown `gameState` values are logged (ADR-013) and skipped.
    """
    games = _games_on(payload, data_date)
    season: str | None = None
    for g in games:
        s = g.get("season")
        if s is not None:
            season = str(s)
            break

    game_ids: list[int] = []
    for g in games:
        if g.get("gameType") != REGULAR_SEASON:
            continue
        state = g.get("gameState")
        if state in COMPLETED_STATES:
            game_ids.append(int(g["id"]))
        elif state is None or state in {"FUT", "PRE", "LIVE", "CRIT"}:
            # Known not-done states (documented or expected). Silent skip.
            continue
        else:
            log.warning(
                json.dumps(
                    {
                        "event": "unknown_game_state",
                        "gameId": g.get("id"),
                        "gameState": state,
                    }
                )
            )
    return season, game_ids
