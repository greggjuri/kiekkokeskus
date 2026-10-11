"""Pure build function for `leijonat.json`. Dict in, dict out — no I/O, no clock.

Composition:
- Row set = Finnish bios (ADR-011). Never drop a row (ADR-030, ADR-035 join rule).
- Name resolution per playerId, in order (ADR-037 Fix 4):
    1. Scan every club-stats payload in `club_stats_by_team` for a matching playerId → use its
       localized `firstName` + `lastName` (ADR-018). Carries `fi` keys for players who have them.
    2. Fallback via bios: `lastName` + suffix-strip of `*FullName` → `{default}`. Warning logged.
    3. Suffix mismatch → raise `NameSuffixMismatch`. Payload surprise.
- Rookie flag: `playerId in rookie_set` → non-null bool.
- Last-night inclusion: Finn skater with `points ≥ 1`; Finn goalie with `starter == True`
  (ADR-012). `game.result` and `game.decidedIn` are derived from boxscore
  `gameOutcome.lastPeriodType` + score comparison — never from goalie `decision`.
- `teams[]`: aggregate counts by `bios.currentTeamAbbrev`, with `teamName` from standings.
"""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

from kiekkokeskus.parse import bios as bios_parse
from kiekkokeskus.parse import boxscore as box_parse
from kiekkokeskus.parse import stats_rest
from kiekkokeskus.parse.standings import rows as standings_rows

log = logging.getLogger(__name__)


class NameSuffixMismatch(ValueError):
    """Raised when bios `*FullName` doesn't end with `" " + lastName` (ADR-037 Fix 4)."""


# --- name resolution --------------------------------------------------------


def _resolve_name(
    *,
    pid: int,
    bios_row: dict[str, Any],
    club_stats_by_team: dict[str, dict[str, Any]],
    is_goalie: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return `(firstName, lastName)` as localized objects (ADR-018)."""
    # Step 1: scan all club-stats payloads
    for cs in club_stats_by_team.values():
        group = cs.get("goalies" if is_goalie else "skaters") or []
        for row in group:
            if row.get("playerId") == pid:
                fn, ln = row.get("firstName"), row.get("lastName")
                if isinstance(fn, dict) and isinstance(ln, dict):
                    return fn, ln

    # Step 2: bios fallback
    full_key = "goalieFullName" if is_goalie else "skaterFullName"
    full = bios_row.get(full_key)
    last = bios_row.get("lastName")
    if isinstance(full, str) and isinstance(last, str) and full.endswith(" " + last):
        first = full[: -(len(last) + 1)].strip()
        log.warning(
            json.dumps(
                {
                    "event": "name_fallback",
                    "playerId": pid,
                    "source": "bios_suffix_strip",
                }
            )
        )
        return {"default": first}, {"default": last}

    # Step 3: payload surprise
    raise NameSuffixMismatch(
        f"playerId {pid}: {full_key}={full!r} does not end with ' ' + lastName={last!r}"
    )


# --- teams block ------------------------------------------------------------


def _teams_block(
    bios_merged: dict[str, dict[int, dict[str, Any]]],
    standings_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    counts: dict[str, dict[str, int]] = {}
    for row in bios_merged["skaters"].values():
        team = row.get("currentTeamAbbrev")
        if not team:
            continue
        counts.setdefault(team, {"skaters": 0, "goalies": 0})["skaters"] += 1
    for row in bios_merged["goalies"].values():
        team = row.get("currentTeamAbbrev")
        if not team:
            continue
        counts.setdefault(team, {"skaters": 0, "goalies": 0})["goalies"] += 1

    names_by_abbrev: dict[str, Any] = {}
    for r in standings_rows(standings_payload):
        names_by_abbrev[r["team"]] = r.get("teamName")

    out = []
    for abbrev, c in counts.items():
        out.append(
            {
                "abbrev": abbrev,
                "name": names_by_abbrev.get(abbrev),
                "skaters": c["skaters"],
                "goalies": c["goalies"],
            }
        )
    out.sort(key=lambda t: (-(t["skaters"] + t["goalies"]), t["abbrev"]))
    return out


# --- season rows ------------------------------------------------------------


def _skater_season_row(
    *,
    bios_row: dict[str, Any],
    summary: dict[str, Any],
    realtime: dict[str, Any],
    faceoff: dict[str, Any],
    first_name: dict[str, Any],
    last_name: dict[str, Any],
    rookie: bool,
) -> dict[str, Any]:
    total_face = faceoff.get("totalFaceoffs")
    face_pct = None if total_face in (None, 0) else faceoff.get("faceoffWinPct")
    toi_per_game = summary.get("timeOnIcePerGame")
    toi_int = None if toi_per_game is None else int(toi_per_game)
    return {
        "playerId": bios_row["playerId"],
        "firstName": first_name,
        "lastName": last_name,
        "team": bios_row.get("currentTeamAbbrev"),
        "positionCode": bios_row.get("positionCode"),
        "rookie": rookie,
        "gp": summary.get("gamesPlayed"),
        "g": summary.get("goals"),
        "a": summary.get("assists"),
        "p": summary.get("points"),
        "pm": summary.get("plusMinus"),
        "pim": summary.get("penaltyMinutes"),
        "toiPerGame": toi_int,
        "sog": summary.get("shots"),
        "shootingPct": summary.get("shootingPct"),
        "ppg": summary.get("ppGoals"),
        "shg": summary.get("shGoals"),
        "gwg": summary.get("gameWinningGoals"),
        "ppp": summary.get("ppPoints"),
        "faceoffPct": face_pct,
        "hits": realtime.get("hits"),
        "blocks": realtime.get("blockedShots"),
    }


def _goalie_season_row(
    *,
    bios_row: dict[str, Any],
    summary: dict[str, Any],
    first_name: dict[str, Any],
    last_name: dict[str, Any],
    rookie: bool,
) -> dict[str, Any]:
    toi = summary.get("timeOnIce")
    toi_int = None if toi is None else int(toi)
    return {
        "playerId": bios_row["playerId"],
        "firstName": first_name,
        "lastName": last_name,
        "team": bios_row.get("currentTeamAbbrev"),
        "rookie": rookie,
        "gp": summary.get("gamesPlayed"),
        "gs": summary.get("gamesStarted"),
        "w": summary.get("wins"),
        "l": summary.get("losses"),
        "otl": summary.get("otLosses"),
        "so": summary.get("shutouts"),
        "svPct": summary.get("savePct"),
        "gaa": summary.get("goalsAgainstAverage"),
        "toi": toi_int,
    }


# --- last night --------------------------------------------------------------


def _games_completed_on(schedule_payload: dict[str, Any], data_date: date) -> int:
    """Fix 6: filter gameWeek to date == dataDate, then gameType==2 and state ∈ {OFF, FINAL}."""
    target = data_date.isoformat()
    for w in schedule_payload.get("gameWeek") or []:
        if w.get("date") != target:
            continue
        return sum(
            1
            for g in w.get("games") or []
            if g.get("gameType") == 2 and g.get("gameState") in {"OFF", "FINAL"}
        )
    return 0


def _game_object_for(
    *,
    ctx: dict[str, Any],
    finn_team: str,
) -> dict[str, Any]:
    is_home = ctx["home"]["abbrev"] == finn_team
    me = ctx["home"] if is_home else ctx["away"]
    opp = ctx["away"] if is_home else ctx["home"]
    me_score = me.get("score")
    opp_score = opp.get("score")
    decided_in = ctx.get("decidedIn")  # REG / OT / SO / None
    if me_score is None or opp_score is None:
        result = None
    elif me_score > opp_score:
        result = "W"
    elif decided_in in {"OT", "SO"}:
        result = "OTL"
    else:
        result = "L"
    return {
        "gameId": ctx["id"],
        "home": is_home,
        "opponent": opp.get("abbrev"),
        "teamScore": me_score,
        "oppScore": opp_score,
        "result": result,
        "decidedIn": decided_in,
    }


def _last_night(
    *,
    bios_merged: dict[str, dict[int, dict[str, Any]]],
    schedule_payload: dict[str, Any],
    boxscore_payloads: list[dict[str, Any]],
    data_date: date,
    name_cache: dict[int, tuple[dict[str, Any], dict[str, Any]]],
) -> dict[str, Any]:
    skaters_out: list[dict[str, Any]] = []
    goalies_out: list[dict[str, Any]] = []
    finn_skater_ids = set(bios_merged["skaters"].keys())
    finn_goalie_ids = set(bios_merged["goalies"].keys())

    for bx in boxscore_payloads:
        ctx = box_parse.game_context(bx)
        rows = box_parse.player_rows(bx)
        for row in rows:
            pid = row.get("playerId")
            if pid is None:
                continue
            if row.get("position") == "G":
                if pid not in finn_goalie_ids:
                    continue
                if not row.get("starter"):
                    continue
                first_name, last_name = name_cache.get(
                    pid,
                    ({"default": "?"}, {"default": "?"}),  # should always be in cache
                )
                goalies_out.append(
                    {
                        "playerId": pid,
                        "firstName": first_name,
                        "lastName": last_name,
                        "team": row.get("team"),
                        "saves": row.get("saves"),
                        "shotsAgainst": row.get("shotsAgainst"),
                        "svPct": row.get("savePctg"),
                        "decision": row.get("decision"),
                        "toi": row.get("toi"),
                        "game": _game_object_for(ctx=ctx, finn_team=row["team"]),
                    }
                )
            else:
                if pid not in finn_skater_ids:
                    continue
                if (row.get("points") or 0) < 1:
                    continue
                first_name, last_name = name_cache.get(pid, ({"default": "?"}, {"default": "?"}))
                skaters_out.append(
                    {
                        "playerId": pid,
                        "firstName": first_name,
                        "lastName": last_name,
                        "team": row.get("team"),
                        "g": row.get("goals"),
                        "a": row.get("assists"),
                        "p": row.get("points"),
                        "pm": row.get("plusMinus"),
                        "sog": row.get("sog"),
                        "pim": row.get("pim"),
                        "toi": row.get("toi"),
                        "game": _game_object_for(ctx=ctx, finn_team=row["team"]),
                    }
                )

    def _skater_sort_key(r: dict) -> tuple:
        return (
            -(r.get("p") or 0),
            -(r.get("g") or 0),
            (r["lastName"].get("default") or ""),
        )

    skaters_out.sort(key=_skater_sort_key)
    goalies_out.sort(
        key=lambda r: (
            -(r.get("svPct") if r.get("svPct") is not None else -1.0),
            r["lastName"].get("default") or "",
        ),
    )

    return {
        "date": data_date.isoformat(),
        "gamesCompleted": _games_completed_on(schedule_payload, data_date),
        "skaters": skaters_out,
        "goalies": goalies_out,
    }


# --- top-level build --------------------------------------------------------


def build(
    *,
    data_date: date,
    season: str,
    now_iso: str,
    bios_skater_pages: list[dict[str, Any]],
    bios_goalie_pages: list[dict[str, Any]],
    summary_payload: dict[str, Any],
    realtime_payload: dict[str, Any],
    faceoff_payload: dict[str, Any],
    goalie_summary_payload: dict[str, Any],
    rookie_skater_ids: set[int],
    rookie_goalie_ids: set[int],
    club_stats_by_team: dict[str, dict[str, Any]],
    boxscore_payloads: list[dict[str, Any]],
    schedule_payload: dict[str, Any],
    standings_payload: dict[str, Any],
) -> dict[str, Any]:
    merged = bios_parse.merged(bios_skater_pages, bios_goalie_pages)

    summary_idx = stats_rest.by_player_id(
        summary_payload,
        [
            "gamesPlayed",
            "goals",
            "assists",
            "points",
            "plusMinus",
            "penaltyMinutes",
            "timeOnIcePerGame",
            "shots",
            "shootingPct",
            "ppGoals",
            "shGoals",
            "gameWinningGoals",
            "ppPoints",
        ],
    )
    realtime_idx = stats_rest.by_player_id(realtime_payload, ["hits", "blockedShots"])
    faceoff_idx = stats_rest.by_player_id(faceoff_payload, ["totalFaceoffs", "faceoffWinPct"])
    goalie_summary_idx = stats_rest.by_player_id(
        goalie_summary_payload,
        [
            "gamesPlayed",
            "gamesStarted",
            "wins",
            "losses",
            "otLosses",
            "shutouts",
            "savePct",
            "goalsAgainstAverage",
            "timeOnIce",
        ],
    )

    # Pre-resolve names once per Finn so last-night rows reuse the lookup.
    name_cache: dict[int, tuple[dict[str, Any], dict[str, Any]]] = {}
    for pid, bios_row in merged["skaters"].items():
        name_cache[pid] = _resolve_name(
            pid=pid,
            bios_row=bios_row,
            club_stats_by_team=club_stats_by_team,
            is_goalie=False,
        )
    for pid, bios_row in merged["goalies"].items():
        name_cache[pid] = _resolve_name(
            pid=pid,
            bios_row=bios_row,
            club_stats_by_team=club_stats_by_team,
            is_goalie=True,
        )

    skaters_out: list[dict[str, Any]] = []
    for pid, bios_row in merged["skaters"].items():
        first_name, last_name = name_cache[pid]
        skaters_out.append(
            _skater_season_row(
                bios_row=bios_row,
                summary=summary_idx.get(pid, {}),
                realtime=realtime_idx.get(pid, {}),
                faceoff=faceoff_idx.get(pid, {}),
                first_name=first_name,
                last_name=last_name,
                rookie=pid in rookie_skater_ids,
            )
        )

    goalies_out: list[dict[str, Any]] = []
    for pid, bios_row in merged["goalies"].items():
        first_name, last_name = name_cache[pid]
        goalies_out.append(
            _goalie_season_row(
                bios_row=bios_row,
                summary=goalie_summary_idx.get(pid, {}),
                first_name=first_name,
                last_name=last_name,
                rookie=pid in rookie_goalie_ids,
            )
        )

    def _skater_sort_key(r: dict) -> tuple:
        return (
            -(r.get("p") or 0),
            -(r.get("g") or 0),
            (r["lastName"].get("default") or ""),
        )

    skaters_out.sort(key=_skater_sort_key)
    goalies_out.sort(key=lambda r: r["lastName"].get("default") or "")

    return {
        "schemaVersion": 1,
        "generatedAt": now_iso,
        "dataDate": data_date.isoformat(),
        "season": season,
        "teams": _teams_block(merged, standings_payload),
        "lastNight": _last_night(
            bios_merged=merged,
            schedule_payload=schedule_payload,
            boxscore_payloads=boxscore_payloads,
            data_date=data_date,
            name_cache=name_cache,
        ),
        "skaters": skaters_out,
        "goalies": goalies_out,
    }
