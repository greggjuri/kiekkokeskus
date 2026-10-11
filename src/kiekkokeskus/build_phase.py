"""Two independent builders — bolts + leijonat. One failing doesn't freeze the other.

Called by the handler after the fetch/manifest phase. Each builder runs in its own `try`.
Returns `(outputs, errors)` so the handler can write each successful page's JSON and raise
after any failure.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date
from typing import Any

from kiekkokeskus import build_bolts, build_leijonat

log = logging.getLogger(__name__)


def _rookie_id_set(payload: dict[str, Any] | None) -> set[int]:
    if payload is None:
        return set()
    return {int(r["playerId"]) for r in payload.get("data") or [] if r.get("playerId")}


def run_builders(
    *,
    bodies: dict[str, Any],
    data_date: date,
    season: str,
    now_iso: str,
    boxscore_payloads: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, Exception]]:
    """Run bolts + leijonat builders independently. Return (outputs, errors).

    `outputs` maps builder name → produced dict. `errors` maps builder name → exception.
    Both are non-empty subsets of {"bolts", "leijonat"}.
    """
    outputs: dict[str, dict[str, Any]] = {}
    errors: dict[str, Exception] = {}

    # Bolts
    try:
        outputs["bolts"] = build_bolts.build(
            data_date=data_date,
            season=season,
            now_iso=now_iso,
            standings_payload=bodies["standings"],
            club_stats_payload=bodies["club-stats"],
            club_schedule_payload=bodies["club-schedule"],
            skater_summary_payload=bodies["skater-summary"],
            skater_realtime_payload=bodies["skater-realtime"],
            skater_faceoff_payload=bodies["skater-faceoff"],
            team_summary_payload=bodies["team-summary"],
        )
    except Exception as e:  # noqa: BLE001
        log.error(
            '{"event": "build_failed", "builder": "bolts", "error": %r}'  # noqa: UP031
            % str(e)
        )
        errors["bolts"] = e

    # Leijonat
    try:
        outputs["leijonat"] = build_leijonat.build(
            data_date=data_date,
            season=season,
            now_iso=now_iso,
            bios_skater_pages=bodies.get("bios-skater", []),
            bios_goalie_pages=bodies.get("bios-goalie", []),
            summary_payload=bodies["summary-FIN"],
            realtime_payload=bodies["realtime-FIN"],
            faceoff_payload=bodies["faceoff-FIN"],
            goalie_summary_payload=bodies["goalie-summary-FIN"],
            rookie_skater_ids=_rookie_id_set(bodies.get("rookies-FIN")),
            rookie_goalie_ids=_rookie_id_set(bodies.get("goalie-rookies-FIN")),
            club_stats_by_team=bodies.get("club-stats-by-team", {}),
            boxscore_payloads=boxscore_payloads,
            schedule_payload=bodies["schedule"],
            standings_payload=bodies["standings"],
        )
    except Exception as e:  # noqa: BLE001
        log.error(
            '{"event": "build_failed", "builder": "leijonat", "error": %r}'  # noqa: UP031
            % str(e)
        )
        errors["leijonat"] = e

    return outputs, errors


# PutObject signature matches archive.PutObject.
PutObject = Callable[[str, bytes, str, str, str | None], None]


def write_outputs(
    *,
    put: PutObject,
    prefix: str,
    outputs: dict[str, dict[str, Any]],
) -> list[str]:
    """Write each successful output to `{prefix}{name}.json` with ADR-022 Cache-Control.

    Returns the list of built names (sorted alphabetically for `_health.built`).
    """
    import json

    built: list[str] = []
    for name in sorted(outputs):
        key = f"{prefix}{name}.json"
        body = json.dumps(outputs[name], separators=(",", ":")).encode()
        put(key, body, "application/json", "public, max-age=300", None)
        built.append(name)
        log.info(f'{{"event": "built_written", "key": "{key}"}}')
    return built
