"""Layer-1 standings parser tests. Covers ADR-015, ADR-033 (season_id), ADR-036."""

from __future__ import annotations

import gzip
import json
import pathlib

from kiekkokeskus.parse import standings

FX = pathlib.Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads(gzip.decompress((FX / name).read_bytes()))


def test_rows_returns_32_teams() -> None:
    payload = _load("standings__2026-10-08__2026-10-09.json.gz")
    rows = standings.rows(payload)
    assert len(rows) == 32
    assert all(r.get("team") for r in rows), "every row must have a teamAbbrev"


def test_team_abbrev_is_flattened_string() -> None:
    payload = _load("standings__2026-10-08__2026-10-09.json.gz")
    rows = standings.rows(payload)
    tbl = standings.by_team(rows, "TBL")
    assert tbl is not None
    assert isinstance(tbl["team"], str)
    assert tbl["team"] == "TBL"
    assert isinstance(tbl["teamName"], dict), "teamName stays localized (ADR-018)"
    assert "default" in tbl["teamName"]


def test_missing_fields_become_none_at_0_gp() -> None:
    """ADR-015: 0-GP teams omit pointPctg / streakCode / streakCount etc."""
    # 2026-10-02 is before OTT played its opener on 2026-10-07; expect at least one 0-GP team.
    payload = _load("standings__2026-10-02__2026-10-03.json.gz")
    rows = standings.rows(payload)
    zero_gp = [r for r in rows if r.get("gamesPlayed") == 0]
    assert zero_gp, "fixture expected to contain at least one 0-GP team"
    r = zero_gp[0]
    assert r.get("pointPctg") is None
    assert r.get("streakCode") is None
    assert r.get("streakCount") is None


def test_division_leader() -> None:
    payload = _load("standings__2026-10-08__2026-10-09.json.gz")
    rows = standings.rows(payload)
    tbl = standings.by_team(rows, "TBL")
    assert tbl is not None
    leader = standings.division_leader(rows, tbl["divisionAbbrev"])
    assert leader is not None
    assert leader["divisionSequence"] == 1


def test_playoff_line_in_position_uses_wildcard3() -> None:
    """For a division top-3 team, reference team is conference wildcardSequence==3."""
    payload = _load("standings__2026-10-08__2026-10-09.json.gz")
    rows = standings.rows(payload)
    # Pick a division top-3 team (TBL today is Atlantic #2)
    pl = standings.playoff_line(rows, "TBL")
    assert pl is not None
    assert pl["inPosition"] is True
    # ref is the "wildcardSequence==3" team in TBL's conference
    conf = standings.by_team(rows, "TBL")["conferenceAbbrev"]
    ref_pts = next(
        r["points"] for r in rows if r["conferenceAbbrev"] == conf and r["wildcardSequence"] == 3
    )
    assert pl["teamPts"] == ref_pts


def test_playoff_line_out_of_position_uses_wildcard2() -> None:
    """Out-of-position: reference team is conference wildcardSequence==2.

    Construct a minimal synthetic standings payload rather than hunting for an out-of-position
    team in today's data (TBL is in-position).
    """
    payload = {
        "standings": [
            # In-focus team: out of playoff position
            {
                "teamAbbrev": {"default": "ZZZ"},
                "teamName": {"default": "Zed"},
                "gamesPlayed": 5,
                "wins": 1,
                "losses": 4,
                "otLosses": 0,
                "points": 2,
                "divisionAbbrev": "A",
                "conferenceAbbrev": "E",
                "divisionSequence": 7,
                "conferenceSequence": 15,
                "leagueSequence": 30,
                "wildcardSequence": 5,
            },
            # The wildcard==2 team in the same conference
            {
                "teamAbbrev": {"default": "WC2"},
                "teamName": {"default": "WildCard2"},
                "gamesPlayed": 6,
                "wins": 3,
                "losses": 2,
                "otLosses": 1,
                "points": 7,
                "divisionAbbrev": "A",
                "conferenceAbbrev": "E",
                "divisionSequence": 5,
                "conferenceSequence": 8,
                "leagueSequence": 16,
                "wildcardSequence": 2,
            },
            # A wildcard==3 team should be ignored for an out-of-position team
            {
                "teamAbbrev": {"default": "WC3"},
                "teamName": {"default": "WildCard3"},
                "gamesPlayed": 6,
                "wins": 3,
                "losses": 2,
                "otLosses": 1,
                "points": 7,
                "divisionAbbrev": "A",
                "conferenceAbbrev": "E",
                "divisionSequence": 6,
                "conferenceSequence": 9,
                "leagueSequence": 17,
                "wildcardSequence": 3,
            },
        ]
    }
    rows = standings.rows(payload)
    pl = standings.playoff_line(rows, "ZZZ")
    assert pl is not None
    assert pl["inPosition"] is False
    assert pl["team"] == "WC2"
    assert pl["teamPts"] == 7
    assert pl["gap"] == 5, "deficit = ref.points - team.points = 7 - 2"
    assert pl["gamesInHand"] == 1  # 6 - 5


def test_playoff_line_gap_sign_preserved_at_zero_and_negative() -> None:
    """ADR-036: gap is signed. Equal points → gap=0; crafted tiebreaker → gap<0.

    Synthetic: TBL and the wildcard-3 reference team have equal points (gap=0). Also test a
    case where the reference team has more points — gap would still be shown as signed,
    which can happen with a tiebreaker producing an unexpected order.
    """

    def base(abbrev: str, pts: int, wild: int, divseq: int) -> dict:
        return {
            "teamAbbrev": {"default": abbrev},
            "teamName": {"default": abbrev},
            "gamesPlayed": 5,
            "wins": 2,
            "losses": 2,
            "otLosses": 1,
            "points": pts,
            "divisionAbbrev": "A",
            "conferenceAbbrev": "E",
            "divisionSequence": divseq,
            "conferenceSequence": divseq,
            "leagueSequence": divseq,
            "wildcardSequence": wild,
        }

    # Case 1: TBL is in-position (divSeq=2), ref is wild-3 with equal points → gap==0.
    payload = {"standings": [base("TBL", 5, 0, 2), base("WC3", 5, 3, 6)]}
    rows_a = standings.rows(payload)
    pl_a = standings.playoff_line(rows_a, "TBL")
    assert pl_a["inPosition"] is True
    assert pl_a["gap"] == 0

    # Case 2: TBL is out-of-position (divSeq=7), ref is wild-2 with fewer points than TBL
    # (shouldn't happen under normal ordering, but tests sign preservation).
    payload2 = {"standings": [base("TBL", 10, 5, 7), base("WC2", 7, 2, 5)]}
    rows_b = standings.rows(payload2)
    pl_b = standings.playoff_line(rows_b, "TBL")
    assert pl_b["inPosition"] is False
    assert pl_b["gap"] == -3, "ref.points - team.points = 7 - 10 = -3 (never abs()-ed)"
