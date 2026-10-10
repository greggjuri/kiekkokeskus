"""NHL fetch + URL builders. stdlib only (ADR-003 constraint on no runtime deps).

Policies:
- Sequential, 250ms post-pause (`PAUSE_S`).
- 3 attempts total on 429, 5xx, or network error. Exponential backoff (1, 2, 4s) + jitter.
  Honor `Retry-After` when present.
- Non-429 4xx fails immediately (no retry).
- Dated URLs only (ADR-008/ADR-033). URL builders never produce "/now".
- Defensive gzip decode on the response body (future-proofing; today's endpoints return plain).
"""

from __future__ import annotations

import gzip
import json
import logging
import random
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from kiekkokeskus import __version__

log = logging.getLogger(__name__)

USER_AGENT = f"kiekkokeskus/{__version__} (+https://jurigregg.com; personal, non-commercial)"
PAUSE_S = 0.25
TIMEOUT_S = 20.0
MAX_ATTEMPTS = 3
BACKOFF_S = (1.0, 2.0, 4.0)

_API_WEB = "https://api-web.nhle.com/v1"
_STATS = "https://api.nhle.com/stats/rest/en"


@dataclass(frozen=True)
class Endpoint:
    slug: str
    url: str


@dataclass(frozen=True)
class FetchResult:
    url: str
    final_url: str
    status: int
    body: bytes
    attempts: int
    headers: dict[str, str]


class FetchError(Exception):
    """Raised when fetch gives up after retries, or on a non-retryable client error."""


# --- URL builders -----------------------------------------------------------


def _assert_no_now(url: str) -> str:
    """Guards ADR-008: never emit a URL containing 'now' as a path segment."""
    for seg in url.split("/"):
        if seg == "now":
            raise ValueError(f"URL builder would emit a /now segment: {url}")
    return url


def url_schedule(data_date: date) -> str:
    return _assert_no_now(f"{_API_WEB}/schedule/{data_date.isoformat()}")


def url_standings(data_date: date) -> str:
    return _assert_no_now(f"{_API_WEB}/standings/{data_date.isoformat()}")


def url_club_schedule_season(team: str, season: str) -> str:
    return _assert_no_now(f"{_API_WEB}/club-schedule-season/{team}/{season}")


def url_club_stats(team: str, season: str) -> str:
    # /2 = gameType regular season (ADR-014)
    return _assert_no_now(f"{_API_WEB}/club-stats/{team}/{season}/2")


def url_boxscore(game_id: int) -> str:
    return _assert_no_now(f"{_API_WEB}/gamecenter/{game_id}/boxscore")


def _bios_url(path: str, season: str, start: int, limit: int) -> str:
    from urllib.parse import urlencode

    qs = urlencode(
        {
            "cayenneExp": f'seasonId={season} and nationalityCode="FIN"',
            "limit": str(limit),
            "start": str(start),
        }
    )
    return _assert_no_now(f"{_STATS}/{path}?{qs}")


def url_skater_bios(season: str, start: int = 0, limit: int = 1000) -> str:
    return _bios_url("skater/bios", season, start, limit)


def url_goalie_bios(season: str, start: int = 0, limit: int = 1000) -> str:
    return _bios_url("goalie/bios", season, start, limit)


def _stats_rest_team_url(path: str, season: str, team: str, start: int, limit: int) -> str:
    """Stats REST team-filtered URL builder (ADR-035 team-scoped sources)."""
    from urllib.parse import urlencode

    qs = urlencode(
        {
            "cayenneExp": f'gameTypeId=2 and teamAbbrevs="{team}" and seasonId={season}',
            "limit": str(limit),
            "start": str(start),
        }
    )
    return _assert_no_now(f"{_STATS}/{path}?{qs}")


def url_skater_summary(season: str, team: str = "TBL", *, start: int = 0, limit: int = 1000) -> str:  # noqa: E501
    return _stats_rest_team_url("skater/summary", season, team, start, limit)


def url_skater_realtime(
    season: str, team: str = "TBL", *, start: int = 0, limit: int = 1000
) -> str:  # noqa: E501
    return _stats_rest_team_url("skater/realtime", season, team, start, limit)


def url_skater_faceoff(season: str, team: str = "TBL", *, start: int = 0, limit: int = 1000) -> str:  # noqa: E501
    """ADR-035: `totalFaceoffs` lives here; needed to distinguish 'took none' from 'won 0 %'."""
    return _stats_rest_team_url("skater/faceoffpercentages", season, team, start, limit)


def url_team_summary(season: str, *, start: int = 0, limit: int = 1000) -> str:
    """All 32 teams. Used for PP%/PK% league ranks (ADR-036)."""
    from urllib.parse import urlencode

    qs = urlencode(
        {
            "cayenneExp": f"gameTypeId=2 and seasonId={season}",
            "limit": str(limit),
            "start": str(start),
        }
    )
    return _assert_no_now(f"{_STATS}/team/summary?{qs}")


# --- Fetch -------------------------------------------------------------------

Opener = Callable[[urllib.request.Request, float], Any]
SleepFn = Callable[[float], None]


def _default_opener(req: urllib.request.Request, timeout: float) -> Any:
    return urllib.request.urlopen(req, timeout=timeout)  # noqa: S310 — trusted NHL hosts


def _is_retryable(status: int) -> bool:
    return status == 429 or 500 <= status < 600


def _parse_retry_after(headers: dict[str, str]) -> float | None:
    val = headers.get("retry-after") or headers.get("Retry-After")
    if val is None:
        return None
    try:
        return max(0.0, float(val))
    except ValueError:
        return None


def _maybe_gunzip(body: bytes, headers: dict[str, str]) -> bytes:
    enc = (headers.get("content-encoding") or headers.get("Content-Encoding") or "").lower()
    if "gzip" in enc:
        return gzip.decompress(body)
    return body


def fetch(
    url: str,
    *,
    opener: Opener | None = None,
    sleep: SleepFn = time.sleep,
    rand: Callable[[], float] = random.random,
) -> FetchResult:
    """Fetch with retries. See module docstring for policy."""
    opener = opener or _default_opener
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last_error: str | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = opener(req, TIMEOUT_S)
            # Normalize headers to a plain dict (case-insensitive via .get)
            headers = {k.lower(): v for k, v in resp.headers.items()}
            status = getattr(resp, "status", 200)
            final_url = getattr(resp, "url", url)
            body = resp.read()
            body = _maybe_gunzip(body, headers)
            if final_url != url:
                log.warning(json.dumps({"event": "redirect", "from": url, "to": final_url}))
            if status >= 400:
                raise urllib.error.HTTPError(url, status, "status", resp.headers, None)
            sleep(PAUSE_S)  # always pause after a successful request (politeness)
            return FetchResult(
                url=url,
                final_url=final_url,
                status=status,
                body=body,
                attempts=attempt,
                headers=headers,
            )
        except urllib.error.HTTPError as e:
            headers = {k.lower(): v for k, v in e.headers.items()} if e.headers else {}
            if not _is_retryable(e.code):
                last_error = f"HTTP {e.code}"
                raise FetchError(f"non-retryable {e.code} for {url}") from e
            last_error = f"HTTP {e.code}"
            if attempt == MAX_ATTEMPTS:
                raise FetchError(f"gave up after {attempt} attempts on {url}: {last_error}") from e
            delay = _parse_retry_after(headers) or (BACKOFF_S[attempt - 1] + rand() * 0.25)
            sleep(delay)
        except urllib.error.URLError as e:
            last_error = f"network: {e.reason}"
            if attempt == MAX_ATTEMPTS:
                raise FetchError(f"gave up after {attempt} attempts on {url}: {last_error}") from e
            delay = BACKOFF_S[attempt - 1] + rand() * 0.25
            sleep(delay)

    raise FetchError(f"unreachable fallthrough on {url}: {last_error}")
