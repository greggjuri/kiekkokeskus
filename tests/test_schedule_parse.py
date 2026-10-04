"""Layer-1 parser tests. Fed real fixtures (ADR-033, 013, 014) + the __unknown-state variant."""

from __future__ import annotations

import gzip
import json
import logging
import pathlib
from datetime import date

from kiekkokeskus.parse import schedule as sched_parse
from kiekkokeskus.parse import standings as st_parse

FX = pathlib.Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads(gzip.decompress((FX / name).read_bytes()))


# --- schedule: season extraction (ADR-033) ----------------------------------


def test_season_from_games_on_data_date() -> None:
    payload = _load("schedule-2026-10-01__2026-10-03.json.gz")
    season, _ = sched_parse.extract(payload, date(2026, 10, 1))
    assert season == "20262027"


def test_season_none_when_no_games_on_data_date() -> None:
    """A date beyond the gameWeek yields no games and no season — caller must fall back."""
    payload = _load("schedule-2026-10-01__2026-10-03.json.gz")
    # gameWeek covers 2026-10-01 .. 2026-10-07; pick a date outside it.
    season, ids = sched_parse.extract(payload, date(2026, 10, 20))
    assert season is None
    assert ids == []


# --- schedule: completed reg-season IDs on data_date (ADR-013, 014) ---------


def test_completed_regular_season_ids_only_on_data_date() -> None:
    payload = _load("schedule-2026-10-01__2026-10-03.json.gz")
    _, ids = sched_parse.extract(payload, date(2026, 10, 1))
    assert ids, "expected completed regular-season games on 2026-10-01"
    assert 2026020010 in ids, "TBL @ NYR gameId expected"


def test_preseason_excluded() -> None:
    """2026-09-26 fixture is all gameType=1 FINAL (preseason). Must be excluded."""
    payload = _load("schedule-2026-09-26__2026-10-03.json.gz")
    _, ids = sched_parse.extract(payload, date(2026, 9, 26))
    assert ids == []


def test_fut_excluded() -> None:
    """2026-12-15 fixture has gameType=2 but gameState=FUT. Must be excluded."""
    payload = _load("schedule-2026-12-15__2026-10-03.json.gz")
    _, ids = sched_parse.extract(payload, date(2026, 12, 15))
    assert ids == []


def test_unknown_state_logged_and_skipped(caplog) -> None:
    """ADR-013 variant: one game's gameState mutated to XYZ. Log, don't crash."""
    payload = _load("schedule-2026-10-01__2026-10-03__unknown-state.json.gz")
    with caplog.at_level(logging.WARNING, logger="kiekkokeskus.parse.schedule"):
        _, ids = sched_parse.extract(payload, date(2026, 10, 1))
    # XYZ game (2026020009) is excluded
    assert 2026020009 not in ids
    # Other completed games still returned
    assert 2026020010 in ids
    assert any("unknown_game_state" in rec.message for rec in caplog.records)


# --- standings season fallback (ADR-033) ------------------------------------


def test_standings_season_id_present() -> None:
    payload = _load("standings-2026-10-02__2026-10-03.json.gz")
    assert st_parse.season_id(payload) == "20262027"


def test_standings_season_id_old_season() -> None:
    payload = _load("standings-2026-04-01__2026-10-03.json.gz")
    assert st_parse.season_id(payload) == "20252026"


def test_standings_season_id_none_when_empty() -> None:
    assert st_parse.season_id({"standings": []}) is None
    assert st_parse.season_id({}) is None
