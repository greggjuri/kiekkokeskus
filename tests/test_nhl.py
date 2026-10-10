from __future__ import annotations

import gzip
import io
import urllib.error
from collections.abc import Iterator
from datetime import date
from typing import Any

import pytest

from kiekkokeskus import nhl
from kiekkokeskus.nhl import (
    FetchError,
    fetch,
    url_boxscore,
    url_club_schedule_season,
    url_club_stats,
    url_goalie_bios,
    url_schedule,
    url_skater_bios,
    url_skater_faceoff,
    url_skater_realtime,
    url_skater_summary,
    url_standings,
    url_team_summary,
)


class FakeResp:
    def __init__(
        self,
        status: int = 200,
        body: bytes = b'{"ok":true}',
        headers: dict[str, str] | None = None,
        url: str = "https://api-web.nhle.com/v1/schedule/2026-10-02",
    ) -> None:
        self.status = status
        self._body = body
        self.headers = headers or {"content-type": "application/json"}
        self.url = url

    def read(self) -> bytes:
        return self._body


class FakeSleep:
    def __init__(self) -> None:
        self.calls: list[float] = []

    def __call__(self, s: float) -> None:
        self.calls.append(s)


# --- URL builders ------------------------------------------------------------


def test_url_builders_use_dated_values_and_no_now() -> None:
    d = date(2026, 10, 2)
    urls = [
        url_schedule(d),
        url_standings(d),
        url_club_schedule_season("TBL", "20262027"),
        url_club_stats("TBL", "20262027"),
        url_boxscore(2026020010),
        url_skater_bios("20262027", start=0, limit=1000),
        url_goalie_bios("20262027", start=0, limit=1000),
        url_skater_summary("20262027"),
        url_skater_realtime("20262027"),
        url_skater_faceoff("20262027"),
        url_team_summary("20262027"),
    ]
    for u in urls:
        # path segment check (not just substring): "/now" and "now/" shouldn't appear
        segs = u.split("/")
        assert "now" not in segs, f"'now' segment in {u}"
    assert "2026-10-02" in urls[0]
    assert "/club-stats/TBL/20262027/2" in urls[3]
    assert "cayenneExp=" in urls[5]
    assert "limit=1000" in urls[5]


def test_stats_rest_team_filtered_urls_carry_cayenneexp() -> None:
    # Default limit is 1000; team defaults to TBL
    for u in [
        url_skater_summary("20262027"),
        url_skater_realtime("20262027"),
        url_skater_faceoff("20262027"),
    ]:
        assert "cayenneExp=" in u
        assert "gameTypeId%3D2" in u, "gameTypeId=2 required (ADR-014)"
        assert "teamAbbrevs%3D%22TBL%22" in u, "TBL filter required"
        assert "seasonId%3D20262027" in u
        assert "limit=1000" in u
        assert "start=0" in u

    # Specific paths
    assert "/skater/summary?" in url_skater_summary("20262027")
    assert "/skater/realtime?" in url_skater_realtime("20262027")
    assert "/skater/faceoffpercentages?" in url_skater_faceoff("20262027")


def test_team_summary_url_is_league_wide() -> None:
    u = url_team_summary("20262027")
    assert "/team/summary?" in u
    assert "cayenneExp=" in u
    assert "gameTypeId%3D2" in u
    assert "seasonId%3D20262027" in u
    assert "teamAbbrevs" not in u, "team summary must not filter by team"


# --- Fetch -------------------------------------------------------------------


def test_fetch_200_returns_body_and_pauses() -> None:
    def opener(req: Any, timeout: float) -> FakeResp:
        return FakeResp()

    sleep = FakeSleep()
    r = fetch("https://api-web.nhle.com/v1/schedule/2026-10-02", opener=opener, sleep=sleep)
    assert r.status == 200
    assert r.body == b'{"ok":true}'
    assert r.attempts == 1
    assert sleep.calls == [nhl.PAUSE_S]  # one post-success pause


def test_fetch_retries_on_429_then_200(monkeypatch: pytest.MonkeyPatch) -> None:
    responses: Iterator[Any] = iter(
        [
            urllib.error.HTTPError(
                "u",
                429,
                "throttle",
                {"Retry-After": "7"},
                io.BytesIO(b""),
            ),
            FakeResp(),
        ]
    )

    def opener(req: Any, timeout: float) -> Any:
        v = next(responses)
        if isinstance(v, Exception):
            raise v
        return v

    sleep = FakeSleep()
    r = fetch("https://x", opener=opener, sleep=sleep, rand=lambda: 0.0)
    assert r.attempts == 2
    # Retry-After=7 honored (not default backoff 1), then one post-success pause
    assert sleep.calls == [7.0, nhl.PAUSE_S]


def test_fetch_500_three_times_raises() -> None:
    def opener(req: Any, timeout: float) -> Any:
        raise urllib.error.HTTPError("u", 500, "boom", {}, io.BytesIO(b""))

    sleep = FakeSleep()
    with pytest.raises(FetchError, match="gave up after 3"):
        fetch("https://x", opener=opener, sleep=sleep, rand=lambda: 0.0)
    assert sleep.calls == [1.0, 2.0]  # two retry delays, no final pause


def test_fetch_404_fails_immediately_without_retry() -> None:
    def opener(req: Any, timeout: float) -> Any:
        raise urllib.error.HTTPError("u", 404, "nope", {}, io.BytesIO(b""))

    sleep = FakeSleep()
    with pytest.raises(FetchError, match="non-retryable 404"):
        fetch("https://x", opener=opener, sleep=sleep)
    assert sleep.calls == []  # no delays


def test_fetch_records_redirect() -> None:
    def opener(req: Any, timeout: float) -> FakeResp:
        return FakeResp(url="https://api-web.nhle.com/v1/schedule/2026-10-02")

    r = fetch(
        "https://api-web.nhle.com/v1/schedule/some-redirecting-url",
        opener=opener,
        sleep=FakeSleep(),
    )
    assert r.url != r.final_url


def test_fetch_defensive_gunzip_on_gzip_encoding() -> None:
    original = b'{"gzipped":true}'
    body = gzip.compress(original)

    def opener(req: Any, timeout: float) -> FakeResp:
        return FakeResp(body=body, headers={"content-encoding": "gzip"})

    r = fetch("https://x", opener=opener, sleep=FakeSleep())
    assert r.body == original


def test_fetch_backoff_sequence_without_retry_after() -> None:
    def opener(req: Any, timeout: float) -> Any:
        raise urllib.error.HTTPError("u", 503, "down", {}, io.BytesIO(b""))

    sleep = FakeSleep()
    with pytest.raises(FetchError):
        fetch("https://x", opener=opener, sleep=sleep, rand=lambda: 0.5)
    # Base backoff 1 + 0.5*0.25 = 1.125; then 2 + 0.125 = 2.125; no 3rd (we raised)
    assert sleep.calls == [pytest.approx(1.125), pytest.approx(2.125)]
