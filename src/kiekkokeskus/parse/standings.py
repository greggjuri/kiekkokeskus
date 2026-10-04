"""Pure parser for the standings payload. Season-id extract only in init-03."""

from __future__ import annotations

from typing import Any


def season_id(payload: dict[str, Any]) -> str | None:
    """Return `standings[0].seasonId` as a string, or None if standings is empty."""
    rows = payload.get("standings") or []
    if not rows:
        return None
    sid = rows[0].get("seasonId")
    return None if sid is None else str(sid)
