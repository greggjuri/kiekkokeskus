# PRP-07: /bolts Page

**Created**: 2026-10-11
**Initial**: `initials/init-07-bolts-page.md`
**Status**: Complete
**ADRs relied on**: ADR-002, 003, 015–018, 020–022, 024, 028, 030, 034–036, 038, 039
**New ADRs this PRP adds**: ADR-040 (Page hero art) in `docs/DECISIONS.md`

---

## Overview

### Problem Statement
`bolts.json` is published daily and the shared UI layer is live, but there's no page. The
init-06 harness also exposed a design gap: each section owned its own state glue (toggle,
pills, sort, URL) and that glue produced the `langExplicit` bug (`fix(06)` commit `8e09b56`).
It also re-fetched the JSON on every re-render. Copying that pattern into two pages would
mean two copies of both bugs.

### Proposed Solution
Build a page controller (`site/kiekkokeskus/page.js`) that owns the state reducer, URL
writes, `<html lang>` sync, banners, header (with an optional hero image), pills, both
tables, and the footer. It takes a single `renderSections` callback for page-specific
sections, calls `loadData` exactly once per page load, and re-renders from the cached data
on every state change. `/bolts` is a thin shell: a pure view model (`site/bolts/view.js`)
that returns display strings for every section, plus `main.js` that plants those strings
into DOM slots. `/leijonat` (init-08) reuses the same controller.

### Success Criteria
- [ ] `node --test "site/kiekkokeskus/*.test.js" "site/bolts/*.test.js"` green, covering
      every gotcha row below and the P0 golden expected-strings table
- [ ] `ruff`, `pytest` (≥ 80%) green, with a deploy test for the sync order and arguments
- [ ] `python scripts/preview.py --fresh` → `/bolts/` in Chrome desktop and 375 px: every
      string / name / number switches EN⇄FI; tiles / cards / tables match the golden table;
      hero sits behind the title on phone; no page-level horizontal scroll
- [ ] TESTING.md manual checklist line "Safari and Chrome" becomes **"Chrome"**; init-06
      Verify item 4 (Safari `Intl` parity) is recorded as **dropped** in the PRP-07 report
- [ ] DevTools Network: exactly one `bolts.json` request across toggling, filtering, sorting
- [ ] `cdk diff` shows no differences; `deploy.py --approved` syncs `kiekkokeskus/` first
      then `bolts/`; `smoke.py` green including `/bolts` + `/bolts/hero.webp`
- [ ] `https://jurigregg.com/bolts` renders live data in both languages
- [ ] ADR-040 added to `docs/DECISIONS.md`; TESTING.md gains the Page-logic rows below;
      TASK.md updated
- [ ] No code file over 500 lines (ADR-034)

---

## Context

### Related Documentation
- `docs/PLANNING.md`: data contract envelope (`schemaVersion`, `generatedAt`, `dataDate`,
  `season`), fractions 0–1, TOI int seconds, 36-h stale rule, cost budget
- `docs/DECISIONS.md`: ADR-002 (not-affiliated footer), ADR-003 (same-origin only), ADR-020
  (prefix layout), ADR-021 (`add-index-html` untouched), ADR-022 (own Cache-Control for
  current-state JSON; legacy TTL default 3600 — the reason ADR-039 is needed for assets),
  ADR-024 (prefix-scoped syncs, no `--delete` at bucket root), ADR-028 (EN/FI toggle +
  rules), ADR-030 (sortable + filterable player tables), ADR-034 (500-line code limit, docs
  exempt), ADR-038 (EN/FI display conventions, FI minus and NBSP, UTC-noon date parse,
  viewer-tz for gameTime), ADR-039 (shared assets deploy + Cache-Control)
- `docs/DECISIONS-DATA.md`: ADR-015 (null for missing), ADR-016 (fractions stay 0–1 — pages
  format), ADR-017 (TOI int seconds), ADR-018 (localized names), ADR-035 (bolts source map,
  faceoffPct null rule), ADR-036 (signed gaps, in-position/out-of-position reference team)
- `docs/TESTING.md`: Layer 5 (`node --test`), Layer 6 (smoke), Layer 7 (manual browser)

### Dependencies
- **Required**:
  - PRP-04 complete (`bolts.json` builder) — golden committed at
    `tests/golden/bolts.json` with the shape the view consumes
  - PRP-06 complete (shared UI deployed) — provides `format.js`, `columns.js`, `sort.js`,
    `url.js`, `data.js`, `i18n.js`, `strings.js`, `table.js`, `chrome.js`, `kk.css`, plus
    live `kiekkokeskus/*` on S3 with `Cache-Control: public, max-age=300`
- **Optional**: none.

### Files to Modify/Create
```
CLAUDE.md                                   MODIFY: Housekeeping — `node --test site/kiekkokeskus/`
                                                     → `node --test "site/kiekkokeskus/*.test.js"`
docs/TESTING.md                             MODIFY: Same housekeeping + add Page-logic gotcha rows
site/kiekkokeskus/format.js                 MODIFY: + `ordinal(n, lang)`, + `season(id)`
site/kiekkokeskus/format.test.js            MODIFY: tests for ordinal / season / signed(-0)
site/kiekkokeskus/i18n.js                   MODIFY: + `tp(key, n, lang, vars)` (plural lookup) +
                                                     `localName(obj, lang)` for team names
                                                     (`fi ?? default ?? '–'`) — avoids
                                                     `renderName` hack for teams; init-08 reuses
site/kiekkokeskus/i18n.test.js              MODIFY: tests for tp and localName
site/kiekkokeskus/strings.js                MODIFY: + ~30 keys for tiles, cards, special teams,
                                                     divisions, confs, plural units, streak,
                                                     result/decided, opp.home/away, nextGames,
                                                     page title + subtitle
site/kiekkokeskus/strings.test.js           MODIFY: parity + pin FI division/conference names
site/kiekkokeskus/chrome.js                 MODIFY: `renderHeader` accepts optional `hero: {src,
                                                     width, height, alt}`
site/kiekkokeskus/page.js                   NEW: `mountPage` DOM entry (createController + renderers)
site/kiekkokeskus/controller.js             NEW: `createController({fetchFn, history, storage,
                                                   location, nav, render})` — pure, no DOM;
                                                   owns pageReducer, single loadData, writeState,
                                                   localStorage, dispatch → render(state, data)
site/kiekkokeskus/controller.test.js        NEW: reducer, fetch-once, langExplicit, error, schema,
                                                   localStorage try/catch — all with a recording
                                                   render stub (no fake DOM needed)
site/kiekkokeskus/_dev/harness.html         REWRITE: both sections use `page.js` — no per-section
                                                     state glue; the inline module becomes very small
site/kiekkokeskus/kk.css                    MODIFY: + hero (desktop & <600 px), + tiles layout,
                                                     + .kk-tile, .kk-card-grid, .kk-badge
site/bolts/index.html                       NEW: shell (<title>, viewport, kk.css link, Google
                                                   Fonts, module script tag)
site/bolts/main.js                          NEW: thin DOM glue — resolves slots, calls page.js
                                                 with boltsView for renderSections
site/bolts/view.js                          NEW: pure `boltsView(data, lang)` → display strings
                                                 for standings tiles, lastGame, nextGames, special
site/bolts/view.test.js                     NEW: golden-driven assertions matching the P0 table
site/bolts/hero.webp                        GIT-TRACK: already in place (900×604, 52 KB — ADR-040)
art/bolts-hero-source.jpg                   GIT-TRACK: never deployed (art/ is outside site/)
scripts/deploy.py                           MODIFY: add bolts sync after `kiekkokeskus/` sync
tests/test_deploy_bolts.py                  NEW: sync order + arguments
scripts/smoke.py                            MODIFY: + `/bolts` + `/bolts/` + `/bolts/hero.webp`
tests/test_smoke_bolts.py                   NEW: content-type and body-contains helpers (pure)
docs/DECISIONS.md                           MODIFY: append ADR-040 (Page hero art)
docs/TASK.md                                MODIFY: move init-07 to Recently Completed; next=init-08
```
Code files stay under 500 lines (ADR-034). Expected sizes: `page.js` ~200, `kk.css` ~450,
`strings.js` ~140, `boltsView` ~180, `main.js` ~80, `index.html` ~60, every other
module under 250. **Docs are exempt.**

---

## Verification of Unconfirmed Facts

| Assumption | Checked how | Result | Follow-up |
|---|---|---|---|
| `standing.streak.code` values (Verify item 1) | Scanned all 5 archived `standings__*.json.gz` fixtures (`2026-04-01`, `-10-01`, `-10-02`, `-10-08`, `-10-09`) with `python -c "sorted(set(r.get('streakCode') ...))"` | **Only `W`, `L`, `OT`.** No `SO`, no `TIE`, no `PRE`. The three `streak.{W,L,OT}` keys cover every observed value | None. If a 4th code ever appears, add a string key and a fixture; today it would log a key lookup miss (gracefully, since `t()` returns the key itself). The gotcha-matrix row for `0 GP state` covers the `streak: null` case independently |
| `Intl.PluralRules('en-US', {type: 'ordinal'})` + `('fi-FI')` exist in Node 22 and give the expected categories (Verify item 2) | `node --input-type=module -e "..."` with the EN category table and FI ordinal | **Confirmed on 22.23.3.** EN: 1→one (`st`), 2→two (`nd`), 3→few (`rd`), 4/11/12/13/111/113→other (`th`), 21→one (`21st`), 22→two (`22nd`), 101→one (`101st`), 111→other (`111th`). FI: everything →`other` (correct — FI ordinal is `n.` regardless) | `ordinal(n, 'en')` uses the `{one:'st', two:'nd', few:'rd', other:'th'}` map; `ordinal(n, 'fi')` returns `${n}.` |
| `s3://jurigregg-static-site/bolts/` is empty before first sync (Verify item 3) | `aws s3 ls … --recursive --profile default` + `aws s3api list-objects-v2 --bucket … --prefix bolts/` | **Confirmed empty.** `list-objects-v2` returned no `Contents` key, just `{"RequestCharged": null, "Prefix": "bolts/"}` | The first deploy's dry-run must show 0 `delete:` lines (we assert this before the real sync — spec P0.10). If the prefix fills between now and deploy, stop and show the user before proceeding |
| `signed(-0)` must render `"0"`, never `"-0"` or `"+0"` (gotcha row) | `node -e "Intl.NumberFormat('en-US', {signDisplay:'exceptZero'}).format(-0)"` and same for `fi-FI` | **Confirmed.** Both EN and FI return `"0"` for `-0` (and `0`). My existing `format.signed` is already correct — the gotcha is prevented by `Intl` + `exceptZero`, and the test just locks it in | The gotcha-matrix row still gets a test; no code change needed |
| `season("20262027") === "2026–27"` (U+2013) | `node -e "const s='20262027'; s.slice(0,4)+'–'+s.slice(6,8)"` | **Confirmed** → `"2026–27"` | `season()` is a two-line pure helper in `format.js` |
| Golden `tests/golden/bolts.json` has every field the P0 strings expect | `python -c "..."` probe | **Confirmed.** `standing.{gp:4,w:3,l:1,otl:0,pts:6,streak:{W,3}}`, `division:{A,2}`, `conference:{E,4}`, `leagueRank:8`, `divisionLead:{OTT,6,0,0}`, `playoffLine:{inPosition:true,NYI,4,gap:2,gih:0}`, `lastGame:{2026-10-08, home:true, Wild, 3-2, W, REG}`, `specialTeams:{ppPct:0.0625, ppRank:30, pkPct:0.777778, pkRank:19}`, 3 nextGames | None — golden suffices as the Layer 5 fixture |
| Node 22 `Intl.DateTimeFormat('fi-FI', numeric-day)` on `2026-10-08T12:00:00Z` with `timeZone:'UTC'` → `"8.10.2026"` | Live `node` eval | **Confirmed** → `"8.10.2026"` matches the golden-expected FI last-game date | None |
| Hero assets exist pre-execution (ADR-040 says Juri's art is attached to the spec) | `ls -la art/ site/bolts/hero.webp` + `file site/bolts/hero.webp` | **Confirmed.** `site/bolts/hero.webp` is `RIFF Web/P VP8 900x604`, 52,308 bytes; `art/bolts-hero-source.jpg` is 508,912 bytes. Both currently untracked | Git-add both in the shell commit (Step 6). `art/` is outside `site/` so deploy ignores it. No need to re-encode |

**No NHL fetch is required.** All Layer 5 tests read `tests/golden/bolts.json` or synthesize
the specific gotcha inputs inline.

---

## Technical Specification

### Output Schema
Page is **read-only**. `schemaVersion` unchanged (expects `1`). No builder change, no new S3
JSON keys. The page consumes these existing `bolts.json` fields:

| Field | Units / type | Nullable | Rendered as |
|---|---|---|---|
| envelope `schemaVersion`, `generatedAt`, `dataDate`, `season` | int, ISO UTC, `YYYY-MM-DD`, 8-char season string | no | schema check, stale banner, footer `data through`, subtitle `season()` |
| `standing.{gp,w,l,otl,pts}` | int | no | record tile value + sub-line |
| `standing.streak.{code,count}` | enum `W/L/OT`, int | yes (null at 0 GP, ADR-015) | record sub-line suffix (`streak {W3}`) |
| `standing.division.{abbrev,rank}` | string, int | no | division tile value + title |
| `standing.conference.{abbrev,rank}`, `.leagueRank` | string, int, int | no | division sub-line |
| `standing.divisionLead.{leader,leaderPts,gap,gamesInHand}` | string, int, signed int (ADR-036), signed int | no | division-lead tile |
| `standing.playoffLine.{inPosition,team,teamPts,gap,gamesInHand}` | bool, string, int, signed, signed | no | playoff-line tile |
| `lastGame.{date,home,opponent.{abbrev,name},tblScore,oppScore,result,decidedIn}` | ET date, bool, {default,fi?}, int, int, enum `W/L/OTL`, enum `REG/OT/SO` | object nullable; `decidedIn` nullable | last-game card |
| `nextGames[].{startTimeUTC,home,opponent}` | ISO UTC, bool, {default,fi?} | list may be `[]` | next-games card |
| `specialTeams.{ppPct,pkPct}` | fraction 0–1 | yes | `pct1Sign` |
| `specialTeams.{ppRank,pkRank}` | int | yes | `ordinal() + "in NHL"` |

`standing.pointPct`, `gf`, `ga`, `team.name` are intentionally **not shown** on this page.

**S3 keys written** by `deploy.py --approved`:
- `s3://jurigregg-static-site/kiekkokeskus/*` (updated: new `page.js`, modified `chrome.js`,
  `format.js`, `i18n.js`, `strings.js`, `kk.css`)
- `s3://jurigregg-static-site/bolts/*` (new: `index.html`, `main.js`, `view.js`, `hero.webp`)
- Both with `Cache-Control: public, max-age=300` (ADR-039). `--delete` scoped per prefix.

### Module Design

```javascript
// site/kiekkokeskus/format.js — additions
export function ordinal(n, lang) { … }   // '1st'/'2nd'/'3rd'/'4th'… or FI 'n.'
export function season(id) { … }         // '20262027' → '2026–27' (U+2013)

// site/kiekkokeskus/i18n.js — additions
export function tp(key, n, lang, vars) { … }
// Looks up `${key}.one` / `${key}.other` via Intl.PluralRules cardinal, fills {n} + vars.

export function localName(obj, lang) { … }
// For team names (and anything else carrying a {default, fi?} object that is NOT a person).
// FI → obj.fi ?? obj.default ?? '–'; EN → obj.default ?? '–'. Pure. Avoids reusing
// `renderName` (which assumes a first/last pair) for teams. init-08 reuses for `teams[].name`.

// site/kiekkokeskus/chrome.js — modified
export function renderHeader({
  root, titleKey, subtitleKey, lang, onLangChange,
  hero,  // NEW optional: { src, width, height, alt='' }
}) { … }
// subtitleKey stays as a thin convenience; mountPage passes a resolved string via the
// subtitle(data, lang) callback (see below) and sets subtitleKey = null when it supplies text.

// site/kiekkokeskus/controller.js — NEW (pure, no DOM)
export function pageReducer(state, action) { … }
//   actions: { type: 'setLang', lang } | 'setPos', pos | 'setSort', sortKey, dir | 'setGsort', ...
//   setLang → { ...state, lang, langExplicit: true }; others → leave langExplicit untouched

export function createController({
  dataPath, expectedSchemaVersion, columns, goalieColumns,
  defaults,
  fetchFn, history, storage, location, nav,
  render,  // (state, data|null, { error }) => void — called after every dispatch
}) { … }
// Owns resolveLang, initial readState, a single loadData call (result cached in closure),
// writeState after every action (uses state.langExplicit), <html lang> is NOT touched here
// (that's a DOM concern — mountPage does it inside its render adapter), localStorage
// try/catch on setLang. Returns { dispatch, start } — start() kicks off loadData + initial
// render. Pure: tested in Node with a recording `render` stub, no DOM.

// site/kiekkokeskus/page.js — NEW (DOM entry; thin adapter on top of createController)
export async function mountPage({
  dataPath, expectedSchemaVersion, columns, goalieColumns,
  defaults,
  titleKey, subtitle, hero,  // ← subtitle is (data, lang) → string. See "Subtitle contract".
  renderSections,
  slots,
  window: win = window, document: doc = document, fetchFn,
  now,  // optional Date for harness ?now= override
}) { … }
// Wires createController's `render(state, data, { error })` to the real DOM renderers:
// updates <html lang>, calls renderHeader (resolves subtitle(data, lang) each render),
// renderPills, renderStaleBanner / renderErrorBanner (mutually exclusive — error wins),
// renderTable x2, renderSections callback, renderFooter.

// Subtitle contract (fixes "literal {season}" rendering during load / on error):
//   subtitle(data, lang):
//     - data === null  → return a safe placeholder string that does NOT reference {season}
//     - data           → return the full subtitle, interpolated against season(data.season)
//   For bolts, main.js passes:
//     (data, lang) => data
//       ? t('page.bolts.subtitle',         { season: season(data.season) }, lang)
//       : t('page.bolts.subtitleNoSeason', null,                              lang)

// site/bolts/view.js — NEW (pure)
export function boltsView(data, lang) {
  return {
    pageTitle, subtitle, hero: { src, width, height, alt },
    tiles: { record, division, divisionLead, playoffLine }, // each: {label, value, sub}
    lastGame: { badge, score, oppLine, dateStr } | null,     // null → 'table.empty'
    nextGames: [{ when, oppLine }],                          // [] → 'nextGames.none'
    special: { pp: {label, pct, rank}, pk: {label, pct, rank} },
  };
}
```

**Why the split**: PRP-06 made a point of not writing hand-rolled `Document` stubs. If
`mountPage` were the only entry, exercising fetch-once / langExplicit / schema / storage
behavior from `node --test` would need a fake `document` + `history` + `localStorage`. That's
the exact time sink we skipped. `createController` holds everything that doesn't touch the
DOM; a recording `render` stub lets Layer 5 drive every action without jsdom. `mountPage` is
exercised by the dev harness (Step 5) and the Chrome manual pass (Step 9).

### Page Changes
- `/bolts` is **new**. Pure HTML shell at `site/bolts/index.html` with ten slot elements, one
  `<script type="module" src="/bolts/main.js">`. Section order: header (with hero) → stale →
  error → standings tiles (4) → three-card row (last game | next games | special teams) →
  skaters card (with pills + table) → goalies card → footer.
- `/leijonat` **unchanged** this PRP. init-08 will reuse `page.js`, the hero param, and the
  tiles' CSS.
- New i18n keys per P0.9 (full list in the spec). `page.{bolts}.{title,subtitle}` get added
  now; `page.leijonat.*` added in init-08.

### Infra Changes
**None.** No CDK changes; `cdk diff` must show "no differences" on Step 9 pre-deploy.
Ownership Check: AWS resources created or changed → **none**. S3 prefixes written: `bolts/`
(new) and `kiekkokeskus/` (update). The main site is untouched — `add-index-html` serves the
clean URLs as-is (ADR-021).

---

## Implementation Steps

Each step is one validated commit: `{type}(07): {description}`.

### Step 0: Housekeeping and spec start
**Files**: `docs/TASK.md`, `CLAUDE.md`, `docs/TESTING.md`, `initials/init-07-bolts-page.md`,
`prps/prp-07-bolts-page.md`

- Move init-07 to In Progress in `docs/TASK.md`.
- Replace every occurrence of `node --test site/kiekkokeskus/` with
  `node --test "site/kiekkokeskus/*.test.js"` in `CLAUDE.md` (Quick Commands) and
  `docs/TESTING.md` (Test Layers tables + any other mention). The directory form fails on Node
  22 (PRP-06 finding; already captured in `fix(06)` commit `e11c973` for test wiring, and in
  CI as the glob form).
- Add the init + PRP files to git (prior pattern — see `docs(04): start`, `docs(05): start`,
  `docs(06): start`).

**Validation**:
- [ ] `grep -nE 'node --test site/kiekkokeskus/[^"*]' CLAUDE.md docs/TESTING.md` returns no
      lines
- [ ] `.venv/bin/pytest -q` green (baseline unchanged)
- [ ] `node --test "site/kiekkokeskus/*.test.js"` green (73 tests from PRP-06)

**Commit**: `docs(07): start`

### Step 1: Shared format helpers — `ordinal`, `season`, plus signed(-0) pin
**Files**: `site/kiekkokeskus/format.js`, `site/kiekkokeskus/format.test.js`

Add two pure helpers; both return `'–'` on nullish input (consistent with every other
formatter in `format.js`).

```javascript
// ordinal(n, lang): EN uses Intl.PluralRules { type: 'ordinal' } with { one:'st',
// two:'nd', few:'rd', other:'th' }; FI is `${n}.` for every n.
export function ordinal(n, lang) { … }

// season('20262027') → '2026–27' (U+2013 EN DASH, not U+2010 hyphen).
export function season(id) { … }
```

**Validation**:
- [ ] `node --test "site/kiekkokeskus/format.test.js"` green on new cases:
  - `ordinal(1,'en') === '1st'`; `2 → '2nd'`; `3 → '3rd'`; `4 → '4th'`; `11 → '11th'`;
    `12 → '12th'`; `13 → '13th'`; `21 → '21st'`; `22 → '22nd'`; `101 → '101st'`;
    `111 → '111th'`
  - `ordinal(1,'fi') === '1.'`; `21 → '21.'`; `111 → '111.'`
  - `ordinal(null, 'en') === '–'`
  - `season('20262027') === '2026–27'` (assert exact char code U+2013 at index 4)
- [ ] **Gotcha row** (negative zero): `signed(-0,'en') === '0'` and `signed(-0,'fi') === '0'`
      — not `'-0'`, not `'+0'`
- [ ] `format.js` under 300 lines

**Commit**: `feat(07): ordinal, season, signed-zero pin`

### Step 2: Plural lookup + `localName` team-name helper
**Files**: `site/kiekkokeskus/i18n.js`, `site/kiekkokeskus/i18n.test.js`

```javascript
// tp(key, n, lang, vars): Intl.PluralRules (cardinal) → pick `${key}.${cat}`, fall back to
// `${key}.other`, then interpolate {n} and any extra vars via the same {name} rule as t().
export function tp(key, n, lang, vars) { … }

// localName(obj, lang): for team names and anything else carrying a {default, fi?} object
// that is NOT a person (which uses renderName). FI → obj.fi ?? obj.default ?? '–';
// EN → obj.default ?? '–'. Null-safe. init-08 reuses for `teams[].name`.
export function localName(obj, lang) { … }
```

**Validation**:
- [ ] `node --test "site/kiekkokeskus/i18n.test.js"` green on new cases:
  - `tp('unit.pts', 1, 'en') === '1 pt'`
  - `tp('unit.pts', 6, 'en') === '6 pts'`
  - `tp('unit.pts', 1, 'fi') === '1 p'`
  - `tp('unit.pts', 6, 'fi') === '6 p'`
  - `tp('gih.ahead', 1, 'en') === '1 game in hand'`
  - `tp('gih.ahead', 2, 'en') === '2 games in hand'`
  - `tp('gih.behind', 2, 'en') === '2 more games played'`
  - FI variants: `1 ottelu vähemmän pelattuna` / `2 ottelua vähemmän pelattuna`
  - Unknown key falls back to the key string (parity with `t()`)
- [ ] `localName({default:'Wild'}, 'en') === 'Wild'` and same for `'fi'` (today's teams
      carry no `fi` key)
- [ ] `localName({default:'Dallas Stars', fr:'Stars de Dallas'}, 'fi') === 'Dallas Stars'`
      (ignores other-lang keys when no `fi`)
- [ ] `localName({default:'Minnesota', fi:'Minnesota Villit'}, 'fi') === 'Minnesota Villit'`
      (synthetic — proves `fi` wins when present)
- [ ] `localName(null, 'en') === '–'`, `localName({}, 'en') === '–'`
- [ ] `i18n.js` under 200 lines

**Commit**: `feat(07): tp() plural lookup and localName() team helper`

### Step 3: Strings
**Files**: `site/kiekkokeskus/strings.js`, `site/kiekkokeskus/strings.test.js`

Add every key from the P0.9 table to both languages — ~30 new keys, dot-notation. Including
plural pairs (`unit.pts.one` / `.other`, `gih.ahead.one` / `.other`, `gih.behind.one` /
`.other`). Keep `col.*` out of `strings.js` (ADR: single source in `columns.js`).

Division names: `div.A/M/C/P` (EN: `Atlantic Division`/…; FI: `Atlantin divisioona`/`Metropolitanin divisioona`/`Keskinen divisioona`/`Tyynenmeren divisioona`).
Conference: `conf.E/W` (EN `East`/`West`; FI `Itä`/`Länsi`).

**Also add** `page.bolts.subtitleNoSeason` → `"Tampa Bay Lightning"` in **both** EN and FI.
`mountPage` renders the header before `bolts.json` arrives (and again on error), and it must
not emit the literal placeholder `{season}`. The subtitle callback (Step 5 / Step 6) uses this
key when `data === null`.

**Validation**:
- [ ] `node --test "site/kiekkokeskus/strings.test.js"` green:
  - Parity test still passes with every new key in both langs
  - FI division names pinned (ADR-038 style — exact strings, so a rename shows up as a diff):
    `div.A → 'Atlantin divisioona'`, `div.M → 'Metropolitanin divisioona'`,
    `div.C → 'Keskinen divisioona'`, `div.P → 'Tyynenmeren divisioona'`
  - FI conference names pinned: `conf.E → 'Itä'`, `conf.W → 'Länsi'`
  - FI streak suffixes pinned: `streak.W → 'V{n}'`, `.L → 'H{n}'`, `.OT → 'JH{n}'`
  - FI decided suffixes pinned: `decided.OT → 'JA'`, `.SO → 'VL'`
  - `page.bolts.subtitle` contains `{season}` placeholder (sanity check that the key is a
    template, not pre-filled)
  - `page.bolts.subtitleNoSeason` **contains no `{`** in either language — a `t('page.bolts.subtitleNoSeason', null, lang).includes('{') === false` assertion. Prevents the "literal
    `{season}` leaks into the DOM during load" regression
- [ ] `strings.js` under 200 lines

**Commit**: `feat(07): strings for tiles, cards, divisions, plurals`

### Step 4: Hero param on `renderHeader`
**Files**: `site/kiekkokeskus/chrome.js`

Add an optional `hero: { src, width, height, alt='' }` to `renderHeader`'s parameter object.
When present, render an `<img class="kk-hero">` after the title block with `alt`, `width`,
`height`, `decoding="async"`, **no** `loading="lazy"` (above the fold, ADR-040). The image
tag has no `src` fallback: if `hero` is omitted the element isn't created, so legacy pages /
tests behave the same.

**Validation**:
- [ ] `node --test "site/kiekkokeskus/*.test.js"` green (73 + Step 1/2/3 additions pass; no
      regression). Chrome's DOM is exercised by the harness in Step 5 and `/bolts` in Step 7,
      not here
- [ ] Pure read-check: inspect `chrome.js` is still under 200 lines

**Commit**: `feat(07): renderHeader hero param`

### Step 5: Shared page controller + harness rewrite
**Files**: `site/kiekkokeskus/page.js`, `site/kiekkokeskus/page.test.js`,
`site/kiekkokeskus/_dev/harness.html`

`controller.js` (pure, no DOM) exports:
- `pageReducer(state, action)` — pure. Actions `{type:'setLang', lang}` sets
  `{ ...state, lang, langExplicit: true }`. `{type:'setPos', pos}`, `{type:'setSort', sortKey,
  dir}`, `{type:'setGsort', sortKey, dir}` leave `langExplicit` alone.
- `createController({ dataPath, expectedSchemaVersion, columns, goalieColumns, defaults,
  fetchFn, history, storage, location, nav, render })` — returns `{ dispatch, start }`:
  - `resolveLang({ url: new URL(location.href), storage, nav })` → initial lang
  - `readState({ search: location.search, columns, goalieColumns, resolvedLang })` → initial state
  - `start()` runs **one** `loadData(dataPath, expectedSchemaVersion, { fetchFn })`, caches
    `{ data | null, error | null }` in closure, calls `render(state, data, { error })` once
    for the initial frame
  - `dispatch(action)` → new `state = pageReducer(state, action)`; `writeState(state, {
    history, pathname: location.pathname, langExplicit: state.langExplicit })`; if `setLang`,
    also `storage.setItem('kk.lang', state.lang)` in try/catch; then `render(state, data,
    { error })` using the cached data (no refetch — the whole point of the fetch-once contract)

`page.js` (DOM entry) exports `mountPage({...})` which:
- builds a `render(state, data, { error })` adapter that touches the DOM: sets `<html lang>`,
  calls `renderHeader` (with hero and the resolved subtitle string from
  `subtitle(data, lang)`), `renderPills`, `renderStaleBanner` **or** `renderErrorBanner`
  (mutually exclusive — error wins), `renderTable` x2, `renderSections({ data, lang, slots })`,
  `renderFooter`
- calls `createController` with that `render` and the real `window.*` globals
- wires onClick handlers on the toggle / pills / sort headers to `controller.dispatch`
- threads an optional `now` Date through to `renderStaleBanner` (harness `?now=` override, P1.2)

Rewrite `site/kiekkokeskus/_dev/harness.html` to use `mountPage` directly: each of the two
sections (bolts, leijonat) calls `mountPage({...})` with its own `dataPath`, columns, and a
trivial `renderSections` that writes "preview" placeholders (no view model — view models live
in `site/bolts/` and `site/leijonat/`). The `?now=` override (P1.2) is threaded through
`mountPage({ now: harnessNow() })`.

**Why the split (fixing a PRP-06 anti-pattern)**: `mountPage` touches the real DOM. Testing
`mountPage` in Node would need a hand-rolled `document` / `history` / `localStorage` stub —
exactly the time sink PRP-06 agreed not to take. `createController` has zero DOM references;
tests inject a recording `render` and plain-object `history` / `storage` / `location` / `nav`
stubs, which is trivially cheap. `mountPage` is covered by the harness (visual, Step 5
reload) and the Chrome manual pass (Step 9).

**Validation**:
- [ ] `node --test "site/kiekkokeskus/controller.test.js"` green:
  - **Reducer**: `setLang('fi')` → `langExplicit: true`; `setPos('d')` on
    `{langExplicit:false}` → `{...langExplicit: false}`; same for `setSort` / `setGsort`
  - **Gotcha row — `fetch once`**: inject a counting `fetchFn`, call `createController` +
    `start()`, then `dispatch` `setLang`, `setPos`, `setSort`, `setGsort`. Assert
    `fetchFn.callCount === 1` and `render` was called 5 times (1 initial + 4 dispatches),
    each with the same `data` object identity
  - **Gotcha row — `langExplicit survives`**: `dispatch setLang('fi')` then `setPos('d')`
    then `setSort({sortKey:'g', dir:'desc'})`. Assert the fake `history.replaceState`
    tape's last entry still contains `lang=fi`
  - **Error path**: a `fetchFn` returning `{ ok: false, status: 500 }` makes `start()` call
    `render(state, null, { error: 'http' })`. Subsequent dispatches re-call `render` with
    the same `(null, { error })` — no retry
  - **Schema mismatch**: `fetchFn` returns `{ schemaVersion: 2 }` → `render(state, null,
    { error: 'schema' })`, no throw
  - **localStorage try/catch**: a `storage.setItem` that throws on `setLang` does not break
    the dispatch — the subsequent `render` still fires with the new lang
  - **`subtitle(null, lang)` safety hook**: not strictly tested in controller tests (DOM
    concern), but see Step 6 view.test.js "no `{` placeholder in rendered strings"
- [ ] Harness still loads in a browser (visual check in Step 9 Chrome open; no automated
      assertion for this). File `_dev/harness.html` under 250 lines
- [ ] `controller.js` under 250 lines; `page.js` under 250 lines

**Commit**: `feat(07): controller + mountPage + harness rewrite`

### Step 6: Bolts view model + shell + hero asset + CSS additions
**Files**: `site/bolts/index.html`, `site/bolts/main.js`, `site/bolts/view.js`,
`site/bolts/view.test.js`, `site/bolts/hero.webp` (git-add existing), `art/bolts-hero-source.jpg`
(git-add existing), `site/kiekkokeskus/kk.css` (modify)

`boltsView(data, lang)` returns:
```javascript
{
  pageTitle: t('page.bolts.title', null, lang),
  subtitle: t('page.bolts.subtitle', { season: season(data.season) }, lang),
  hero: { src: '/bolts/hero.webp', width: 900, height: 604, alt: '' },
  tiles: {
    record: {
      label: t('tile.record', null, lang),
      value: `${s.w}–${s.l}–${s.otl}`,       // U+2013
      sub: s.streak
        ? `${tp('unit.pts', s.pts, lang)} · ${t('tile.streak', null, lang)} ${
            t('streak.' + s.streak.code, { n: s.streak.count }, lang)}`
        : tp('unit.pts', s.pts, lang),
    },
    division: {
      label: t('div.' + s.division.abbrev, null, lang),
      value: ordinal(s.division.rank, lang),
      sub: t('tile.divisionSub', {
        confRank: ordinal(s.conference.rank, lang),
        conf: t('conf.' + s.conference.abbrev, null, lang),
        leagueRank: ordinal(s.leagueRank, lang),
      }, lang),
    },
    divisionLead: {
      label: s.divisionLead.leader === 'TBL' ? t('tile.divLeader', null, lang) : t('tile.divLead', null, lang),
      value: s.divisionLead.leader === 'TBL' ? '0' : signed(-s.divisionLead.gap, lang),
      sub: `${s.divisionLead.leader} · ${tp('unit.pts', s.divisionLead.leaderPts, lang)}`
        + gihClause(s.divisionLead.gamesInHand, lang),
    },
    playoffLine: {
      label: s.playoffLine.inPosition ? t('tile.playoffIn', null, lang) : t('tile.playoffOut', null, lang),
      value: signed(s.playoffLine.inPosition ? +s.playoffLine.gap : -s.playoffLine.gap, lang),
      sub: `${s.playoffLine.team} · ${tp('unit.pts', s.playoffLine.teamPts, lang)}`
        + gihClause(s.playoffLine.gamesInHand, lang),
    },
  },
  lastGame: data.lastGame ? {
    badge: t('result.' + data.lastGame.result, null, lang),           // W/L/OTL → V/H/JH
    score: `${data.lastGame.tblScore}–${data.lastGame.oppScore}`,     // U+2013
    suffix: data.lastGame.decidedIn && data.lastGame.decidedIn !== 'REG'
      ? t('decided.' + data.lastGame.decidedIn, null, lang) : '',
    oppLine: t(data.lastGame.home ? 'opp.home' : 'opp.away',
      { opp: localName(data.lastGame.opponent.name, lang) },          // localName — not renderName
      lang),
    dateStr: date(data.lastGame.date, lang),
  } : null,
  nextGames: (data.nextGames || []).map(g => ({
    when: gameTime(g.startTimeUTC, lang),
    oppLine: t(g.home ? 'opp.home' : 'opp.away',
      { opp: localName(g.opponent.name, lang) },                      // localName — not renderName
      lang),
  })),
  special: {
    pp: {
      label: t('special.pp', null, lang),
      pct: pct1Sign(data.specialTeams?.ppPct, lang),                  // '–' if null
      rank: data.specialTeams?.ppRank != null
        ? t('special.rank', { rank: ordinal(data.specialTeams.ppRank, lang) }, lang)
        : null,                                                        // null → UI drops the line
    },
    pk: { … },
  },
}
```

Helpers in the same file:
- `gihClause(gih, lang)` → `' · ' + tp('gih.ahead', gih, lang)` when `gih > 0`;
  `' · ' + tp('gih.behind', -gih, lang)` when `gih < 0`; `''` when `gih === 0`.

`site/bolts/main.js` is thin DOM glue:
```javascript
import { SKATER_COLUMNS, GOALIE_COLUMNS } from '/kiekkokeskus/columns.js';
import { mountPage } from '/kiekkokeskus/page.js';
import { boltsView } from './view.js';

const columns = SKATER_COLUMNS.filter(c => c.key !== 'team');
const goalieColumns = GOALIE_COLUMNS.filter(c => c.key !== 'team');

mountPage({
  dataPath: '/data/kiekkokeskus/bolts.json',
  expectedSchemaVersion: 1,
  columns, goalieColumns,
  defaults: { pos: 'all', sort: 'p', dir: 'desc', gsort: 'gp', gdir: 'desc' },
  titleKey: 'page.bolts.title',
  // Subtitle must not leak a literal '{season}' into the DOM during load / on error.
  // mountPage calls this on every render — including before data arrives.
  subtitle: (data, lang) => data
    ? t('page.bolts.subtitle',         { season: season(data.season) }, lang)
    : t('page.bolts.subtitleNoSeason', null,                              lang),
  hero: { src: '/bolts/hero.webp', width: 900, height: 604, alt: '' },
  slots: { … },
  renderSections: ({ data, lang, slots }) => {
    const view = data ? boltsView(data, lang) : null;
    // Place tiles, lastGame, nextGames, special into their slots. When view === null (load
    // failure or pre-fetch), render '–' placeholders for every tile/card value so the layout
    // still measures correctly.
    …
  },
});
```

`site/bolts/index.html` is a 10-slot shell: `<title>bolts · kiekkokeskus</title>`,
`<html lang="en">` (controller overwrites on resolve), `kk.css` link + Google Fonts (same
import as init-06 — reuses the browser cache from `/kiekkokeskus/kk.css`), one
`<script type="module" src="/bolts/main.js">`.

**CSS additions in `kk.css`**:
- `.kk-hero` (desktop: height = header height, right-aligned; <600 px: absolute behind title,
  opacity 0.25, centered — ADR-040 "pre-flattened onto `--kk-bg`, never on `.kk-card`")
- `.kk-tiles` (grid, 4 cols desktop / 2 cols tablet / 1 col ≤600 px)
- `.kk-tile` (card-like, label small-caps, value Barlow Condensed 48 px, sub muted)
- `.kk-card-grid` (3-column grid for lastGame | nextGames | special; stacks ≤600 px)
- `.kk-badge` (result badge in last-game card; `data-result` attribute for color)

Git-add the hero asset and the source JPG:
```bash
git add site/bolts/hero.webp art/bolts-hero-source.jpg
```

**Validation**:
- [ ] `node --test "site/bolts/*.test.js"` green:
  - **Golden expected-strings** per the P0 "Fixtures and Gotchas" table — assert all 14
    cells (EN: record, division, division lead, playoff line, last game, PP, PK; FI mirror).
    Example: `v.tiles.record.value === '3–1–0'`; `.sub === '6 pts · streak W3'` in EN,
    `'6 p · putki V3'` in FI
  - **Gotcha row — signed gaps from Tampa's view (ADR-036)**: synthesize a data with
    `divisionLead.gap: 4` → view value `−4`; `playoffLine.inPosition: false, gap: 2` → label
    `Below the playoff line`, value `−2`
  - **Gotcha row — TBL leads division**: `leader: 'TBL', gap: 0` → value `'0'`, label
    `'Division leader'`
  - **Gotcha row — games in hand**: `gih=1 → sub contains '1 game in hand'`;
    `gih=-2 → '2 more games played'`; `gih=0 → sub omits the clause entirely`
  - **Gotcha row — 0 GP state**: synthetic with `streak: null`, `lastGame: null`,
    `nextGames: []`, `specialTeams.ppPct: null, ppRank: null` →
    `view.tiles.record.sub` has no streak text; `view.lastGame === null`;
    `view.nextGames.length === 0`; `view.special.pp.pct === '–'`; `view.special.pp.rank === null`
  - **Gotcha row — OT / SO suffix**: `decidedIn: 'OT'` → `suffix: 'OT'` (EN) / `'JA'` (FI);
    `'SO'` → `'SO'` / `'VL'`; `'REG'` → `suffix: ''`
  - FI/EN last game `vs Wild` / `Wild (koti)` on `home: true` (team name via `localName`,
    not `renderName`)
  - **New guardrail — no `{` in any rendered view string**: build the view against the
    golden in both languages, flatten every string in the returned object, assert no value
    contains `{` or `}`. This catches a missing-key or missing-var regression even when a
    test doesn't check that exact string. (Backstop for the "literal `{season}`" bug the
    subtitle callback fixes.)
- [ ] `site/bolts/view.js` under 300 lines; `main.js` under 150; `index.html` under 100
- [ ] `kk.css` under 500 lines (currently 307; add ~150 for hero + tiles + cards)
- [ ] `site/bolts/hero.webp` and `art/bolts-hero-source.jpg` tracked by git

**Commit**: `feat(07): bolts page shell, view, hero and tiles CSS`

### Step 7: Deploy — add bolts sync after shared
**Files**: `scripts/deploy.py`, `tests/test_deploy_bolts.py`

Add a second sync step in `page_sync()` that runs **after** the existing `kiekkokeskus/`
sync. **`--exclude "*.test.js"`** is mandatory — Step 6 writes `site/bolts/view.test.js` into
the same folder as `site/bolts/main.js`, and without the exclude it would ship to prod
alongside the real page assets:
```python
BOLTS_SYNC_DEST = "s3://jurigregg-static-site/bolts/"
BOLTS_SYNC_SOURCE = "site/bolts/"

def _bolts_sync_cmd() -> list[str]:
    return [
        "aws", "s3", "sync", BOLTS_SYNC_SOURCE, BOLTS_SYNC_DEST,
        "--delete",
        "--exclude", "*.test.js",   # Step 6 puts view.test.js in site/bolts/; keep it out of prod.
        "--cache-control", "public, max-age=300",
        "--profile", "default",
    ]

def page_sync() -> None:
    _check_allowed(SHARED_SYNC_DEST)
    subprocess.run(_shared_sync_cmd(), cwd=REPO_ROOT, env=_subprocess_env(), check=True)
    _check_allowed(BOLTS_SYNC_DEST)
    subprocess.run(_bolts_sync_cmd(), cwd=REPO_ROOT, env=_subprocess_env(), check=True)
```

`tests/test_deploy_bolts.py`:
- `_bolts_sync_cmd()` returns the exact arg list (`--delete`, `--exclude "*.test.js"`,
  `--cache-control "public, max-age=300"`, `--profile default`) with no extraneous flags
- **Explicit assertion**: `"--exclude" in cmd` and the following positional is `"*.test.js"`.
  A missing exclude is the regression we're preventing (`view.test.js` deploying to prod)
- `page_sync()` with a `subprocess.run` monkeypatch records the call sequence and asserts
  **shared sync runs first, then bolts sync** (ordering matters per spec P0.10 — "a new page
  never points at shared modules that haven't arrived yet"). Record the two full `cmd` lists
  in order and assert `calls[0][0] == _shared_sync_cmd()` and `calls[1][0] == _bolts_sync_cmd()`
- `page_sync()` with `_check_allowed` monkeypatched to reject the bolts dest aborts **before**
  invoking subprocess for bolts (belt-and-suspenders)
- `env` on every subprocess call is `_subprocess_env()` (same test pattern as PRP-06)
- Pre-deploy workflow guidance recorded in `deploy.py`'s docstring: before the first real
  bolts sync, run `aws s3 ls s3://jurigregg-static-site/bolts/ --recursive` + the sync
  command **with the same `--exclude "*.test.js"`** and `--dryrun`, and inspect for any
  `delete:` line. (If the exclude is dropped from the dry-run but kept in the real command,
  the expected upload count below won't match reality.)

**Validation**:
- [ ] `.venv/bin/pytest tests/test_deploy_bolts.py tests/test_deploy_shared.py -q` green
- [ ] `scripts/deploy.py` without `--approved` still prints the `cdk diff` and exits 0
- [ ] File still ≤ 200 lines

**Commit**: `feat(07): deploy syncs bolts/`

### Step 8: Smoke — `/bolts`, `/bolts/`, `/bolts/hero.webp`
**Files**: `scripts/smoke.py`, `tests/test_smoke_bolts.py`

Extend `smoke.py`:
- `GET /bolts` → 200, `content-type` starts with `text/html`, body contains
  `/kiekkokeskus/kk.css`
- `GET /bolts/` → 200, same `text/html` content-type (served through `add-index-html`
  rewrite, ADR-021)
- `GET /bolts/hero.webp` → 200, `content-type: image/webp`, `cache-control` contains
  `max-age=300`

Keep every existing check: `/`, `/sports`, health, bolts.json, leijonat.json, kk.css, i18n.js.

`tests/test_smoke_bolts.py` tests pure helpers (content-type matchers, body-contains helper).
No network. Pattern mirrors `test_smoke_assets.py`.

**Validation**:
- [ ] `.venv/bin/pytest tests/test_smoke_bolts.py -q` green
- [ ] `smoke.py` under 300 lines

**Commit**: `feat(07): smoke checks /bolts and hero`

### Step 9: Deploy and verify
```bash
# 1. CI must be green on the branch before deploy
gh run watch                               # wait for the latest push

# 2. CDK diff (no infra change expected)
cd infra && PATH="/opt/homebrew/opt/node@22/bin:$PATH" AWS_PROFILE=default npx cdk diff

# 3. Pre-deploy inspection — stop if anything unexpected
aws s3 ls s3://jurigregg-static-site/bolts/ --recursive --profile default
# bolts dry-run must mirror the real sync's flags (including the test-file exclude)
aws s3 sync site/bolts/ s3://jurigregg-static-site/bolts/ --delete \
  --exclude "*.test.js" --dryrun --profile default
# expect: 0 delete: lines, exactly 4 (dryrun) upload: lines
#         (index.html, main.js, view.js, hero.webp). NO view.test.js.
# If the count is 5, --exclude isn't matching — stop and show.
aws s3 sync site/kiekkokeskus/ s3://jurigregg-static-site/kiekkokeskus/ --delete \
  --exclude "*.test.js" --exclude "_dev/*" --exclude "package.json" --dryrun --profile default
# expect: 0 delete: lines (page.js + controller.js are new; chrome/format/i18n/strings/kk.css updated)

# 4. Deploy
.venv/bin/python scripts/deploy.py                 # cdk diff + exit
.venv/bin/python scripts/deploy.py --approved      # cdk deploy (no-op) + kiekkokeskus/ sync + bolts/ sync

# 5. Smoke + live checks
.venv/bin/python scripts/smoke.py
curl -sI https://jurigregg.com/bolts | grep -iE 'HTTP|content-type|cache-control|x-cache'
curl -sI https://jurigregg.com/bolts/ | grep -iE 'HTTP|content-type'
curl -sI https://jurigregg.com/bolts/hero.webp | grep -iE 'HTTP|content-type|cache-control'

# 6. Post-deploy guard — no test file leaked into prod
aws s3 ls s3://jurigregg-static-site/bolts/ --recursive --profile default | grep -F '.test.js' \
  && { echo "FAIL: test file in bolts/ — delete immediately"; exit 1; } || echo "OK: no test files"
```

**Live Layer 7 manual (Chrome only — Safari parity dropped per spec)**:
- [ ] Open `https://jurigregg.com/bolts` in Chrome desktop and 375 px
- [ ] Hero visible on desktop (right side), hero behind title on phone at 25 % opacity, title
      still legible
- [ ] Record tile: `3–1–0`, `6 pts · streak W3`; FI toggle → `3–1–0`, `6 p · putki V3`
- [ ] Division tile: `Atlantic Division`, `2nd`, `4th East · 8th NHL`; FI: `Atlantin
      divisioona`, `2.`, `Itä 4. · NHL 8.`
- [ ] Division lead tile: `0`, `OTT · 6 pts`; FI: `0`, `OTT · 6 p`
- [ ] Playoff tile: `Above the playoff line`, `+2`, `NYI · 4 pts`
- [ ] Last game: `W` badge, `3–2`, `vs Wild`, `Oct 8, 2026`; FI: `V`, `3–2`, `Wild (koti)`,
      `8.10.2026`
- [ ] Next games: 3 rows with viewer-local time
- [ ] PP `6.3%`, `30th in NHL`; PK `77.8%`, `19th in NHL`; FI: `6,3 %`, `NHL:n 30.`
- [ ] Skater and goalie tables render with pills and sort; no `team` column; nulls last; name
      column pinned at 375 px
- [ ] Footer: data-through line and the ADR-002 disclaimer
- [ ] DevTools Network: open `/bolts`, click FI toggle, click Defense pill, click a sort
      header — only **one** `bolts.json` request total (fetch-once contract)
- [ ] No console errors
- [ ] Breadcrumb `jurigregg.com` is a link to `https://jurigregg.com/` (P1.1)

If live content-type on any object is wrong, add a per-ext second-pass sync and commit as
`fix(07): per-ext content-type on bolts sync` (same pattern reserved for PRP-06).

**Validation**:
- [ ] `cdk diff` prints `no differences`
- [ ] Bolts dry-run (with `--exclude "*.test.js"`): **0 `delete:` lines**, exactly 4 uploads
      (`index.html`, `main.js`, `view.js`, `hero.webp`) — **not 5**
- [ ] Shared dry-run: 0 `delete:` lines; expected updates include `page.js`, `controller.js`,
      modified `chrome.js`, `format.js`, `i18n.js`, `strings.js`, `kk.css`
- [ ] Post-deploy `aws s3 ls s3://jurigregg-static-site/bolts/ --recursive` grep for
      `.test.js` returns **nothing**; if anything matches, delete it immediately with
      `aws s3 rm` (prefix-scoped, ADR-024) before continuing
- [ ] Smoke 30+/30+ pass (new checks + existing)
- [ ] Every Layer 7 item above verified
- [ ] Lighthouse (Chrome DevTools, mobile) — record LCP, CLS, console-errors in the report
      (P1.2; not a gate)

**Commit**: no new commit unless a content-type fix is needed.

### Step 10: Documentation and close-out
**Files**: `docs/DECISIONS.md` (append ADR-040), `docs/TESTING.md` (Page-logic gotcha rows +
"Chrome only" line), `docs/TASK.md`, `prps/prp-07-bolts-page.md` (status flip)

- Append **ADR-040** (Page hero art) using the init-07 Notes draft verbatim.
- Add the Page-logic gotcha rows below to `docs/TESTING.md`'s matrix.
- Change the TESTING.md manual-checklist line "Safari and Chrome" → "Chrome" (ties into the
  spec Success Criterion that drops Safari parity).
- `docs/TASK.md`: move init-07 to Recently Completed with a one-line outcome; set `init-08-leijonat-page`
  as Up Next; update Last-updated date.
- Flip PRP status Ready → Complete.

**Validation**:
- [ ] `grep "ADR-040" docs/DECISIONS.md` succeeds
- [ ] `awk '/^## Open Questions/{flag=1; next} /^## /{flag=0} flag' docs/TASK.md | grep -F "Safari"`
      returns no lines (Safari dropped from TASK too, if it was there — it wasn't; this is the
      TESTING.md checklist change)
- [ ] `grep -c "Safari and Chrome" docs/TESTING.md` returns `0`
- [ ] All layered checks green: `pytest`, `node --test ...`, infra `npm test`, `smoke.py`

**Commit**: `docs(07): ADR-040, TESTING, TASK, complete`

---

## Testing Requirements

| Layer (TESTING.md) | Tests | Fixture / Gotcha row |
|---|---|---|
| 1 Parse contract | n/a — no parser touched | — |
| 2 Builder golden | n/a — `tests/golden/bolts.json` used as Layer 5 input only | — |
| 3 Orchestration | n/a — no handler change | — |
| 4 Infra | `cdk diff` prints no differences; existing `infra/test/` assertions remain green | — |
| 5 Page logic | `format.test.js`, `i18n.test.js`, `strings.test.js`, `page.test.js`, `site/bolts/view.test.js` | every row below |
| 6 Smoke | `scripts/smoke.py` extends to `/bolts`, `/bolts/`, `/bolts/hero.webp` | — |
| 7 Manual | Step 9 live checklist (Chrome only) | — |

### Page-logic gotcha rows (new in `docs/TESTING.md`)

| ADR | Gotcha | Fixture / input | Assert |
|---|---|---|---|
| 036 | signed gaps from Tampa's view | synthetic `divisionLead.gap: 4`; `playoffLine` out-of-position, `gap: 2` | tiles show `−4`; `Below the playoff line` + value `−2` |
| 036 | TBL leads division | `divisionLead: {leader:'TBL', gap:0}` | tile value `0`, label `'Division leader'` (EN) / `'Divisioonan kärjessä'` (FI) |
| 038 | signed(-0) renders `0` | `signed(-0, {en,fi})` | returns `'0'` — not `'-0'`, not `'+0'`; locked by Intl `exceptZero` |
| 040 | games in hand both signs + zero | `gamesInHand` = `1`, `-2`, `0` | `' · 1 game in hand'`; `' · 2 more games played'`; clause omitted when `0` |
| 015 | 0 GP state | `streak:null`, `lastGame:null`, `nextGames:[]`, `specialTeams.ppPct:null, ppRank:null` | no streak text in record sub; `view.lastGame === null`; empty nextGames; `special.pp.pct === '–'`; `rank === null` |
| 040 | OT / SO suffix | `decidedIn` = `OT`, `SO`, `REG` | last-game suffix `'OT'` / `'SO'` (FI `'JA'` / `'VL'`); nothing on `REG` |
| 040 | ordinals | 1, 2, 3, 4, 11, 12, 13, 21, 22, 101, 111 | EN `1st 2nd 3rd 4th 11th 12th 13th 21st 22nd 101st 111th`; FI `n.` |
| 040 | plural units | `pts` = 1 and 6 | EN `1 pt` / `6 pts`; FI `1 p` / `6 p` |
| 040 | fetch once | stub `fetchFn`, mount, then `setLang` + `setPos` + `setSort` + `setGsort` | `fetchFn.callCount === 1` |
| 040 | langExplicit survives | `setLang('fi')` then `setPos('d')` | URL (via fake `replaceState`) keeps `lang=fi` after the second dispatch |
| 040 | result badges | `result` `W` / `L` / `OTL` | EN `W` / `L` / `OTL`; FI `V` / `H` / `JH` |
| 040 | opp.home vs opp.away | `home: true` and `home: false` with `opponent.name = {default:'Wild'}` | EN `'vs Wild'` / `'at Wild'`; FI `'Wild (koti)'` / `'Wild (vieras)'` |

Also: the existing TESTING.md matrix row **`038 — missing i18n key`** continues to apply —
the parity test must still pass after the new keys are added.

---

## Error Handling and Edge Cases

| Case | Source | Handling | Test |
|---|---|---|---|
| Fetch throws / 404 / invalid JSON | `data.loadData` | `{ok:false, reason:…}` → `renderErrorBanner`; `renderSections` called with `data: null`; tables empty | `page.test.js` error path |
| `schemaVersion !== 1` | `data.loadData` | `{ok:false, reason:'schema'}` → error banner; no throw | `page.test.js` schema case |
| `lastGame === null` (preseason, no completed games yet) | ADR-015 | `view.lastGame === null`; the `last game` card renders `table.empty` string | `view.test.js` 0 GP row |
| `nextGames` empty | ADR-015 | `view.nextGames.length === 0`; card shows `nextGames.none` | `view.test.js` 0 GP row |
| `specialTeams.ppPct` / `pkPct` null | ADR-015 (early season) | `pct1Sign` returns `'–'`; `rank` is null → UI drops the rank line | `view.test.js` 0 GP row |
| `streak` null (0 GP) | ADR-015 | sub is `'{pts} pts'` with no streak suffix | `view.test.js` streak-null case |
| `divisionLead.gap === 0, leader !== 'TBL'` | ADR-036 | `signed(-0, …)` → `'0'`; sub shows the leader's `pts` plural | golden EN row (`6 pts`) + FI row (`6 p`) |
| `divisionLead.gap === 0, leader === 'TBL'` | spec P0.5 | value `'0'`; label `tile.divLeader` | gotcha row "TBL leads division" |
| `playoffLine` out of position | spec P0.5 + ADR-036 | value `signed(-gap)` (negative); label `tile.playoffOut` | synthetic gotcha row |
| `localStorage.setItem` throws (private mode / quota) | `page.setLang` | try/catch; render continues | `page.test.js` localStorage case |
| `decidedIn === null` (impossible in current builder, but allowed by data contract) | spec P0.6 | treat same as `REG` → no suffix | `view.test.js` guard |
| Opponent name missing / lacks fi (today's reality) | ADR-018 | `renderName` falls back to `name.default`; FI `Wild (koti)` | golden EN + FI rows |
| Hero asset 404 | ADR-040 | `alt=""` means AT reads nothing; browser renders broken-image glyph above the fold | manual Layer 7 check |

---

## Cost Impact

**None.** No Lambda change, no new storage class, no new request pattern. The browser now
makes 2 new same-origin requests on first `/bolts` load (`main.js` + `view.js` + `hero.webp`;
`kk.css`/`i18n.js`/other shared modules reuse the browser cache from any shared asset load).
All cacheable at `max-age=300`. Well within the PLANNING.md 150 KB-per-page target
(`hero.webp` 52 KB + `kk.css` ~6 KB + modules < 20 KB + bolts.json ~7 KB ≈ 85 KB).

---

## Rollback Plan

1. **Code**: `git revert` the PRP's commits, then `.venv/bin/python scripts/deploy.py
   --approved`. The reverted `page_sync()` reverts the bolts sync; the `kiekkokeskus/`
   objects revert to the init-06 versions.
2. **Data**: no `data/` paths written. `bolts.json`/`leijonat.json` untouched. S3 noncurrent
   versions kept 7 days (ADR-023) if needed.
3. **Visible rollback**: `/bolts` 404s cleanly through `add-index-html` once `index.html` is
   deleted. To force-remove instead of waiting for a reverted deploy:
   `aws s3 rm s3://jurigregg-static-site/bolts/ --recursive --profile default` (prefix-scoped,
   allowed by ADR-024).
4. **Verify**: `.venv/bin/python scripts/smoke.py`; `/`, `/sports`, `/data/kiekkokeskus/*`
   remain 200. If `/bolts` was rolled back fully, the bolts-specific smoke checks will fail —
   remove them in the same revert.

---

## Open Questions

(none)

---

## Confidence Scores

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 9 | Spec gives every string, every expected display value for the golden, every nullability rule. Only wiggle room is the exact DOM structure inside each tile/card — a design choice this PRP freezes |
| Feasibility | 9 | Vanilla HTML/CSS/JS; no new runtime deps; shared layer already live. The page controller is the biggest new piece and its contract is well-bounded |
| Completeness | 9 | Every output field has a source, nullability, and formatter; every gotcha row has a named test. Hero asset already supplied. The one deferred policy call (Safari parity dropped) is captured in the Success Criteria |
| Payload certainty | 10 | No NHL endpoint called. Reads `tests/golden/bolts.json` and the live `bolts.json` only. Streak codes verified across 5 archived payloads |
| **Average** | **9.25** | **Ready to execute** |

### Verification results (surprises)
- **No surprises.** All three Verify-in-PRP items resolved cleanly.
- Streak codes across 5 standings archives: only `W`, `L`, `OT` — matches spec assumption.
- Node 22 `Intl.PluralRules` for ordinals works as expected; EN category table matches the
  `{one:'st', two:'nd', few:'rd', other:'th'}` suffix map.
- `s3://jurigregg-static-site/bolts/` is confirmed empty via `s3api list-objects-v2` (no
  `Contents` key). First sync will show 0 deletes.
- `signed(-0)` already renders `'0'` via `Intl` `signDisplay: 'exceptZero'` — the gotcha-row
  test will just lock that behavior in; no code change needed.
- Hero assets are already in `site/bolts/hero.webp` (900×604, 52.3 KB) and
  `art/bolts-hero-source.jpg` (509 KB). Both untracked — Step 6 git-adds them.

### Suggested new ADRs
- **ADR-040** (`docs/DECISIONS.md`) — Page hero art. Draft text in init-07 Notes:
  decorative all-blue WebP flattened on `--kk-bg`, originals kept in `art/` (never deployed),
  must sit on the page background and never on a `.kk-card` surface.

### Follow-ups to flag at report time
- TESTING.md's "Safari and Chrome" line in the Manual Checklist (Layer 7) becomes "Chrome"
  per spec Success Criterion. Init-06 Verify item 4 (Safari `Intl` parity) is **dropped** —
  record in the PRP-07 completion report.
- CLAUDE.md + TESTING.md `node --test site/kiekkokeskus/` → `node --test "site/kiekkokeskus/*.test.js"`
  (first commit, per spec P0.0).
