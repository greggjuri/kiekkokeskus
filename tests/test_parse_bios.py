"""Layer-1 bios parser tests. Covers ADR-010 (Finn), ADR-011 (pagination, no dedupe)."""

from __future__ import annotations

import copy
import gzip
import json
import pathlib

import pytest

from kiekkokeskus.parse import bios
from kiekkokeskus.parse.bios import BiosDuplicateError

FX = pathlib.Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads(gzip.decompress((FX / name).read_bytes()))


SK = "skater-bios-FIN__20262027__p0__2026-10-10.json.gz"
GO = "goalie-bios-FIN__20262027__p0__2026-10-10.json.gz"


def test_merged_single_page_skaters_and_goalies() -> None:
    sk = _load(SK)
    go = _load(GO)
    result = bios.merged([sk], [go])
    assert len(result["skaters"]) == 30
    assert len(result["goalies"]) == 5
    # Keys are int playerIds
    for pid in result["skaters"]:
        assert isinstance(pid, int)


def test_kapanen_included_as_finn() -> None:
    """ADR-010: nationalityCode `FIN` wins over birthCountryCode `SWE`."""
    sk = _load(SK)
    result = bios.merged([sk], [])
    # Kasperi Kapanen (EDM today) — look up by last name since playerId varies
    kapanen = next(
        (r for r in result["skaters"].values() if r.get("lastName") == "Kapanen"),
        None,
    )
    assert kapanen is not None, "Kapanen must be in the FIN bios set"
    assert kapanen["nationalityCode"] == "FIN"


def test_multi_page_merge() -> None:
    """Simulated 2-page split merges, no dupes."""
    full = _load(SK)
    half = len(full["data"]) // 2
    page1 = {"data": full["data"][:half], "total": full["total"]}
    page2 = {"data": full["data"][half:], "total": full["total"]}
    result = bios.merged([page1, page2], [])
    assert len(result["skaters"]) == len(full["data"])


def test_duplicate_player_id_across_pages_raises() -> None:
    """ADR-011: a duplicate across pages is a payload surprise, not a silent dedupe."""
    full = _load(SK)
    page1 = {"data": full["data"][:5], "total": full["total"]}
    # Second page re-includes one of page1's rows
    page2 = {"data": [full["data"][2]] + full["data"][5:10], "total": full["total"]}
    with pytest.raises(BiosDuplicateError, match="duplicate playerId"):
        bios.merged([page1, page2], [])


def test_merge_does_not_mutate_inputs() -> None:
    full = _load(SK)
    before = copy.deepcopy(full)
    bios.merged([full], [])
    assert full == before


def test_rows_without_player_id_are_skipped() -> None:
    """Defensive: a payload row missing `playerId` is dropped (no KeyError)."""
    payload = {"data": [{"playerId": 1}, {"lastName": "orphan"}], "total": 2}
    result = bios.merged([payload], [])
    assert set(result["skaters"].keys()) == {1}
