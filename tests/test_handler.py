from __future__ import annotations

import json
import re
from datetime import UTC, datetime

import pytest

from kiekkokeskus import __version__
from kiekkokeskus.handler import handler


class FakePut:
    def __init__(self) -> None:
        self.calls: list[tuple[str, bytes, str, str]] = []

    def __call__(self, key: str, body: bytes, content_type: str, cache_control: str) -> None:
        self.calls.append((key, body, content_type, cache_control))


FIXED_NOW = datetime(2026, 10, 3, 14, 0, 12, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BUCKET", "jurigregg-static-site")
    monkeypatch.setenv("PREFIX", "data/kiekkokeskus/")


def test_manual_event_writes_health_with_injected_put_and_now() -> None:
    put = FakePut()
    result = handler({}, None, put=put, now=lambda: FIXED_NOW)
    assert result == {"status": "ok", "key": "data/kiekkokeskus/_health.json"}
    assert len(put.calls) == 1
    key, body, ctype, cache = put.calls[0]
    assert key == "data/kiekkokeskus/_health.json"
    assert ctype == "application/json"
    assert cache == "public, max-age=300"
    assert json.loads(body) == {
        "schemaVersion": 1,
        "generatedAt": "2026-10-03T14:00:12Z",
        "status": "ok",
        "version": __version__,
        "trigger": "manual",
    }


def test_scheduled_event_sets_trigger_schedule() -> None:
    put = FakePut()
    handler({"source": "scheduled"}, None, put=put, now=lambda: FIXED_NOW)
    payload = json.loads(put.calls[0][1])
    assert payload["trigger"] == "schedule"


def test_force_error_raises() -> None:
    put = FakePut()
    with pytest.raises(RuntimeError, match="forced error"):
        handler({"forceError": True}, None, put=put, now=lambda: FIXED_NOW)
    assert put.calls == []


def test_default_now_path_runs_without_crashing() -> None:
    """Guards against the `_now_default()` parens bug: default-callable path must execute."""
    put = FakePut()
    result = handler({}, None, put=put)  # now not injected
    assert result["status"] == "ok"
    body = json.loads(put.calls[0][1])
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", body["generatedAt"])
