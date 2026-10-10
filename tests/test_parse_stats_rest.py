"""Layer-1 stats REST parser tests. Covers ADR-035 pagination guard + join helpers."""

from __future__ import annotations

import gzip
import json
import pathlib

import pytest

from kiekkokeskus.parse import stats_rest
from kiekkokeskus.parse.stats_rest import StatsRestTruncated

FX = pathlib.Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads(gzip.decompress((FX / name).read_bytes()))


def test_check_complete_passes_when_total_equals_rows() -> None:
    payload = _load("skater-summary-TBL__20262027__2026-10-09.json.gz")
    stats_rest.check_complete(payload, "skater-summary-TBL__20262027")  # no raise


def test_check_complete_raises_on_truncated() -> None:
    """ADR-035: raise loudly rather than silently truncate."""
    payload = {"data": [{"playerId": 1}], "total": 5}
    with pytest.raises(StatsRestTruncated, match="total=5"):
        stats_rest.check_complete(payload, "slug")


def test_check_complete_noop_when_total_missing() -> None:
    stats_rest.check_complete({"data": [{"playerId": 1}]}, "slug")  # no raise


def test_by_player_id_summary_picks_ppPoints() -> None:
    payload = _load("skater-summary-TBL__20262027__2026-10-09.json.gz")
    idx = stats_rest.by_player_id(payload, ["ppPoints", "shootingPct"])
    assert len(idx) == 20
    # Every indexed value should carry both keys (even if value is None)
    for pid, row in idx.items():
        assert isinstance(pid, int)
        assert "ppPoints" in row
        assert "shootingPct" in row


def test_by_player_id_realtime_picks_hits_blocks() -> None:
    payload = _load("skater-realtime-TBL__20262027__2026-10-09.json.gz")
    idx = stats_rest.by_player_id(payload, ["hits", "blockedShots"])
    assert len(idx) == 20
    for row in idx.values():
        # Ints — may be 0 but should exist (None acceptable per ADR-015)
        assert row["hits"] is None or isinstance(row["hits"], int)
        assert row["blockedShots"] is None or isinstance(row["blockedShots"], int)


def test_by_player_id_faceoff_picks_totalFaceoffs() -> None:
    payload = _load("skater-faceoff-TBL__20262027__2026-10-09.json.gz")
    idx = stats_rest.by_player_id(payload, ["totalFaceoffs", "faceoffWinPct"])
    assert len(idx) == 20
    # Some players (D-men) have 0 faceoffs; faceoffWinPct is None in that case
    zero_face = [row for row in idx.values() if row["totalFaceoffs"] == 0]
    assert zero_face, "expect at least one 0-attempt player (ADR-035)"
    for row in zero_face:
        assert row["faceoffWinPct"] is None


def test_variant_player_missing_from_realtime() -> None:
    """ADR-035 join resilience: one TBL skater pulled from realtime; builder must keep the row."""
    payload = _load("skater-realtime-TBL__20262027__2026-10-09__player-missing.json.gz")
    idx = stats_rest.by_player_id(payload, ["hits", "blockedShots"])
    assert len(idx) == 19  # one less than the base fixture
    # The removed playerId (8476453) must NOT appear
    assert 8476453 not in idx


def test_team_rows_indexes_by_full_name() -> None:
    payload = _load("team-summary__20262027__2026-10-09.json.gz")
    teams = stats_rest.team_rows(payload)
    assert "Tampa Bay Lightning" in teams
    tbl = teams["Tampa Bay Lightning"]
    assert tbl["powerPlayPct"] is not None
    assert 0.0 <= tbl["powerPlayPct"] <= 1.0, "ADR-016 fraction 0-1"
    assert 0.0 <= tbl["penaltyKillPct"] <= 1.0
