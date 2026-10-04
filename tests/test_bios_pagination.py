"""ADR-011: paginate bios until `total`. Uses real p0 fixture with a fake opener + small limit."""

from __future__ import annotations

import gzip
import json
import pathlib
from typing import Any
from urllib.parse import parse_qs, urlparse

from kiekkokeskus.nhl import fetch

FX = pathlib.Path(__file__).parent / "fixtures"


def _all_rows() -> list[dict]:
    payload = json.loads(
        gzip.decompress((FX / "skater-bios-FIN-20262027-p0__2026-10-03.json.gz").read_bytes())
    )
    return payload["data"]


class PagedBiosOpener:
    """Serves `limit`/`start` slices of a fixed row list, with the real `total` field."""

    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.calls: list[tuple[int, int]] = []  # (start, limit) per request

    def __call__(self, req: Any, timeout: float) -> Any:  # noqa: ARG002
        qs = parse_qs(urlparse(req.full_url).query)
        start = int(qs.get("start", ["0"])[0])
        limit = int(qs.get("limit", ["1000"])[0])
        self.calls.append((start, limit))
        slice_ = self.rows[start : start + limit]
        body = json.dumps({"data": slice_, "total": len(self.rows)}).encode()

        class R:
            def __init__(self, body: bytes) -> None:
                self._body = body
                self.status = 200
                self.url = req.full_url
                self.headers = {"content-type": "application/json"}

            def read(self) -> bytes:
                return self._body

        return R(body)


def _paginate(url_builder, season: str, *, limit: int, opener) -> list[dict]:
    """Minimal paginator — the real one lives in handler.py but exercises the same contract."""
    rows: list[dict] = []
    start = 0
    while True:
        r = fetch(
            url_builder(season, start=start, limit=limit), opener=opener, sleep=lambda _s: None
        )
        payload = json.loads(r.body)
        rows.extend(payload["data"])
        total = payload["total"]
        if start + len(payload["data"]) >= total or not payload["data"]:
            return rows
        start += len(payload["data"])


def test_pagination_in_three_pages_with_limit_10() -> None:
    from kiekkokeskus.nhl import url_skater_bios

    rows = _all_rows()
    assert len(rows) == 26  # sanity: today's FIN skater count
    opener = PagedBiosOpener(rows)

    collected = _paginate(url_skater_bios, "20262027", limit=10, opener=opener)
    assert len(collected) == 26
    # Three pages: (0,10), (10,10), (20,10) → returns 10, 10, 6
    assert opener.calls == [(0, 10), (10, 10), (20, 10)]
    # No duplicates
    ids = [r["playerId"] for r in collected]
    assert len(ids) == len(set(ids))


def test_pagination_single_page_when_limit_exceeds_total() -> None:
    from kiekkokeskus.nhl import url_skater_bios

    rows = _all_rows()
    opener = PagedBiosOpener(rows)
    collected = _paginate(url_skater_bios, "20262027", limit=1000, opener=opener)
    assert len(collected) == 26
    assert opener.calls == [(0, 1000)]


def test_pagination_stops_on_empty_data() -> None:
    """Guard against infinite loop when the server returns empty data unexpectedly."""
    from kiekkokeskus.nhl import url_skater_bios

    class EmptyOpener:
        def __call__(self, req: Any, timeout: float) -> Any:  # noqa: ARG002
            class R:
                status = 200
                url = req.full_url
                headers = {"content-type": "application/json"}

                def read(self) -> bytes:
                    return json.dumps({"data": [], "total": 100}).encode()

            return R()

    collected = _paginate(url_skater_bios, "20262027", limit=10, opener=EmptyOpener())
    assert collected == []
