"""Layer-2 golden test for build_bolts.

The golden fixture is produced from the real captured payloads + a fixed `now_iso` and
`data_date`. To regenerate it after an intentional change: `UPDATE_GOLDEN=1 pytest`.
Review the diff like code before committing.
"""

from __future__ import annotations

import gzip
import json
import os
import pathlib
from datetime import date

from kiekkokeskus.build_bolts import build

FX = pathlib.Path(__file__).parent / "fixtures"
GOLDEN = pathlib.Path(__file__).parent / "golden" / "bolts.json"

DATA_DATE = date(2026, 10, 8)
SEASON = "20262027"
NOW_ISO = "2026-10-09T14:00:12Z"


def _load(name: str) -> dict:
    return json.loads(gzip.decompress((FX / name).read_bytes()))


def _call_build(
    *,
    club_stats_name: str = "club-stats-TBL__20262027__2__2026-10-09.json.gz",
    realtime_name: str = "skater-realtime-TBL__20262027__2026-10-09.json.gz",
) -> dict:
    return build(
        data_date=DATA_DATE,
        season=SEASON,
        now_iso=NOW_ISO,
        standings_payload=_load("standings__2026-10-08__2026-10-09.json.gz"),
        club_stats_payload=_load(club_stats_name),
        club_schedule_payload=_load("club-schedule-season-TBL__20262027__2026-10-09.json.gz"),
        skater_summary_payload=_load("skater-summary-TBL__20262027__2026-10-09.json.gz"),
        skater_realtime_payload=_load(realtime_name),
        skater_faceoff_payload=_load("skater-faceoff-TBL__20262027__2026-10-09.json.gz"),
        team_summary_payload=_load("team-summary__20262027__2026-10-09.json.gz"),
    )


def test_golden_matches() -> None:
    """Compare canonical JSON — stable sort order and no whitespace."""
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
    assert out["dataDate"] == "2026-10-08"
    assert out["season"] == SEASON


def test_team_section() -> None:
    out = _call_build()
    assert out["team"]["abbrev"] == "TBL"
    assert isinstance(out["team"]["name"], dict), "ADR-018"
    assert "default" in out["team"]["name"]


def test_standing_signed_gaps() -> None:
    """ADR-036: divisionLead.gap and playoffLine.gap are signed ints, never abs()."""
    out = _call_build()
    assert isinstance(out["standing"]["divisionLead"]["gap"], int)
    assert isinstance(out["standing"]["playoffLine"]["gap"], int)
    # TBL is Atlantic #2 today → in position, gap could be 0 or positive cushion
    assert out["standing"]["playoffLine"]["inPosition"] is True


def test_last_game_shape() -> None:
    out = _call_build()
    g = out["lastGame"]
    if g is None:
        return  # season may not have started before data_date in some fixtures
    assert isinstance(g["gameId"], int)
    assert g["result"] in {"W", "L", "OTL"}
    assert g["decidedIn"] in {"REG", "OT", "SO", None}
    assert isinstance(g["home"], bool)
    assert isinstance(g["opponent"]["name"], dict)


def test_next_games_up_to_3_and_future() -> None:
    out = _call_build()
    assert len(out["nextGames"]) <= 3
    for g in out["nextGames"]:
        assert g["date"] > "2026-10-08"


def test_special_teams_fractions_and_ranks() -> None:
    out = _call_build()
    st = out["specialTeams"]
    for k in ("ppPct", "pkPct"):
        v = st[k]
        assert v is None or (0.0 <= v <= 1.0), f"{k}={v} not a fraction"
    for k in ("ppRank", "pkRank"):
        v = st[k]
        assert v is None or (1 <= v <= 32)


def test_skaters_full_rows_and_units() -> None:
    """Unit guards: every fraction ∈ [0,1] ∪ {None}; every TOI is int; names localized."""
    out = _call_build()
    skaters = out["skaters"]
    assert len(skaters) == 20
    for s in skaters:
        assert isinstance(s["firstName"], dict) and isinstance(s["lastName"], dict)
        assert s["toiPerGame"] is None or isinstance(s["toiPerGame"], int)
        for k in ("shootingPct", "faceoffPct"):
            v = s[k]
            assert v is None or (0.0 <= v <= 1.0), f"{k}={v}"


def test_faceoff_pct_null_when_total_faceoffs_zero() -> None:
    """ADR-035 rule: zero attempts → None (D-men typically)."""
    out = _call_build()
    # At least one skater should have faceoffPct=None (verified: 12/20 have 0 attempts today)
    nones = [s for s in out["skaters"] if s["faceoffPct"] is None]
    assert nones, "expected at least one skater with faceoffPct=None"
    # Spot-check: a D-position player has None
    dmen_none = [s for s in nones if s["positionCode"] == "D"]
    assert dmen_none, "expected at least one defenseman with faceoffPct=None"


def test_goalies_rows() -> None:
    out = _call_build()
    goalies = out["goalies"]
    assert len(goalies) == 2
    for g in goalies:
        assert g["toi"] is None or isinstance(g["toi"], int)
        assert g["svPct"] is None or (0.0 <= g["svPct"] <= 1.0)


def test_player_missing_from_realtime_keeps_row_with_null_hits() -> None:
    """ADR-035 join resilience: dropped from realtime → row kept, hits/blocks=None."""
    out = _call_build(
        realtime_name="skater-realtime-TBL__20262027__2026-10-09__player-missing.json.gz",
    )
    # The removed playerId from the variant builder = 8476453
    row = next((s for s in out["skaters"] if s["playerId"] == 8476453), None)
    assert row is not None, "club-stats skater must remain even if missing from realtime"
    assert row["hits"] is None
    assert row["blocks"] is None


def test_goalie_no_shots_variant() -> None:
    """ADR-015 null handling for a 0-shots goalie's percentages."""
    out = _call_build(
        club_stats_name="club-stats-TBL__20262027__2__2026-10-09__goalie-no-shots.json.gz",
    )
    g0 = out["goalies"][0]
    assert g0["svPct"] is None
    assert g0["gaa"] is None
