# PRP-03: Collector Core

**Created**: 2026-10-04
**Initial**: `initials/init-03-collector-core.md`
**Status**: Complete
**ADRs**: ADR-003, 005, 006, 008, 009, 010, 011, 012, 013, 014, 020, 022, 025, 032; **adds ADR-033** (schedule season source, DECISIONS-DATA.md); may update ADR-009

---

## Overview

### Problem Statement

The Lambda only writes a heartbeat. Real NHL data doesn't start accumulating until the collector
fetches it. Per ADR-006, raw responses are archived before any parsing; init-04/05 then build
from fixtures. The fetch, retry, date logic, and archive machinery are shared, so they get built
and tested once, here.

### Proposed Solution

Pure date module (`season.py`), stdlib fetcher (`nhl.py`) with retries + politeness, raw-first
archive (`archive.py`) under `data/kiekkokeskus/raw/{runDateET}/`, a per-run manifest, and an
orchestrating `handler.py` that keeps init-02's shape. `scripts/fetch_fixture.py` captures real
NHL payloads with provenance. Deploy tonight (Lambda code change only), seed `raw/2026-10-03/`,
re-verify ADR-009 from the raw standings diff.

### Success Criteria

- [ ] pytest green across dates / URL builders / fetch / schedule parse / pagination /
      orchestration; coverage ≥ 80% on `src/kiekkokeskus/`
- [ ] Every new fixture captured by `fetch_fixture.py` with a provenance row
- [ ] ADR-009 re-verified from raw standings diffs; DECISIONS-DATA.md updated either way
- [ ] `cdk diff` shows **only** the Lambda code asset changing
- [ ] Tonight's manual invoke archives `raw/2026-10-03/` with a clean `_manifest.json`
      (every entry `error: null`)
- [ ] Tomorrow's 10:00 ET run writes `raw/2026-10-04/` and `_health.json` with
      `trigger: "schedule"` (coordinated with init-02 Step 8)
- [ ] `scripts/smoke.py` passes (health now carries `dataDate` + `rawCount`)
- [ ] No file over 500 lines

---

## Context

### Related Documentation

- `docs/PLANNING.md`: Collector tech stack, Data Contract, Key Constraints 2/3/8
- `docs/DECISIONS.md`: ADR-003 (browser never calls NHL), 005 (ET schedule), 006 (raw first),
  008 (dated URLs, never `/now`), 020 (bucket/prefixes), 022 (Cache-Control), 025 (profile), 032 (ops baseline + deploy gate)
- `docs/DECISIONS-DATA.md`: ADR-009 (dated standings; re-verify here),
  010 (Finn = nationalityCode FIN), 011 (bios paginated), 012 (boxscore join), 013 (gameState OFF/FINAL),
  014 (gameType 2)
- `docs/TESTING.md`: Layer 1 (parse contract), Layer 3 (orchestration), fixture rules, gotcha matrix rows 008, 009, 010, 011, 012, 013, 014

### Dependencies

init-02 deployed (Steps 0–7); init-02 Steps 8–9 run in parallel today after the 10:00 ET
scheduled run. Both specs stay In Progress in TASK.md.

### Files to Modify/Create

```
src/kiekkokeskus/season.py                          # NEW: run_date_et, data_date, event override
src/kiekkokeskus/nhl.py                             # NEW: URL builders + fetch (urllib, retries)
src/kiekkokeskus/archive.py                         # NEW: raw gz writer + manifest
src/kiekkokeskus/parse/__init__.py                  # NEW: empty
src/kiekkokeskus/parse/schedule.py                  # NEW: pure parse of schedule payload
src/kiekkokeskus/parse/standings.py                 # NEW: pure parse of standings payload (seasonId extract)
src/kiekkokeskus/handler.py                         # MODIFY: orchestrate collection
scripts/fetch_fixture.py                            # NEW
scripts/rerun.py                                    # NEW (P1)
tests/test_season.py                                # NEW
tests/test_nhl.py                                   # NEW (URL builders + fetch retry)
tests/test_schedule_parse.py                        # NEW (layer 1, real fixtures)
tests/test_bios_pagination.py                       # NEW
tests/test_handler_orchestration.py                 # NEW (expand init-02 tests)
# Fixture filename convention: date in filename = capture date in ET.
# Game date / standings date / etc. lives inside the slug and in the provenance row.
# Today's captures (ET) all tag __2026-10-03.
tests/fixtures/schedule__2026-10-01__2026-10-03.json.gz          # NEW: schedule for 2026-10-01, captured 2026-10-03
tests/fixtures/schedule__2026-09-26__2026-10-03.json.gz          # NEW: preseason FINAL
tests/fixtures/schedule__2026-12-15__2026-10-03.json.gz          # NEW: FUT games
tests/fixtures/schedule__2026-10-01__2026-10-03__unknown-state.json.gz  # NEW: variant for ADR-013
tests/fixtures/standings__2026-04-01__2026-10-03.json.gz         # NEW
tests/fixtures/standings__2026-10-01__2026-10-03.json.gz         # NEW
tests/fixtures/standings__2026-10-02__2026-10-03.json.gz         # NEW
tests/fixtures/boxscore__2026020010__2026-10-03.json.gz          # NEW: Tolvanen game (played 2026-10-01)
tests/fixtures/skater-bios-FIN__20262027__p0__2026-10-03.json.gz  # NEW
tests/fixtures/goalie-bios-FIN__20262027__p0__2026-10-03.json.gz  # NEW
tests/fixtures/README.md                            # MODIFY (provenance rows)
docs/DECISIONS-DATA.md                              # MODIFY: ADR-033 + ADR-009 note or new ADR
docs/PLANNING.md                                    # MODIFY: Data Contract rows for raw/manifest
docs/TASK.md                                        # MODIFY: In Progress → Recently Completed
```

Largest expected file: `src/kiekkokeskus/handler.py` ~180 lines; `nhl.py` ~160; `parse/schedule.py` ~60; stays under 500.

---

## Verification of Unconfirmed Facts

| Assumption | Result | Follow-up |
|---|---|---|
| `schedule/{date}` has `currentSeason` and covers one date | **No**, and **no**. Top-level keys are `nextStartDate`, `previousStartDate`, `gameWeek`, `oddsPartners`, `preSeasonStartDate`, `regularSeasonStartDate`, `regularSeasonEndDate`, `playoffEndDate`, `numberOfGames`. **`currentSeason` is absent.** `gameWeek` is 7 entries starting at the requested date. | **ADR-033** (DECISIONS-DATA.md): season from `gameWeek[].games[].season` on games on `dataDate`, else `standings[0].seasonId`; filter `gameWeek` to `dataDate` for the boxscore join (ADR-012). **ADR-033 partially supersedes ADR-008's "`currentSeason`" wording**; the spirit (read from payload, don't compute) holds. CLAUDE.md Rule 2 and PLANNING must be updated in the same commit so no later PRP chases a field that doesn't exist. |
| Season fallback if no games on `dataDate` | Standings is dated and doesn't need the season. Rows carry `seasonId` (verified: `standings[].seasonId == 20262027` on 2026-10-02). | **Fallback via standings, not the week**: season from `games[].season` on `dataDate` → else `standings.standings[0].seasonId` → else fail. Prevents a short in-season gap (e.g. All-Star break) from alarming every morning. |
| bios query string + pagination | `?cayenneExp=seasonId=20262027 and nationalityCode="FIN"&limit=N&start=M` works. Response: `{"data": [...], "total": N}`. `limit=1000` accepted; today returns all 26 FIN skaters in one page. | Use `limit=1000` by default (one page covers today's season). Tests force small `limit` via fake opener to exercise pagination logic (ADR-011). |
| TBL @ NYR 2026-10-01 `gameId` | **`2026020010`**, `gameType=2`, `gameState=OFF`. | fixture filename: `boxscore__2026020010__2026-10-02.json.gz` (dataDate = 2026-10-02 run date yields last-night games) |
| Dates for fixture variants | Preseason FINAL: **2026-09-26** (14 games, `gameType=1, FINAL`). FUT regular: **2026-12-15** (11 games, `gameType=2, FUT`). | Use these for `schedule__2026-09-26` and `schedule__2026-12-15` fixtures. |
| Encodings — does any endpoint return gzip or non-JSON by default? | Headers show `content-type: application/json` and `vary: Accept-Encoding`. Python's `urllib.request.urlopen` does not send `Accept-Encoding` by default → server returns **plain** JSON. | Defensive: fetch inspects `Content-Encoding` response header and decompresses if present. Archive always stores the **plain** JSON body (gzipped once, by us). |

Full raw payloads live under `/tmp/nhl-verify/` during generation — not committed. Fixtures are
captured properly in execution Step 4 via `fetch_fixture.py`.

---

## Technical Specification

### Dates — `src/kiekkokeskus/season.py`

```python
from datetime import date, datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

def run_date_et(now_utc: datetime) -> date:
    return now_utc.astimezone(ET).date()

def data_date(run_date: date) -> date:
    return run_date - timedelta(days=1)

def resolve_data_date(event: dict, now_utc: datetime) -> date:
    """Honor event['date'] (YYYY-MM-DD, not future), else data_date(run_date_et(now_utc))."""
```

Rules: `now` is always injected. Event override validated strictly (`fromisoformat`); future
dates rejected. Nothing calls `datetime.now()` inside logic (CLAUDE.md convention).

### URL builders + fetch — `src/kiekkokeskus/nhl.py`

```python
USER_AGENT = f"kiekkokeskus/{__version__} (+https://jurigregg.com; personal, non-commercial)"
PAUSE_S = 0.25
TIMEOUT_S = 20.0
MAX_ATTEMPTS = 3
BACKOFF = (1.0, 2.0, 4.0)   # before jitter, plus Retry-After when present

@dataclass(frozen=True)
class Endpoint:
    slug: str
    url: str

def url_schedule(data_date: date) -> str: ...
def url_standings(data_date: date) -> str: ...
def url_club_schedule_season(team: str, season: str) -> str: ...
def url_club_stats(team: str, season: str) -> str: ...        # /2 appended (ADR-014)
def url_boxscore(game_id: int) -> str: ...
def url_skater_bios(season: str, start: int, limit: int) -> str: ...
def url_goalie_bios(season: str, start: int, limit: int) -> str: ...
# None of these may contain the string "now" — a unit test asserts it.

def fetch(url: str, *, opener=None, sleep=time.sleep) -> FetchResult:
    """Sequential, 250ms post-pause, 3 attempts total, backoff+jitter, honors Retry-After.
    Non-429/5xx 4xx → fail immediately. Redirect → follow + log + record both URLs.
    Returns (final_url, status, body_bytes, attempts, headers)."""
```

The opener and `sleep` are injected; tests use fakes and never really sleep. Defensive gzip
decode: if the response's `Content-Encoding` is `gzip`, decompress before returning.

### Raw archive + manifest — `src/kiekkokeskus/archive.py`

Writes under `data/kiekkokeskus/raw/{runDateET}/{slug}.json.gz`:
- Body: gzip of the fetched JSON body (plain bytes)
- Headers: `Content-Type: application/json`, `Content-Encoding: gzip`,
  `Cache-Control: public, max-age=31536000, immutable`

`_manifest.json` (always written, even on failure):

```json
{
  "schemaVersion": 1,
  "runDateET": "2026-10-03",
  "dataDate": "2026-10-02",
  "season": "20262027",
  "trigger": "manual",
  "startedAt": "2026-10-03T...Z",
  "finishedAt": "2026-10-03T...Z",
  "version": "0.1.0",
  "requests": [
    {"slug": "schedule__2026-10-02", "url": "...", "finalUrl": "...",
     "status": 200, "bytes": 123456, "sha256": "...", "fetchedAt": "...Z",
     "attempts": 1, "error": null}
    /* ... one row per request ... */
  ]
}
```

Cache-Control: `public, max-age=300`. Written at the end of the run via `put`.

### Orchestration — `src/kiekkokeskus/handler.py`

Shape (preserves init-02's injection points):

1. Log `invoked` with event (ADR-032 behavior preserved).
2. Compute `now_utc`, `run_date_et`, `data_date` (from event override or default).
3. **Fetch + archive** `schedule/{dataDate}` (ADR-006 — raw first). Then call pure
   `parse.schedule.extract(payload, data_date)` → `(season_or_none, game_ids: list[int])`.
   Unknown `gameState` is logged and skipped (ADR-013). `game_ids` is filtered to
   `gameType == 2` and `gameState in {"OFF", "FINAL"}` on `dataDate` (ADR-013, 014).
4. **Fetch + archive** `standings/{dataDate}`. Call pure
   `parse.standings.season_id(payload)` → `str | None`. **Season resolution** is now:
   `season = schedule_season or standings_season`. If **both** are None, log, set
   `season = None`, record the error, and **still write `_manifest.json`** (the schedule and
   standings raw files are already stored — the manifest is the main debugging artifact), then
   raise after the manifest write. `_health.json` is NOT written.
5. If `season` is known, fetch + archive the remaining endpoints in order: `club-schedule-season/TBL/{season}`,
   `club-stats/TBL/{season}/2` (ADR-014), each boxscore on `dataDate`, each skater-bios page,
   each goalie-bios page. For bios use `limit=1000` default; loop while
   `start + len(data) < total`.
6. For each endpoint: fetch → archive (immediately, before the next request). Record the manifest row.
7. Write `_manifest.json` **always** — on success and on failure. If **any** request failed after
   retries OR season couldn't be resolved OR schedule parse raised, raise after the manifest
   write and do **not** write `_health.json`.
8. On all-green: `_health.json` gains `dataDate` (string) and `rawCount` (int).
   `schemaVersion` stays 1 (additive).

Keep init-02's `forceError` and `source=="scheduled"` → `trigger=="schedule"` behavior.

### Infra Changes

No stack change in init-03. Lambda **code asset** changes (new modules); `cdk diff` must show
only the asset content difference (new `S3Key`), nothing else. If anything else is in the diff
→ STOP (CLAUDE.md Rule 1).

---

## Implementation Steps

### Step 0: Prereqs (no commit)

- Node 22 already installed (init-02 Step 0). `/opt/homebrew/opt/node@22/bin/node --version` → 22.x.
- `.venv` already set up. `.venv/bin/pytest` green.
- Scratch fetches confirmed; no AWS state change until Step 7.

### Step 1: `docs(03): start`

Move `init-03-collector-core` In Progress in `docs/TASK.md` (alongside init-02, which stays In
Progress until Steps 8–9 wrap up today). Update `*Last updated:*`. **Commit + push.**

### Step 2: `feat(03): date and season logic`

**Files**: `src/kiekkokeskus/season.py`, `tests/test_season.py`.

Pure dates. Tests cover:
- Run at **03:30 UTC Oct 4, 2026** → `run_date_et == 2026-10-03`, `data_date == 2026-10-02`
  (DST: ET is `-04:00` on Oct 4 → still prior day in ET from UTC early morning)
- DST transition **2026-11-01** (`-04:00` → `-05:00`): the run just before, on, and after all
  resolve the correct ET date; property-based parametrized test
- Event override valid (`"2026-04-01"`), malformed (`"4/1/26"`, `"2026-13-01"`), future (reject)

**Validation**: `.venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/pytest`.
Commit + push; wait for CI green.

### Step 3: `feat(03): fetch with retry and URL builders`

**Files**: `src/kiekkokeskus/nhl.py`, `tests/test_nhl.py`.

Tests (all with fake opener + fake sleep):
- URL builders produce exact-dated / exact-season URLs; a `grep -F 'now' <built-urls>` returns nothing
- 200 → one attempt, body returned, 250 ms post-pause applied
- 429 → 200: retried, `Retry-After` respected over the default backoff
- 500 ×3 → `FetchError` after 3 attempts
- 404 → immediate `FetchError`, zero retries
- Redirect: follows, logs, returns both `url` and `finalUrl`
- `sleep` receives the expected backoff sequence (property check)
- Defensive gzip-decoded response → body returned as plain JSON bytes

Commit + push; wait for CI green.

### Step 4: `feat(03): fetch_fixture script and captured fixtures`

**Files**: `scripts/fetch_fixture.py`, 10 captured fixtures (listed above) + the
`__unknown-state` variant, `tests/fixtures/README.md` with a provenance row per fixture,
`tests/test_schedule_parse.py`, `tests/test_bios_pagination.py`,
`docs/DECISIONS-DATA.md` (ADR-033 and the ADR-009 re-verify entry).

- `fetch_fixture.py` imports `nhl.py` to reuse User-Agent / politeness; writes
  `tests/fixtures/{slug}__{captureDateET}[__variant].json.gz`; appends a provenance row
  (file, URL, fetched-at UTC, HTTP status, variant of, ADR) to `tests/fixtures/README.md`.
- **Date convention**: the date in a fixture's filename is the **ET date it was captured**. The
  content's date (game date, standings date, bios season) lives in the **slug**. Today's
  captures all tag `__2026-10-03`.
- Variant: `schedule__2026-10-01__2026-10-03__unknown-state.json.gz` is a documented
  hand-mutation of the real schedule payload — change exactly one game's `gameState` to `"XYZ"`.
  The provenance row calls it out as the variant source + ADR-013.

**ADR-009 re-verification**: After capturing `standings__2026-04-01`, `__2026-10-01`,
`__2026-10-02`, diff `season` + `gamesPlayed` for TBL across the three dates:
- Expected (per ADR-009): `__2026-04-01` → season `20252026`, TBL ~74 GP; `__2026-10-01` →
  `20262027`, TBL 1 GP; `__2026-10-02` → `20262027`, TBL 1 GP.
- If confirmed: strike the "caveat: verified through a summarizing fetch, not raw diff" line
  from ADR-009 and add "Re-verified from raw: 2026-10-04".
- If **not** confirmed: write a new ADR in DECISIONS-DATA.md documenting the actual behavior and
  **STOP**. init-09 backfill planning depends on this.

Layer-1 parse tests (fed by real fixtures), module-by-module:
- `parse.schedule.extract(payload, data_date)` → `(season_or_none, game_ids)`: season from games
  on `dataDate`; `None` when no games on that date (even if the week has other days with games);
  completed reg-season IDs only (`gameType==2`, `gameState∈{OFF,FINAL}`); preseason excluded;
  FUT excluded; `__unknown-state` variant → logged (via `caplog`) and skipped
- `parse.standings.season_id(payload)` → `str | None`: returns `standings[0].seasonId` when
  present; `None` when standings is empty. Pure (no I/O, no clock).
- Bios pagination: with `limit=10` through a fake opener, 26 FIN skaters is fetched in 3 pages
  (10, 10, 6); no duplicates; stops at `total`.

Commit + push; wait for CI green.

### Step 5: `feat(03): raw archive and manifest`

**Files**: `src/kiekkokeskus/archive.py`, tests in `tests/test_handler_orchestration.py` or a
new `tests/test_archive.py`.

Tests:
- key format: `data/kiekkokeskus/raw/{runDateET}/{slug}.json.gz`
- headers: `Content-Type: application/json`, `Content-Encoding: gzip`, long immutable
  Cache-Control
- gzip round-trips to the original body bytes
- manifest round-trips: `_manifest.json` schema v1, every request row has `slug/url/finalUrl/status/bytes/sha256/fetchedAt/attempts/error`

Commit + push; wait for CI green.

### Step 6: `feat(03): collector orchestration`

**Files**: modify `src/kiekkokeskus/handler.py`, `tests/test_handler_orchestration.py`,
`scripts/smoke.py` (health now has `dataDate`), optional `scripts/rerun.py` (P1).

Tests (layer 3, injected fetch + put):
- Raw-before-parse: a parser raising still leaves the schedule's raw object stored.
- All keys under `data/kiekkokeskus/raw/{runDate}/…` except `_health.json`.
- Failure path: manifest written with the error, `_health.json` NOT written, handler raises.
- Success path: manifest lists every request; `_health.json` has `dataDate` and `rawCount`.
- **Season fallback via standings**: schedule has zero games on `dataDate` but standings has
  `seasonId` → season resolved from standings; downstream fetches still happen; run succeeds.
- **Both-missing case**: schedule and standings both yield no season →
  `_manifest.json` written with `season: null` and the error; `_health.json` NOT written; raises.
- init-02's `forceError`, trigger detection, and `_default_put` default-path tests still pass.
- Property: on a run with N fetches, exactly N raw-object `put` calls + 1 for `_manifest.json`
  + 1 for `_health.json` on success; on failure, N raw + 1 for `_manifest.json` and no `_health.json`.

Coverage ≥ 80% on `src/kiekkokeskus/`.

Commit + push; wait for CI green.

### Step 7: Deploy, invoke, seed (no commit)

1. `python scripts/deploy.py` (default) → prints `cdk diff`. **Verify only the Lambda code asset
   changes** (new `S3Key`). Show to user.
2. On `go`: `python scripts/deploy.py --approved` → deploys new code (ADR-032).
3. `aws lambda invoke --function-name kiekkokeskus-collector --profile default --region us-east-1 /tmp/out.json`
   with no payload → should return `{"status":"ok","key":"data/kiekkokeskus/_health.json"}` after
   writing all raw objects.
4. `aws s3 ls s3://jurigregg-static-site/data/kiekkokeskus/raw/2026-10-03/ --profile default` →
   every expected object + `_manifest.json`. Pull `_manifest.json` and confirm every entry has
   `error: null`.
5. Spot-check through CloudFront:
   `curl -s https://jurigregg.com/data/kiekkokeskus/raw/2026-10-03/standings__2026-10-02.json.gz | gunzip | head -c 300`.
6. `python scripts/smoke.py` passes.

If any of 3–6 fails: do **not** proceed to Step 8. Investigate from logs + the manifest.

### Step 8: `docs(03): ADR-008 supersede note, CLAUDE Rule 2, PLANNING, TASK` + `docs(03): complete`

**Files**: `docs/DECISIONS.md`, `CLAUDE.md`, `docs/PLANNING.md`, `docs/TASK.md`,
`prps/prp-03-collector-core.md` (status → Complete). (ADR-033 and the ADR-009 update already
landed in Step 4's DECISIONS-DATA.md commit — this commit covers the sibling docs.)

- `docs/DECISIONS.md` → **ADR-008**: append a "**Partially superseded by ADR-033**" note under
  Status. The season **source** is now `gameWeek[].games[].season` → `standings[0].seasonId`,
  because `currentSeason` is absent from `schedule/{date}` as actually observed. ADR-008's
  substantive rule — "resolve season from a payload; never compute; dated URLs, no `/now`" —
  still holds; ADR-033 only amends the field name and adds the standings fallback.
- `CLAUDE.md` **Rule 2** (NHL API rules) → update: "The season comes from the payload (schedule
  `games[].season` → standings `seasonId`), never computed (ADR-008 as amended by ADR-033)."
- `docs/PLANNING.md` → update the Architecture Overview and any inline mention of
  `currentSeason` to the new source. Add data-contract rows for `raw/{runDateET}/{slug}.json.gz`
  and `_manifest.json`.
- `docs/TASK.md` → `init-03-collector-core` → Recently Completed with a one-line outcome
  (coordinate wording with init-02 if it also closed today). Resolve or move the "off-season
  gap" question if listed under Open Questions.

Commit + push; wait for CI green; then flip PRP status: `docs(03): complete`.

---

## Testing Requirements

| Layer | Tests | Fixture / Gotcha |
|---|---|---|
| 1 Parse | schedule season extraction, completed-reg-season ID filter, pagination mechanics | 008 (no `/now`), 013 (OFF/FINAL + unknown-state variant), 014 (gameType 2), 011 (pagination); real `schedule__2026-10-01`, `__2026-09-26`, `__2026-12-15`, `skater-bios…p0`, `goalie-bios…p0` |
| 3 Orchestration | raw-before-parse, failure-path manifest, no `_health` on failure, prefix check, `forceError`, trigger detection | injected fetch + put |
| 4 Infra | existing jest from init-02 still green (no CDK changes); the Lambda asset digest changes but resources don't | — |
| 6 Smoke | `scripts/smoke.py` after deploy: `/`, `/sports`, `_health.json` with new `dataDate`+`rawCount` | — |
| 7 Manual | manifest spot-check; raw object spot-check through CloudFront | — |

Coverage floor stays at 80% on `src/kiekkokeskus/`.

---

## Error Handling and Edge Cases

| Case | Handling | Tested in |
|---|---|---|
| Zero games on `dataDate` AND standings has no `seasonId` | Log, record error, write `_manifest.json` with `"season": null` and the error (schedule/standings raw are already stored), raise. `_health.json` not written. | orchestration test (schedule+standings both yield no season) |
| Zero games on `dataDate` but standings has `seasonId` | Season from standings; club-stats/bios still fetched. One in-season gap day does NOT fail the run. | orchestration test (schedule empty for dataDate) |
| Game on `dataDate` has unknown `gameState` (e.g. `XYZ`) | Logged via `log.warning`, excluded; other games still processed (ADR-013) | layer-1 test with `__unknown-state` variant |
| 429 with `Retry-After: 7` | Respected over default backoff; attempt counter unchanged | fetch test |
| Non-429/5xx 4xx (e.g. 404) | Immediate `FetchError`, no retry; manifest row has `error: "<status>"` | fetch test |
| Redirect on a dated URL | Follows, logs warning, records both `url` and `finalUrl` in manifest | fetch test |
| One endpoint fails after 3 attempts | Manifest row has the error; subsequent endpoints still attempted; final step raises after writing manifest; `_health.json` not written | orchestration test |
| Response arrives gzip-encoded | Decompressed before archive; archive still stores a single gzip layer | fetch test |
| Re-run on the same `runDateET` | Overwrites raw/manifest; S3 versioning + ADR-023 lifecycle expires noncurrent in 7 days | manual Step 7 re-invoke |

---

## Cost Impact

Still ~$0/month. One extra Lambda run adds <1 s of compute; raw payloads are a few MB/day
(mostly the TBL season schedule), gzipped. ADR-023 expires noncurrent versions after 7 days.

---

## Rollback Plan

1. **Code**: `git revert` the PRP's commits in reverse order and push; S3 state survives.
   Previous Lambda version is redeployed via `python scripts/deploy.py --approved` on the
   reverted tree.
2. **Data (raw)**: raw objects for today's `runDateET` are new. **Only on Juri's explicit
   instruction**, delete just that prefix:
   `aws s3 rm --recursive s3://jurigregg-static-site/data/kiekkokeskus/raw/{runDateET}/ --profile default`.
   Never run this without the instruction and never widen the prefix.
3. **_health.json**: previous version retrievable via S3 VersionId (ADR-023 noncurrent 7 days).
4. **No infra teardown**: `cdk destroy` is not needed; this PRP only changed the Lambda asset.
   If it ever is needed, same gate as init-02's rollback (explicit instruction, no `--force`).

---

## Open Questions — none

---

## Confidence Scores

| Dimension | Score | Notes |
|---|---|---|
| Clarity | 9 | Spec is explicit; every endpoint, fixture, test row named. |
| Feasibility | 8 | Lots of pure modules + one orchestration; mostly offline testable; the deploy is a code-only change. |
| Completeness | 9 | Every Verify-in-PRP resolved; ADR-033 proposed; ADR-009 re-verification baked into Step 4. |
| Payload certainty | 8 | Three surprises resolved in verification: no `currentSeason` in schedule, `gameWeek` is 7-day, bios limit=1000 accepted. Residual uncertainty: ADR-009 re-verify may still contradict today's doc; if so, PRP stops and goes back. |
| **Average** | **8.5** | **Ready** |
