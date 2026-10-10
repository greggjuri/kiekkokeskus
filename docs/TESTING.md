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
node --test site/kiekkokeskus/                         # 5 (no npm deps in site/)
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
- [ ] Sorting each column works in both directions, and nulls sort last
- [ ] Position filter: All / F / D
- [ ] Reload with URL params restores the same view; a shared link opens in the same language and
      view
- [ ] Stale banner shows when `generatedAt` is more than 36 h old (test with an old local JSON)
- [ ] Disclaimer present in the footer
- [ ] Phone width: tables scroll horizontally with the name column pinned
- [ ] Safari and Chrome

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
