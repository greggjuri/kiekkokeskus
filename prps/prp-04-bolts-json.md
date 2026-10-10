# PRP-04: bolts.json Builder

**Created**: 2026-10-09
**Initial**: `initials/init-04-bolts-json.md`
**Status**: Complete
**ADRs**: ADR-003, 006, 008/033, 012–018, 020, 022, 030, 032, 034; **adds ADR-035** (field sources for `bolts.json`), **ADR-036** (standings definitions) — both in `docs/DECISIONS-DATA.md`

---

## Overview

### Problem Statement

The collector archives raw NHL data every morning (init-03), but nothing turns it into what the
`/bolts` page reads. This spec produces exactly one JSON file, with every field sourced and every
unit fixed, so init-07 is pure rendering.

### Proposed Solution

Add three stats REST endpoints to the manifest (summary, realtime, team-summary), write pure
parsers per endpoint family, write a pure builder that composes parsed inputs plus `dataDate`
into the `bolts.json` dict, add a **build phase** to the handler between `_manifest.json` and
`_health.json` that holds this run's bodies in memory and emits `bolts.json` with
`Cache-Control: public, max-age=300`. Builds that fail skip both `bolts.json` and `_health.json`
and raise. Golden-file test on real captured fixtures. Smoke adds a `bolts.json` check.

### Success Criteria

- [ ] 3 new endpoints verified, archived with `__` slugs, and listed in the manifest
- [ ] ADR-035 + ADR-036 land in `docs/DECISIONS-DATA.md`, gotcha-matrix rows added to TESTING.md
- [ ] Layer-1 tests per new parser + layer-2 golden `bolts.json` pass; coverage ≥ 80%
- [ ] Orchestration test: build failure → no `bolts.json`, no `_health.json`, raises
- [ ] `cdk diff` shows **only** the Lambda code asset change
- [ ] Manual invoke → `https://jurigregg.com/data/kiekkokeskus/bolts.json` 200 with `max-age=300`;
      record, rank, last game, and one skater line spot-check against NHL.com
- [ ] `smoke.py` checks `bolts.json`
- [ ] TASK.md: "hits and blocks source" resolved; "traded players" updated
- [ ] No code file over 500 lines (ADR-034)

---

## Context

### Related Documentation

- `docs/PLANNING.md`: Data Contract (adds `bolts.json`), Non-Functional §Freshness
- `docs/DECISIONS.md`: ADR-003, 006, 008/033, 020, 022, 030, 032, 034
- `docs/DECISIONS-DATA.md`: ADR-012–018, especially 015 (missing-at-0-GP), 016 (fractions not %),
  017 (TOI units), 018 (localized names), 030 (full rows, positionCode)
- `docs/TESTING.md`: Layer 1 (parsers, real fixtures), Layer 2 (builder goldens), Layer 3
  (orchestration — build-failure path), Layer 6 (smoke), Fixtures Rules

### Dependencies — init-03 complete (collector core + raw archive + `__` slugs).

### Files to Modify/Create

```
src/kiekkokeskus/nhl.py                              # MODIFY: url_skater_summary, url_skater_realtime, url_team_summary
src/kiekkokeskus/parse/standings.py                  # MODIFY: extend to one normalized row per team
src/kiekkokeskus/parse/club_stats.py                 # NEW: skater + goalie rows
src/kiekkokeskus/parse/stats_rest.py                 # NEW: summary / realtime / team-summary (reusable by init-05)
src/kiekkokeskus/parse/club_schedule.py              # NEW: reg-season games normalized
src/kiekkokeskus/build_bolts.py                      # NEW: pure build function (dict in, dict out)
src/kiekkokeskus/handler.py                          # MODIFY: build phase + bolts write + health "built"
scripts/smoke.py                                     # MODIFY: bolts.json check
scripts/build_local.py                               # NEW (P1): local build from a raw/ folder
tests/test_parse_standings.py                        # NEW
tests/test_parse_club_stats.py                       # NEW
tests/test_parse_stats_rest.py                       # NEW
tests/test_parse_club_schedule.py                    # NEW
tests/test_build_bolts.py                            # NEW: layer-2 golden
tests/test_handler_bolts.py                          # NEW: layer-3 (build-failure skips bolts + health)
tests/golden/bolts.json                              # NEW: golden fixture (reviewed in commit)
tests/fixtures/skater-summary-TBL__20262027__2026-10-09.json.gz   # NEW (captured)
tests/fixtures/skater-realtime-TBL__20262027__2026-10-09.json.gz  # NEW (captured)
tests/fixtures/skater-faceoff-TBL__20262027__2026-10-09.json.gz   # NEW (captured)
tests/fixtures/team-summary__20262027__2026-10-09.json.gz         # NEW (captured)
tests/fixtures/club-stats-TBL__20262027__2__2026-10-09.json.gz    # NEW (captured; one-day set)
tests/fixtures/club-schedule-season-TBL__20262027__2026-10-09.json.gz  # NEW (captured)
tests/fixtures/standings__2026-10-08__2026-10-09.json.gz          # NEW (captured; today's standings)
tests/fixtures/club-stats-TBL__20262027__2__2026-10-09__goalie-no-shots.json.gz  # NEW (variant for ADR-015)
tests/fixtures/skater-realtime-TBL__20262027__2026-10-09__player-missing.json.gz # NEW (variant for ADR-035 join)
tests/fixtures/README.md                             # MODIFY: provenance rows
docs/DECISIONS-DATA.md                               # MODIFY: ADR-035 + ADR-036
docs/TESTING.md                                      # MODIFY: gotcha-matrix rows for 035/036
docs/PLANNING.md                                     # MODIFY: Data Contract row for bolts.json
docs/TASK.md                                         # MODIFY: In Progress / Recently Completed
CLAUDE.md                                            # MODIFY: Quick Commands may add build_local
```

Largest expected code file: `build_bolts.py` ~250 lines; `parse/standings.py` grows to ~90.
All code stays under 500 (ADR-034); docs exempt.

---

## Verification of Unconfirmed Facts

| Assumption | Result | Follow-up |
|---|---|---|
| TBL-only `skater/summary` filter + fields | `?cayenneExp=gameTypeId=2 and teamAbbrevs="TBL" and seasonId=20262027&limit=100&start=0` → `{data,total}`, **total=20** today. Fields present: `playerId`, `skaterFullName`, `firstName`/`lastName` (strings here, not localized — see note), `positionCode`, `ppPoints`, `shootingPct` (fraction 0–1, e.g. `0.0909`), `faceoffWinPct` (fraction 0–1), `teamAbbrevs` (string, not plural object), `pointsPerGame`, `otGoals`. | Use. Localized names come from club-stats, not summary. |
| TBL-only `skater/realtime` filter + fields | Same filter works. `total=20`. Fields: `playerId`, **`hits`** (int), **`blockedShots`** (int), `takeaways`, `giveaways`. | Use. |
| `team/summary` fields and whether PP%/PK% are fractions | `powerPlayPct=0.0625`, `penaltyKillPct=0.777778` — **fractions 0–1** (ADR-016). `total=32`. | Use. Alongside: `powerPlayNetPct`, `penaltyKillNetPct` exist; stick to the non-"Net" fields (standard broadcast definition). |
| Traded players (club-stats vs summary with TBL filter) | **Can't fully resolve today** — no mid-season trade yet. Both endpoints return the same 20 TBL players with identical stats. | **Not a blocker; proceed as watch item.** ADR-035 records the asymmetry: `ppp`/`hits`/`blocks` come from `teamAbbrevs`-filtered stats REST and may include **other-team season totals** for traded players, while club-stats columns (gp, g, a, p, +/-, pim, toi/gp, sog, s%, ppg, shg, gwg) are TBL-only. Re-verify at the first TBL trade; add to **TASK.md Known Issues** in Step 8. |
| Faceoffs: distinguish "took none" from "won 0 %" | **Solved via a 4th stats REST endpoint**: `skater/faceoffpercentages` carries `totalFaceoffs` (int, attempts) alongside `faceoffWinPct` (fraction or `None`). Verified: Ryan McDonagh (D) today → `totalFaceoffs: 0`, `faceoffWinPct: None`. | Add `skater-faceoff-TBL__{season}` to the manifest. **Rule in ADR-035**: `faceoffPct = null when totalFaceoffs == 0`, else `faceoffWinPct` (already fraction 0–1 or `None`). Fallback (if the endpoint ever disappears): `null` when `positionCode == 'D'` OR `faceoffWinPctg == 0.0`. |
| Goalie TOI field + units in club-stats | `club-stats.goalies[].timeOnIce` → int **total seconds** (e.g. `10552`). Also `gamesStarted`, `wins`, `losses`, `savePercentage` (0.9), `goalsAgainstAverage` (float), `shutouts`. **`overtimeLosses`** is the OTL field (not `otLosses`). | Use. Spec said `otl` — maps to `overtimeLosses` here. |
| Club schedule: OT/SO outcome, home/away, ET date, opponent name | `gameOutcome.lastPeriodType` ∈ {`REG`,`OT`,`SO`}. `homeTeam.abbrev`/`awayTeam.abbrev` + `score` on each. `gameDate` is ET date string. Opponent name = `commonName` (localized `{default, fr?}`). Preseason: `gameType==1`; TBL season has 4 preseason + 84 reg-season entries. | Pass `commonName` (localized object) through as the opponent name. `commonName` has only `default` and sometimes `fr`, no `fi` — pages render `fi ?? default`. |
| Standings `wildcardSequence == 0` for division top-3 | **Verified** across all four divisions on 2026-10-08: `divisionSequence ∈ {1,2,3} → wildcardSequence == 0`; `divisionSequence ∈ {4,5,...} → wildcardSequence ∈ {1,2,3,4,...}`. **`teamName`** shape: `{"default": "New York Rangers", "fr": "Rangers de New York"}` — no `fi` key observed. `teamAbbrev` is also localized `{"default": "NYR"}` — flatten to the default string for `team.abbrev`. | ADR-036 holds. |

Scratch data lives in `/tmp/nhl-04/` during generation; fixtures committed in execution Step 1.

---

## Technical Specification

### URL builders — `nhl.py` additions

```python
def url_skater_summary(season: str, team: str = "TBL", *, start: int = 0, limit: int = 1000) -> str: ...
def url_skater_realtime(season: str, team: str = "TBL", *, start: int = 0, limit: int = 1000) -> str: ...
def url_skater_faceoff(season: str, team: str = "TBL", *, start: int = 0, limit: int = 1000) -> str: ...   # stats REST path: skater/faceoffpercentages
def url_team_summary(season: str, *, start: int = 0, limit: int = 1000) -> str: ...
```

`limit=1000` by default — well above any realistic team roster or 32-team league count, so a
single page is expected. The parser raises if `total > len(data)` (see **stats_rest** below).

`cayenneExp` for TBL skater endpoints: `gameTypeId=2 and teamAbbrevs="{team}" and seasonId={season}`.
For team-summary: `gameTypeId=2 and seasonId={season}` (all 32 teams).

### Output schema — `data/kiekkokeskus/bolts.json`

```jsonc
{
  "schemaVersion": 1,
  "generatedAt": "2026-10-09T14:00:12Z",
  "dataDate": "2026-10-08",
  "season": "20262027",
  "team": {"abbrev": "TBL", "name": {"default": "Lightning"}},
  "standing": {
    "gp": 4, "w": 3, "l": 1, "otl": 0, "pts": 6,
    "pointPct": 0.75,
    "gf": 15, "ga": 10,
    "streak": {"code": "W", "count": 2},
    "division": {"abbrev": "A", "rank": 2},
    "conference": {"abbrev": "E", "rank": 4},
    "leagueRank": 8,
    "divisionLead": {"leader": "OTT", "leaderPts": 6, "gap": 0, "gamesInHand": 0},
    "playoffLine": {"inPosition": true, "team": "BOS", "teamPts": 6, "gap": 0, "gamesInHand": 1}
    // Note (ADR-036): `divisionLead.gap` and `playoffLine.gap` are SIGNED ints. They can be ≤ 0
    // when standings order comes from tiebreakers. Never abs() them.
  },
  "lastGame": {"gameId": 2026020010, "date": "2026-10-08", "home": false,
    "opponent": {"abbrev": "NYR", "name": {"default": "Rangers", "fr": "Rangers de New York"}},
    "tblScore": 1, "oppScore": 5, "result": "L", "decidedIn": "REG"},
  "nextGames": [
    {"gameId": 2026020089, "date": "2026-10-10", "startTimeUTC": "2026-10-11T00:00:00Z",
     "home": true, "opponent": {"abbrev": "DET", "name": {"default": "Red Wings"}}}
  ],
  "specialTeams": {"ppPct": 0.0625, "pkPct": 0.777778, "ppRank": 28, "pkRank": 10},
  "skaters": [ /* one row per club-stats skater; see table in init-04 */ ],
  "goalies":  [ /* one row per club-stats goalie */ ]
}
```

- `schemaVersion` **unchanged** elsewhere; this file is new.
- Null policy: ADR-015 — fields absent at 0 GP come through as `null`. `shootingPct` is `null`
  when `shots == 0`. `faceoffPct` is `null` when `positionCode == 'D'` (ADR-035 rule).
- Headshots and logos: **dropped**. ADR-003 + ADR-002.
- All fractions 0–1 (ADR-016). All TOI int seconds (ADR-017). All names localized (ADR-018).

### Module design — parsers (all pure, dict in, dict/list out, no I/O, no clock)

**`parse/standings.py`** (extend). Keeps `season_id(payload)`. New:
```python
def rows(payload: dict) -> list[dict]: ...        # one per team with the 15 fields from init-04 table
def tbl_row(payload: dict) -> dict | None: ...    # convenience
def division_leader(rows: list[dict], division: str) -> dict | None: ...
def playoff_line(rows: list[dict], team: str) -> dict: ...   # ADR-036 definitions
```

**`parse/club_stats.py`** (new):
```python
def skaters(payload: dict) -> list[dict]: ...     # localized names, int TOI seconds, dropped `headshot`
def goalies(payload: dict) -> list[dict]: ...     # maps `overtimeLosses` → `otl`, keeps int `toi`
```

**`parse/stats_rest.py`** (new; reused by init-05):
```python
def by_player_id(payload: dict, fields: list[str]) -> dict[int, dict]: ...  # for summary/realtime/faceoff
def team_rows(payload: dict) -> dict[str, dict]: ...                        # for team/summary, keyed by teamFullName (lookup helper below)
def check_complete(payload: dict, slug: str) -> None: ...                   # raise if total > len(data)
```

**Pagination guard** (per PRP update): `check_complete(payload, slug)` raises `StatsRestTruncated`
when `payload["total"] > len(payload["data"])`. The handler calls it after fetching each stats
REST body. Rationale: today's TBL roster = 20 and league = 32, well under `limit=1000`. Rather
than add pagination that will never trigger, we raise loudly if NHL ever returns > 1000 — the
operator chooses to bump the limit or add pagination in a follow-up PRP.

**`parse/club_schedule.py`** (new):
```python
def games_regular_season(payload: dict) -> list[dict]: ...   # filter gameType==2 (ADR-014)
def last_completed_before(games: list[dict], team: str, data_date: date) -> dict | None: ...
def next_games_after(games: list[dict], data_date: date, limit: int = 3) -> list[dict]: ...
```

Opponent handling: for each game, pick `homeTeam` if `awayTeam.abbrev == team` else `awayTeam`;
pass `{abbrev, name: commonName}` through.

### Builder — `src/kiekkokeskus/build_bolts.py` (pure)

```python
def build(
    *,
    data_date: date,
    season: str,
    now_iso: str,
    standings_payload: dict,
    club_stats_payload: dict,
    club_schedule_payload: dict,
    skater_summary_payload: dict,
    skater_realtime_payload: dict,
    skater_faceoff_payload: dict,
    team_summary_payload: dict,
) -> dict: ...
```

Builds the envelope + sections per the schema above. The join on `playerId`:
`skaters = club_stats.skaters` → union-left with `summary` (gets `ppPoints`), `realtime`
(gets `hits`, `blockedShots`), and `faceoff` (gets `totalFaceoffs`, `faceoffWinPct`). A player
missing from any of them keeps the row; those fields become `null` (ADR-030 full-rows,
ADR-035 join rule). `faceoffPct` is `null when totalFaceoffs == 0` else `faceoffWinPct` (ADR-035). Special-teams rank: rows filtered to
`gamesPlayed > 0`, sorted by `powerPlayPct`/`penaltyKillPct` descending, standard competition
ranking (1-2-2-4) for ties.

### Handler build phase — `src/kiekkokeskus/handler.py`

Add a new step after the manifest write and before the health write:

```python
# ... existing: fetch+archive each endpoint, keep bodies in memory ...
# ... existing: write _manifest.json ...

if had_error:
    raise RuntimeError(...)   # existing

# Build phase
try:
    bolts = build_bolts.build(
        data_date=data_date, season=season, now_iso=iso_z(now_utc),
        standings_payload=bodies["standings"],
        club_stats_payload=bodies["club-stats"],
        club_schedule_payload=bodies["club-schedule-season"],
        skater_summary_payload=bodies["skater-summary"],
        skater_realtime_payload=bodies["skater-realtime"],
        skater_faceoff_payload=bodies["skater-faceoff"],
        team_summary_payload=bodies["team-summary"],
    )
except Exception as e:
    log.error(json.dumps({"event": "build_failed", "builder": "bolts", "error": str(e)}))
    raise

body = json.dumps(bolts, separators=(",", ":")).encode()
put(f"{PREFIX}bolts.json", body, "application/json", "public, max-age=300", None)
built = ["bolts"]

# Health write gets built=[...]; schemaVersion stays 1
_write_health(..., built=built)
```

`bodies` is a dict keyed by endpoint-family that `_fetch_and_archive` populates on each
successful fetch (new, local to the handler run). Build runs only when `had_error == False`
(existing invariant).

### Infra — `cdk diff`

Lambda code asset change only (new slugs → new zip hash). No construct changes. If **anything**
non-`kiekkokeskus-*` appears in the diff, STOP (CLAUDE.md Rule 1).

---

## Implementation Steps

Each step is one commit, pushed; CI green before the next.

### Step 0: Prereqs

Working tree clean, Steps 0–7 of init-03 complete. No AWS state change in Steps 1–3.

### Step 1: `docs(04): start`

TASK.md: `init-04-bolts-json` → In Progress; `*Last updated:*`. Commit + push.

### Step 2: `feat(04): stats REST endpoints in manifest`

**Files**: `src/kiekkokeskus/nhl.py` (3 URL builders), `src/kiekkokeskus/handler.py` (append the 3
endpoints to the orchestrated fetch list after bios, under the `season is known` branch), tests
in `tests/test_nhl.py` (URL assertions — segments, no `/now`, `cayenneExp` content).

Also capture the 6 new fixtures via `scripts/fetch_fixture.py` into `tests/fixtures/`, add the 2
variants (`__goalie-no-shots` from the real club-stats, `__player-missing` from realtime by
removing one TBL playerId), and append provenance rows (ADR-012/015/035 tags).

**Validation**:
- `.venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/pytest -q`
- No new runtime deps.

Commit + push; wait for CI green.

### Step 3: `feat(04): standings, club-stats, club-schedule, stats-rest parsers`

**Files**: `src/kiekkokeskus/parse/standings.py` (extend), `parse/club_stats.py` (new),
`parse/stats_rest.py` (new), `parse/club_schedule.py` (new), + layer-1 tests fed real fixtures.

Each test file covers at minimum:
- **standings**: `rows()` returns 32; `tbl_row()` finds TBL; 0-GP team (use
  `standings__2026-10-02__2026-10-03.json.gz`) → missing keys become `null` (ADR-015);
  `division_leader` returns the `divisionSequence==1` team; `playoff_line` on an in-position
  team uses `wildcardSequence==3` opponent; on an out-of-position team uses `wildcardSequence==2`.
  **Signed-gap test** (ADR-036): craft a mini standings dict where TBL and the reference team
  have equal points but TBL ranks higher by tiebreaker → `gap == 0` (not abs); and where
  the reference team has fewer points but ranks higher → `gap < 0`. Assert the sign is preserved.
- **club_stats**: skater names stay localized; `avgTimeOnIcePerGame` float → int seconds; shots==0
  → `shootingPct=null`; D-position → `faceoffPct=null`; `headshot` dropped; goalie TOI stays int
  total seconds; `overtimeLosses` → `otl`; `__goalie-no-shots` variant → `svPct=null`, `gaa=null`.
- **stats_rest**: `by_player_id(summary, ["ppPoints"])` and `by_player_id(realtime, ["hits","blockedShots"])`;
  `team_rows(team_summary)` keyed by lookup usable by builder; verifies PP%/PK% stay fractions.
- **club_schedule**: regular-season filter; `last_completed_before(2026-10-08)` for TBL returns
  a game with `gameOutcome.lastPeriodType` as `decidedIn`; `next_games_after` orders ascending.

**Validation**: `.venv/bin/pytest -q`, coverage ≥ 80%.

Commit + push.

### Step 4: `feat(04): build_bolts + golden`

**Files**: `src/kiekkokeskus/build_bolts.py`, `tests/test_build_bolts.py`, `tests/golden/bolts.json`.

Golden-file test: feed all 6 real fixtures + fixed `now_iso="2026-10-09T14:00:12Z"` and
`data_date=2026-10-08`; assert the produced dict equals `tests/golden/bolts.json` byte-for-byte
(json-canonical sorted keys). Unit guards: every fraction ∈ [0, 1] ∪ {None}; every TOI is `int`;
every name is `dict`; no raw NHL float TOI leaks through.

Golden regeneration: a `--update-golden` env var (`UPDATE_GOLDEN=1 pytest`) overwrites
`tests/golden/bolts.json` for intentional changes — diff reviewed in the commit.

**Validation**: tests green; the golden file is checked in; manual eyeball of top-level fields.

Commit + push.

### Step 5: `feat(04): build phase in handler`

**Files**: `src/kiekkokeskus/handler.py` (build phase + `bodies` collection + `_write_health`
with `built=[]`), `tests/test_handler_bolts.py`.

New orchestration tests (layer 3, inject fetch + put):
- Happy path: all fetches 200 → `bolts.json` written with `max-age=300`; `_health.json` includes
  `built: ["bolts"]`; `schemaVersion` stays `1`.
- **Build failure**: inject a `build_bolts.build` that raises → `bolts.json` **not** written,
  `_health.json` **not** written, handler raises; `_manifest.json` already written in prior step.
- Existing invariant preserved: a fetch error short-circuits before build runs; neither bolts
  nor health is written.
- init-02/03 tests still pass with the extended `_write_health` signature.

**Validation**: full suite green; coverage ≥ 80%.

Commit + push.

### Step 6: `feat(04): smoke checks bolts.json`

**Files**: `scripts/smoke.py` adds a check: `GET bolts.json` 200, `cache-control` contains
`max-age=300`, body JSON parses, `schemaVersion==1`, `dataDate` present and matches the health
file's `dataDate` (do the health GET first, pass along), `len(skaters) >= 1`.

**Validation**: `.venv/bin/python -m py_compile scripts/smoke.py`; test green.

Commit + push.

### Step 7: Deploy, invoke, verify (no commit)

Interactive — needs user go.

1. `.venv/bin/python scripts/deploy.py` → shows `cdk diff`. Only the Lambda code asset should change.
2. On `go`: `.venv/bin/python scripts/deploy.py --approved`.
3. `aws lambda invoke --function-name kiekkokeskus-collector --profile default --region us-east-1 --cli-binary-format raw-in-base64-out --payload '{}' /tmp/out.json`.
4. `aws s3 ls s3://jurigregg-static-site/data/kiekkokeskus/raw/{todayET}/` — expect 3 new slugs
   (`skater-summary-TBL__...`, `skater-realtime-TBL__...`, `team-summary__...`) plus the
   existing set. `_manifest.json` all `error: null`. `bolts.json` present.
5. `curl -sI https://jurigregg.com/data/kiekkokeskus/bolts.json | grep -i cache-control`.
6. `.venv/bin/python scripts/smoke.py`.
7. Spot-check against NHL.com: TBL record, division rank, last game result and score, one
   skater's G/A/P/TOI. Report each result inline.

### Step 8: `docs(04): ADR-035/036, TESTING, PLANNING, TASK` + `docs(04): complete`

**Files**: `docs/DECISIONS-DATA.md` (add **ADR-035** + **ADR-036**), `docs/TESTING.md`
(gotcha-matrix rows), `docs/PLANNING.md` (data contract row), `docs/TASK.md`,
`prps/prp-04-bolts-json.md` → Complete.

**ADR-035** content must include:
- Field-source table (per init-04).
- **Faceoff rule**: `faceoffPct = null when totalFaceoffs == 0` (from `skater/faceoffpercentages`),
  else `faceoffWinPct` (fraction). Fallback rule if the endpoint disappears: `null when
  positionCode == 'D'` OR `faceoffWinPctg == 0.0`.
- **Traded-players asymmetry**: club-stats columns (gp, g, a, p, +/-, pim, toi/gp, sog, s%,
  ppg, shg, gwg) are TBL-only; `teamAbbrevs`-filtered stats REST fields (`ppp`, `hits`, `blocks`)
  may include other-team season totals for a player who played elsewhere earlier in the season.
  **Re-verify at first TBL trade.**
- `stats_rest.check_complete` guard: raises when `total > len(data)`.

**ADR-036** content must include:
- Division-lead definition (`divisionSequence==1`; `gamesInHand = leader.gp - tbl.gp`, can be
  negative when TBL has played more).
- Playoff-line two-case definition (in-position / out-of-position), referencing
  `wildcardSequence==3` and `==2` respectively.
- **Signed gaps**: `playoffLine.gap` and `divisionLead.gap` are **signed integers**. They can be
  ≤ 0 when standings order comes from tiebreakers (e.g., TBL in position but behind the division
  leader by tiebreaker with equal points → `divisionLead.gap = 0`; a team *just ahead* in points
  can still rank below TBL by tiebreakers, producing a negative gap). **Never `abs()` them.**
- Rank rule: PP%/PK% ranks over teams with `gamesPlayed > 0`, standard-competition ranking
  (1-2-2-4), 1 = best.

**TASK.md updates**:
- Resolve "hits and blocks source" → stats REST `skater/realtime`.
- Move "traded players" from Open Questions to **Known Issues**: "ppp/hits/blocks may include
  other-team totals from the `teamAbbrevs`-filtered stats REST endpoints while club-stats is
  TBL-only; re-verify at first TBL trade (ADR-035)."
- Move init-04 to Recently Completed.

**TESTING.md** gets gotcha-matrix rows for:
- **ADR-035** join resilience: a player missing from `summary`/`realtime`/`faceoff` keeps the
  row with those fields `null`.
- **ADR-036** reference teams: in-position (ref = wildcard-3), out-of-position (ref = wildcard-2);
  **gap sign preserved** (test with a crafted tiebreaker scenario).

Commit + push; wait for CI green; then flip status with a trivial `docs(04): complete` commit.

---

## Testing Requirements

| Layer | Tests | Fixture / Gotcha |
|---|---|---|
| 1 Parse | per-parser real-fixture tests (standings 015, club-stats 015/017/018, club-schedule 014, stats-rest 016) | 10 captured + 2 variants |
| 2 Builder | `test_build_bolts.py` golden-file; unit guards on units/types | `tests/golden/bolts.json` |
| 3 Orchestration | `test_handler_bolts.py` happy path + build-failure path; init-02/03 tests still pass | injected fetch + put |
| 4 Infra | existing jest unchanged (no CDK diff beyond code asset) | — |
| 6 Smoke | `bolts.json` check | — |
| 7 Manual | NHL.com spot-check: record, rank, last game, one skater | — |

Coverage floor stays at 80% on `src/kiekkokeskus/`.

---

## Error Handling and Edge Cases

| Case | Handling | Tested in |
|---|---|---|
| 0-GP standings fields missing (OTT today) | `.get()` → `null` output (ADR-015) | parse_standings test |
| 0-shots goalie missing `savePercentage`/`goalsAgainstAverage` | parser emits `null` (ADR-015) | club-stats `__goalie-no-shots` |
| Skater missing from `summary` or `realtime` (traded, not yet synced, late scratch) | row kept via club-stats; `ppp`/`hits`/`blocks` = `null` (ADR-035) | realtime `__player-missing` |
| Defenseman faceoff percentage | `faceoffPct = null` when `positionCode == 'D'` (ADR-035) | club-stats test |
| OT/SO result on `lastGame` | from `gameOutcome.lastPeriodType` ∈ {REG,OT,SO} | club-schedule test |
| No completed TBL games yet (first days of season, hypothetical) | `lastGame = null` | club-schedule test |
| Build raises | handler logs `event: build_failed`, raises; no `bolts.json`, no `_health.json`; manifest already written | handler-bolts test |

---

## Cost Impact

~$0/month. 3 extra GETs per daily run (small payloads).

---

## Rollback Plan

1. **Code**: `git revert` PRP commits in reverse order and push. S3 state survives.
2. **Data**: `bolts.json` versioning + ADR-023 lifecycle keep 7 days of noncurrent versions.
   To restore the prior version, `aws s3api copy-object` by VersionId. **Only on Juri's explicit
   instruction** should any delete happen; `aws s3 rm` is scoped to the prefix if used.
3. **Raw**: new raw objects under `raw/{today}/` are additive; nothing to clean up.
4. **Infra**: no CDK changes to roll back. `cdk destroy` is **never** run without explicit
   instruction (ADR-032 posture; same gate as prior PRPs).

---

## Open Questions — none

---

## Confidence Scores

| Dimension | Score | Notes |
|---|---|---|
| Clarity | 9 | Spec is explicit; every field has a source + units; definitions in ADR-036 are unambiguous. |
| Feasibility | 8 | Six moving parts (3 endpoints, 4 parsers, 1 builder, handler build phase) + a golden; mostly offline-testable. |
| Completeness | 9 | Every Verify item resolved. Two residual watch items (traded players, faceoff attempts) have documented rules in ADR-035, not blocking. |
| Payload certainty | 8 | Three sources verified live against today's 2026-10-08/09 data; traded-player behavior is "watch, not known". |
| **Average** | **8.5** | **Ready** |
