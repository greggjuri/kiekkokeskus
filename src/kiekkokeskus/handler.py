"""Collector orchestration. ADR-006 (raw before parse), ADR-032 (ops + alarms), ADR-033 (season).

Order per PRP-03 Step 6:
    schedule → (parse: season candidate + game ids)
    standings → (parse: season fallback)
    if season is None after both: write manifest with season=null + error, raise.
    club-schedule-season/TBL/{season} → club-stats/TBL/{season}/2 → boxscores
    → skater-bios (paginated) → goalie-bios (paginated)
    → _manifest.json → _health.json (only on all-green).
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from kiekkokeskus import __version__, build_phase, nhl
from kiekkokeskus.archive import (
    Manifest,
    PutObject,
    iso_z,
    make_request_row,
    write_manifest,
    write_raw,
)
from kiekkokeskus.parse import schedule as sched_parse
from kiekkokeskus.parse import standings as st_parse
from kiekkokeskus.parse import stats_rest
from kiekkokeskus.season import resolve_data_date, run_date_et

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

TBL = "TBL"
HEALTH_SLUG = "_health.json"


def _default_put() -> PutObject:
    import boto3

    client = boto3.client("s3")
    bucket = os.environ["BUCKET"]

    def put(
        key: str,
        body: bytes,
        content_type: str,
        cache_control: str,
        content_encoding: str | None,
    ) -> None:
        kwargs: dict[str, Any] = {
            "Bucket": bucket,
            "Key": key,
            "Body": body,
            "ContentType": content_type,
            "CacheControl": cache_control,
        }
        if content_encoding:
            kwargs["ContentEncoding"] = content_encoding
        client.put_object(**kwargs)

    return put


def _now_default() -> datetime:
    return datetime.now(UTC)


def _write_health(
    *,
    put: PutObject,
    now: Callable[[], datetime],
    prefix: str,
    trigger: str,
    data_date_iso: str,
    raw_count: int,
    built: list[str],
) -> str:
    key = f"{prefix}{HEALTH_SLUG}"
    payload = {
        "schemaVersion": 1,
        "generatedAt": now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "ok",
        "version": __version__,
        "trigger": trigger,
        "dataDate": data_date_iso,
        "rawCount": raw_count,
        "built": built,
    }
    body = json.dumps(payload, separators=(",", ":")).encode()
    put(key, body, "application/json", "public, max-age=300", None)
    return key


def _check_stats_rest(payload: dict | None, slug: str, requests: list) -> None:
    """If a stats REST payload is paginated unexpectedly, mark the last manifest row as errored.

    `_fetch_and_archive` appends the row before this is called, so index -1 is correct.
    ADR-035: raise loudly rather than silently truncate; the had_error branch at the end picks
    this up.
    """
    if payload is None:
        return
    try:
        stats_rest.check_complete(payload, slug)
    except stats_rest.StatsRestTruncated as e:
        requests[-1].error = str(e)


def _fetch_and_archive(
    *,
    put: PutObject,
    now: Callable[[], datetime],
    run_date,
    slug: str,
    url: str,
    requests: list,
    fetch_fn=nhl.fetch,
) -> dict[str, Any] | None:
    """Returns the parsed JSON payload, or None on fetch failure. Appends a manifest row."""
    try:
        r = fetch_fn(url)
    except Exception as e:  # noqa: BLE001
        requests.append(
            make_request_row(
                slug=slug,
                url=url,
                final_url="",
                status=0,
                body=None,
                sha=None,
                fetched_at=iso_z(now()),
                attempts=0,
                error=str(e),
            )
        )
        return None
    _, sha, _ = write_raw(put=put, run_date=run_date, slug=slug, body=r.body)
    requests.append(
        make_request_row(
            slug=slug,
            url=url,
            final_url=r.final_url,
            status=r.status,
            body=r.body,
            sha=sha,
            fetched_at=iso_z(now()),
            attempts=r.attempts,
            error=None,
        )
    )
    try:
        return json.loads(r.body)
    except json.JSONDecodeError:
        return None


def handler(
    event: dict[str, Any],
    context: Any,
    *,
    put: PutObject | None = None,
    now: Callable[[], datetime] | None = None,
    fetch_fn: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Writes raw/{runDate}/*, _manifest.json, and (on success) _health.json."""
    log.info(json.dumps({"event": "invoked", "payload": event}))
    if event.get("forceError"):
        raise RuntimeError("forced error for alarm test")

    put = put or _default_put()
    now = now or _now_default
    fetch_fn = fetch_fn or nhl.fetch
    prefix = os.environ["PREFIX"]
    trigger = "schedule" if event.get("source") == "scheduled" else "manual"

    now_utc = now()
    run_date = run_date_et(now_utc)
    data_date = resolve_data_date(event, now_utc)

    manifest = Manifest(
        runDateET=run_date.isoformat(),
        dataDate=data_date.isoformat(),
        season=None,
        trigger=trigger,
        startedAt=iso_z(now_utc),
        version=__version__,
    )

    # In-memory parsed payloads keyed by endpoint family. Used by the build phase so we don't
    # re-read S3 (init-04).
    bodies: dict[str, dict] = {}

    # Step 1: schedule
    sched_payload = _fetch_and_archive(
        put=put,
        now=now,
        run_date=run_date,
        slug=f"schedule__{data_date.isoformat()}",
        url=nhl.url_schedule(data_date),
        requests=manifest.requests,
        fetch_fn=fetch_fn,
    )
    if sched_payload is not None:
        bodies["schedule"] = sched_payload
    schedule_season: str | None = None
    game_ids: list[int] = []
    if sched_payload is not None:
        schedule_season, game_ids = sched_parse.extract(sched_payload, data_date)

    # Step 2: standings (independent of season)
    st_payload = _fetch_and_archive(
        put=put,
        now=now,
        run_date=run_date,
        slug=f"standings__{data_date.isoformat()}",
        url=nhl.url_standings(data_date),
        requests=manifest.requests,
        fetch_fn=fetch_fn,
    )
    if st_payload is not None:
        bodies["standings"] = st_payload
    standings_season = st_parse.season_id(st_payload) if st_payload else None

    season = schedule_season or standings_season
    manifest.season = season

    # If season can't be resolved: write manifest + raise. Do NOT write health.
    if season is None:
        err = "could not resolve season from schedule or standings"
        log.error(json.dumps({"event": "season_unresolved"}))
        manifest.requests.append(
            make_request_row(
                slug="_season_resolution",
                url="",
                final_url="",
                status=0,
                body=None,
                sha=None,
                fetched_at=iso_z(now()),
                attempts=0,
                error=err,
            )
        )
        write_manifest(put=put, run_date=run_date, manifest=manifest, now_iso=iso_z(now()))
        raise RuntimeError(err)

    # Step 3: TBL club endpoints
    cs_payload = _fetch_and_archive(
        put=put,
        now=now,
        run_date=run_date,
        slug=f"club-schedule-season-{TBL}__{season}",
        url=nhl.url_club_schedule_season(TBL, season),
        requests=manifest.requests,
        fetch_fn=fetch_fn,
    )
    if cs_payload is not None:
        bodies["club-schedule"] = cs_payload
    cst_payload = _fetch_and_archive(
        put=put,
        now=now,
        run_date=run_date,
        slug=f"club-stats-{TBL}__{season}__2",
        url=nhl.url_club_stats(TBL, season),
        requests=manifest.requests,
        fetch_fn=fetch_fn,
    )
    if cst_payload is not None:
        bodies["club-stats"] = cst_payload

    # Step 4: boxscores for completed reg-season games on dataDate. Collect for build_leijonat.
    boxscore_payloads: list[dict[str, Any]] = []
    for gid in game_ids:
        bx_payload = _fetch_and_archive(
            put=put,
            now=now,
            run_date=run_date,
            slug=f"boxscore__{gid}",
            url=nhl.url_boxscore(gid),
            requests=manifest.requests,
            fetch_fn=fetch_fn,
        )
        if bx_payload is not None:
            boxscore_payloads.append(bx_payload)

    # Step 5: bios paginated. Collect pages into bodies for init-05 build.
    bodies["bios-skater"] = []
    bodies["bios-goalie"] = []
    for family, url_fn, bucket in (
        ("skater-bios-FIN", nhl.url_skater_bios, "bios-skater"),
        ("goalie-bios-FIN", nhl.url_goalie_bios, "bios-goalie"),
    ):
        start = 0
        page = 0
        while True:
            payload = _fetch_and_archive(
                put=put,
                now=now,
                run_date=run_date,
                slug=f"{family}__{season}__p{page}",
                url=url_fn(season, start=start, limit=1000),
                requests=manifest.requests,
                fetch_fn=fetch_fn,
            )
            if payload is None:
                break
            bodies[bucket].append(payload)
            n = len(payload.get("data", []))
            total = payload.get("total", 0)
            if n == 0 or start + n >= total:
                break
            start += n
            page += 1

    # Step 5.5: club-stats fan-out for Finnish-name `fi` keys (ADR-037). Must run AFTER both
    # bios loops because we need `currentTeamAbbrev` from each Finn. TBL's payload is already
    # fetched in Step 3 and lives at bodies["club-stats"]; we add it to the by-team dict by
    # reference without re-fetching.
    finn_teams: set[str] = set()
    for pages in (bodies.get("bios-skater", []), bodies.get("bios-goalie", [])):
        for page_payload in pages:
            for row in page_payload.get("data") or []:
                abbrev = row.get("currentTeamAbbrev")
                if abbrev:
                    finn_teams.add(abbrev)
    bodies["club-stats-by-team"] = {}
    if "club-stats" in bodies:
        bodies["club-stats-by-team"][TBL] = bodies["club-stats"]
    for team in sorted(finn_teams - {TBL}):
        payload = _fetch_and_archive(
            put=put,
            now=now,
            run_date=run_date,
            slug=f"club-stats-{team}__{season}__2",
            url=nhl.url_club_stats(team, season),
            requests=manifest.requests,
            fetch_fn=fetch_fn,
        )
        if payload is not None:
            bodies["club-stats-by-team"][team] = payload

    # Step 6: stats REST — TBL-scoped skater reports + league-wide team summary.
    # Single-page fetches with limit=1000. Pagination guard (ADR-035): raise loudly on
    # unexpected truncation by marking the manifest row as errored.
    for bucket, slug_prefix, url_fn in (
        ("skater-summary", "skater-summary-TBL", nhl.url_skater_summary),
        ("skater-realtime", "skater-realtime-TBL", nhl.url_skater_realtime),
        ("skater-faceoff", "skater-faceoff-TBL", nhl.url_skater_faceoff),
    ):
        slug = f"{slug_prefix}__{season}"
        payload = _fetch_and_archive(
            put=put,
            now=now,
            run_date=run_date,
            slug=slug,
            url=url_fn(season),
            requests=manifest.requests,
            fetch_fn=fetch_fn,
        )
        if payload is not None:
            bodies[bucket] = payload
            _check_stats_rest(payload, slug, manifest.requests)

    ts_slug = f"team-summary__{season}"
    ts_payload = _fetch_and_archive(
        put=put,
        now=now,
        run_date=run_date,
        slug=ts_slug,
        url=nhl.url_team_summary(season),
        requests=manifest.requests,
        fetch_fn=fetch_fn,
    )
    if ts_payload is not None:
        bodies["team-summary"] = ts_payload
        _check_stats_rest(ts_payload, ts_slug, manifest.requests)

    # Step 7: FIN nationality-filtered stats REST (ADR-037). Four 1-page fetches, guarded.
    for bucket, slug_prefix, url_fn in (
        ("summary-FIN", "skater-summary-FIN", nhl.url_skater_summary_nationality),
        ("realtime-FIN", "skater-realtime-FIN", nhl.url_skater_realtime_nationality),
        ("faceoff-FIN", "skater-faceoff-FIN", nhl.url_skater_faceoff_nationality),
        ("goalie-summary-FIN", "goalie-summary-FIN", nhl.url_goalie_summary_nationality),
    ):
        slug = f"{slug_prefix}__{season}"
        payload = _fetch_and_archive(
            put=put,
            now=now,
            run_date=run_date,
            slug=slug,
            url=url_fn(season),
            requests=manifest.requests,
            fetch_fn=fetch_fn,
        )
        if payload is not None:
            bodies[bucket] = payload
            _check_stats_rest(payload, slug, manifest.requests)

    # Step 8: FIN rookie flag via isRookie=1 filter (ADR-037). Two 1-page fetches.
    for bucket, slug_prefix, url_fn in (
        ("rookies-FIN", "skater-rookies-FIN", nhl.url_skater_rookies_nationality),
        ("goalie-rookies-FIN", "goalie-rookies-FIN", nhl.url_goalie_rookies_nationality),
    ):
        slug = f"{slug_prefix}__{season}"
        payload = _fetch_and_archive(
            put=put,
            now=now,
            run_date=run_date,
            slug=slug,
            url=url_fn(season),
            requests=manifest.requests,
            fetch_fn=fetch_fn,
        )
        if payload is not None:
            bodies[bucket] = payload
            _check_stats_rest(payload, slug, manifest.requests)

    # Fail loudly if any request errored
    had_error = any(req.error for req in manifest.requests)
    raw_count = sum(1 for req in manifest.requests if req.error is None and req.status == 200)

    write_manifest(put=put, run_date=run_date, manifest=manifest, now_iso=iso_z(now()))

    if had_error:
        raise RuntimeError(
            f"collector run had {sum(1 for r in manifest.requests if r.error)} errored requests"
        )

    # Build phase (ADR-035/037): two independent builders.
    outputs, errors = build_phase.run_builders(
        bodies=bodies,
        data_date=data_date,
        season=season,
        now_iso=iso_z(now()),
        boxscore_payloads=boxscore_payloads,
    )
    built = build_phase.write_outputs(put=put, prefix=prefix, outputs=outputs)

    if errors:
        # Any builder failure means no health file; alarm fires.
        names = ", ".join(sorted(errors))
        raise RuntimeError(f"builder(s) failed: {names}")

    key = _write_health(
        put=put,
        now=now,
        prefix=prefix,
        trigger=trigger,
        data_date_iso=data_date.isoformat(),
        raw_count=raw_count,
        built=built,
    )
    log.info(json.dumps({"event": "health_written", "key": key, "trigger": trigger}))
    return {"status": "ok", "key": key, "rawCount": raw_count, "built": built}
