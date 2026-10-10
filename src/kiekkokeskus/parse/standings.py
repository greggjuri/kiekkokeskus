"""Pure standings parser. ADR-015 (missing-at-0-GP → null), ADR-036 (definitions)."""

from __future__ import annotations

from typing import Any

# Fields that come through verbatim as ints when present; .get() → None when absent (ADR-015).
_INT_FIELDS = ("gamesPlayed", "wins", "losses", "otLosses", "points", "goalFor", "goalAgainst")

# Fields that come through as numbers (fraction / per-game); None when absent (ADR-015, 016).
_NUMBER_FIELDS = ("pointPctg",)


def season_id(payload: dict[str, Any]) -> str | None:
    """Return `standings[0].seasonId` as a string, or None if standings is empty."""
    rows = payload.get("standings") or []
    if not rows:
        return None
    sid = rows[0].get("seasonId")
    return None if sid is None else str(sid)


def _team_abbrev(row: dict[str, Any]) -> str | None:
    """`teamAbbrev` is a localized object `{"default": "TBL"}`; flatten to the default string."""
    v = row.get("teamAbbrev")
    if isinstance(v, dict):
        return v.get("default")
    return v


def rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """One normalized row per team.

    All stats fields pass through `.get()` → `None` when absent (ADR-015). `pointPctg` stays a
    fraction 0–1 (ADR-016). `teamAbbrev` is flattened to the default string.
    """
    out: list[dict[str, Any]] = []
    for r in payload.get("standings") or []:
        row = {"team": _team_abbrev(r), "teamName": r.get("teamName")}
        for k in _INT_FIELDS:
            row[k] = r.get(k)
        for k in _NUMBER_FIELDS:
            row[k] = r.get(k)
        row["streakCode"] = r.get("streakCode")
        row["streakCount"] = r.get("streakCount")
        row["divisionAbbrev"] = r.get("divisionAbbrev")
        row["conferenceAbbrev"] = r.get("conferenceAbbrev")
        row["divisionSequence"] = r.get("divisionSequence")
        row["conferenceSequence"] = r.get("conferenceSequence")
        row["leagueSequence"] = r.get("leagueSequence")
        row["wildcardSequence"] = r.get("wildcardSequence")
        out.append(row)
    return out


def by_team(rs: list[dict[str, Any]], team: str) -> dict[str, Any] | None:
    for r in rs:
        if r.get("team") == team:
            return r
    return None


def division_leader(rs: list[dict[str, Any]], division: str) -> dict[str, Any] | None:
    """Team with `divisionSequence == 1` in the given division (ADR-036)."""
    for r in rs:
        if r.get("divisionAbbrev") == division and r.get("divisionSequence") == 1:
            return r
    return None


def playoff_line(rs: list[dict[str, Any]], team: str) -> dict[str, Any] | None:
    """Playoff-line reference for `team` (ADR-036).

    In-position (division top-3 OR wildcard 1/2):
        reference team = conference `wildcardSequence == 3`
        gap = team.points - reference.points   (signed; positive = cushion)
    Out-of-position:
        reference team = conference `wildcardSequence == 2`
        gap = reference.points - team.points   (signed; positive = deficit)

    `gap` is **signed** and never `abs()`-ed — standings order can come from tiebreakers.
    """
    me = by_team(rs, team)
    if me is None:
        return None
    conf = me.get("conferenceAbbrev")
    div_seq = me.get("divisionSequence")
    wild_seq = me.get("wildcardSequence")
    # In-position if we're division top-3 OR wildcardSequence ∈ {1, 2}.
    in_position = (div_seq is not None and div_seq <= 3) or (wild_seq in (1, 2))

    target_wild = 3 if in_position else 2
    ref = next(
        (
            r
            for r in rs
            if r.get("conferenceAbbrev") == conf and r.get("wildcardSequence") == target_wild
        ),
        None,
    )
    if ref is None:
        return None

    my_pts = me.get("points") or 0
    ref_pts = ref.get("points") or 0
    my_gp = me.get("gamesPlayed") or 0
    ref_gp = ref.get("gamesPlayed") or 0

    gap = my_pts - ref_pts if in_position else ref_pts - my_pts

    return {
        "inPosition": in_position,
        "team": ref.get("team"),
        "teamPts": ref_pts,
        "gap": gap,
        "gamesInHand": ref_gp - my_gp,
    }
