"""Handler orchestration tests. Preserves init-02 guards and adds PRP-03 flow coverage."""

from __future__ import annotations

import gzip
import json
import pathlib
from datetime import UTC, datetime
from typing import Any

import pytest

from kiekkokeskus import __version__
from kiekkokeskus import handler as handler_mod
from kiekkokeskus.handler import handler

FX = pathlib.Path(__file__).parent / "fixtures"


class FakePut:
    """5-arg PutObject matching archive.PutObject."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, bytes, str, str, str | None]] = []

    def __call__(
        self,
        key: str,
        body: bytes,
        content_type: str,
        cache_control: str,
        content_encoding: str | None,
    ) -> None:
        self.calls.append((key, body, content_type, cache_control, content_encoding))


FIXED_NOW = datetime(2026, 10, 3, 14, 0, 12, tzinfo=UTC)


def _load_fixture(name: str) -> bytes:
    return gzip.decompress((FX / name).read_bytes())


class FakeFetchResult:
    def __init__(self, body: bytes, url: str, status: int = 200, attempts: int = 1) -> None:
        self.body = body
        self.url = url
        self.final_url = url
        self.status = status
        self.attempts = attempts
        self.headers = {}


def _make_fetch(mapping: dict[str, bytes | Exception], default: bytes | None = None):
    """URL → body (or Exception). Partial-match on substring; longest key wins."""
    ordered = sorted(mapping.items(), key=lambda kv: len(kv[0]), reverse=True)

    def fetch_fn(url: str, **_: Any) -> FakeFetchResult:
        for u, v in ordered:
            if u in url:
                if isinstance(v, Exception):
                    raise v
                return FakeFetchResult(v, url)
        if default is not None:
            return FakeFetchResult(default, url)
        raise AssertionError(f"no fake for url: {url}")

    return fetch_fn


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BUCKET", "jurigregg-static-site")
    monkeypatch.setenv("PREFIX", "data/kiekkokeskus/")


# --- init-02 guards preserved -----------------------------------------------


def test_force_error_still_raises_before_any_put() -> None:
    put = FakePut()
    with pytest.raises(RuntimeError, match="forced error"):
        handler(
            {"forceError": True},
            None,
            put=put,
            now=lambda: FIXED_NOW,
            fetch_fn=lambda *_a, **_k: None,
        )
    assert put.calls == []


def test_default_now_path_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guards against the `_now_default()` parens bug: default-callable path must execute."""
    # Smoke: inject fetch to short-circuit, don't inject now → exercises default callable
    put = FakePut()
    with pytest.raises(RuntimeError):
        # Season will be unresolved on empty schedule+standings → raises after manifest write
        handler(
            {"date": "2026-10-03"},
            None,
            put=put,
            fetch_fn=_make_fetch(
                {"schedule": b'{"gameWeek":[]}', "standings": b'{"standings":[]}'}
            ),
        )
    # manifest exists with proper ISO-8601 generatedAt-style strings in startedAt
    manifest_calls = [c for c in put.calls if c[0].endswith("_manifest.json")]
    assert manifest_calls, "manifest must be written on failure"
    manifest = json.loads(manifest_calls[0][1])
    assert manifest["startedAt"].endswith("Z")


# --- happy-path: real fixtures end-to-end -----------------------------------


def test_happy_path_writes_raw_manifest_and_health() -> None:
    sched_body = _load_fixture("schedule__2026-10-01__2026-10-03.json.gz")
    st_body = _load_fixture("standings__2026-10-01__2026-10-03.json.gz")
    box_body = _load_fixture("boxscore__2026020010__2026-10-03.json.gz")
    skaters_body = _load_fixture("skater-bios-FIN__20262027__p0__2026-10-03.json.gz")
    goalies_body = _load_fixture("goalie-bios-FIN__20262027__p0__2026-10-03.json.gz")
    # Stand-ins for club-schedule and club-stats (not tested here, just need valid payloads)
    stub = b'{"ok": true, "games": []}'

    put = FakePut()
    # 2026-10-01 schedule has 8 completed reg-season games; stub boxscores for all of them.
    # The specific body for the Tolvanen game (2026020010) is checked below.
    fetch_fn = _make_fetch(
        {
            "schedule/2026-10-01": sched_body,
            "standings/2026-10-01": st_body,
            "club-schedule-season/TBL": stub,
            "club-stats/TBL": stub,
            "gamecenter/2026020010/boxscore": box_body,
            "gamecenter/": b'{"ok": true}',  # catches the other 7 boxscores
            "skater/bios": skaters_body,
            "goalie/bios": goalies_body,
        }
    )

    result = handler(
        {"date": "2026-10-01", "source": "scheduled"},
        None,
        put=put,
        now=lambda: FIXED_NOW,
        fetch_fn=fetch_fn,
    )
    assert result["status"] == "ok"

    # Every raw key under raw/{runDate}/ except _health
    keys = [c[0] for c in put.calls]
    assert all(k.startswith("data/kiekkokeskus/") for k in keys)
    non_raw = [k for k in keys if not k.startswith("data/kiekkokeskus/raw/")]
    assert non_raw == ["data/kiekkokeskus/_health.json"]

    # 2 (schedule+standings) + 2 (club x2) + 8 (boxscores) + 1 (skater) + 1 (goalie) = 14
    raw_keys = [
        k
        for k in keys
        if k.startswith("data/kiekkokeskus/raw/") and not k.endswith("_manifest.json")
    ]
    assert len(raw_keys) == 14
    assert any(k.endswith("schedule__2026-10-01.json.gz") for k in raw_keys)
    assert any(k.endswith("standings__2026-10-01.json.gz") for k in raw_keys)
    assert any("boxscore__2026020010" in k for k in raw_keys)
    assert sum(1 for k in raw_keys if "boxscore__" in k) == 8

    # Raw objects are gzipped and advertise it
    sched_call = next(c for c in put.calls if c[0].endswith("schedule__2026-10-01.json.gz"))
    assert sched_call[4] == "gzip"
    assert gzip.decompress(sched_call[1]) == sched_body

    # Manifest exists, written exactly once, on success
    manifest_calls = [c for c in put.calls if c[0].endswith("_manifest.json")]
    assert len(manifest_calls) == 1
    manifest = json.loads(manifest_calls[0][1])
    assert manifest["schemaVersion"] == 1
    assert manifest["season"] == "20262027"
    assert manifest["trigger"] == "schedule"
    assert manifest["dataDate"] == "2026-10-01"
    assert all(r["error"] is None for r in manifest["requests"])
    assert all(r["status"] == 200 for r in manifest["requests"])

    # Health has dataDate + rawCount, schemaVersion stays 1
    health_call = next(c for c in put.calls if c[0].endswith("_health.json"))
    health = json.loads(health_call[1])
    assert health["schemaVersion"] == 1
    assert health["trigger"] == "schedule"
    assert health["dataDate"] == "2026-10-01"
    assert health["rawCount"] == 14
    assert health["version"] == __version__


# --- season fallback via standings (ADR-033) --------------------------------


def test_season_fallback_via_standings_when_schedule_empty_for_data_date() -> None:
    """Schedule has an entry for data_date but no games — fall back to standings."""
    # Craft a schedule payload where gameWeek has data_date with empty games
    sched_payload = {
        "gameWeek": [
            {"date": "2026-10-01", "games": []},
            {"date": "2026-10-02", "games": []},
        ]
    }
    sched_body = json.dumps(sched_payload).encode()
    st_body = _load_fixture("standings__2026-10-01__2026-10-03.json.gz")
    stub = b'{"ok": true}'

    put = FakePut()
    fetch_fn = _make_fetch(
        {
            "schedule/2026-10-01": sched_body,
            "standings/2026-10-01": st_body,
            "club-schedule-season/TBL": stub,
            "club-stats/TBL": stub,
            "skater/bios": b'{"data":[],"total":0}',
            "goalie/bios": b'{"data":[],"total":0}',
        }
    )
    result = handler(
        {"date": "2026-10-01"}, None, put=put, now=lambda: FIXED_NOW, fetch_fn=fetch_fn
    )
    assert result["status"] == "ok"

    manifest = next(json.loads(c[1]) for c in put.calls if c[0].endswith("_manifest.json"))
    assert manifest["season"] == "20262027"  # from standings
    assert manifest["requests"][0]["slug"] == "schedule__2026-10-01"
    assert manifest["requests"][1]["slug"] == "standings__2026-10-01"


# --- both-missing: schedule+standings yield no season -----------------------


def test_both_missing_writes_manifest_with_null_season_and_no_health() -> None:
    sched_body = json.dumps({"gameWeek": []}).encode()
    st_body = json.dumps({"standings": []}).encode()
    put = FakePut()
    fetch_fn = _make_fetch({"schedule": sched_body, "standings": st_body})

    with pytest.raises(RuntimeError, match="season"):
        handler({"date": "2026-10-01"}, None, put=put, now=lambda: FIXED_NOW, fetch_fn=fetch_fn)

    keys = [c[0] for c in put.calls]
    assert "data/kiekkokeskus/_health.json" not in keys  # health NOT written
    manifest_calls = [c for c in put.calls if c[0].endswith("_manifest.json")]
    assert len(manifest_calls) == 1
    manifest = json.loads(manifest_calls[0][1])
    assert manifest["season"] is None
    assert any("season" in (r["error"] or "") for r in manifest["requests"])


# --- fetch error on a required endpoint -------------------------------------


def test_fetch_failure_records_error_and_prevents_health() -> None:
    """A standings fetch error after season is known: run still fails loudly, no _health."""
    sched_body = _load_fixture("schedule__2026-10-01__2026-10-03.json.gz")
    put = FakePut()
    fetch_fn = _make_fetch(
        {
            "schedule/2026-10-01": sched_body,
            "standings/2026-10-01": RuntimeError("gave up after 3 attempts"),
            "club-schedule-season/TBL": b'{"ok":true}',
            "club-stats/TBL": b'{"ok":true}',
            "boxscore/2026020010": b'{"ok":true}',
            "gamecenter/2026020010": b'{"ok":true}',
            "skater/bios": b'{"data":[],"total":0}',
            "goalie/bios": b'{"data":[],"total":0}',
        }
    )
    with pytest.raises(RuntimeError, match="errored requests"):
        handler({"date": "2026-10-01"}, None, put=put, now=lambda: FIXED_NOW, fetch_fn=fetch_fn)

    keys = [c[0] for c in put.calls]
    assert "data/kiekkokeskus/_health.json" not in keys
    manifest = next(json.loads(c[1]) for c in put.calls if c[0].endswith("_manifest.json"))
    standings_row = next(r for r in manifest["requests"] if r["slug"] == "standings__2026-10-01")
    assert standings_row["error"] == "gave up after 3 attempts"
    assert standings_row["bytes"] == 0


# --- raw-before-parse (ADR-006) ---------------------------------------------


def test_raw_schedule_stored_even_if_parser_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    sched_body = _load_fixture("schedule__2026-10-01__2026-10-03.json.gz")

    def exploding_extract(*_a, **_k):
        raise ValueError("boom in parse.schedule")

    monkeypatch.setattr(handler_mod.sched_parse, "extract", exploding_extract)
    put = FakePut()
    fetch_fn = _make_fetch({"schedule/2026-10-01": sched_body})
    with pytest.raises(ValueError, match="boom"):
        handler({"date": "2026-10-01"}, None, put=put, now=lambda: FIXED_NOW, fetch_fn=fetch_fn)

    # The schedule raw object was already stored before the parser was called.
    raw_sched = [c for c in put.calls if c[0].endswith("schedule__2026-10-01.json.gz")]
    assert len(raw_sched) == 1
    assert gzip.decompress(raw_sched[0][1]) == sched_body
