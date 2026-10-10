"""Layer-1 club-schedule parser tests. Covers ADR-013 (gameState), ADR-014 (gameType)."""

from __future__ import annotations

import gzip
import json
import pathlib
from datetime import date

from kiekkokeskus.parse import club_schedule

FX = pathlib.Path(__file__).parent / "fixtures"
FIXTURE = "club-schedule-season-TBL__20262027__2026-10-09.json.gz"


def _load(name: str) -> dict:
    return json.loads(gzip.decompress((FX / name).read_bytes()))


def test_filters_to_regular_season_only() -> None:
    """ADR-014: preseason (gameType==1) is excluded."""
    payload = _load(FIXTURE)
    games = club_schedule.games_regular_season(payload, "TBL")
    # Verified during PRP generation: TBL season has 4 preseason + 84 regular
    assert len(games) == 84, f"expected 84 regular-season games, got {len(games)}"


def test_home_away_flip() -> None:
    """Away game: `home=False`; opponent is the home team."""
    payload = _load(FIXTURE)
    games = club_schedule.games_regular_season(payload, "TBL")
    tbl_at_nyr = next(g for g in games if g["gameId"] == 2026020010)
    assert tbl_at_nyr["home"] is False
    assert tbl_at_nyr["opponent"]["abbrev"] == "NYR"
    assert isinstance(tbl_at_nyr["opponent"]["name"], dict), "name is a localized object"
    assert tbl_at_nyr["opponent"]["name"]["default"] == "Rangers"


def test_last_completed_before() -> None:
    """2026-10-08 is yesterday ET; TBL has played some games by then."""
    payload = _load(FIXTURE)
    games = club_schedule.games_regular_season(payload, "TBL")
    g = club_schedule.last_completed_before(games, date(2026, 10, 8))
    assert g is not None
    assert g["state"] in {"OFF", "FINAL"}
    assert g["date"] <= "2026-10-08"
    assert g["result"] in {"W", "L", "OTL"}
    # decidedIn must come from gameOutcome.lastPeriodType
    assert g["decidedIn"] in {"REG", "OT", "SO", None}


def test_last_completed_result_rules() -> None:
    """OT loss → `OTL`; regulation loss → `L`; any-time win → `W`."""
    games = [
        # Reg loss
        {
            "gameId": 1,
            "date": "2026-10-01",
            "home": False,
            "opponent": {"abbrev": "NYR", "name": {"default": "Rangers"}},
            "teamScore": 1,
            "oppScore": 5,
            "state": "OFF",
            "decidedIn": "REG",
            "startTimeUTC": "2026-10-01T23:00:00Z",
        },
        # OT loss
        {
            "gameId": 2,
            "date": "2026-10-03",
            "home": True,
            "opponent": {"abbrev": "FLA", "name": {"default": "Panthers"}},
            "teamScore": 2,
            "oppScore": 3,
            "state": "FINAL",
            "decidedIn": "OT",
            "startTimeUTC": "2026-10-03T23:00:00Z",
        },
        # Win
        {
            "gameId": 3,
            "date": "2026-10-05",
            "home": True,
            "opponent": {"abbrev": "BOS", "name": {"default": "Bruins"}},
            "teamScore": 4,
            "oppScore": 2,
            "state": "OFF",
            "decidedIn": "REG",
            "startTimeUTC": "2026-10-05T23:00:00Z",
        },
    ]
    assert club_schedule.last_completed_before(games, date(2026, 10, 1))["result"] == "L"
    assert club_schedule.last_completed_before(games, date(2026, 10, 3))["result"] == "OTL"
    assert club_schedule.last_completed_before(games, date(2026, 10, 5))["result"] == "W"


def test_last_completed_none_when_no_completed_games_before() -> None:
    games = [
        {
            "gameId": 1,
            "date": "2026-10-10",
            "home": False,
            "opponent": {"abbrev": "NYR", "name": {"default": "Rangers"}},
            "teamScore": None,
            "oppScore": None,
            "state": "FUT",
            "decidedIn": None,
            "startTimeUTC": "2026-10-10T23:00:00Z",
        },
    ]
    assert club_schedule.last_completed_before(games, date(2026, 10, 8)) is None


def test_next_games_after() -> None:
    payload = _load(FIXTURE)
    games = club_schedule.games_regular_season(payload, "TBL")
    nxt = club_schedule.next_games_after(games, date(2026, 10, 8), limit=3)
    assert len(nxt) <= 3
    for g in nxt:
        assert g["date"] > "2026-10-08"
    # Ascending by date
    dates = [g["date"] for g in nxt]
    assert dates == sorted(dates)


def test_fut_games_feed_next_games() -> None:
    """ADR-013: FUT games appear in nextGames; completed games do not."""
    payload = _load(FIXTURE)
    games = club_schedule.games_regular_season(payload, "TBL")
    nxt = club_schedule.next_games_after(games, date(2026, 10, 8), limit=3)
    for g in nxt:
        assert g["state"] not in {"OFF", "FINAL"}, "future list must not contain completed games"
