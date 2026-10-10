"""Pure parsers for stats REST payloads (summary / realtime / faceoff / team-summary).

Reused by init-05 (nationality filters). All functions are pure dict/list → dict/list.

ADR-035: `check_complete` raises when `total > len(data)`. Pagination for these endpoints was
deemed unnecessary (TBL roster ~20, league 32, well under limit=1000) — if NHL ever returns a
partial page, we raise loudly rather than silently truncate.
"""

from __future__ import annotations

from typing import Any


class StatsRestTruncated(Exception):
    """Raised when a stats REST payload is paginated and we expected a single page."""


def check_complete(payload: dict[str, Any], slug: str) -> None:
    """Raise if `total > len(data)`. Call once per fetched stats REST body (ADR-035)."""
    total = payload.get("total")
    data = payload.get("data") or []
    if total is None:
        return  # unknown; caller decides
    if total > len(data):
        raise StatsRestTruncated(
            f"{slug}: stats REST returned {len(data)} rows but total={total}; "
            "raise the limit or paginate"
        )


def by_player_id(payload: dict[str, Any], fields: list[str]) -> dict[int, dict[str, Any]]:
    """Index `data[]` by `playerId`, keeping just the requested fields.

    Used for summary/realtime/faceoff lookups. Missing field → `None`. Missing playerId skipped.
    """
    out: dict[int, dict[str, Any]] = {}
    for row in payload.get("data") or []:
        pid = row.get("playerId")
        if pid is None:
            continue
        out[int(pid)] = {k: row.get(k) for k in fields}
    return out


def team_rows(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Index team-summary `data[]` by `teamFullName`.

    `team/summary` doesn't carry an abbreviation reliably (`teamAbbrevs` was `None` in the
    verification). Builders look up by full name using a shared mapping, or by iterating.
    """
    out: dict[str, dict[str, Any]] = {}
    for row in payload.get("data") or []:
        name = row.get("teamFullName")
        if name is None:
            continue
        out[name] = row
    return out
