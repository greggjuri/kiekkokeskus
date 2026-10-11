# PRP-05: leijonat.json Builder

**Created**: 2026-10-10
**Initial**: `initials/init-05-leijonat-json.md`
**Status**: Complete
**ADRs**: ADR-003, 006, 010–018, 022, 028, 030, 033, 035; **adds ADR-037** (DECISIONS-DATA.md)

---

## Overview

### Problem Statement

The collector archives Finn bios and last-night boxscores daily, but nothing turns them into
what `/leijonat` reads. This spec produces `data/kiekkokeskus/leijonat.json` so init-08 is pure
rendering.

### Proposed Solution

Add four nationality-filtered stats REST endpoints to the manifest (`skater/summary`,
`skater/realtime`, `skater/faceoffpercentages`, `goalie/summary` with
`nationalityCode="FIN"`), plus two `isRookie=1` lookups (skaters + goalies) and a **club-stats
fan-out** across the ~19 distinct current teams of a Finn to pick up the `fi`-localized
`lastName` keys (stats REST ASCII-fies some Finnish names). Add `parse/bios.py` and
`parse/boxscore.py`, write `src/kiekkokeskus/build_leijonat.py`, make the handler run **two
independent builders** (bolts + leijonat) so one failure doesn't freeze the other, extend smoke
to check `leijonat.json`, and document everything in ADR-037. **Every fetch — including the two
rookie lookups and each of the ~18 club-stats fan-out fetches — is a potential failure point
that fails the whole run** (CLAUDE.md "never silently catch"); the collector's HTTP retries
mitigate transient failures.

### Success Criteria

- [ ] 4 FIN stats REST endpoints + 2 rookie-filter endpoints verified, archived, guarded by
      `check_complete`, and in the manifest
- [ ] Club-stats fan-out for Finn teams works (TBL fetch is reused — not duplicated)
- [ ] ADR-037 in `docs/DECISIONS-DATA.md`, gotcha-matrix rows in `docs/TESTING.md`
- [ ] Layer-1 tests (`parse/bios.py`, `parse/boxscore.py`, stats REST additions) + layer-2
      golden `leijonat.json` pass; coverage ≥ 80%
- [ ] Orchestration tests: `bolts` fails → `leijonat.json` written, no health, raises;
      `leijonat` fails → `bolts.json` written, no health, raises
- [ ] `cdk diff` shows **only** the Lambda code asset change
- [ ] Live `https://jurigregg.com/data/kiekkokeskus/leijonat.json` serves with `max-age=300`;
      Finn count, one last-night line, one skater line, one goalie line match NHL.com
- [ ] Umlaut names present (`Määttä`, `Teräväinen`)
- [ ] `smoke.py` checks `leijonat.json`
- [ ] No code file over 500 lines (ADR-034). `handler.py` is extracted into a `build_phase`
      helper if it grows close.

---

## Context

### Related Documentation

- `docs/PLANNING.md`: Data Contract (adds `leijonat.json`), Key Constraints 2/3/8 (~50 req/run budget)
- `docs/DECISIONS.md`: ADR-003, 006, 022, 028
- `docs/DECISIONS-DATA.md`: ADR-010–018, 030, 033, 035
- `docs/TESTING.md`: Layer 1 (parsers), Layer 2 (builder golden), Layer 3 (orchestration — the
  two-independent-builders case), Layer 6 (smoke)

### Dependencies — init-03 + init-04 complete.

### Files to Modify/Create

```
src/kiekkokeskus/nhl.py                              # MODIFY: 4 FIN URL builders + 2 rookie-filter + reuse url_club_stats
src/kiekkokeskus/parse/bios.py                       # NEW: merge pages, split skater/goalie, dup detection
src/kiekkokeskus/parse/boxscore.py                   # NEW: game context + per-player rows
src/kiekkokeskus/parse/stats_rest.py                 # MODIFY (if any): goalie-row shaping only if needed
src/kiekkokeskus/build_leijonat.py                   # NEW
src/kiekkokeskus/handler.py                          # MODIFY: additional fetches, bodies collection, two-builder phase
src/kiekkokeskus/build_phase.py                      # NEW (extracted): run_builders() to keep handler.py < 500
scripts/smoke.py                                     # MODIFY: leijonat.json check
scripts/build_local.py                               # NEW (P1): compose both bolts + leijonat from local raw/
tests/test_parse_bios.py                             # NEW
tests/test_parse_boxscore.py                         # NEW
tests/test_build_leijonat.py                         # NEW: layer-2 golden
tests/test_handler_leijonat.py                       # NEW: independent-builder-failure tests
tests/golden/leijonat.json                           # NEW
# Fixtures captured today (ET 2026-10-10):
tests/fixtures/skater-summary-FIN__20262027__2026-10-10.json.gz          # NEW
tests/fixtures/skater-realtime-FIN__20262027__2026-10-10.json.gz         # NEW
tests/fixtures/skater-faceoff-FIN__20262027__2026-10-10.json.gz          # NEW
tests/fixtures/goalie-summary-FIN__20262027__2026-10-10.json.gz          # NEW
tests/fixtures/skater-rookies-FIN__20262027__2026-10-10.json.gz          # NEW (summary with isRookie=1)
tests/fixtures/goalie-rookies-FIN__20262027__2026-10-10.json.gz          # NEW (0 rows today; still captured)
tests/fixtures/skater-bios-FIN__20262027__p0__2026-10-10.json.gz         # NEW: fresh for 30 Finns
tests/fixtures/goalie-bios-FIN__20262027__p0__2026-10-10.json.gz         # NEW: fresh for 5 Finns
tests/fixtures/schedule__2026-10-09__2026-10-10.json.gz                  # NEW: data_date = 2026-10-09
tests/fixtures/standings__2026-10-09__2026-10-10.json.gz                 # NEW
tests/fixtures/club-stats-{TEAM}__20262027__2__2026-10-10.json.gz        # NEW: 19 Finn teams
tests/fixtures/boxscore__{gameId}__2026-10-10.json.gz                    # NEW: every completed game on 2026-10-09
# OT + SO boxscores captured for ADR-037 last-night derivations (real, not hand-mutated):
tests/fixtures/boxscore__2026020025__2026-10-10.json.gz                  # CAR @ PHI 2026-10-03, OT
tests/fixtures/boxscore__2026020065__2026-10-10.json.gz                  # TOR @ VGK 2026-10-08, SO
# Variants (hand-mutated):
tests/fixtures/skater-summary-FIN__20262027__2026-10-10__player-missing.json.gz  # ADR-035 join
tests/fixtures/skater-bios-FIN__20262027__p0__2026-10-10__duplicate.json.gz      # ADR-011 dup detection
tests/fixtures/skater-bios-FIN__20262027__p0__2026-10-10__name-suffix-mismatch.json.gz  # Fix 4 raise case
tests/fixtures/README.md                             # MODIFY: provenance rows
docs/DECISIONS-DATA.md                               # MODIFY: ADR-037
docs/TESTING.md                                      # MODIFY: gotcha rows for 037 (+ existing 010/011/012/015/018)
docs/PLANNING.md                                     # MODIFY: data contract row
docs/TASK.md                                         # MODIFY
```

Largest expected code file: `build_leijonat.py` ~260 lines; `handler.py` kept well under 500 by
the `build_phase.py` extraction.

---

## Verification of Unconfirmed Facts

| Assumption | Result | Follow-up |
|---|---|---|
| `nationalityCode="FIN"` on all 4 stats REST endpoints + totals | **All work** with `gameTypeId=2 and nationalityCode="FIN" and seasonId=20262027&limit=1000`. Totals today: `skater/summary=30`, `skater/realtime=30`, `skater/faceoffpercentages=30`, `goalie/summary=5`. **Matches bios totals** (30 skaters, 5 goalies). | Use. All 4 endpoints single-page with `check_complete` guard (ADR-035). |
| Bios w/o `gameTypeId` leaks preseason-only Finns | **No.** Bios without filter returns the same 30 Finns as with `gameTypeId=2`. Bios with `gameTypeId=1` only returns 0 FIN players (preseason-only). | Keep bios URL unchanged; ADR-037 records "verified identical on 2026-10-10". |
| Umlaut source for `Määttä`/`Teräväinen`/`Meriläinen` | **Stats REST summary and bios are ASCII** for most names (`Olli Maatta`, `Teuvo Teravainen`) — but inconsistent (`Aatu Räty` has `ä`). **club-stats `lastName` carries `fi` key** (e.g. `MIN.Maatta → {default:"Maatta", fi:"Määttä"}`; `CHI.Teravainen → fi:"Teräväinen"`). | **P0.6 outcome**: use the **club-stats fan-out**. Fetch `club-stats/{team}/{season}/2` for each distinct current team of a Finn (**19 teams today**; TBL is already fetched by init-04 — reuse, not re-fetch). Costs ~18 extra requests. ADR-037 records the chosen source. |
| Current team field + traded shape | Bios has `currentTeamAbbrev` (string). Summary row has `teamAbbrevs` (string today: just the current team's abbrev for today's non-traded Finns). **Traded shape unknown** — no mid-season trade yet. | Use **`bios.currentTeamAbbrev`** as authoritative. Watch item on `teamAbbrevs` shape at first trade; mirrors ADR-035's Known Issue. |
| Rookie: `isRookie` field or filter | **No `isRookie` field** in rows. **`isRookie=1` works as a `cayenneExp` filter.** Today: 4 FIN rookie skaters (Hyry, Ottavainen, Lambert, Helenius); 0 FIN rookie goalies. | Use the filter. **Two extra 1-page fetches** per run: `skater/summary` with `isRookie=1` and `goalie/summary` with `isRookie=1`. Build the rookie-id set, flag Finns in the main set. **`rookie` is a non-null bool**; if either fetch fails, the manifest row errors and the whole run fails (existing invariant). |
| Summary units | `timeOnIcePerGame=1172.4` (**float seconds per game**, same as club-stats convention — ADR-017). `shootingPct=0.25` (fraction 0–1). `faceoffWinPct` fraction. Goalie `savePct=0.79611` (fraction). Goalie `timeOnIce=11237` (**int total seconds**). | Builder emits int seconds; parser normalizes float → int. |
| Boxscore shape | Confirmed: `playerByGameStats.{awayTeam,homeTeam}.{forwards,defense,goalies}`. Skater fields: `playerId`, `name` (localized, initials), `position`, `goals`, `assists`, `points`, `plusMinus`, `pim`, `hits`, `blockedShots`, `sog`, `toi` (`"MM:SS"` string → int seconds, ADR-017), `faceoffWinningPctg`. Goalie fields: `playerId`, `name`, `saves`, `shotsAgainst`, `savePctg` (fraction), `decision` (`W`/`L`/`O`/`None`), `starter` (bool), `toi` (`"MM:SS"`). Non-starter today → `decision=None, savePctg=None, starter=False` (ADR-015). | Use. **`decision` value `O` for OT losses** (verify in a captured OT game; fallback: derive OTL from `gameOutcome.lastPeriodType != "REG"` + the team losing). |

Request budget: current pipeline is ~20 requests. Add 4 FIN stats REST + 2 rookie + 18 club-stats
= **~44 per run**, within the "~50" PLANNING budget (Key Constraint 8).

---

## Technical Specification

### URL builders — `nhl.py` additions

```python
def _stats_rest_nationality_url(path: str, season: str, nationality: str,
                                 start: int, limit: int, is_rookie: bool = False) -> str: ...

def url_skater_summary_nationality(season, nationality="FIN", *, start=0, limit=1000): ...
def url_skater_realtime_nationality(season, nationality="FIN", *, start=0, limit=1000): ...
def url_skater_faceoff_nationality(season, nationality="FIN", *, start=0, limit=1000): ...
def url_goalie_summary_nationality(season, nationality="FIN", *, start=0, limit=1000): ...
def url_skater_rookies_nationality(season, nationality="FIN", *, limit=1000): ...   # cayenneExp += " and isRookie=1"
def url_goalie_rookies_nationality(season, nationality="FIN", *, limit=1000): ...
```

Existing `url_club_stats(team, season)` is reused for the fan-out.

### Output schema — `data/kiekkokeskus/leijonat.json`

Follows the init-05 contract. Envelope + `teams[]`, `lastNight{date,gamesCompleted,skaters[],goalies[]}`,
`skaters[]`, `goalies[]`. `schemaVersion: 1` (new file).

### Parser modules

**`parse/bios.py`** (pure):
```python
def merged(pages: list[dict]) -> dict:
    """Merge all skater/goalie bios pages. Raise on duplicate playerId (ADR-011)."""
    # returns {"skaters": {pid: row}, "goalies": {pid: row}}
```

**`parse/boxscore.py`** (pure):
```python
def game_context(payload: dict) -> dict:
    """id, homeTeam.abbrev/score, awayTeam.abbrev/score, state, decidedIn."""

def player_rows(payload: dict) -> list[dict]:
    """One row per player with team (abbrev), position, playerId, name, and the stat columns.
       Skater toi 'MM:SS' → int seconds (ADR-017). Goalie savePctg/decision None at 0 shots
       (ADR-015)."""
```

**`parse/stats_rest.py`**: no shape changes needed — `by_player_id` already works for the
goalie summary and the faceoff endpoint.

### Builder — `src/kiekkokeskus/build_leijonat.py` (pure)

```python
def build(
    *,
    data_date: date,
    season: str,
    now_iso: str,
    bios_skater_pages: list[dict],          # fed by handler
    bios_goalie_pages: list[dict],
    summary_payload: dict,
    realtime_payload: dict,
    faceoff_payload: dict,
    goalie_summary_payload: dict,
    rookie_skater_ids: set[int],            # from skater-rookies-FIN
    rookie_goalie_ids: set[int],
    name_fi_overrides: dict[int, dict],     # playerId → {firstName: {default, fi?}, lastName: {default, fi?}}
    boxscore_payloads: list[dict],          # yesterday's completed games (schedule-filtered)
    schedule_payload: dict,                 # for lastNight.gamesCompleted
    standings_payload: dict,                # for teams[].name (teamName)
) -> dict: ...
```

- **Row set** = bios Finns (skaters + goalies). Never drop; ADR-030, ADR-035 join rule.
- **Name resolution** (per `playerId`, in order):
  1. **Scan every club-stats payload in the fan-out** (`bodies["club-stats-by-team"].values()`
     — not just the Finn's current team's). This catches a traded Finn who still appears in
     his old team's club-stats roster for a day after a trade.
  2. **Fallback via bios**: use `bios.lastName` as `{default}`. For `firstName`, take
     `bios.{skaterFullName,goalieFullName}` and check whether it ends with `" " + lastName`.
     If so, strip that suffix and emit `{default: firstName_stripped}`. **Log a warning
     with the playerId.**
  3. **If the suffix doesn't match** (e.g. `fullName` doesn't end with `" {lastName}"`),
     **raise** `NameSuffixMismatch`. Payload surprise; same posture as `BiosDuplicateError`
     (ADR-011). The whole run fails, the alarm fires, we fix the parser on next day.
- Resolved names are localized objects `{default, fi?}` (ADR-018). **Never pick a language**
  (ADR-028).
- **Last night**: `gamesCompleted = len([g for w in schedule.gameWeek if w.date == dataDate
  for g in w.games if g.gameType == 2 and g.gameState ∈ {OFF, FINAL}])` (ADR-033: `gameWeek`
  is a 7-day window, filter to `dataDate` first). Boxscores are joined by `playerByGameStats`.
  Includes Finn skater if `points ≥ 1`; Finn goalie if `starter == True` (ADR-012). Row order:
  skaters by `p` desc then `g` desc then `lastName.default` asc; goalies by `svPct` desc nulls
  last, then `lastName.default`. Game-level `result` / `decidedIn` are derived from the
  **boxscore's** `gameOutcome.lastPeriodType` + score comparison (not the goalie's `decision`).
- **Teams block**: aggregate by `bios.currentTeamAbbrev` with counts of
  `{skaters, goalies}`. Order by `(skaters+goalies) desc, abbrev asc`.
- **Rookie flag**: `playerId in rookie_*_ids` → `True`; else `False`. **Non-null bool.** A failed
  rookie fetch fails the whole run (handler short-circuits before build) — the builder is only
  called with both rookie id sets present.

### Handler build phase — split into `build_phase.py`

```python
def run_builders(bodies, data_date, season, now_iso) -> tuple[dict[str, dict], dict[str, Exception]]:
    """Returns (outputs, errors). Each builder runs in its own try. Independent."""
```

Handler calls it, writes each successful output to its S3 key with `max-age=300` + `null`
encoding, writes `_health.json` **only when `errors` is empty**, and raises after the write if
`errors` is non-empty.

### Infra — `cdk diff`

Lambda code asset change only (new slugs → new zip hash). No construct changes.

---

## Implementation Steps

Each step is one commit, pushed; CI green before the next.

### Step 0: Prereqs

Clean tree. init-03 + init-04 complete.

### Step 1: `docs(05): start`

TASK.md: `init-05-leijonat-json` → In Progress. Commit + push.

### Step 2: `feat(05): FIN stats REST endpoints in manifest`

**Files**: `src/kiekkokeskus/nhl.py` (6 URL builders: 4 FIN stats REST + 2 isRookie variants),
`src/kiekkokeskus/handler.py` (append fetches + `bodies["summary-FIN"]`, `["realtime-FIN"]`,
`["faceoff-FIN"]`, `["goalie-summary-FIN"]`, `["rookies-FIN"]`, `["goalie-rookies-FIN"]`), URL
tests in `tests/test_nhl.py`.

Capture 8 fixtures via `scripts/fetch_fixture.py` with explicit `--slug`:
- `skater-summary-FIN__20262027`, `skater-realtime-FIN__20262027`,
  `skater-faceoff-FIN__20262027`, `goalie-summary-FIN__20262027`
- `skater-rookies-FIN__20262027`, `goalie-rookies-FIN__20262027`
- `skater-bios-FIN__20262027__p0`, `goalie-bios-FIN__20262027__p0` (fresh)
- `schedule__{data_date}`, `standings__{data_date}` where data_date = 2026-10-09

Plus every boxscore for `data_date` (fetch via `scripts/fetch_fixture.py` iterating the
schedule's completed games), plus two **real-OT/SO reference boxscores** captured specifically
for ADR-037 last-night derivation tests:
- `2026020025` — CAR @ PHI, 2026-10-03, `lastPeriodType=OT`
- `2026020065` — TOR @ VGK, 2026-10-08, `lastPeriodType=SO`

Commit + push.

### Step 3: `feat(05): club-stats fan-out for FI names`

**Files**: `src/kiekkokeskus/handler.py` adds the fan-out, **ordered after both bios page loops
have completed** (because the fan-out needs `bios.currentTeamAbbrev` to pick teams).

Logic:
```python
# After bios fetches (both skater + goalie pages) and after the TBL club-stats fetch:
teams_with_finns = {
    row.get("currentTeamAbbrev")
    for pages in (bios_skater_pages, bios_goalie_pages)
    for page in pages
    for row in page.get("data", [])
    if row.get("currentTeamAbbrev")   # skip null currentTeamAbbrev (unsigned / free agent)
}
# TBL is already fetched by init-04; add its payload to the by-team dict without re-fetching.
bodies["club-stats-by-team"] = {}
if "club-stats" in bodies:
    bodies["club-stats-by-team"]["TBL"] = bodies["club-stats"]   # reference, no re-fetch
for team in sorted(teams_with_finns - {"TBL"}):
    payload = _fetch_and_archive(...)
    if payload is not None:
        bodies["club-stats-by-team"][team] = payload
```

**Keep `bodies["club-stats"]` as the TBL-only payload** that `build_bolts` already reads;
`bodies["club-stats-by-team"]` is the new dict that includes TBL by reference plus the fan-out.

Capture 18 fresh `club-stats-{team}__20262027__2__2026-10-10.json.gz` fixtures (the 19 Finn
teams minus TBL — TBL's fixture already exists from init-04). Append provenance rows.

**Order assertion** in `test_handler_leijonat.py`: a mock fetch records the order of fetched
URLs and asserts that `skater/bios` and `goalie/bios` complete before any fan-out
`club-stats/{team}/...` URL other than `TBL`'s. Also assert no team is fetched twice.

Commit + push.

### Step 4: `feat(05): bios and boxscore parsers`

**Files**: `src/kiekkokeskus/parse/bios.py`, `src/kiekkokeskus/parse/boxscore.py`,
`tests/test_parse_bios.py`, `tests/test_parse_boxscore.py`.

**bios tests** (fed real fixtures, including a hand-mutated duplicate variant):
- `merged([single page])` → correct skater/goalie split with 30/5 Finns
- Two-page split merges, no dupes (verify via synthetic 2-page shim)
- Duplicate `playerId` across pages → raises `BiosDuplicateError`
- Kapanen (FIN nationality, SWE birth) included (ADR-010)

**boxscore tests** (fed real captured OT + SO boxscores — no hand-mutated variant):
- `game_context` returns `{id, home: {abbrev, score}, away: {abbrev, score}, state, decidedIn}`
- `player_rows` returns one row per player across both teams
- Skater `toi` `"14:18"` → `858` int seconds (ADR-017)
- Non-starter goalie: `savePctg=None, decision=None, starter=False` (ADR-015)
- Goalie `"MM:SS"` TOI → int seconds; `"00:00"` → 0
- **Goalie `decision` passes through as-is from the payload** — the builder does **not**
  assert specific string values; init-05's `build_leijonat` derives `game.result` and
  `game.decidedIn` from `gameOutcome.lastPeriodType` + score comparison, independent of
  `decision`.
- **OT reference fixture (`boxscore__2026020025__2026-10-10.json.gz`, CAR @ PHI 2026-10-03)**:
  `decidedIn == "OT"`; the losing team's `game.result == "OTL"`.
- **SO reference fixture (`boxscore__2026020065__2026-10-10.json.gz`, TOR @ VGK 2026-10-08)**:
  `decidedIn == "SO"`; the losing team's `game.result == "OTL"`.

Commit + push.

### Step 5: `feat(05): build_leijonat + golden`

**Files**: `src/kiekkokeskus/build_leijonat.py`, `tests/test_build_leijonat.py`,
`tests/golden/leijonat.json`.

Golden: fed all captured fixtures + fixed `data_date=2026-10-09`, `now_iso`, `season=20262027`.
Generate with `UPDATE_GOLDEN=1 pytest`; review the diff in the commit.

Tests cover:
- Envelope: `schemaVersion==1`, `dataDate`, `season`, `generatedAt`
- **Umlaut names present**: `Määttä` (MIN), `Teräväinen` (CHI), `Meriläinen` wherever applicable.
  Specifically assert `lastName.fi == "Määttä"` for Olli Määttä (playerId 8476874).
- Row counts: `len(skaters)==30`, `len(goalies)==5` (matches today's totals)
- Join resilience variant: a Finn removed from summary → row kept, `g/a/p/...` all `None`
- Teams block: order correct, ≤32 teams, every count ≥ 1
- Last night: Finn skater on 1+ pts included; Finn skater on 0 pts excluded; starter goalie
  included; relief goalie excluded; `gamesCompleted` matches schedule
- `rookie: True` for the 4 skater IDs; `False` otherwise; goalie all `False`
- Unit guards: every fraction ∈ [0, 1] ∪ {None}; every TOI is `int`; every name is `dict`

Commit + push.

### Step 6: `feat(05): independent builders in handler`

**Files**: `src/kiekkokeskus/build_phase.py` (new, extracted), `src/kiekkokeskus/handler.py`
(call `run_builders`, write each output, write health only on all-green),
`tests/test_handler_leijonat.py`.

Orchestration tests (layer 3, inject fetch + put):
- Happy path: both builders succeed → `bolts.json` + `leijonat.json` written; health has
  `built: ["bolts", "leijonat"]`; `schemaVersion==1`.
- **Bolts fails, leijonat succeeds**: `leijonat.json` IS written; `bolts.json` NOT written;
  `_health.json` NOT written; handler raises.
- **Leijonat fails, bolts succeeds**: mirror — `bolts.json` written, `leijonat.json` not,
  no health, raises.
- Both fail → neither file written, no health, raises.
- Rookie-fetch failure (whole stats REST endpoint): manifest row errored → run fails before
  the build phase (existing invariant). (Add a cheap test that confirms this preserves init-04
  behavior.)

Also update **`test_build_failure_skips_bolts_and_health_and_raises`** from init-04 (now:
`bolts.json` NOT written because the mock makes `build_bolts.build` raise; `leijonat.json`
written if its stubbed inputs let it succeed, or NOT if the stubs make it also raise). I'll
split that test into the two directions above.

`handler.py` line count check: `wc -l src/kiekkokeskus/handler.py` < 500 after extraction.

Commit + push.

### Step 7: `feat(05): smoke checks leijonat.json`

**Files**: `scripts/smoke.py`. Add checks:
- `GET /data/kiekkokeskus/leijonat.json` → 200
- `cache-control` contains `max-age=300`
- `schemaVersion == 1`
- `dataDate` equals **`bolts.json`**'s `dataDate` (ADR-032: health is ops-only; do not compare
  data files against the health file). Smoke now captures `bolts.json`'s `dataDate` before the
  leijonat check.
- `len(skaters) >= 1`
- health's `built` list contains `"leijonat"`

Commit + push.

### Step 8: Deploy + verify (no commit)

1. `python scripts/deploy.py` → **show diff**. Only Lambda code asset should change.
2. On user `go`: `python scripts/deploy.py --approved`.
3. Manual invoke: expect `{"status":"ok","rawCount":~44,"built":["bolts","leijonat"]}`.
4. `aws s3 ls` the raw prefix: expect ~18 club-stats + 4 FIN + 2 rookie + the existing TBL + bios + boxscores + 2 league.
5. Pull `_manifest.json`: every row `error: null`.
6. `curl -sI https://jurigregg.com/data/kiekkokeskus/leijonat.json` → `cache-control: public, max-age=300`.
7. `.venv/bin/python scripts/smoke.py` → all PASS.
8. Spot-check against NHL.com:
   - Finn count (today: 30 skaters + 5 goalies)
   - Last night: a Finn who scored (I'll pick one from today's games)
   - One season skater row (e.g. Aho or Barkov — top scorers)
   - One goalie row (e.g. Lankinen)
   - `Olli Määttä` and `Teuvo Teräväinen` carry umlauts via `fi` key

### Step 9: `docs(05): ADR-037, TESTING, PLANNING, TASK` + `docs(05): complete`

**Files**: `docs/DECISIONS-DATA.md` (ADR-037 content below), `docs/TESTING.md` (gotcha rows),
`docs/PLANNING.md` (data contract row), `docs/TASK.md`, `prps/prp-05-leijonat-json.md` → Complete.

**ADR-037 must include**:
- Field-source map for `leijonat.json`.
- **Name resolution order** (Fix 4):
  1. Scan every club-stats payload in the fan-out dict by `playerId` (not just the Finn's
     current team's — catches a just-traded Finn still on the old team's roster).
  2. Fallback: bios `lastName` + suffix-strip of `*FullName`. Warning logged with `playerId`.
  3. Suffix mismatch → raise `NameSuffixMismatch`. Payload surprise; run fails.
- Name source: club-stats fan-out chosen because stats REST ASCII-fies most Finnish names
  (verified 2026-10-10). TBL's club-stats fetch is reused by reference. ~18 extra requests per run.
- Rookie source: `isRookie=1` cayenneExp filter (two 1-page fetches per run — skater + goalie).
  **`rookie` is a non-null bool**; a failed rookie fetch fails the whole run (CLAUDE.md
  "never silently catch", existing invariant).
- **Fan-out failure semantics (Fix 8)**: each of the ~24 extra fetches (4 FIN + 2 rookie +
  ~18 club-stats) is **a new way the whole run can fail** — any single failed fetch means
  **neither builder runs** and neither page updates (existing invariant: no build on
  `had_error`). Accepted for now given the collector's 3-attempt backoff retries. **Revisit
  if a single team's club-stats regularly fails a run.** Candidate future ADR: let the name
  fallback cover a missing team's payload instead of failing — but today that risks silent
  wrong-name output on a trade day, so the strict posture holds.
- `teams[].name` from standings `teamName` (localized `{default, fr?}`, no `fi` observed).
- `lastNight.gamesCompleted` filters `schedule.gameWeek` to **`date == dataDate`** first
  (ADR-033: `gameWeek` is 7-day), then counts `gameType == 2 and gameState ∈ {OFF, FINAL}`.
- `lastNight` inclusion rule (points ≥ 1 for skater; `starter == True` for goalie) and the
  `result`/`decidedIn` derivation using `gameOutcome.lastPeriodType` + score comparison from
  the boxscore. Goalie `decision` is passed through raw and **not** used for `result`.
- Preseason-only bios: **verified** today's bios without `gameTypeId` filter returns the same
  30 Finns as with `gameTypeId=2`; no URL change needed.
- **Traded Finns**: season totals across teams (opposite of ADR-035's TBL-only posture).
  `team` from `bios.currentTeamAbbrev`. The `teamAbbrevs` shape under multi-team seasons
  is unknown today — **re-verify at first FIN trade** (TASK.md Known Issues).
- Bios pagination duplicate detection: raise `BiosDuplicateError`, don't silently dedupe
  (ADR-011).

**TESTING.md gotcha rows for ADR-037**:
- Umlaut name resolution via club-stats `fi` key: `Määttä` / `Teräväinen` asserted
- Preseason-only Finn filter: verified empty (no URL change)
- Name resolution step 1: Finn found via a non-current-team's club-stats (crafted scenario)
- Name resolution fallback: bios lastName + suffix-stripped firstName, warning logged
- Name resolution raise: `*FullName` doesn't end with `" " + lastName` → `NameSuffixMismatch`
- OT: real captured boxscore `2026020025` → `result="OTL"` for the loser, `decidedIn="OT"`
- SO: real captured boxscore `2026020065` → `result="OTL"` for the loser, `decidedIn="SO"`
- Fan-out ordering: bios fetches complete before any non-TBL `club-stats/{team}` fetch
- Two-independent-builder failure modes (bolts fails / leijonat fails / both fail)

**TASK.md updates**:
- `init-05-leijonat-json` → Recently Completed with outcome
- Up Next → `init-06-shared-ui` (Phase 3)
- Resolve/update: **FIN save % format** stays (init-06), **chart rendering** stays (init-09),
  **raw/ publicly served** stays
- Known Issues: add "FIN traded players: stats REST `teamAbbrevs` shape unknown; re-verify at
  first FIN mid-season trade (ADR-037)". The existing ADR-035 trade watch item stays separate.

Commit + push; wait for CI green; flip PRP status with trailing `docs(05): complete`.

---

## Testing Requirements

| Layer | Tests | Fixture / Gotcha |
|---|---|---|
| 1 Parse | `test_parse_bios.py` (merge, dup detection — ADR-011; Kapanen FIN/SWE — ADR-010); `test_parse_boxscore.py` (game_context, player_rows, `MM:SS`→int — ADR-017, non-starter goalie nulls — ADR-015, OT variant for `decision`) | 10 captured + 2 variants |
| 2 Builder | `test_build_leijonat.py` golden; umlaut assertion; rookie flag; teams count; last-night inclusion rule | `tests/golden/leijonat.json` |
| 3 Orchestration | `test_handler_leijonat.py`: two independent builders, bolts-fail / leijonat-fail / both-fail / all-green | injected fetch + put |
| 4 Infra | jest unchanged | — |
| 6 Smoke | `leijonat.json` + `built` includes "leijonat" | — |
| 7 Manual | NHL.com spot-check | — |

Coverage floor: 80% on `src/kiekkokeskus/`.

---

## Error Handling and Edge Cases

| Case | Handling | Tested in |
|---|---|---|
| Finn not found in his current team's club-stats but found in another team's (just-traded) | step 1 scans the whole fan-out dict by playerId; row emitted with the other team's name (may have `fi`). | build-leijonat test with a crafted scenario |
| Finn not in any club-stats payload | step 2 fallback: bios `lastName`, firstName via suffix-strip of `*FullName`; warning logged with playerId; row still emitted. | build-leijonat test with a crafted missing-everywhere scenario |
| Suffix mismatch during fallback | step 3: raise `NameSuffixMismatch`; whole run fails loudly. | build-leijonat test with a crafted bios row where `fullName` doesn't end with `" " + lastName` |
| Rookie fetch failed | handler short-circuits before build phase (existing invariant). Empty rookie body (fetch OK but 0 rows) → all `rookie=False`, run succeeds. | orchestration test |
| Finn missing from `summary`/`realtime`/`faceoff` | row kept from bios; those fields `None` (ADR-035) | build-leijonat variant test |
| Bios duplicate playerId across pages | `BiosDuplicateError` raised; handler recorded as error → run fails | parse-bios test |
| Game went to OT/SO | boxscore `gameOutcome.lastPeriodType ∈ {OT,SO}`; losing team's `game.result == "OTL"`; `game.decidedIn` carries OT/SO | boxscore `__ot-win` variant |
| Zero completed games on `dataDate` | `lastNight.skaters[]` and `[]` empty; `gamesCompleted = 0`; builder doesn't raise | synthetic empty-schedule test |
| Build raises for leijonat only | bolts.json written; leijonat.json NOT written; no health; handler raises | orchestration test |
| Build raises for bolts only | leijonat.json written; bolts.json NOT written; no health; handler raises | orchestration test |
| Both builds raise | neither file written; no health; raises | orchestration test |

---

## Cost Impact

~$0/month. ~24 extra GETs per daily run (4 FIN stats REST + 2 rookie + ~18 club-stats fan-out).
Still well below the ~50/run PLANNING budget.

---

## Rollback Plan

1. **Code**: `git revert` the PRP's commits in reverse order and push. S3 state survives.
2. **Data**: `leijonat.json` versioning + ADR-023 lifecycle keep 7 days of noncurrent versions.
   Restore prior version via `aws s3api copy-object` by VersionId. **Only on Juri's explicit
   instruction** should any delete happen; `aws s3 rm` scoped to the single prefix if used.
3. **Raw**: new raw objects (18 club-stats + 4 FIN + 2 rookie) are additive under
   `data/kiekkokeskus/raw/{runDate}/`. Nothing to clean up unless explicitly instructed.
4. **Infra**: no CDK changes to roll back. `cdk destroy` is **never** run without explicit
   instruction (ADR-032 posture).

---

## Open Questions — none

---

## Confidence Scores

| Dimension | Score | Notes |
|---|---|---|
| Clarity | 9 | Spec is explicit; every field has a source + units; two-independent-builder design is clear. |
| Feasibility | 8 | Many moving parts (6 new URL builders, 2 new parsers, 1 builder, handler extraction, 24 extra fetches), but each piece is well-scoped and offline-testable. |
| Completeness | 9 | All 7 Verify items resolved. Residual: traded-FIN shape under watch (mirrors ADR-035). |
| Payload certainty | 9 | Everything verified live against 2026-10-10 data. Umlaut source clean (club-stats fi); rookie filter clean. |
| **Average** | **8.75** | **Ready** |
