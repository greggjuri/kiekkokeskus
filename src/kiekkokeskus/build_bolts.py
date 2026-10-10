"""Pure build function for `bolts.json`. Dict in, dict out — no I/O, no clock.

Composes the parsed inputs plus `data_date` into the final shape documented in init-04.
Join rule (ADR-035): the club-stats skater set is authoritative; stats REST adds `ppp`,
`hits`, `blocks`, and the faceoff fields. A player missing from a stats REST side keeps the
row with those fields `null`.
"""

from __future__ import annotations

import math
from datetime import date
from typing import Any

from kiekkokeskus.parse import club_schedule, club_stats, standings, stats_rest

TBL = "TBL"
TBL_TEAM_FULLNAME = "Tampa Bay Lightning"


# --- team + standing --------------------------------------------------------


def _streak(row: dict[str, Any]) -> dict[str, Any] | None:
    code = row.get("streakCode")
    count = row.get("streakCount")
    if code is None and count is None:
        return None
    return {"code": code, "count": count}


def _division_lead(rows: list[dict[str, Any]], tbl_row: dict[str, Any]) -> dict[str, Any]:
    """ADR-036. `gap` is signed; 0 when TBL leads. `gamesInHand` = leader.gp - tbl.gp."""
    leader = standings.division_leader(rows, tbl_row.get("divisionAbbrev") or "")
    leader_pts = (leader.get("points") if leader else None) or 0
    leader_gp = (leader.get("gamesPlayed") if leader else None) or 0
    tbl_pts = tbl_row.get("points") or 0
    tbl_gp = tbl_row.get("gamesPlayed") or 0
    return {
        "leader": (leader or {}).get("team"),
        "leaderPts": leader_pts,
        "gap": leader_pts - tbl_pts,  # signed; never abs() (ADR-036)
        "gamesInHand": leader_gp - tbl_gp,
    }


def _standing_section(rows: list[dict[str, Any]], tbl_row: dict[str, Any]) -> dict[str, Any]:
    division = {
        "abbrev": tbl_row.get("divisionAbbrev"),
        "rank": tbl_row.get("divisionSequence"),
    }
    conference = {
        "abbrev": tbl_row.get("conferenceAbbrev"),
        "rank": tbl_row.get("conferenceSequence"),
    }
    return {
        "gp": tbl_row.get("gamesPlayed"),
        "w": tbl_row.get("wins"),
        "l": tbl_row.get("losses"),
        "otl": tbl_row.get("otLosses"),
        "pts": tbl_row.get("points"),
        "pointPct": tbl_row.get("pointPctg"),
        "gf": tbl_row.get("goalFor"),
        "ga": tbl_row.get("goalAgainst"),
        "streak": _streak(tbl_row),
        "division": division,
        "conference": conference,
        "leagueRank": tbl_row.get("leagueSequence"),
        "divisionLead": _division_lead(rows, tbl_row),
        "playoffLine": standings.playoff_line(rows, TBL),
    }


# --- schedule-derived -------------------------------------------------------


def _last_game_section(g: dict[str, Any] | None) -> dict[str, Any] | None:
    """Rename `teamScore` → `tblScore` for the output."""
    if g is None:
        return None
    return {
        "gameId": g.get("gameId"),
        "date": g.get("date"),
        "home": g.get("home"),
        "opponent": g.get("opponent"),
        "tblScore": g.get("teamScore"),
        "oppScore": g.get("oppScore"),
        "result": g.get("result"),
        "decidedIn": g.get("decidedIn"),
    }


def _next_game_section(g: dict[str, Any]) -> dict[str, Any]:
    return {
        "gameId": g.get("gameId"),
        "date": g.get("date"),
        "startTimeUTC": g.get("startTimeUTC"),
        "home": g.get("home"),
        "opponent": g.get("opponent"),
    }


# --- special teams ----------------------------------------------------------


def _competition_ranks(values: list[tuple[str, float | None]]) -> dict[str, int]:
    """Standard competition ranking (1-2-2-4), 1 = best. `None` values are excluded."""
    scored = [(name, v) for name, v in values if v is not None]
    scored.sort(key=lambda t: t[1], reverse=True)
    ranks: dict[str, int] = {}
    i = 0
    while i < len(scored):
        # Find the span of ties
        j = i
        while j + 1 < len(scored) and math.isclose(scored[j + 1][1], scored[i][1]):
            j += 1
        rank = i + 1  # 1-based; after a 2-way tie at rank 2, next rank is 4
        for k in range(i, j + 1):
            ranks[scored[k][0]] = rank
        i = j + 1
    return ranks


def _special_teams_section(team_summary_payload: dict[str, Any]) -> dict[str, Any]:
    teams = stats_rest.team_rows(team_summary_payload)
    # Teams with GP > 0 only; TBL's values pass through
    pp_values: list[tuple[str, float | None]] = []
    pk_values: list[tuple[str, float | None]] = []
    for name, row in teams.items():
        gp = row.get("gamesPlayed") or 0
        if gp <= 0:
            continue
        pp_values.append((name, row.get("powerPlayPct")))
        pk_values.append((name, row.get("penaltyKillPct")))
    pp_ranks = _competition_ranks(pp_values)
    pk_ranks = _competition_ranks(pk_values)

    tbl = teams.get(TBL_TEAM_FULLNAME, {})
    return {
        "ppPct": tbl.get("powerPlayPct"),
        "pkPct": tbl.get("penaltyKillPct"),
        "ppRank": pp_ranks.get(TBL_TEAM_FULLNAME),
        "pkRank": pk_ranks.get(TBL_TEAM_FULLNAME),
    }


# --- players ----------------------------------------------------------------


def _skater_row(
    s: dict[str, Any],
    summary_idx: dict[int, dict[str, Any]],
    realtime_idx: dict[int, dict[str, Any]],
    faceoff_idx: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    pid = s["playerId"]
    sm = summary_idx.get(pid, {})
    rt = realtime_idx.get(pid, {})
    fo = faceoff_idx.get(pid, {})

    # ADR-035 faceoff rule: null when totalFaceoffs == 0, else faceoffWinPct
    total_face = fo.get("totalFaceoffs")
    face_pct = None if total_face in (None, 0) else fo.get("faceoffWinPct")

    return {
        "playerId": pid,
        "firstName": s["firstName"],
        "lastName": s["lastName"],
        "positionCode": s["positionCode"],
        "gp": s["gamesPlayed"],
        "g": s["goals"],
        "a": s["assists"],
        "p": s["points"],
        "pm": s["plusMinus"],
        "pim": s["penaltyMinutes"],
        "toiPerGame": s["toiPerGame"],
        "sog": s["shots"],
        "shootingPct": s["shootingPctg"],
        "ppg": s["powerPlayGoals"],
        "shg": s["shorthandedGoals"],
        "gwg": s["gameWinningGoals"],
        "ppp": sm.get("ppPoints"),
        "faceoffPct": face_pct,
        "hits": rt.get("hits"),
        "blocks": rt.get("blockedShots"),
    }


def _goalie_row(g: dict[str, Any]) -> dict[str, Any]:
    return {
        "playerId": g["playerId"],
        "firstName": g["firstName"],
        "lastName": g["lastName"],
        "gp": g["gamesPlayed"],
        "gs": g["gamesStarted"],
        "w": g["wins"],
        "l": g["losses"],
        "otl": g["otLosses"],
        "so": g["shutouts"],
        "svPct": g["savePercentage"],
        "gaa": g["goalsAgainstAverage"],
        "toi": g["timeOnIce"],
    }


# --- top-level build --------------------------------------------------------


def build(
    *,
    data_date: date,
    season: str,
    now_iso: str,
    standings_payload: dict[str, Any],
    club_stats_payload: dict[str, Any],
    club_schedule_payload: dict[str, Any],
    skater_summary_payload: dict[str, Any],
    skater_realtime_payload: dict[str, Any],
    skater_faceoff_payload: dict[str, Any],
    team_summary_payload: dict[str, Any],
) -> dict[str, Any]:
    rows = standings.rows(standings_payload)
    tbl_row = standings.by_team(rows, TBL)
    if tbl_row is None:
        raise ValueError("TBL row missing from standings")

    team = {"abbrev": TBL, "name": tbl_row.get("teamName")}
    standing = _standing_section(rows, tbl_row)

    games = club_schedule.games_regular_season(club_schedule_payload, TBL)
    last_game = _last_game_section(club_schedule.last_completed_before(games, data_date))
    next_games = [
        _next_game_section(g) for g in club_schedule.next_games_after(games, data_date, limit=3)
    ]

    special_teams = _special_teams_section(team_summary_payload)

    summary_idx = stats_rest.by_player_id(skater_summary_payload, ["ppPoints"])
    realtime_idx = stats_rest.by_player_id(skater_realtime_payload, ["hits", "blockedShots"])
    faceoff_idx = stats_rest.by_player_id(
        skater_faceoff_payload, ["totalFaceoffs", "faceoffWinPct"]
    )

    skaters = [
        _skater_row(s, summary_idx, realtime_idx, faceoff_idx)
        for s in club_stats.skaters(club_stats_payload)
    ]
    goalies = [_goalie_row(g) for g in club_stats.goalies(club_stats_payload)]

    return {
        "schemaVersion": 1,
        "generatedAt": now_iso,
        "dataDate": data_date.isoformat(),
        "season": season,
        "team": team,
        "standing": standing,
        "lastGame": last_game,
        "nextGames": next_games,
        "specialTeams": special_teams,
        "skaters": skaters,
        "goalies": goalies,
    }
