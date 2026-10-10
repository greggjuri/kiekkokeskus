# init-03: Collector Core

**Created**: 2026-10-03
**Phase**: 1 Foundation
**Depends On**: init-02 (deployed stack; init-02 Steps 8–9 may close in parallel)
**ADRs**: ADR-003, 005, 006, 008, 009, 010, 011, 012, 013, 014, 020, 022, 025, 032; may add ADRs in DECISIONS-DATA.md

---

## Problem Statement

The Lambda only writes a heartbeat. Real NHL data doesn't start accumulating until the collector
fetches it. Per ADR-006, raw responses must be archived *before* any parsing, so a parse bug in
init-04/05 costs a re-parse, not a lost day. The fetch, retry, date logic, and archive machinery is
shared by everything after this, so it gets built and tested once, here.

## Goal

The deployed collector resolves the season and the data date, fetches a defined set of NHL
endpoints politely with retries, writes every response gzipped to `raw/<runDate>/` **before parsing
anything**, writes a per-run manifest, and then writes `_health.json`. A manual invoke tonight
archives real data for 2026-10-02, and from tomorrow's 10:00 ET run onward the archive grows daily.
It doesn't build `bolts.json` or `leijonat.json`; those are init-04 and init-05.

## Requirements

### Must Have (P0)

1. **Dates** (`season.py`, pure)
   - `run_date_et(now_utc) -> date`: today in `America/New_York`, via `zoneinfo`
   - `data_date(run_date_et) -> date`: run date minus one day ("last night")
   - The event may override it: `{"date": "YYYY-MM-DD"}` sets the data date explicitly, for
     re-runs and backfill. Validate the format strictly and reject future dates.
   - `now` is always injected; never call `datetime.now()` inside logic.

2. **Season resolution** (ADR-008)
   - The season ID comes from `currentSeason` in a schedule payload and is never computed.
   - Bootstrap from the **dated** league schedule for the data date: `schedule/{dataDate}`. If that
     payload has no `currentSeason`, follow the verified fallback chosen in the PRP. The final URL
     actually used is recorded in the manifest.

3. **Endpoint manifest** (`nhl.py`): one list of what a run fetches, so init-04/05 extend it rather
   than rewriting the fetch loop. In init-03 it contains:

   | Slug | URL | Notes |
   |---|---|---|
   | `schedule__{dataDate}` | `api-web.nhle.com/v1/schedule/{dataDate}` | yesterday's games + season |
   | `standings__{dataDate}` | `api-web.nhle.com/v1/standings/{dataDate}` | ADR-009 |
   | `club-schedule-season-TBL__{season}` | `…/club-schedule-season/TBL/{season}` | large; raw only (Observed State note) |
   | `club-stats-TBL__{season}-2` | `…/club-stats/TBL/{season}/2` | `gameType` 2 per ADR-014 |
   | `boxscore__{gameId}` | `…/gamecenter/{gameId}/boxscore` | one per completed regular-season game on `dataDate` (ADR-012/013/014) |
   | `skater-bios-FIN__{season}__p{n}` | `api.nhle.com/stats/rest/en/skater/bios?…nationalityCode="FIN"…` | paginate until `total` (ADR-011) |
   | `goalie-bios-FIN__{season}__p{n}` | same, against `goalie/bios` | ADR-011 |

   - The URL builders **never** produce `/now` (tested).
   - Boxscore IDs come from the schedule payload: games on `dataDate` with `gameType == 2` and
     `gameState ∈ {OFF, FINAL}`. Unknown states are logged and skipped, never guessed (ADR-013).
     This minimal parse runs **after** the schedule's raw response is already written.

4. **Fetch** (`nhl.py`)
   - stdlib `urllib`, sequential, and a fixed 250 ms pause between requests
   - `User-Agent: kiekkokeskus/<version> (+https://jurigregg.com; personal, non-commercial)`
   - Timeout 20 s. On 429, 5xx, or a network error, retry up to 3 attempts total with exponential
     backoff (1 s, 2 s, 4 s, plus jitter), honoring `Retry-After` when it's present. Any other 4xx
     fails immediately with no retry.
   - A redirect on a dated URL is unexpected: follow it, but log a warning and record both URLs in
     the manifest.
   - The opener and `sleep` are injected, so tests run offline and never really sleep.

5. **Raw archive** (`archive.py`; ADR-006, 020)
   - Key: `data/kiekkokeskus/raw/{runDateET}/{slug}.json.gz`, holding the response body exactly as
     received, gzipped, with `Content-Type: application/json`, `Content-Encoding: gzip`.
     Write-once, cached long: `Cache-Control: public, max-age=31536000, immutable`.
   - A re-run on the same run date overwrites. That's fine with versioning on, and noncurrent
     versions expire under ADR-023.
   - **Each response is written immediately after its fetch, before the next request and before any
     parsing.**
   - `raw/{runDateET}/_manifest.json`: run metadata (`runDateET`, `dataDate`, `season`, `trigger`,
     `startedAt`, `finishedAt`, `version`) plus one entry per request: `slug`, `url`, `finalUrl`,
     `status`, `bytes`, `sha256`, `fetchedAt`, `attempts`, `error` (or null). It's written at the
     end, **including on failure**, because the manifest of a failed run is the main debugging
     artifact. `Cache-Control: public, max-age=300`.

6. **Orchestration** (`handler.py`)
   - Keep from init-02: `forceError`, `{"source":"scheduled"}` → `trigger: "schedule"`, injected
     `put`/`now`, and the 0 async retries in infra.
   - Order: resolve dates → schedule (fetch, archive, parse season and game IDs) → the rest of the
     manifest in table order, archiving each → `_manifest.json` → `_health.json`.
   - **If any fetch fails after retries**, or the schedule can't be parsed: finish what can be
     fetched safely, write the manifest including the errors, **don't** write `_health.json`, and
     raise. The run fails loudly and trips the alarm.
   - `_health.json` gains `dataDate` (string) and `rawCount` (int). These are additive, so
     `schemaVersion` stays 1 (PLANNING: only breaking changes bump it).
   - `bolts.json`/`leijonat.json` aren't written yet, so there's nothing to protect, but the
     structure leaves a clear "build" phase that init-04/05 slot into after archiving.

7. **`scripts/fetch_fixture.py`** (TESTING.md fixtures rule 1)
   - Takes a URL and an optional `--variant`, writes
     `tests/fixtures/{endpoint-slug}__{date}[__variant].json.gz`, and appends a provenance row
     (file, URL, fetched-at UTC, HTTP status, variant of, ADR) to `tests/fixtures/README.md`
   - Uses the same User-Agent and politeness as the collector, by importing `nhl.py`.

8. **Fixtures to capture** (real payloads, through the script)

   | Fixture | Why | Gotcha rows |
   |---|---|---|
   | `schedule__2026-10-01` | completed reg-season game (TBL @ NYR, `OFF`) | 013, 014 |
   | `schedule__<late-Sept preseason date>` | `gameType: 1`, `FINAL` | 013, 014 |
   | `schedule__<a date with FUT games>` | not-completed state | 013 |
   | `standings__2026-04-01`, `__2026-10-01`, `__2026-10-02` | ADR-009 raw re-verify | 009, 015 (0-GP keys) |
   | `boxscore-<2026-10-01 TBL-NYR id>` | the Tolvanen game | 012 (used in init-05) |
   | `skater-bios-FIN__20262027__p0`, `goalie-bios-FIN__20262027__p0` | pagination shape, `total` | 010, 011 |

   Variant: `schedule__…__unknown-state` (one game's `gameState` set to `XYZ`), for ADR-013's
   "log, don't crash".

9. **ADR-009 raw re-verification** (TASK.md Known Issue): diff `gamesPlayed` and the season across
   the three standings fixtures. If confirmed, update ADR-009 to remove the caveat. If not, write a
   new ADR in DECISIONS-DATA.md and **stop**: the init-09 backfill plan depends on it.

10. **Tests**
    - **Dates**: run at 03:30 UTC Oct 4 (still Oct 3 in ET) gives the right data date; the DST
      change on **2026-11-01** (the run before, the run on, the run after); event override valid,
      malformed, and future
    - **URL builders**: no URL contains `now`; the season is never computed
    - **Fetch**: 200; 429 then 200 (retried, `Retry-After` honored); 500 ×3 → error; 404 →
      immediate error with no retry; redirect recorded; the injected sleep receives the backoff
      sequence
    - **Schedule parse** (layer 1, real fixtures): `currentSeason` extracted; completed reg-season
      IDs only; preseason excluded; FUT excluded; the unknown-state variant is logged and skipped
    - **Pagination**: `total` honored, no duplicates, stops correctly. Use the real p0 fixture plus
      a small `limit` to force several pages through a fake opener.
    - **Orchestration** (layer 3):
      - raw is written before parse (a parser that raises still leaves the schedule's raw object
        stored)
      - every key starts with `data/kiekkokeskus/raw/{runDate}/` except `_health.json`
      - on failure: the manifest is written with the error, `_health.json` is **not** written, and
        the handler raises
      - on success: the manifest lists every request, and the health file has `dataDate` and
        `rawCount`
      - init-02's `forceError` and trigger tests still pass
    - Coverage ≥ 80% on `src/kiekkokeskus/`

11. **Deploy and seed tonight**
    1. `cdk diff`: **only the Lambda code asset changes**. No IAM change is expected, because
       `raw/` is inside the existing `data/kiekkokeskus/*` scope. Show it, get go,
       `deploy.py --approved`.
    2. Manual invoke with no event, so the data date is 2026-10-02.
    3. `aws s3 ls s3://jurigregg-static-site/data/kiekkokeskus/raw/2026-10-03/ --profile default`:
       the objects and `_manifest.json` are all there. Every manifest entry has `error: null`.
    4. Spot-check one object through CloudFront: `curl -s …/raw/2026-10-03/standings__2026-10-02.json.gz | gunzip | head -c 300`.
    5. `scripts/smoke.py` passes (health now carries `dataDate`).

### Should Have (P1)

1. A `smoke.py` check that `_manifest.json` for the health file's run date exists and has no
   errors.
2. `scripts/rerun.py --date YYYY-MM-DD`: invokes the collector with a date override, for re-running
   a failed day.

## Output / Data Contract

| Key | Writer | Cache-Control | Notes |
|---|---|---|---|
| `raw/{runDateET}/{slug}.json.gz` | Lambda | `public, max-age=31536000, immutable` | exact NHL body, gzipped |
| `raw/{runDateET}/_manifest.json` | Lambda | `public, max-age=300` | written on success **and** failure |
| `_health.json` | Lambda | `public, max-age=300` | + `dataDate`, `rawCount` (additive) |

- **schemaVersion change?** No. Health stays 1, additive only. The manifest starts with its own
  `schemaVersion: 1`.
- **S3 keys written**: all under `data/kiekkokeskus/`

## Ownership Check

- **AWS resources created or changed**: the Lambda code only; no IAM, schedule, or alarm changes
- **S3 prefixes written**: `data/kiekkokeskus/raw/…`, `data/kiekkokeskus/_health.json`
- **Touches anything owned by the main site?** No

## Success Criteria

- [ ] pytest passes (dates, URLs, fetch, schedule parse, pagination, orchestration), coverage ≥ 80%
- [ ] Every new fixture was captured by `fetch_fixture.py`, with a provenance row
- [ ] ADR-009 is re-verified from raw diffs, and DECISIONS-DATA.md is updated either way
- [ ] `cdk diff` showed only the Lambda code change
- [ ] Tonight's manual invoke archived `raw/2026-10-03/`, with a clean manifest
- [ ] Tomorrow's 10:00 ET run archives `raw/2026-10-04/` with `trigger: "schedule"` (verified
      together with init-02's Step 8)
- [ ] `smoke.py` passes
- [ ] No file over 500 lines

## Out of Scope

- `bolts.json`/`leijonat.json` builders, and any field-level parsing beyond season and game IDs
  (init-04/05)
- stats REST `summary`/`realtime` reports for the ADR-030 columns. init-04/05 add them to the
  manifest.
- Records API / milestones (Future)
- History snapshots, backfill (init-09)

## Verify in PRP

- [ ] Does `schedule/{date}` contain `currentSeason`, and does it cover just that date or a week?
      If it's a week, filter to `dataDate`.
      If `currentSeason` is absent, pick a fallback that still records an explicit final URL.
- [ ] The exact stats REST bios query string: `cayenneExp` with `seasonId` + `nationalityCode`,
      `limit`/`start`, `total` location, and the largest `limit` the endpoint accepts
- [ ] A late-September 2026 date with preseason `FINAL` games, and a date with `FUT` games, for the
      fixtures
- [ ] The 2026-10-01 TBL @ NYR `gameId`
- [ ] Whether any endpoint returns non-JSON or gzip-encoded bodies by default. The archive stores
      the decoded JSON body.

## Open Questions

(none)

## Notes

- init-02 Steps 8–9 are still pending. Deploying this tonight means tomorrow's scheduled run is the
  init-03 collector rather than the stub. It still writes `_health.json` with
  `trigger: "schedule"`, so init-02's Step 8 checks stay valid. Both specs are In Progress in
  TASK.md at the same time; note that.
- Suggested commits:
  1. `feat(03): date and season logic`
  2. `feat(03): fetch with retry and URL builders`
  3. `feat(03): fetch_fixture script and captured fixtures` (plus the ADR-009 re-verify)
  4. `feat(03): raw archive and manifest`
  5. `feat(03): collector orchestration`
  6. `docs(03): …`

  The deploy and seed come after commit 5.
