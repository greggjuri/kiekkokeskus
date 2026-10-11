"""Layer-2 golden test for build_leijonat (init-05, ADR-037)."""

from __future__ import annotations

import copy
import gzip
import json
import os
import pathlib
from datetime import date

import pytest

from kiekkokeskus.build_leijonat import NameSuffixMismatch, build

FX = pathlib.Path(__file__).parent / "fixtures"
GOLDEN = pathlib.Path(__file__).parent / "golden" / "leijonat.json"

DATA_DATE = date(2026, 10, 9)
SEASON = "20262027"
NOW_ISO = "2026-10-10T14:00:12Z"


def _load(name: str) -> dict:
    return json.loads(gzip.decompress((FX / name).read_bytes()))


def _club_stats_by_team() -> dict[str, dict]:
    teams = [
        "TBL",  # from init-04 fixture
        "ANA",
        "BUF",
        "CAR",
        "CHI",
        "COL",
        "DAL",
        "EDM",
        "FLA",
        "LAK",
        "MIN",
        "NSH",
        "NYI",
        "NYR",
        "OTT",
        "PHI",
        "PIT",
        "SEA",
        "VAN",
        "WPG",
    ]
    return {
        t: _load(f"club-stats-{t}__20262027__2__2026-10-{'09' if t == 'TBL' else '10'}.json.gz")
        for t in teams
    }


def _rookie_ids(name: str, kind: str) -> set[int]:
    payload = _load(name)
    return {int(r["playerId"]) for r in payload.get("data") or []}


def _boxscores_for_data_date() -> list[dict]:
    # 2026-10-09 completed reg-season games (captured in Step 2)
    return [
        _load(f"boxscore__{gid}__2026-10-10.json.gz")
        for gid in (2026020066, 2026020067, 2026020068, 2026020069)
    ]


def _call_build(
    *,
    summary_name: str = "skater-summary-FIN__20262027__2026-10-10.json.gz",
    bios_sk_pages: list[dict] | None = None,
    bios_go_pages: list[dict] | None = None,
) -> dict:
    sk_pages = bios_sk_pages or [_load("skater-bios-FIN__20262027__p0__2026-10-10.json.gz")]
    go_pages = bios_go_pages or [_load("goalie-bios-FIN__20262027__p0__2026-10-10.json.gz")]
    return build(
        data_date=DATA_DATE,
        season=SEASON,
        now_iso=NOW_ISO,
        bios_skater_pages=sk_pages,
        bios_goalie_pages=go_pages,
        summary_payload=_load(summary_name),
        realtime_payload=_load("skater-realtime-FIN__20262027__2026-10-10.json.gz"),
        faceoff_payload=_load("skater-faceoff-FIN__20262027__2026-10-10.json.gz"),
        goalie_summary_payload=_load("goalie-summary-FIN__20262027__2026-10-10.json.gz"),
        rookie_skater_ids=_rookie_ids("skater-rookies-FIN__20262027__2026-10-10.json.gz", "skater"),
        rookie_goalie_ids=_rookie_ids("goalie-rookies-FIN__20262027__2026-10-10.json.gz", "goalie"),
        club_stats_by_team=_club_stats_by_team(),
        boxscore_payloads=_boxscores_for_data_date(),
        schedule_payload=_load("schedule__2026-10-09__2026-10-10.json.gz"),
        standings_payload=_load("standings__2026-10-09__2026-10-10.json.gz"),
    )


def test_golden_matches() -> None:
    """Byte-canonical JSON comparison. UPDATE_GOLDEN=1 to regenerate."""
    out = _call_build()
    canonical = json.dumps(out, sort_keys=True, separators=(",", ":"), default=str)
    if os.environ.get("UPDATE_GOLDEN") == "1":
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(json.dumps(out, sort_keys=True, indent=2, default=str) + "\n")
        return
    expected = json.dumps(
        json.loads(GOLDEN.read_text()),
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    assert canonical == expected, "golden drift — review and `UPDATE_GOLDEN=1 pytest` to accept"


def test_envelope_fields() -> None:
    out = _call_build()
    assert out["schemaVersion"] == 1
    assert out["generatedAt"] == NOW_ISO
    assert out["dataDate"] == "2026-10-09"
    assert out["season"] == SEASON


def test_counts_match_bios_totals() -> None:
    out = _call_build()
    assert len(out["skaters"]) == 30
    assert len(out["goalies"]) == 5


def test_umlaut_names_present_via_club_stats_fi_key() -> None:
    """ADR-037 Fix 4 step 1: Olli Määttä (MIN) + Teuvo Teräväinen (CHI) carry `fi` keys."""
    out = _call_build()
    # Olli Määttä (playerId 8476874, MIN)
    maatta = next(s for s in out["skaters"] if s["playerId"] == 8476874)
    assert maatta["lastName"]["fi"] == "Määttä"
    assert maatta["firstName"]["default"] == "Olli"
    # Teuvo Teräväinen (playerId 8476882, CHI)
    tera = next(s for s in out["skaters"] if s["playerId"] == 8476882)
    assert tera["lastName"]["fi"] == "Teräväinen"


def test_rookie_flag_matches_isRookie_filter() -> None:
    """ADR-037: isRookie=1 cayenneExp filter is authoritative. Non-null bool."""
    out = _call_build()
    rookie_ids = _rookie_ids("skater-rookies-FIN__20262027__2026-10-10.json.gz", "skater")
    for s in out["skaters"]:
        assert isinstance(s["rookie"], bool)
        assert s["rookie"] == (s["playerId"] in rookie_ids)
    # Today: 4 FIN skater rookies
    assert sum(1 for s in out["skaters"] if s["rookie"]) == 4
    # 0 FIN goalie rookies
    assert sum(1 for g in out["goalies"] if g["rookie"]) == 0


def test_teams_block_ordered_by_count_then_abbrev() -> None:
    out = _call_build()
    teams = out["teams"]
    # Every team has at least one Finn
    for t in teams:
        assert (t["skaters"] + t["goalies"]) >= 1
    # Ordering: by (skaters+goalies) desc, then abbrev asc
    sorted_check = sorted(teams, key=lambda t: (-(t["skaters"] + t["goalies"]), t["abbrev"]))
    assert teams == sorted_check


def test_last_night_games_completed_matches_schedule() -> None:
    """ADR-037 Fix 6: gameWeek filtered to dataDate first."""
    out = _call_build()
    # 2026-10-09 had 4 completed reg-season games (verified during fixture capture)
    assert out["lastNight"]["gamesCompleted"] == 4


def test_last_night_inclusion_rule_points_ge_1_or_starter() -> None:
    """ADR-012: Finn skater with points >= 1 or Finn goalie who started."""
    out = _call_build()
    for s in out["lastNight"]["skaters"]:
        assert (s.get("p") or 0) >= 1
    # Any FIN goalie listed must have started
    for g in out["lastNight"]["goalies"]:
        assert "saves" in g  # starter fields present


def test_unit_guards() -> None:
    out = _call_build()
    for s in out["skaters"]:
        assert isinstance(s["firstName"], dict) and isinstance(s["lastName"], dict)
        assert s["toiPerGame"] is None or isinstance(s["toiPerGame"], int)
        for k in ("shootingPct", "faceoffPct"):
            v = s[k]
            assert v is None or (0.0 <= v <= 1.0), f"{k}={v}"
    for g in out["goalies"]:
        assert isinstance(g["firstName"], dict) and isinstance(g["lastName"], dict)
        assert g["toi"] is None or isinstance(g["toi"], int)
        assert g["svPct"] is None or (0.0 <= g["svPct"] <= 1.0)


def test_player_missing_from_summary_keeps_row() -> None:
    """ADR-035 join resilience: a Finn removed from summary → row kept, stats None."""
    sm_full = _load("skater-summary-FIN__20262027__2026-10-10.json.gz")
    # Remove one Finn (first row) by shrinking the data array
    sm_mut = copy.deepcopy(sm_full)
    removed_pid = sm_mut["data"][0]["playerId"]
    sm_mut["data"] = sm_mut["data"][1:]
    sm_mut["total"] = len(sm_mut["data"])  # keep total consistent so check_complete passes
    # Write a temp copy into fixtures for the test
    tmp = FX / "_tmp_skater-summary-FIN-missing.json.gz"
    tmp.write_bytes(gzip.compress(json.dumps(sm_mut).encode()))
    try:
        out = _call_build(summary_name=tmp.name)
        row = next((s for s in out["skaters"] if s["playerId"] == removed_pid), None)
        assert row is not None, "row must stay even if summary drops the player"
        # Stats from summary are None; row still has bios-derived fields
        assert row["gp"] is None
        assert row["g"] is None
        assert row["p"] is None
    finally:
        tmp.unlink()


def test_name_suffix_mismatch_raises() -> None:
    """ADR-037 Fix 4 step 3: `*FullName` doesn't end with ' ' + lastName → raise."""
    full = _load("skater-bios-FIN__20262027__p0__2026-10-10.json.gz")
    # Pick the first Finn not covered by any club-stats fixture — flip a lastName so the
    # suffix check fails. We also need to ensure step 1 (club-stats scan) misses this player,
    # which happens because we're testing a synthetic row with a new playerId.
    mut = copy.deepcopy(full)
    mut["data"].append(
        {
            "playerId": 9999999,
            "skaterFullName": "Mikko Testaaja",
            "lastName": "ValidLastButSuffixMismatch",  # suffix won't match
            "currentTeamAbbrev": "TBL",
            "positionCode": "C",
            "nationalityCode": "FIN",
            "firstSeasonForGameType": "20262027",
        }
    )
    mut["total"] = len(mut["data"])
    with pytest.raises(NameSuffixMismatch):
        _call_build(bios_sk_pages=[mut])
