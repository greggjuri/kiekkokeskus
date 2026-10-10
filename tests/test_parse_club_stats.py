"""Layer-1 club-stats parser tests. Covers ADR-015/017/018."""

from __future__ import annotations

import gzip
import json
import pathlib

from kiekkokeskus.parse import club_stats

FX = pathlib.Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads(gzip.decompress((FX / name).read_bytes()))


FIXTURE = "club-stats-TBL__20262027__2__2026-10-09.json.gz"
VARIANT = "club-stats-TBL__20262027__2__2026-10-09__goalie-no-shots.json.gz"


def test_skaters_count_and_names_localized() -> None:
    payload = _load(FIXTURE)
    rows = club_stats.skaters(payload)
    assert len(rows) == 20
    s0 = rows[0]
    assert isinstance(s0["firstName"], dict), "ADR-018: names stay localized objects"
    assert "default" in s0["firstName"]
    assert isinstance(s0["lastName"], dict)


def test_toi_normalized_to_int_seconds() -> None:
    """ADR-017: `avgTimeOnIcePerGame` is float seconds; we store int seconds."""
    payload = _load(FIXTURE)
    rows = club_stats.skaters(payload)
    for s in rows:
        toi = s.get("toiPerGame")
        assert toi is None or isinstance(toi, int)


def test_headshot_dropped() -> None:
    """ADR-003: no NHL image URLs in our output."""
    payload = _load(FIXTURE)
    for s in club_stats.skaters(payload):
        assert "headshot" not in s


def test_zero_shots_shooting_pct_is_none() -> None:
    """ADR-015: a player with 0 shots gets `shootingPctg=None`, not 0.0."""
    payload = _load(FIXTURE)
    rows = club_stats.skaters(payload)
    for s in rows:
        if s.get("shots") in (None, 0):
            assert s.get("shootingPctg") is None


def test_goalies_use_overtime_losses_name() -> None:
    """The NHL field is `overtimeLosses`; we normalize to `otLosses`."""
    payload = _load(FIXTURE)
    goalies = club_stats.goalies(payload)
    assert len(goalies) == 2
    for g in goalies:
        # otLosses present (int or None); the raw NHL `otLosses` was unreliable
        assert "otLosses" in g


def test_goalie_toi_is_int_total_seconds() -> None:
    payload = _load(FIXTURE)
    for g in club_stats.goalies(payload):
        toi = g.get("timeOnIce")
        assert toi is None or isinstance(toi, int)
    # The verification showed `timeOnIce=10552` for Vasilevskiy — a 4-digit int (not 0.9x hours).
    first_toi = club_stats.goalies(payload)[0].get("timeOnIce")
    assert first_toi is None or first_toi > 100, "expected total-seconds, not minutes"


def test_variant_goalie_no_shots_nulls_svpct_and_gaa() -> None:
    """ADR-015: a goalie whose savePercentage / goalsAgainstAverage are absent → None."""
    payload = _load(VARIANT)
    goalies = club_stats.goalies(payload)
    # The mutated goalie is goalies[0]
    assert goalies[0]["savePercentage"] is None
    assert goalies[0]["goalsAgainstAverage"] is None


def test_skater_faceoffWinPctg_passed_through_raw() -> None:
    """Raw value passes through; builder resolves `faceoffPct` via totalFaceoffs (ADR-035)."""
    payload = _load(FIXTURE)
    rows = club_stats.skaters(payload)
    # Confirm the field name is preserved
    assert "faceoffWinPctg" in rows[0]
