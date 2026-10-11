"""Pure parser for the FIN bios pages (ADR-010, ADR-011, ADR-037).

Merges all skater/goalie bios pages into dicts keyed by `playerId`. Raises on duplicate IDs
across pages — ADR-011's "no silent dedupe" rule.
"""

from __future__ import annotations

from typing import Any


class BiosDuplicateError(ValueError):
    """Raised when a `playerId` appears in more than one bios page (ADR-011)."""


def _merge(pages: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for page in pages:
        for row in page.get("data") or []:
            pid = row.get("playerId")
            if pid is None:
                continue
            pid = int(pid)
            if pid in out:
                raise BiosDuplicateError(f"duplicate playerId {pid} across bios pages (ADR-011)")
            out[pid] = row
    return out


def merged(
    skater_pages: list[dict[str, Any]], goalie_pages: list[dict[str, Any]]
) -> dict[str, dict[int, dict[str, Any]]]:
    """Return `{"skaters": {pid: row}, "goalies": {pid: row}}`.

    Each `row` is the raw bios row (keys like `skaterFullName`/`goalieFullName`, `lastName`,
    `currentTeamAbbrev`, `nationalityCode`, `positionCode`, `firstSeasonForGameType`, ...).
    """
    return {"skaters": _merge(skater_pages), "goalies": _merge(goalie_pages)}
