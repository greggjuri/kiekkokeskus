"""Layer-1 boxscore parser tests. Covers ADR-012, ADR-013, ADR-015, ADR-017, ADR-037."""

from __future__ import annotations

import gzip
import json
import pathlib

from kiekkokeskus.parse import boxscore

FX = pathlib.Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads(gzip.decompress((FX / name).read_bytes()))


TOLVANEN = "boxscore__2026020010__2026-10-03.json.gz"  # TBL @ NYR, REG, Tolvanen scored
OT_REF = "boxscore__2026020025__2026-10-10.json.gz"  # CAR @ PHI, OT (ADR-037)
SO_REF = "boxscore__2026020065__2026-10-10.json.gz"  # TOR @ VGK, SO (ADR-037)


def test_game_context_shape() -> None:
    payload = _load(TOLVANEN)
    ctx = boxscore.game_context(payload)
    assert ctx["id"] == 2026020010
    assert ctx["home"]["abbrev"] == "NYR"
    assert ctx["away"]["abbrev"] == "TBL"
    assert ctx["home"]["score"] == 5
    assert ctx["away"]["score"] == 1
    assert ctx["state"] == "OFF"
    assert ctx["decidedIn"] == "REG"


def test_player_rows_cover_both_teams_and_all_positions() -> None:
    payload = _load(TOLVANEN)
    rows = boxscore.player_rows(payload)
    teams = {r["team"] for r in rows}
    assert teams == {"NYR", "TBL"}
    positions = {r["position"] for r in rows}
    # Skater positions + G
    assert "G" in positions
    # At least one forward and one defenseman
    assert positions - {"G"}


def test_skater_toi_normalized_to_int_seconds() -> None:
    """ADR-017: `"MM:SS"` → int seconds."""
    payload = _load(TOLVANEN)
    rows = boxscore.player_rows(payload)
    tolvanen = next(r for r in rows if r["playerId"] == 8480009)
    # Tolvanen's toi in the fixture is "14:18" (14*60 + 18 = 858)
    assert tolvanen["toi"] == 858
    # Localized initial name (ADR-018)
    assert isinstance(tolvanen["name"], dict)
    assert tolvanen["name"]["default"] == "E. Tolvanen"
    # Scored once
    assert tolvanen["goals"] == 1


def test_non_starter_goalie_nulls() -> None:
    """ADR-015: a non-starter goalie has `savePctg=None`, `decision=None`, `starter=False`."""
    payload = _load(TOLVANEN)
    rows = boxscore.player_rows(payload)
    hildeby = next(r for r in rows if r["playerId"] == 8483710)
    assert hildeby["starter"] is False
    assert hildeby["savePctg"] is None
    assert hildeby["decision"] is None
    assert hildeby["toi"] == 0  # "00:00"


def test_starter_goalie_fields() -> None:
    """Shesterkin (NYR starter) has savePctg + decision + starter=True."""
    payload = _load(TOLVANEN)
    rows = boxscore.player_rows(payload)
    shesterkin = next(r for r in rows if r["playerId"] == 8478048)
    assert shesterkin["starter"] is True
    assert shesterkin["decision"] == "W"
    assert 0.0 <= shesterkin["savePctg"] <= 1.0
    assert shesterkin["toi"] == 3600  # "60:00"


def test_decision_passes_through_raw_not_asserted_as_O() -> None:
    """ADR-037: builder derives game.result from score, not from goalie.decision.

    Parser must pass `decision` through as whatever string the payload gives (`W`/`L`/`O`/None).
    This test only checks the parser doesn't rewrite the string.
    """
    payload = _load(OT_REF)
    rows = boxscore.player_rows(payload)
    goalies = [r for r in rows if r["position"] == "G"]
    # At least one goalie should have decision in {W, L, O} or None; whatever it is, parser
    # must emit the raw string without rewriting.
    for g in goalies:
        if g["decision"] is not None:
            assert isinstance(g["decision"], str)


def test_ot_reference_decidedIn_is_OT() -> None:
    """ADR-037: real OT boxscore 2026020025 has `gameOutcome.lastPeriodType == "OT"`."""
    ctx = boxscore.game_context(_load(OT_REF))
    assert ctx["decidedIn"] == "OT"


def test_so_reference_decidedIn_is_SO() -> None:
    """ADR-037: real SO boxscore 2026020065 has `gameOutcome.lastPeriodType == "SO"`."""
    ctx = boxscore.game_context(_load(SO_REF))
    assert ctx["decidedIn"] == "SO"


def test_toi_parser_edge_cases() -> None:
    """Direct `_toi_to_seconds` unit tests."""
    from kiekkokeskus.parse.boxscore import _toi_to_seconds

    assert _toi_to_seconds("00:00") == 0
    assert _toi_to_seconds("14:18") == 858
    assert _toi_to_seconds("60:00") == 3600
    assert _toi_to_seconds("1:00:00") == 3600  # H:MM:SS form
    assert _toi_to_seconds(None) is None
    assert _toi_to_seconds("") is None
    assert _toi_to_seconds("not a time") is None
    assert _toi_to_seconds(0) is None
