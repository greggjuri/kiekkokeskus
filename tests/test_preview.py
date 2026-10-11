"""Preview-server unit tests. The server itself isn't started; we test the pure helpers that
decide what to serve. ADR-003 holds: no network calls."""

from __future__ import annotations

import json
import pathlib

import preview
import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent


# --- resolve_data_path ---


def test_resolve_data_path_maps_bolts():
    out = preview.resolve_data_path(REPO / "tests" / "golden", "/data/kiekkokeskus/bolts.json")
    assert out == REPO / "tests" / "golden" / "bolts.json"


def test_resolve_data_path_maps_leijonat():
    out = preview.resolve_data_path(REPO / "tests" / "golden", "/data/kiekkokeskus/leijonat.json")
    assert out == REPO / "tests" / "golden" / "leijonat.json"


def test_resolve_data_path_unknown_file_returns_none():
    out = preview.resolve_data_path(REPO / "tests" / "golden", "/data/kiekkokeskus/other.json")
    assert out is None


def test_resolve_data_path_outside_prefix_returns_none():
    out = preview.resolve_data_path(REPO / "tests" / "golden", "/kiekkokeskus/kk.css")
    assert out is None


def test_resolve_data_path_honors_data_dir_override(tmp_path: pathlib.Path):
    out = preview.resolve_data_path(tmp_path, "/data/kiekkokeskus/bolts.json")
    assert out == tmp_path / "bolts.json"


# --- transform ---


@pytest.fixture
def sample_bolts() -> bytes:
    payload = {
        "schemaVersion": 1,
        "generatedAt": "2026-10-09T14:00:12Z",
        "dataDate": "2026-10-09",
        "season": "20262027",
        "skaters": [],
    }
    return json.dumps(payload).encode("utf-8")


def test_transform_passthrough_without_flags(sample_bolts: bytes):
    out = preview.transform("bolts.json", sample_bolts, fresh=False, break_=None)
    assert out == sample_bolts


def test_transform_fresh_rewrites_generatedAt(sample_bolts: bytes):
    frozen = "2027-01-01T00:00:00Z"
    out = preview.transform("bolts.json", sample_bolts, fresh=True, break_=None, now_iso=frozen)
    payload = json.loads(out)
    assert payload["generatedAt"] == frozen
    assert payload["schemaVersion"] == 1


def test_transform_break_sets_schemaVersion_999_only_for_named_file(sample_bolts: bytes):
    out = preview.transform("bolts.json", sample_bolts, fresh=False, break_="bolts")
    assert json.loads(out)["schemaVersion"] == 999
    # leijonat untouched when --break bolts
    leijonat = preview.transform("leijonat.json", sample_bolts, fresh=False, break_="bolts")
    assert json.loads(leijonat) == json.loads(sample_bolts)


def test_transform_fresh_and_break_together(sample_bolts: bytes):
    frozen = "2027-01-01T00:00:00Z"
    out = preview.transform("bolts.json", sample_bolts, fresh=True, break_="bolts", now_iso=frozen)
    payload = json.loads(out)
    assert payload["schemaVersion"] == 999
    assert payload["generatedAt"] == frozen


# --- arg parsing ---


def test_parse_args_defaults():
    args = preview._parse_args([])
    assert args.port == 8006
    assert args.fresh is False
    assert args.break_ is None


def test_parse_args_break_choices():
    assert preview._parse_args(["--break", "bolts"]).break_ == "bolts"
    assert preview._parse_args(["--break", "leijonat"]).break_ == "leijonat"
    with pytest.raises(SystemExit):
        preview._parse_args(["--break", "other"])


def test_parse_args_data_override(tmp_path: pathlib.Path):
    args = preview._parse_args(["--data", str(tmp_path)])
    assert args.data == tmp_path
