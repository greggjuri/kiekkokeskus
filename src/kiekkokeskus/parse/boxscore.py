"""Pure parser for the gamecenter boxscore payload (ADR-012, ADR-013, ADR-015, ADR-017, ADR-037).

Produces a game-context dict and a flat list of per-player rows across both teams. Skater `toi`
(`"MM:SS"` string) and goalie `toi` are normalized to int seconds (ADR-017). An absent goalie
`savePctg`/`decision` stays `None` (ADR-015). `game.decidedIn` comes from
`gameOutcome.lastPeriodType`; `game.result` is derived from the score (never from the goalie's
`decision` field).
"""

from __future__ import annotations

from typing import Any


def _toi_to_seconds(toi: Any) -> int | None:
    """`"MM:SS"` or `"H:MM:SS"` → int seconds. `None` or malformed → None."""
    if toi is None or not isinstance(toi, str):
        return None
    parts = toi.split(":")
    if len(parts) == 2:
        m, s = parts
        try:
            return int(m) * 60 + int(s)
        except ValueError:
            return None
    if len(parts) == 3:
        h, m, s = parts
        try:
            return int(h) * 3600 + int(m) * 60 + int(s)
        except ValueError:
            return None
    return None


def game_context(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the per-game header: id, home/away abbrev+score, state, decidedIn."""
    home = payload.get("homeTeam") or {}
    away = payload.get("awayTeam") or {}
    outcome = payload.get("gameOutcome") or {}
    return {
        "id": payload.get("id"),
        "home": {"abbrev": home.get("abbrev"), "score": home.get("score")},
        "away": {"abbrev": away.get("abbrev"), "score": away.get("score")},
        "state": payload.get("gameState"),
        "decidedIn": outcome.get("lastPeriodType"),  # REG / OT / SO / None
    }


def _skater_row(p: dict[str, Any], team_abbrev: str) -> dict[str, Any]:
    return {
        "playerId": p.get("playerId"),
        "name": p.get("name"),  # localized object, initials-only (ADR-018)
        "team": team_abbrev,
        "position": p.get("position"),
        "goals": p.get("goals"),
        "assists": p.get("assists"),
        "points": p.get("points"),
        "plusMinus": p.get("plusMinus"),
        "pim": p.get("pim"),
        "hits": p.get("hits"),
        "blockedShots": p.get("blockedShots"),
        "sog": p.get("sog"),
        "faceoffWinningPctg": p.get("faceoffWinningPctg"),
        "toi": _toi_to_seconds(p.get("toi")),  # int seconds (ADR-017)
    }


def _goalie_row(p: dict[str, Any], team_abbrev: str) -> dict[str, Any]:
    return {
        "playerId": p.get("playerId"),
        "name": p.get("name"),
        "team": team_abbrev,
        "position": "G",
        "starter": p.get("starter"),
        "saves": p.get("saves"),
        "shotsAgainst": p.get("shotsAgainst"),
        "savePctg": p.get("savePctg"),  # fraction 0–1 or None (ADR-015)
        "decision": p.get("decision"),  # W / L / O / None — passed through raw (ADR-037)
        "goalsAgainst": p.get("goalsAgainst"),
        "toi": _toi_to_seconds(p.get("toi")),  # int seconds
    }


def player_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """One row per player across both teams. Preserves order (home → away)."""
    pbgs = payload.get("playerByGameStats") or {}
    home_abbrev = (payload.get("homeTeam") or {}).get("abbrev")
    away_abbrev = (payload.get("awayTeam") or {}).get("abbrev")
    out: list[dict[str, Any]] = []
    for side_key, team_abbrev in (("homeTeam", home_abbrev), ("awayTeam", away_abbrev)):
        side = pbgs.get(side_key) or {}
        for group in ("forwards", "defense"):
            for p in side.get(group) or []:
                out.append(_skater_row(p, team_abbrev))
        for p in side.get("goalies") or []:
            out.append(_goalie_row(p, team_abbrev))
    return out
