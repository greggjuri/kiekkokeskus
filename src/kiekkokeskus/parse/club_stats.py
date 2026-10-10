"""Pure parser for the club-stats payload (ADR-015/017/018/035).

Returns one row per skater and per goalie. Localized names pass through (ADR-018). `headshot` is
dropped (ADR-003 keeps the browser off NHL assets). TOI stays int seconds (ADR-017):
`avgTimeOnIcePerGame` is a float seconds (per-game), `timeOnIce` on goalies is int total seconds.

ADR-015: `.get()` with no default produces `None` when the field is absent at 0 GP / 0 shots.
"""

from __future__ import annotations

from typing import Any


def _int_or_none(v: Any) -> int | None:
    if v is None:
        return None
    return int(v)


def _seconds_from_float(v: Any) -> int | None:
    if v is None:
        return None
    return int(v)


def skaters(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """One row per skater from `payload["skaters"]`.

    Fields come straight from NHL names except where normalization is needed:
    - `avgTimeOnIcePerGame` → `toiPerGame` int seconds (ADR-017)
    - `shots` → `sog`; `shootingPctg` → `shootingPct`
    - `shootingPct` is `None` when `shots == 0` (ADR-015 — absent at 0 shots). We also map
      `shots == 0 and shootingPctg == 0.0` to `None` defensively.
    - `headshot` is dropped (ADR-003).
    Returns the raw NHL `faceoffWinPctg` as `faceoffWinPctg` — the builder resolves the final
    `faceoffPct` field by consulting `skater/faceoffpercentages` for `totalFaceoffs` (ADR-035).
    """
    out: list[dict[str, Any]] = []
    for s in payload.get("skaters") or []:
        shots = s.get("shots")
        shooting = s.get("shootingPctg")
        # Explicitly drop 0/0 to None
        if shots in (None, 0):
            shooting = None

        out.append(
            {
                "playerId": s.get("playerId"),
                "firstName": s.get("firstName"),
                "lastName": s.get("lastName"),
                "positionCode": s.get("positionCode"),
                "gamesPlayed": _int_or_none(s.get("gamesPlayed")),
                "goals": _int_or_none(s.get("goals")),
                "assists": _int_or_none(s.get("assists")),
                "points": _int_or_none(s.get("points")),
                "plusMinus": _int_or_none(s.get("plusMinus")),
                "penaltyMinutes": _int_or_none(s.get("penaltyMinutes")),
                "shots": _int_or_none(shots),
                "shootingPctg": shooting,
                "powerPlayGoals": _int_or_none(s.get("powerPlayGoals")),
                "shorthandedGoals": _int_or_none(s.get("shorthandedGoals")),
                "gameWinningGoals": _int_or_none(s.get("gameWinningGoals")),
                "toiPerGame": _seconds_from_float(s.get("avgTimeOnIcePerGame")),
                "faceoffWinPctg": s.get("faceoffWinPctg"),
            }
        )
    return out


def goalies(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """One row per goalie from `payload["goalies"]`. `overtimeLosses` → `otLosses`."""
    out: list[dict[str, Any]] = []
    for g in payload.get("goalies") or []:
        out.append(
            {
                "playerId": g.get("playerId"),
                "firstName": g.get("firstName"),
                "lastName": g.get("lastName"),
                "gamesPlayed": _int_or_none(g.get("gamesPlayed")),
                "gamesStarted": _int_or_none(g.get("gamesStarted")),
                "wins": _int_or_none(g.get("wins")),
                "losses": _int_or_none(g.get("losses")),
                "otLosses": _int_or_none(g.get("overtimeLosses")),
                "shutouts": _int_or_none(g.get("shutouts")),
                "savePercentage": g.get("savePercentage"),  # fraction 0–1 or None (ADR-015)
                "goalsAgainstAverage": g.get("goalsAgainstAverage"),
                "timeOnIce": _int_or_none(g.get("timeOnIce")),  # int total seconds (ADR-017)
            }
        )
    return out
