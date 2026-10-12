# Kiekkokeskus - Testing Standards

## The One Rule

**Test the contract, not just the arithmetic.** The input to this system is an undocumented API
that omits keys, mislabels units, and changes without notice. A suite fed only well-formed,
hand-written rows will pass and prove nothing. That exact failure cost Tilastokeskus five defects
(its D-44).

So:
- Fixtures are **real archived payloads**.
- Every payload gotcha in `DECISIONS-DATA.md` has a fixture that contains it and a test that fails
  if the gotcha is mishandled.
- A new gotcha found in production gets an ADR, a fixture, and a test before the fix, in that
  order.

## Test Layers

| Layer | What | Where | Tool | When |
|---|---|---|---|---|
| 1. Parse contract | `parse/*` against real payloads and the gotcha matrix | `tests/test_parse_*.py` | pytest | every change |
| 2. Builders | fixture set → `bolts.json`/`leijonat.json`, compared to golden output | `tests/test_build_*.py` | pytest | every change |
| 3. Orchestration | handler with a fake fetcher and fake store: failure modes, write order | `tests/test_handler.py` | pytest | every change |
| 4. Infra | synthesized template asserts we own nothing we shouldn't | `infra/test/` | jest + CDK `Template` | every infra change |
| 5. Page logic | sort, filter, i18n, formatters, URL state (pure JS) | `site/kiekkokeskus/*.test.js` | `node --test` | every page change |
| 6. Smoke | live URLs after deploy | `scripts/smoke.py` | Python stdlib | after every deploy |
| 7. Manual | browser checklist | below | eyes | after page changes |

```bash
pytest --cov=kiekkokeskus --cov-report=term-missing   # 1–3, coverage ≥ 80% on src/
cd infra && npm test                                   # 4
node --test "site/kiekkokeskus/*.test.js"              # 5 (no npm deps in site/; Node 22 needs the glob)
python scripts/smoke.py                                # 6
```

CI (GitHub Actions) runs layers 1–5 on every push. Layers 6 and 7 run from the MacBook after a
deploy.

## Fixtures

### Rules
1. **Captured, never typed.** Use `python scripts/fetch_fixture.py <url>`, which saves the gzipped
   body plus provenance (URL, fetch time, HTTP status) to `tests/fixtures/`.
2. **Naming**: `{archive-slug}__{captureDateET}[__{variant}].json.gz`. The archive slug is the
   endpoint name (dashes OK) joined to each parameter by **`__`** (double underscore). The
   capture date in ET goes after another `__`. Examples:
   - archive: `standings__2026-10-02.json.gz`
   - fixture: `standings__2026-10-02__2026-10-03.json.gz` (standings-for-2026-10-02 captured on 2026-10-03 ET)
   - archive: `club-stats-TBL__20262027__2.json.gz`
   - fixture + variant: `schedule__2026-10-01__2026-10-03__unknown-state.json.gz`

   Archive → fixture mapping: the fixture filename is the archive slug + `__{captureDateET}`
   (+ optional `__{variant}`). The archive slug itself is produced by the collector in
   `handler.py` and by `scripts/fetch_fixture.py` from the URL path.
3. **Variants** are the only allowed hand edits: a real payload with one documented mutation used
   to force a gotcha that no captured payload contains. The variant name says what changed
   (`__goalie-no-shots`), and `tests/fixtures/README.md` records which ADR it serves.
4. **Fixtures are immutable.** If the NHL changes shape, capture a new dated fixture and keep the
   old one. Both must parse, or the old one is explicitly retired by an ADR.
5. Raw archives from production (`data/kiekkokeskus/raw/`) are valid fixture sources: copy them,
   don't refetch.

### Gotcha Matrix (required coverage)

Each row is at least one test. Add a row when DECISIONS-DATA gains an ADR.

| ADR | Gotcha | Fixture must contain | Assert |
|---|---|---|---|
| 008 | `/now` redirects | n/a (URL builder) | built URLs contain explicit date/season, never `now` |
| 009 | dated standings | `standings__2026-04-01`, `__2026-10-01` | parser handles both seasons; `dataDate` = requested date |
| 010 | nationality ≠ birthplace | bios row for Kapanen (FIN/SWE) | included as a Finn |
| 011 | bios pagination | multi-page bios (or `limit` forced small) | all `total` rows collected, no dupes, stops at `total` |
| 011 | goalies separate | `goalie-bios` | goalies present, typed as goalies |
| 012 | boxscore join | boxscore with a Finn (Tolvanen, 2026-10-01) | Finn found by `playerId`; non-Finns excluded |
| 012 | "registered a point or started" | Finn skater with 0 pts; Finn goalie who started | skater excluded, goalie included |
| 013 | game states | `OFF`, `FINAL`, `FUT`, plus variant `__unknown-state` | first two done; others not; unknown logged, not crashed |
| 014 | preseason in schedule | season schedule with `gameType: 1` | excluded from every aggregate |
| 015 | 0-GP standings keys missing | `standings__2026-10-02` (has 0-GP teams) | keys present in OUR output as `null`; no KeyError |
| 015 | goalie faced no shots | boxscore variant `__goalie-no-shots` | `savePctg`/`decision` → `null` |
| 016 | `*Pctg` not percentages | standings with EDM `goalsForPctg: 7.0` | passed through as per-game value; fractions stay 0–1 |
| 017 | TOI formats | club-stats (float s) + boxscore (`"MM:SS"`) | both → same integer seconds |
| 018 | localized names | row with `fi` key (Kucherov) + row with only `default` | object passed through untouched |
| 030 | full rows + position | club-stats / bios | every player emitted with `positionCode`; no top-N cut |
| 035 | join resilience when a stats REST side is missing a player | `skater-realtime-...__player-missing` | row kept from club-stats; `hits`/`blocks`/`ppp`/`faceoffPct` → `null` |
| 035 | faceoffPct rule — "took none" vs "won 0 %" | `skater-faceoff-TBL__...` with a D-position player | `faceoffPct = null when totalFaceoffs == 0`; else fraction 0–1 |
| 035 | pagination guard | synthetic `{data: 1 row, total: 999}` | `stats_rest.check_complete` raises; manifest row errored; run fails |
| 036 | playoff line — in-position reference is wildcard 3 | real standings with TBL in Atlantic top-3 | reference team is conference `wildcardSequence==3` |
| 036 | playoff line — out-of-position reference is wildcard 2 | synthetic standings | reference team is conference `wildcardSequence==2` |
| 036 | gap sign preserved | synthetic standings with equal points / tiebreaker ordering | `gap` can be 0 or negative; never `abs()`-ed |
| 037 | umlaut names via club-stats fan-out | real MIN + CHI club-stats, 2026-10-10 | `Olli Määttä` and `Teuvo Teräväinen` carry `fi` key through to `leijonat.json` |
| 037 | name step 1 — scan all fan-out payloads | crafted scenario | Finn found via a non-current-team's club-stats (just-traded case) |
| 037 | name step 2 — suffix-strip fallback | bios row with `*FullName == "<first> <lastName>"` | emits `{default: first}` + `{default: lastName}`, warning logged |
| 037 | name step 3 — suffix mismatch raises | crafted bios row where fullName doesn't end with `" " + lastName` | `NameSuffixMismatch` raised; run fails |
| 037 | preseason-only bios filter | FIN bios with `gameTypeId=1` | returns 0 FIN players — no URL change needed |
| 037 | OT decidedIn | real boxscore `2026020025` (CAR @ PHI 2026-10-03) | `gameOutcome.lastPeriodType == "OT"`; builder derives loser's `result == "OTL"` from score |
| 037 | SO decidedIn | real boxscore `2026020065` (TOR @ VGK 2026-10-08) | `lastPeriodType == "SO"`; loser's `result == "OTL"` |
| 037 | fan-out ordering | handler orchestration | bios fetches complete before any non-TBL `club-stats/{team}` fetch |
| 037 | two independent builders — bolts fails | mock `build_bolts.build` raises | `leijonat.json` written; `bolts.json` + `_health.json` not; raises |
| 037 | two independent builders — leijonat fails | mock `build_leijonat.build` raises | `bolts.json` written; `leijonat.json` + `_health.json` not; raises |
| 037 | bios duplicate playerId | 2-page split with repeated row | `BiosDuplicateError` raised; no silent dedupe (ADR-011) |

#### Page logic (Layer 5, ADR-038 unless noted)

| ADR | Gotcha | Fixture / input | Assert |
|---|---|---|---|
| 015 | null in any column | golden `faceoffPct: null` (bolts McDonagh) | renders `–` (U+2013); sorts last in asc and desc |
| 018 | partial FI name — `lastName.fi` only | golden Vasilevskiy (`firstName.default` only + `lastName.{default, fi, cs, sk}`) | FI: `Andrei Vasilevski`; EN: `Andrei Vasilevskiy` |
| 018 | extra name languages | golden Teräväinen (`cs`/`sk`/`sv` keys) | passed through untouched; no crash |
| 028 | missing i18n key | every EN key present in FI and reverse | strict parity, failing with the diff list |
| 038 | FI minus and NBSP | `signed(-1, {en,fi})`, `pct1Sign(0.143, 'fi')` | U+2212 in both langs; FI pct has NBSP U+00A0 between `3` and `%` |
| 038 | `pct1` ×100 (not raw fraction) | `pct1(0.143, {en,fi})` | EN `14.3`, FI `14,3` (never `0.1`/`0,1`) |
| 038 | `rate3` edges | `0.9`, `1.0`, `0.0` | EN `.900/1.000/.000`; FI `90,00/100,00/0,00` (exact strings, no trailing `%`/NBSP) |
| 038 | goalie season TOI | `toi(10552, {en,fi})` | EN `175:52`, FI `175.52` |
| 038 | date west of UTC | child `node` with `TZ=America/Los_Angeles` calls `date('2026-10-02','en')` | `Oct 2, 2026` (not `Oct 1`); UTC-noon parse holds |
| 038 | gameTime day rollover | child `node` with `TZ=Europe/Helsinki`, input `2026-10-10T23:30:00Z` | FI matches `/^su 11\.10\. klo 02\.30/u` (whole reason gameTime uses viewer tz) |
| 038 | stale boundary | `isStale(gen, gen ± 36h)` | false at 35h59m, true at 36h01m, false at exactly 36h00m |
| 038 | schema mismatch | stub `fetchFn` returns `{ schemaVersion: 2 }` | `{ ok: false, reason: 'schema' }`, no throw |

#### Page logic — init-07 additions

| ADR | Gotcha | Fixture / input | Assert |
|---|---|---|---|
| 036 | signed gaps from Tampa's view | synthetic `divisionLead.gap: 4`; `playoffLine` out-of-position, `gap: 2` | tiles show `−4`; `Below the playoff line` + value `−2` |
| 036 | TBL leads division | `divisionLead: {leader:'TBL', gap:0}` | tile value `0`, label `'Division leader'` (EN) / `'Divisioonan kärjessä'` (FI). Live-authentic 2026-10-11 (TBL first in Atlantic) |
| 038 | signed(-0) renders `0` | `signed(-0, {en,fi})` | returns `'0'` — not `'-0'`, not `'+0'`; locked by Intl `exceptZero` |
| 040 | games in hand both signs + zero | `gamesInHand` = `1`, `-2`, `0` | `' · 1 game in hand'`; `' · 2 more games played'`; clause omitted when `0` |
| 015 | 0 GP state (page view) | `streak:null`, `lastGame:null`, `nextGames:[]`, `specialTeams.ppPct:null, ppRank:null` | no streak text in record sub; `view.lastGame === null`; empty nextGames; `special.pp.pct === '–'`; `rank === null` |
| 040 | OT / SO suffix | `decidedIn` = `OT`, `SO`, `REG` | last-game suffix `'OT'` / `'SO'` (FI `'JA'` / `'VL'`); nothing on `REG` |
| 040 | ordinals | 1, 2, 3, 4, 11, 12, 13, 21, 22, 101, 111 | EN `1st 2nd 3rd 4th 11th 12th 13th 21st 22nd 101st 111th`; FI `n.` |
| 040 | plural units | `pts` = 1 and 6 | EN `1 pt` / `6 pts`; FI `1 p` / `6 p` |
| 040 | fetch once | counting `fetchFn`, mount, then `setLang` + `setPos` + `setSort` + `setGsort` | `fetchFn.callCount === 1`; `render` called 5 times (1 start + 4 dispatches) with the same data identity. Live-verified on `/bolts` via `performance.getEntriesByType('resource')` |
| 040 | langExplicit survives | `setLang('fi')` then `setPos('d')` then `setSort('g','desc')` | fake `history.replaceState` tape's last entry still contains `lang=fi` |
| 040 | result badges | `result` `W` / `L` / `OTL` | EN `W` / `L` / `OTL`; FI `V` / `H` / `JH` |
| 040 | opp.home vs opp.away via `localName` | `home: true/false` with `opponent.name = {default:'Wild'}` | EN `'vs Wild'` / `'at Wild'`; FI `'Wild (koti)'` / `'Wild (vieras)'` |
| 040 | no placeholder leaks | flatten every string returned by `boltsView(golden, lang)` | none contains `{` or `}` — backstop for the subtitle `{season}` regression |

### Date and Time Boundaries
Logic takes "now" as a parameter and never reads the clock (CLAUDE.md conventions). Test:
- "Yesterday" in ET when the run time is just after midnight UTC, which is still the previous day
  in ET.
- The DST change on **2026-11-01** (`easternUTCOffset -04:00 → -05:00`): the schedule still resolves
  the right game date.
- The first day of a season, and a day with no games (empty "last night" is valid output, not an
  error).

### Watch List (unverified, so test once observed)
- Traded players: how bios and club-stats represent a mid-season team change.
- Playoff `gameType` value (ADR-014 follow-up).
- `gameState` values `PRE`, `LIVE`, `CRIT` (community-documented, never seen).

## Builder Tests (Layer 2)

Golden-file tests: a frozen fixture set plus a fixed `now` produce `tests/golden/{bolts,leijonat}.json`.
- A diff is a failure. If the change is intended, regenerate with `pytest --update-golden` and
  review the golden diff in the commit like code.
- Assert the envelope separately: `schemaVersion`, `generatedAt`, `dataDate`, `season`.
- Assert units: no fraction > 1, all TOI values are `int`, all names are objects.

## Orchestration Tests (Layer 3)

The handler takes injected `fetch` and `store` callables, and the tests use in-memory fakes.
Required cases:
- **Raw is written before parse**, so a parser that raises still leaves the raw objects stored.
- **A parse or build failure leaves current state untouched.** `bolts.json`/`leijonat.json` are
  not written, and history for the day is not written.
- One endpoint failing after 3 retries means the run fails loudly with a non-zero exit and an
  `ERROR` log, which trips the alarm.
- Current-state writes carry `Cache-Control: public, max-age=300` (ADR-022).
- Every write key starts with `data/kiekkokeskus/` (ADR-020).

## Infra Tests (Layer 4)

```typescript
const t = Template.fromStack(stack);
t.resourceCountIs('AWS::S3::Bucket', 0);                 // site bucket is imported, never created
t.resourceCountIs('AWS::CloudFront::Distribution', 0);
t.hasResourceProperties('AWS::Scheduler::Schedule', {
  ScheduleExpressionTimezone: 'America/New_York',
});
// role can only PutObject under data/kiekkokeskus/*
```

Also assert: Lambda runtime `python3.13`, architecture `arm64`, log retention set, and an error
alarm present.

## Page Logic Tests (Layer 5)

Pure modules only (sort, filter, format, i18n, URL state), run with Node's built-in test runner, so
there's no npm in `site/`.
- Sorting: numeric vs. string, `null` always sorts last in both directions, and the sort is stable.
- Filters: F = C+L+R; D; goalies never appear in the skater table.
- Format: `0.915` renders as `.915` (EN) and `,915` or `91,5 %` (FI, per page spec). TOI seconds
  render as `MM:SS`. `null` renders as `–`.
- i18n: every key exists in both EN and FI (the test fails on a missing key). The name rule is
  FI → `fi ?? default`, EN → `default`.
- URL state: `?pos=D&sort=toi&dir=desc&lang=fi` round-trips.

## Smoke Tests (Layer 6)

`scripts/smoke.py` runs after every deploy and exits non-zero on any failure:
- `/bolts` and `/leijonat` return 200 (via the `add-index-html` rewrite, ADR-021).
- `/data/kiekkokeskus/{bolts,leijonat}.json` return 200, valid JSON, and the expected
  `schemaVersion`, with `Cache-Control` containing `max-age=300`.
- **The rest of the site is untouched**: `/` and `/sports` still return 200. This is the guard for
  CLAUDE.md Rule 1.

## Manual Checklist (Layer 7)

After any change to `site/`:
- [ ] Console has no errors, and the Network tab shows exactly one JSON fetch per page (plus
      history if charts are open)
- [ ] EN ⇄ FI switches every string, name, and number format, and `<html lang>` updates
- [ ] Click the same column three times: desc → asc → desc, on both tables (nulls sort last). The two-click-only wording let the stale-closure bug (`fix(07) 4c66c00`) through two manual passes
- [ ] Position filter: All / F / D
- [ ] Reload with URL params restores the same view; a shared link opens in the same language and
      view
- [ ] Stale banner shows when `generatedAt` is more than 36 h old (test with an old local JSON)
- [ ] Disclaimer present in the footer
- [ ] Phone width: tables scroll horizontally with the name column pinned
- [ ] Chrome (Safari parity dropped in init-07; see ADR-038 for why FI uses `fi-FI` Intl output and PRP-07 report for the rationale)

## Lessons Learned

| Project | Bug class | Root cause | Prevention here |
|---|---|---|---|
| Tilastokeskus | five defects past a green suite (D-44) | tests fed only well-formed rows | gotcha matrix with real fixtures |
| Tilastokeskus | lost data on a parse bug (D-20) | parsed before storing | raw-before-parse, layer 3 test |

Add a row for every bug that reaches production.

## Bug Report Template

```markdown
### Bug
### Page / file / date
URL (+ query params) or module; the dataDate involved
### Expected / Actual
### Evidence
- raw payload: s3://jurigregg-static-site/data/kiekkokeskus/raw/<date>/<file>
- Lambda log excerpt
- browser console / network
### Gotcha?
Is this a new payload behavior? If yes, it gets an ADR in DECISIONS-DATA.md + fixture + test first.
```

## Pre-Deployment Checklist

- [ ] `pytest`, `npm test` (infra), and `node --test` all green; coverage ≥ 80%
- [ ] `cdk diff` read: no changes to anything outside `kiekkokeskus-*` resources
- [ ] Golden-file diffs reviewed, if any
- [ ] `schemaVersion` bumped if any output shape broke, with pages updated in the same commit
- [ ] After deploy: `python scripts/smoke.py` passes
- [ ] After page changes: manual checklist done
