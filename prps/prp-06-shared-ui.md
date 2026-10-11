# PRP-06: Shared UI

**Created**: 2026-10-11
**Initial**: `initials/init-06-shared-ui.md`
**Status**: Complete
**ADRs relied on**: ADR-002, 003, 015–018, 020–022, 024, 028, 030, 034, 035, 037
**New ADRs this PRP adds**: ADR-038 (stat display conventions, EN/FI) and ADR-039 (shared assets deploy + Cache-Control), both in `docs/DECISIONS.md`

---

## Overview

### Problem Statement
Both `/bolts` and `/leijonat` need the same machinery: a language toggle, number and name
formatting, sortable and filterable player tables, URL state, stale and error banners, the
disclaimer footer, and one look. Building it inside `/bolts` and then copying to `/leijonat`
would give two drifting copies. This PRP builds it once under `site/kiekkokeskus/`, so
init-07 and init-08 can focus on page-specific layout.

### Proposed Solution
Add nine framework-free ES modules + one stylesheet under `site/kiekkokeskus/`, Node 22's
built-in test runner exercising every gotcha row, a stdlib dev harness and preview server, a
prefix-scoped sync in `scripts/deploy.py`, extra smoke checks for the new assets, and CI running
`node --test`. No page is published yet; no NHL fetch; no infra change; `schemaVersion` unchanged.

### Success Criteria
- [ ] `node --test site/kiekkokeskus/` green, covering every gotcha row below (Layer 5 tests)
- [ ] `ruff check .`, `ruff format --check .`, `pytest --cov=kiekkokeskus` green (≥ 80%), with
      tests for `scripts/preview.py` mapping and the `deploy.py` prefix guard
- [ ] `python scripts/preview.py --fresh`, then the harness in Safari and Chrome: EN ⇄ FI switches
      every string, name and number; both tables sort both ways with nulls last; pills filter;
      reload restores the view from the URL (Layer 7, manual)
- [ ] `--break bolts` shows the error banner; without `--fresh` the stale banner shows (Layer 7)
- [ ] Phone width (375 px): tables scroll, name column pinned, no page-level horizontal scroll
      (Layer 7)
- [ ] `scripts/deploy.py --approved` syncs `kiekkokeskus/` only; `aws s3 ls
      s3://jurigregg-static-site/kiekkokeskus/ --profile default` shows no `*.test.js` or `_dev/`
      (Step 11 live check)
- [ ] `scripts/smoke.py` green, including the new `/kiekkokeskus/kk.css` and
      `/kiekkokeskus/i18n.js` checks and the existing `/`, `/sports` guards (Layer 6)
- [ ] ADR-038 and ADR-039 added to `docs/DECISIONS.md`; TESTING.md matrix gains the Page-logic
      rows; the "FI save % format" Open Question is removed from `docs/TASK.md`
- [ ] No code file over 500 lines (ADR-034)

---

## Context

### Related Documentation
- `docs/PLANNING.md`: data contract (fractions 0–1, TOI int seconds, localized names, 36-h stale
  rule), S3 prefix layout, cost budget, non-functional requirements
- `docs/DECISIONS.md`: ADR-002 (not-affiliated), ADR-003 (same-origin only), ADR-020 (prefix
  layout), ADR-021 (`add-index-html` untouched), ADR-022 (own Cache-Control; legacy TTL default
  3600 — the reason ADR-039 is needed), ADR-024 (prefix-scoped syncs), ADR-028 (EN/FI toggle),
  ADR-030 (sortable + filterable tables), ADR-034 (500-line code limit, docs exempt)
- `docs/DECISIONS-DATA.md`: ADR-015 (null for missing), ADR-016 (fractions stay 0–1), ADR-017
  (TOI int seconds), ADR-018 (localized names), ADR-035 (`faceoffPct` null rule for non-takers),
  ADR-037 (localized name sources, `rookie` non-null bool, `game.result` from score)
- `docs/TESTING.md`: Layer 5 (page logic, `node --test`), Layer 6 (smoke), Layer 7 (manual
  checklist), gotcha matrix

### Dependencies
- **Required**: PRP-02 complete (`scripts/deploy.py` with `_check_allowed` prefix guard,
  `scripts/smoke.py`), PRP-04 complete (`tests/golden/bolts.json`), PRP-05 complete
  (`tests/golden/leijonat.json`). All three live in `docs/TASK.md` Recently Completed.
- **Optional**: none.

### Files to Modify/Create
```
site/kiekkokeskus/strings.js             NEW: EN/FI dictionary, every key in both
site/kiekkokeskus/strings.test.js        NEW: key parity
site/kiekkokeskus/i18n.js                NEW: lang resolution, t(key,vars), name render, toggle
site/kiekkokeskus/i18n.test.js           NEW: resolution rules + localStorage try/catch
site/kiekkokeskus/format.js              NEW: int, signed, rate3, pct1, pct1Sign, dec2, toi, date,
                                              gameTime, position, null fallback
site/kiekkokeskus/format.test.js         NEW: every gotcha row
site/kiekkokeskus/columns.js             NEW: skater + goalie column definitions, FI from Liiga
site/kiekkokeskus/columns.test.js        NEW: structure sanity, posCode render
site/kiekkokeskus/sort.js                NEW: comparator, nulls-last, stable; position filter
site/kiekkokeskus/sort.test.js           NEW: null in any column + stability + locale text
site/kiekkokeskus/url.js                 NEW: parse + serialize view state, replaceState
site/kiekkokeskus/url.test.js            NEW: round-trip + defaults dropped + unknown→default
site/kiekkokeskus/data.js                NEW: fetch same-origin JSON, schemaVersion check, isStale
site/kiekkokeskus/data.test.js           NEW: schema mismatch + stale 35:59 / 36:01 boundaries
site/kiekkokeskus/table.js               NEW: DOM render from columns + rows + state (no unit tests; harness)
site/kiekkokeskus/chrome.js              NEW: header (crumb, toggle), banners, pills, footer (no unit tests)
site/kiekkokeskus/kk.css                 NEW: tokens + components, dark only
site/kiekkokeskus/_dev/harness.html      NEW: never deployed; renders both goldens through all modules
scripts/preview.py                       NEW: stdlib server; --fresh / --break / --port / --data
tests/test_preview.py                    NEW: mapping, --fresh rewrites, --break schemaVersion
scripts/deploy.py                        MODIFY: fill page_sync() for kiekkokeskus/ only
tests/test_deploy_shared.py              NEW: _check_allowed accepts kiekkokeskus/, refuses rest
scripts/smoke.py                         MODIFY: add kk.css + i18n.js 200 + Cache-Control + MIME
tests/test_smoke_assets.py               NEW: pure-logic bits (header parse, no network)
.github/workflows/ci.yml                 MODIFY: run `node --test site/kiekkokeskus/` on push
docs/DECISIONS.md                        MODIFY: append ADR-038, ADR-039
docs/TESTING.md                          MODIFY: add Page-logic gotcha rows
docs/TASK.md                             MODIFY: move init-06 to Recently Completed; drop FI save % Open Q
```
Code files stay under 500 lines (ADR-034). Expected sizes: `format.js` ~220, `kk.css` ~300,
`chrome.js` ~250, every other module under 150. **Docs exempt.**

---

## Verification of Unconfirmed Facts

| Assumption | Checked how | Result | Follow-up |
|---|---|---|---|
| Node 22 runs `.test.js` as ES modules with **no** `package.json` (spec Verify item 1) | Ran `/opt/homebrew/opt/node@22/bin/node --test` on a `.test.js` with `import` statements in a scratch dir | **Confirmed on 22.23.3.** Syntax detection kicks in; no package.json marker needed | None — do not add `package.json`; keep `_dev/` + `*.test.js` excluded from sync anyway (ADR-039) |
| `Intl.NumberFormat('fi-FI', {signDisplay:'exceptZero'})` emits U+2212, `'en-US'` emits U+002D (spec P0.4) | Node 22 `--input-type=module` codepoint check | **Confirmed.** EN `-1` codepoints `[2d 31]`; FI `−1` codepoints `[2212 31]` | `format.signed` normalizes EN output to U+2212 by replacing the leading `-` |
| `Intl.NumberFormat('fi-FI', {style:'percent', min=max=1})` emits NBSP between number and `%` (spec P0.4) | Same scratch | **Confirmed.** FI `14,3 %` codepoints `[31 34 2c 33 a0 25]`; U+00A0 is between `3` and `%` | `pct1Sign` keeps the NBSP in FI. `pct1` (no `%` in cell) **multiplies the fraction by 100** before `style: 'decimal'` formatting, which sidesteps the `%`/NBSP question entirely |
| FI `rate3` edges: `0.9` → `90,00`, `1.0` → `100,00` (spec gotcha row) | Same scratch | **Confirmed** via `Intl.NumberFormat('fi-FI', {style:'percent', min=max=2})` | `rate3` formatter: EN strips leading `0` only (`0.915` → `.915`, `1.000` stays); **FI multiplies by 100 and uses `decimal` style with 2 fraction digits** so the output has no trailing `%`/NBSP to strip — assert `91,57` as an exact string. The `percent`-style alternative would need `/\s*%$/u` (NBSP, not space); documented inline so a future rewrite doesn't fall into that trap |
| EN `Oct 2, 2026`, FI `2.10.2026` from `YYYY-MM-DD` passed as `UTC noon` (spec P0.4) | Same scratch | **Confirmed.** `new Date('2026-10-02T12:00:00Z')` renders in `America/Los_Angeles` as `Oct 2, 2026`; `new Date('2026-10-02')` without time **shifts to Oct 1** west of UTC | `format.date(iso)` must build the Date as `new Date(iso + 'T12:00:00Z')`, never as `new Date(iso)` |
| Python `mimetypes.guess_type('.js') → text/javascript`, `.css → text/css` (spec P0.11 preview; and transitively how AWS CLI v2 maps content types from Python) | `.venv/bin/python -c "import mimetypes; …"` | **Confirmed.** `(text/javascript, None)` and `(text/css, None)` | `preview.py` sets these explicitly. For `aws s3 sync`, verify live in Step 11 via `curl -sI`; if the live `Content-Type` is wrong, add a second-pass sync with `--content-type` per extension (spec Verify item 2 fallback) |
| CloudFront passes an object's `Cache-Control: public, max-age=300` from origin on CSS (spec Verify item 3; already verified for JSON per ADR-022) | Deferred to Step 11 live `curl -sI https://jurigregg.com/kiekkokeskus/kk.css` after first sync | Pending — ADR-022 says legacy TTL `MinTTL=0`, so origin `max-age=300` should win; verify in-step | If CloudFront strips or clobbers `Cache-Control`, fall back to syncing with `--metadata-directive REPLACE --cache-control …` on each run and re-check |
| Safari's `fi-FI` output matches Node for `pct1Sign` and `gameTime` (spec Verify item 4) | Manual check in Step 11 (`python scripts/preview.py --fresh`, open harness in Safari) | Pending — Safari uses the system ICU, so a mismatch is possible on older macOS | If Safari diverges, pin the NBSP by manual string construction (`int.format(0.143) + ' %'` style) in that formatter only |
| `tests/golden/{bolts,leijonat}.json` contain the fixture shapes the gotcha rows need (ADR-018 Vasilevskiy with only `lastName.fi`; ADR-015 skater with `faceoffPct: null`; multi-lang keys on Finn names) | `python -c "..."` probe over both files | **Confirmed.** `bolts.json`: McDonagh has `faceoffPct: null`, Vasilevskiy carries `firstName.default` only + `lastName.{default, fi, cs, sk}`. `leijonat.json`: Teräväinen and Määttä carry `firstName.default` + `lastName.{default, fi, cs, sk, sv}`; `rookie: false` (non-null bool, ADR-037) | None — Layer 5 reads these files directly |

**No NHL fetch is required in this PRP.** All Layer 5 tests read `tests/golden/*.json`.

---

## Technical Specification

### Output Schema
Nothing in the collector changes. **`schemaVersion` unchanged (1 for both files).** Page code is
read-only against the existing contract.

**S3 keys written** by `deploy.py --approved`:
- `s3://jurigregg-static-site/kiekkokeskus/*` with `Cache-Control: public, max-age=300`, excluding
  `*.test.js`, `_dev/*`, and any `package.json` marker (ADR-039). **`--delete` is scoped to the
  `kiekkokeskus/` prefix only** (allowed by ADR-024).

**S3 keys written** by the Lambda: none affected by this PRP.

### Module Design (public surface)

```javascript
// strings.js
export const STRINGS = { en: { 'nav.crumb': '…', … }, fi: { 'nav.crumb': '…', … } };
// NOTE: column labels do NOT live here (single source of truth is columns.js).

// i18n.js
export function resolveLang({ url, storage, nav }) { … }   // ADR-028 order
export function t(key, vars, lang) { … }                   // {name} interpolation
export function renderName({ firstName, lastName }, lang) { … }  // ADR-018 + ADR-028
export function nameSortKey(row, lang) { … }               // last, then first, lowercased
export function wireToggle({ onChange }) { … }             // DOM, writes lang to <html>, URL, localStorage

// format.js  — every fn returns '–' on null/undefined
export function int(n) {}
export function signed(n, lang) {}                         // U+2212 in both langs
export function rate3(n, lang) {}                          // EN .915/1.000, FI 91,57/100,00
export function pct1(n, lang) {}                           // ×100, 1 decimal, NO % sign
export function pct1Sign(n, lang) {}                       // ×100, 1 decimal, EN 14.3%, FI 14,3 % (NBSP)
export function dec2(n, lang) {}
export function toi(seconds, lang) {}                      // EN MM:SS, FI MM.SS
export function date(iso, lang) {}                         // UTC-noon parse
export function gameTime(iso, lang) {}                     // viewer-local tz, short zone
export function position(code, lang) {}                    // C/L/R/D/G or KH/VL/OL/P/MV

// columns.js  — SINGLE SOURCE OF TRUTH for column labels
export const SKATER_COLUMNS = [{ key, en, enTitle, fi, fiTitle, format, firstDir }, …];
export const GOALIE_COLUMNS = [ … ];

// sort.js
export function sortRows(rows, columns, { sortKey, dir, lang }) { … }  // stable, nulls last
export function filterSkaters(rows, posFilter) { … }                   // all | f | d
export function nextSort(state, column) { … }                          // pure header-click reducer:
                                                                       // if state.sortKey == column.key → flip dir
                                                                       // else → { sortKey: column.key, dir: column.firstDir }

// url.js  — readState takes the page's columns so ?sort=team on /bolts falls back silently
export function readState({ search, columns, goalieColumns }) { … }
                                                           // {lang, pos, sort, dir, gsort, gdir, langExplicit}
                                                           // langExplicit = true iff ?lang= was in the URL
export function writeState(state, { history, pathname, search, langExplicit }) { … }
                                                           // replaceState, drop every key equal to its default,
                                                           // drop lang when !langExplicit

// data.js
export async function loadData(path, expectedSchemaVersion, { fetchFn }) { … }
                                                           // returns {ok, data|error}
export function isStale(generatedAt, now) { … }            // pure, > 36 h

// table.js
export function renderTable({ root, columns, rows, state, lang }) { … }

// chrome.js
export function renderHeader({ root, titleKey, subtitleKey, lang, onLangChange }) { … }
export function renderStaleBanner({ root, generatedAt, lang, now }) { … }
export function renderErrorBanner({ root, lang }) { … }
export function renderFooter({ root, dataDate, lang }) { … }
export function renderPills({ root, state, onChange, lang }) { … }
```

Pure modules take `lang`, `now`, `fetchFn`, `history`, `location` as arguments — no globals read.

### Page Changes
No `/bolts` or `/leijonat` HTML. Only the shared module layer, the harness, and the preview
server. init-07 and init-08 wire page HTML and page-specific sections against this layer.

### Infra Changes
**None.** No CDK changes; `cdk diff` must show "no differences" on Step 11 pre-deploy. Spec
Ownership Check confirms: AWS resources created or changed → none.

---

## Implementation Steps

Each step is one validated commit: `{type}(06): {description}`.

### Step 0: Start the spec and verify tool preconditions
**Files**: `docs/TASK.md`
Move init-06 to In Progress. Confirm Node 22 is at `/opt/homebrew/opt/node@22/bin/node` and
accepts a scratch `.test.js` without `package.json` (already verified in the Verification table
above; this step just records it in the commit message).
**Commit**: `docs(06): start`
**Validation**:
- [ ] `.venv/bin/pytest` green (baseline)
- [ ] `git status` otherwise clean

### Step 1: Strings and i18n
**Files**: `site/kiekkokeskus/strings.js`, `strings.test.js`, `i18n.js`, `i18n.test.js`

Populate `STRINGS` with the keys from the init UI table (`nav.crumb`, `lang.group`, `pos.group`,
`pos.{all,f,d}`, `table.{skaters,goalies,sortBy,loading,empty,noMatch}`,
`banner.{stale,error}`, `footer.{through,disclaimer}`, `posCode.{C,L,R,D,G}`). **`col.*` and
`colTitle.*` live only in `columns.js` (single source of truth) and are added in Step 3** —
duplicating them in `STRINGS` would drift and would push `strings.js` past its 150-line target.
Disclaimer EN must match `README.md` verbatim.

`i18n.js`:
- `resolveLang({ url, storage, nav })`: `?lang=fi|en` → `storage.getItem('kk.lang')` →
  `nav.language.startsWith('fi')` → EN. Every `storage` read / write wrapped in try/catch; a
  failure falls through to the next rule.
- `t(key, vars, lang)`: looks up `STRINGS[lang][key]`, replaces `{name}` placeholders with
  `vars[name]`.
- `renderName({ firstName, lastName }, lang)`: ADR-018 + ADR-028. EN = `firstName.default + ' ' +
  lastName.default`. FI = each part separately, `part.fi ?? part.default`. Preserves extra
  languages (`cs`, `sk`, `sv`, `fr`) by never deleting keys — passes the raw object through.
- `nameSortKey(row, lang)`: lowercased `renderName`'s last-then-first ordering, suitable for
  `localeCompare(…, lang)`.
- `wireToggle({ onChange })`: DOM glue, keeps `<html lang>` in sync; URL via `writeState`.

**Validation**:
- [ ] `node --test site/kiekkokeskus/strings.test.js i18n.test.js` green
- [ ] **Gotcha row covered**: *missing i18n key* — asserts every EN key exists in FI and vice
      versa, failing on diff
- [ ] **Gotcha row covered**: *partial FI name* — Vasilevskiy fixture gives FI
      `Andrei Vasilevski`, EN `Andrei Vasilevskiy`
- [ ] **Gotcha row covered**: *extra name languages* — passes `cs`/`sk`/`sv` keys through
      without error
- [ ] localStorage try/catch tested with a stub that throws from `getItem` and `setItem`
- [ ] `strings.js` + `i18n.js` each under 150 lines
**Commit**: `feat(06): strings and i18n`

### Step 2: Formatters
**Files**: `site/kiekkokeskus/format.js`, `format.test.js`

Implement every formatter in the P0.4 table. Rules:
- `null` or `undefined` → `'–'` in every formatter.
- `signed`: `Intl.NumberFormat` with `signDisplay: 'exceptZero'`, then replace the leading
  `U+002D` with `U+2212` for EN (FI already uses U+2212).
- `rate3`: EN = `n.toFixed(3)` then strip leading `0` only (`0.915` → `.915`, `1.000` stays).
  **FI = multiply by 100 and format with `fi-FI` decimal, 2 fraction digits** (`new
  Intl.NumberFormat('fi-FI', { minimumFractionDigits: 2, maximumFractionDigits: 2 })`); this
  avoids any `%`-strip trap and lets the test assert the exact string `91,57`. (If a future
  rewrite reaches for `style: 'percent'` instead, the trailing space is NBSP U+00A0, so the
  strip must be `/\s*%$/u` — a literal `' %'` strip would silently leave `91,57 %` in
  the cell.)
- `pct1`: **both langs multiply the fraction by 100** before formatting (input is 0.143, not
  14.3). Use `style: 'decimal'` with 1 fraction digit so there is **no `%` in the cell** (the
  header carries it): EN `14.3`, FI `14,3`. Formatting the raw fraction with `decimal` would
  give `0.1`/`0,1`, which is wrong.
- `pct1Sign`: multiply by 100 and format with `style: 'percent'`, 1 decimal (or build the
  string by hand to pin exact chars). FI keeps NBSP (`14,3 %`, U+00A0); EN is `14.3%` with
  no space.
- `dec2`: `fi-FI`/`en-US` decimal, 2 digits.
- `toi(seconds, lang)`: `Math.floor(seconds / 60)` then `seconds % 60`, 2-digit pad on seconds.
  EN joins with `:`; FI with `.`.
- `date(iso, lang)`: parse as `new Date(iso + 'T12:00:00Z')`, format with `timeZone: 'UTC'` so
  LA/Europe TZ-shifting can't move the day; EN short month, FI numeric day.month.year.
- `gameTime(iso, lang)`: `Intl.DateTimeFormat` with viewer's local timeZone and the short time-zone
  name; FI style `klo 19.30`.
- `position(code, lang)`: direct map from `STRINGS[lang]['posCode.' + code]`.

**Validation** — every TZ-sensitive test spawns a child Node process (`process.execPath` +
`spawnSync` with `env: { ...process.env, TZ }`) so plain `node --test` covers it (no shell
`TZ=…` prefix needed; CI runs them without extra wiring):
- [ ] `node --test site/kiekkokeskus/format.test.js` green with **no `TZ=`** on the command line
- [ ] **Gotcha row**: *FI minus and NBSP* — `signed(-1, 'en')` is `−1` with U+2212;
      `signed(-1, 'fi')` is `−1`; `pct1Sign(0.143, 'fi')` has U+00A0 between `3` and `%`
- [ ] **New `pct1` assertion** — `pct1(0.143, 'en') === '14.3'` and
      `pct1(0.143, 'fi') === '14,3'`. Locks in the ×100 step; a straight decimal format of
      the raw fraction would give `0.1` / `0,1` and this test would fail
- [ ] **Gotcha row**: *`rate3` edges* — EN `.900` / `1.000` / `.000`; FI `90,00` / `100,00` /
      `0,00`. Assert FI as **exact strings**; a trailing NBSP+`%` leak would fail
- [ ] Additional `rate3` cases — `rate3(0.9157, 'en') === '.916'`;
      `rate3(0.9157, 'fi') === '91,57'` (no trailing space, no `%`)
- [ ] **Gotcha row**: *goalie season TOI* — `toi(10552, 'en') === '175:52'`; FI `175.52`
- [ ] **Gotcha row**: *date west of UTC* — a subtest spawns a child Node with
      `TZ=America/Los_Angeles` that imports `./format.js` and asserts
      `date('2026-10-02', 'en') === 'Oct 2, 2026'`. The child prints the result; the parent
      asserts the stdout. Runs under plain `node --test` (closes "test only runs if someone
      sets TZ by hand")
- [ ] **New gameTime assertions** (none existed in the earlier draft). Fixed UTC input
      `2026-10-10T23:30:00Z` — a late Saturday evening game on the US East Coast — exercised
      from two viewer locales:
  - `TZ=Europe/Helsinki` child → `gameTime('2026-10-10T23:30:00Z', 'fi')` matches
    `/^su 11\.10\. klo 02\.30/u`. **This is the whole point of `gameTime`**: for a Finnish
    viewer the day has rolled over to Sunday 02:30 local time, and the formatter proves it.
    Short-zone suffix (`UTC+3`) may follow; weekday + date + hh.mm are the invariant.
  - `TZ=America/New_York` child → `gameTime('2026-10-10T23:30:00Z', 'en')` matches
    `/Oct 10/` and the local wall-clock `/7:30\s?PM/` (locks the UTC→viewer-local conversion
    so a future rewrite can't silently drop the timezone)
- [ ] **Gotcha row**: *null in any column* — every formatter on `null` / `undefined` returns
      `'–'` (U+2013)
- [ ] `format.js` under 300 lines
**Commit**: `feat(06): formatters`

### Step 3: Columns, sort, filter
**Files**: `site/kiekkokeskus/columns.js`, `columns.test.js`, `sort.js`, `sort.test.js`

`columns.js` holds **the single source of truth for column labels** — EN and FI abbreviations
and titles are declared here only, not in `strings.js`. Entry shape:
`{ key, en, enTitle, fi, fiTitle, format: 'name'|'text'|'int'|'signed'|'toi'|'pct1'|'rate3'|'dec2'|'position', firstDir: 'asc'|'desc' }`.
Only `gaa` has `firstDir: 'asc'`. The `name` and `team` columns use `'name'` / `'text'`
sort-type sentinels, not a formatter — the renderer picks the right formatter.

`sort.js`:
- `compareValues(a, b, type, lang)`:
  - numeric for `int`, `signed`, `toi`, `pct1`, `rate3`, `dec2`
  - `localeCompare(…, lang)` for `text`
  - `name` type: compare by `nameSortKey` from `i18n.js`
  - `position` type: fixed order `C < L < R < D < G`
- `null` **always sorts last in both directions** (ascending and descending). Implementation:
  partition into `[non-null, null]`, sort the non-null half, concat `null`s.
- `sortRows` is stable: when the comparator returns 0, the original index wins.
- `filterSkaters(rows, posFilter)`: `all` = pass-through; `f` keeps rows whose `positionCode ∈
  {C, L, R}`; `d` keeps `D`.
- **`nextSort(state, column)`**: pure header-click reducer. If `state.sortKey === column.key`,
  flip `dir` (`asc`↔`desc`). Otherwise return `{ sortKey: column.key, dir: column.firstDir }`.
  Lets Step 5 skip DOM stubs for sort flipping.

**Validation**:
- [ ] `node --test` green on `columns.test.js`, `sort.test.js`
- [ ] **Column parity test** — every entry in `SKATER_COLUMNS` and `GOALIE_COLUMNS` has
      non-empty `en`, `enTitle`, `fi`, `fiTitle`. A missing label fails loudly with the
      offending `key`
- [ ] **FI abbreviation pin** — assert the exact FI short labels from ADR-038 so a future rename
      is a visible test diff, not silent drift. Skaters: `gp:O, g:M, a:S, p:P, pm:+/−, pim:R,
      toiPerGame:Aika/O, sog:L, shootingPct:L%, ppg:YV, ppp:YVP, shg:AV, gwg:VM,
      faceoffPct:A%, hits:TAK, blocks:BL`. Goalies: `gp:PO, gs:AK, w:V, l:H, otl:JH, svPct:T%,
      gaa:KA, so:NP, toi:Aika`. Also pin `positionCode:PP` (skaters), `name:Pelaaja` /
      `name:Maalivahti`, `team:Joukkue`
- [ ] **Gotcha row**: *null in any column* — fed a row set with mixed nulls, asserts the null
      rows land at the end in both `asc` and `desc`
- [ ] Stability: equal keys preserve input order
- [ ] FI locale compare: `Ö` sorts after `Z` (so `Öberg` after `Zuccarello`)
- [ ] Filter: `f` returns no goalies and no D; `d` returns only D
- [ ] **`nextSort` test** — same-column click flips `dir`; new-column click returns that
      column's `firstDir`
- [ ] `columns.js` under 200 lines; `sort.js` under 150
**Commit**: `feat(06): columns and sort`

### Step 4: URL state and data loading
**Files**: `site/kiekkokeskus/url.js`, `url.test.js`, `site/kiekkokeskus/data.js`,
`data.test.js`

`url.js`:
- `readState({ search, columns, goalieColumns })`: parses `URLSearchParams`. Unknown or invalid
  values fall back to the default silently. **Column keys are validated against the page's own
  `columns` / `goalieColumns`** (passed in by the caller), so `?sort=team` on `/bolts` — which
  has no team column — falls back to the skater default rather than passing validation. Returns
  `{ lang, pos, sort, dir, gsort, gdir, langExplicit }`, where `langExplicit === true` iff
  `?lang=` was in the URL (used by `writeState` and by the toggle wiring to decide whether
  future renders should keep writing `lang` into the URL).
- `writeState(state, { history, pathname, search, langExplicit })`: builds a new query, **drops
  every key equal to its default** (`pos=all`, `sort=p`, `dir=desc`, `gsort=gp`, `gdir=desc`).
  **`lang` is dropped unless `langExplicit` is `true`** — meaning the user either arrived with
  `?lang=` in the URL or clicked the toggle (both set `langExplicit = true`). An unassisted page
  load from browser-language resolution therefore produces a clean URL with no `?lang=`, so
  shared links don't lock recipients to the sender's locale (ADR-028's resolution order holds).
  Calls `history.replaceState(null, '', newUrl)`.
- Round-trips:
  - `?pos=d&sort=toiPerGame&dir=desc&lang=fi` → `readState` returns `langExplicit: true` →
    `writeState` writes `?pos=d&sort=toiPerGame&dir=desc&lang=fi` back exactly.
  - Fresh load with no params, `nav.language === 'en-US'` → `readState` returns
    `{ lang: 'en', …, langExplicit: false }` → `writeState` writes **empty query** (no
    `?lang=en`).

`data.js`:
- `loadData(path, expectedSchemaVersion, { fetchFn })`:
  - `fetchFn ??= (p) => fetch(p)` for prod; tests inject a stub.
  - Returns `{ ok: true, data }` on success + `schemaVersion === expectedSchemaVersion`.
  - Returns `{ ok: false, reason: 'fetch'|'http'|'json'|'schema', detail }` on failure. The caller
    renders the error banner; the module itself does **not** touch the DOM.
  - A thrown error inside `fetch` becomes `{ ok: false, reason: 'fetch' }`; the module never
    rethrows.
  - On failure, the module also calls `console.error(detail)`.
- `isStale(generatedAtIso, nowDate)`: parse `generatedAt` as UTC, return
  `(now - gen) / 3_600_000 > 36`. Pure; takes `now` as a `Date`.

**Validation**:
- [ ] `node --test` green on `url.test.js`, `data.test.js`
- [ ] **No implicit `?lang=` on default load** — `writeState({ lang:'en', pos:'all', sort:'p',
      dir:'desc', gsort:'gp', gdir:'desc' }, { langExplicit: false, … })` yields an **empty
      query** (`newUrl` has no `?`). Prevents shared links from locking recipients to the
      sender's locale
- [ ] Explicit-lang round-trip — load `?pos=d&sort=toiPerGame&dir=desc&lang=fi`,
      `readState` returns `langExplicit: true`, then `writeState(sameState, { langExplicit:
      true })` writes exactly the same query back
- [ ] Default-with-toggle round-trip — load `?lang=fi`, user clicks toggle to EN,
      `writeState({ lang:'en', …defaults }, { langExplicit: true })` keeps `?lang=en` (toggle
      makes it explicit)
- [ ] **Page-scoped column validation** — `readState({ search: '?sort=team', columns:
      BOLTS_SKATER_COLUMNS, goalieColumns: GOALIE_COLUMNS })` where `BOLTS_SKATER_COLUMNS` lacks
      `team` falls back to `sort: 'p'`. The same input with `LEIJONAT_SKATER_COLUMNS` (has
      `team`) returns `sort: 'team'`
- [ ] Unknown `sort=moonshot` falls back to `p`
- [ ] **Gotcha row**: *schema mismatch* — `loadData` with a stub returning
      `{ schemaVersion: 2 }` returns `{ ok: false, reason: 'schema' }` and does **not** throw
- [ ] **Gotcha row**: *stale boundary* — `isStale(gen, gen+35h59m)` is `false`;
      `isStale(gen, gen+36h01m)` is `true`
- [ ] Fetch failure path: a stub `fetchFn` that throws returns `{ ok: false, reason: 'fetch' }`
- [ ] `url.js` under 150 lines; `data.js` under 150
**Commit**: `feat(06): url state and data loading`

### Step 5: Table and chrome DOM
**Files**: `site/kiekkokeskus/table.js`, `site/kiekkokeskus/chrome.js`

**No DOM unit tests.** Click-to-sort already lives in `sort.nextSort(state, column)` (Step 3,
pure, fully covered). Pill `aria-pressed` is a direct projection of `state.pos` — a one-line
`pos === option ? 'true' : 'false'` that needs no isolated test. Full rendering is exercised in
the dev harness (Step 7) and the Layer 7 manual checklist (Step 11). Hand-rolling a `Document`
stub was listed as a time-sink; cut.

`table.js`:
- `renderTable({ root, columns, rows, state, lang, onSort })`: builds a `<table
  class="kk-table">` with sticky name column, right-aligned numbers, header `<button>`s inside
  `<th>` carrying `aria-sort`. On click, calls `onSort(column)`; the caller passes the result
  through `nextSort(state, column)` from `sort.js`. Null cells get class `kk-null` for the
  `--kk-faint` color.
- Empty rows → shows `t('table.empty', _, lang)`; filter-with-no-match → `t('table.noMatch',
  …)`.
- `renderTable` reuses existing `<table>` on re-render (replaces `<tbody>` only), so sort state
  survives EN⇄FI without a layout jump.

`chrome.js`:
- `renderHeader({ root, titleKey, subtitleKey, lang, onLangChange })`: breadcrumb, title,
  subtitle, EN|FI toggle (`aria-pressed`), focus-visible outlines.
- `renderPills({ root, state, onChange, lang })`: `All / F / D`, each a `<button
  aria-pressed="…">`, 44 px min target. `aria-pressed = state.pos === option`.
- `renderStaleBanner({ root, generatedAt, lang, now })`: calls `isStale`; if stale, renders
  `t('banner.stale', { date, time }, lang)`. Hidden otherwise.
- `renderErrorBanner({ root, lang })`: renders `t('banner.error', _, lang)`; the caller shows
  this instead of tables.
- `renderFooter({ root, dataDate, lang })`: `t('footer.through', { date }, lang)` + disclaimer.

**Validation**:
- [ ] `table.js` under 300 lines; `chrome.js` under 300
- [ ] No new `*.test.js` for these modules — the harness is the test
- [ ] Error-and-stale mutual exclusion is a caller-side concern (see Step 7 harness: when
      `renderErrorBanner` is called, do not also call `renderStaleBanner`)
**Commit**: `feat(06): table and chrome`

### Step 6: CSS tokens and components
**Files**: `site/kiekkokeskus/kk.css`

Tokens on `:root` (per init P0.8); components `.kk-table`, `.kk-scroll`, `.kk-pill`, `.kk-lang`,
`.kk-card`, `.kk-banner`, `.kk-null`, footer. Dark only. Barlow Condensed + IBM Plex Sans via
Google Fonts with `display=swap`. Container `max-width: 1180px`, 24 px gutter, 16 px below 600 px.
Tabular numerals in `.kk-table` cells. Visible `:focus-visible`. Touch targets ≥ 44 px.

**Validation**:
- [ ] No tests here; visual confirmation deferred to Step 11 harness check
- [ ] `kk.css` under 500 lines (ADR-034)
**Commit**: `feat(06): css tokens and components`

### Step 7: Dev harness and preview server
**Files**: `site/kiekkokeskus/_dev/harness.html`, `scripts/preview.py`, `tests/test_preview.py`

`_dev/harness.html`: for each of `bolts.json` and `leijonat.json`, renders header + banners +
pills + skater table + goalie table + footer. `leijonat` renders with the team column visible,
`bolts` without (toggle via a `data-page` attribute on the section root).

**P1.2 `?now=` override**: the harness parses `?now=<ISO>` from its own query string and
threads that `Date` into every `isStale` and `renderStaleBanner` call, so the stale banner can
be exercised without editing JSON or using `--fresh`. Missing / invalid `?now=` falls back to
`new Date()`. Documented inline at the top of `harness.html` and in a one-line comment next to
the `isStale` call.

Never deployed.

`scripts/preview.py` (stdlib only):
- Serves `site/` at `/` on `127.0.0.1:8006` (flag `--port`).
- Maps `/data/kiekkokeskus/bolts.json` and `/data/kiekkokeskus/leijonat.json` to `tests/golden/`
  by default, or to `--data DIR` (where a copy pulled with `aws s3 cp` can live).
- `--fresh`: rewrites `generatedAt` to **now** on the way out, so the stale banner can be seen
  both ways (goldens are always stale).
- `--break bolts` (or `leijonat`): serves `schemaVersion: 999` for that file, to force the error
  banner.
- Never writes to disk, never calls AWS, never calls the NHL.
- Sets `Content-Type: text/javascript` for `.js` and `text/css` for `.css` from
  `mimetypes.guess_type` (confirmed in the Verification table).

**Validation**:
- [ ] `.venv/bin/pytest tests/test_preview.py` covers:
  - path mapping (`/data/kiekkokeskus/bolts.json` resolves to `tests/golden/bolts.json`;
    any other `/data/kiekkokeskus/…` path returns 404)
  - `--fresh` rewrites `generatedAt` (compare bytes with a frozen `now`)
  - `--break bolts` writes `schemaVersion: 999` into the bolts response and leaves leijonat alone
  - `--data DIR` wins when passed
- [ ] `preview.py` ≤ 300 lines, stdlib-only (no `boto3`, no `urllib3`)
**Commit**: `feat(06): dev harness and preview server`

### Step 8: Deploy fills in the shared-asset sync
**Files**: `scripts/deploy.py`, `tests/test_deploy_shared.py`

Replace the `page_sync()` placeholder with one `aws s3 sync` call to
`s3://jurigregg-static-site/kiekkokeskus/`:

```python
def page_sync() -> None:
    dest = "s3://jurigregg-static-site/kiekkokeskus/"
    _check_allowed(dest)
    cmd = [
        "aws", "s3", "sync", "site/kiekkokeskus/", dest,
        "--delete",
        "--exclude", "*.test.js",
        "--exclude", "_dev/*",
        "--exclude", "package.json",
        "--cache-control", "public, max-age=300",
        "--profile", "default",
    ]
    # Pass env=_subprocess_env() for consistency with cdk_diff / cdk_deploy — same AWS_PROFILE
    # and the Node 22 PATH prefix (harmless here, keeps all three subprocesses symmetrical).
    subprocess.run(cmd, cwd=REPO_ROOT, env=_subprocess_env(), check=True)
```

`bolts/` and `leijonat/` syncs stay commented out — init-07 and init-08 enable them. The
existing `_check_allowed` already lists `kiekkokeskus/` and will refuse any other prefix.

`tests/test_deploy_shared.py`:
- `_check_allowed('s3://jurigregg-static-site/kiekkokeskus/')` returns normally
- `_check_allowed('s3://jurigregg-static-site/')` calls `sys.exit`
- `_check_allowed('s3://jurigregg-static-site/data/')` calls `sys.exit`
- `_check_allowed('s3://jurigregg-static-site/kiekkokeskus/subdir/')` returns normally
- `page_sync()` with a `subprocess.run` monkeypatch asserts the exact command arguments (ensures
  `--delete` is present, each `--exclude` is passed, `--cache-control` is the expected string,
  `--profile default` is set, no shell interpolation) **and that `env` was passed in** with
  `AWS_PROFILE=default` and `/opt/homebrew/opt/node@22/bin` on `PATH`, matching `cdk_diff` /
  `cdk_deploy`.

**Validation**:
- [ ] `.venv/bin/pytest tests/test_deploy_shared.py` green
- [ ] `scripts/deploy.py` without `--approved` still prints a `cdk diff` and exits 0
- [ ] File still ≤ 150 lines
**Commit**: `feat(06): deploy syncs shared assets`

### Step 9: Smoke checks for shared assets
**Files**: `scripts/smoke.py`, `tests/test_smoke_assets.py`

Extend `smoke.py`:
- `GET /kiekkokeskus/kk.css` → 200, `cache-control` contains `max-age=300`, `content-type`
  contains `text/css`
- `GET /kiekkokeskus/i18n.js` → 200, `cache-control` contains `max-age=300`, `content-type`
  starts with `text/javascript` **or** `application/javascript` (module scripts refuse anything
  else)

Keep every existing check: `/`, `/sports`, health, bolts, leijonat (CLAUDE.md Rule 1).

`tests/test_smoke_assets.py`: pure checks on the content-type matcher helper (any
`application/javascript; charset=utf-8` and `text/javascript` variants accepted; `text/plain` and
`text/html` rejected). No network.

**Validation**:
- [ ] `.venv/bin/pytest tests/test_smoke_assets.py` green
- [ ] `smoke.py` ≤ 300 lines
**Commit**: `feat(06): smoke checks shared assets`

### Step 10: CI runs Layer 5
**Files**: `.github/workflows/ci.yml`

Add a step to the `lint-and-test` job (or a new job) that installs Node 22 and runs
`node --test site/kiekkokeskus/` on push. TESTING.md already claims CI covers layers 1–5; this
step closes the gap left by prior PRPs.

**Validation**:
- [ ] `node --test site/kiekkokeskus/` runs locally and in CI, green
- [ ] `gh run watch` on the push shows the new step passing
**Commit**: `ci(06): run node tests`

### Step 11: Deploy and verify
```bash
cd infra && PATH="/opt/homebrew/opt/node@22/bin:$PATH" AWS_PROFILE=default npx cdk diff
# must print "no differences" — no CDK changes in this PRP
.venv/bin/python scripts/deploy.py                       # diff + exit
.venv/bin/python scripts/deploy.py --approved            # cdk deploy (no-op) + page_sync
.venv/bin/python scripts/smoke.py                        # new asset checks + / + /sports
```

Live checks:
- `aws s3 ls s3://jurigregg-static-site/kiekkokeskus/ --profile default` → no `*.test.js` or
  `_dev/`
- `curl -sI https://jurigregg.com/kiekkokeskus/kk.css` → `cache-control: public, max-age=300`,
  `content-type: text/css`
- `curl -sI https://jurigregg.com/kiekkokeskus/i18n.js` → `cache-control: public, max-age=300`,
  `content-type: text/javascript` (or `application/javascript`)
- If any `Content-Type` is wrong, add a second-pass sync with `--content-type` per extension
  (`--exclude '*' --include '*.js' --content-type 'text/javascript'`, etc.) and re-run smoke.

**Manual browser checklist** (Layer 7, Safari + Chrome):
- [ ] `python scripts/preview.py --fresh` → open `http://127.0.0.1:8006/kiekkokeskus/_dev/harness.html`
- [ ] EN ⇄ FI switches every string, name, number; `<html lang>` updates; URL updates with
      `?lang=`
- [ ] Both tables sort both ways with nulls last; stability holds when clicking the same column
- [ ] Position pills: All / F / D
- [ ] Reload with `?pos=d&sort=toiPerGame&dir=desc&gsort=svPct&gdir=asc&lang=fi` restores
      exactly
- [ ] Stop `--fresh`; the stale banner appears (goldens are from 2026-10-10)
- [ ] `--break bolts` shows the error banner for bolts; leijonat still renders
- [ ] Phone width (375 px, DevTools): tables scroll horizontally with the name column pinned,
      no page-level horizontal scroll
- [ ] Safari and Chrome both show FI `91,57`, `−1` (U+2212), `14,3 %` (NBSP), `2.10.2026`,
      `la 10.10. klo 19.30` with no "�"

**Validation**:
- [ ] `cdk diff` prints `no differences` or only outputs no-op metadata
- [ ] Smoke passes, including `/`, `/sports`
- [ ] All manual checklist items pass; capture any Safari / Chrome mismatch and address before
      marking Complete

**Commit**: nothing to commit here unless a content-type fix is needed. If a content-type pass is
added to `deploy.py`, commit it as `fix(06): per-ext content-type on sync`.

### Step 12: Documentation and close-out
**Files**: `docs/DECISIONS.md`, `docs/TESTING.md`, `docs/TASK.md`, `prps/prp-06-shared-ui.md`
(status flip)

- Append **ADR-038** (Stat display conventions, EN/FI) and **ADR-039** (Shared assets deploy +
  Cache-Control) to `docs/DECISIONS.md`, using the drafts in init-06 Notes verbatim with next
  global numbers.
- Add the Page-logic gotcha rows to `docs/TESTING.md`'s gotcha matrix under a new "Page logic"
  heading, each citing ADR-038 / ADR-015 / ADR-018 / ADR-037 as appropriate (list in Testing
  Requirements below).
- In `docs/TASK.md`: move init-06 to Recently Completed with a one-line outcome; **remove** the
  "FI save %" Open Question (settled by ADR-038); set `init-07-bolts-page` as the next Up Next
  item. Update the Last-updated date.
- Flip `prps/prp-06-shared-ui.md` status Ready → Complete.

**Validation**:
- [ ] `grep "ADR-038" docs/DECISIONS.md` and `grep "ADR-039" docs/DECISIONS.md` succeed
- [ ] `docs/TASK.md`'s **Open Questions section** no longer contains "FI save %" — scope the
      check to that section only (ADR-038's own body in `docs/DECISIONS.md` references the
      question text while settling it, so a repo-wide `grep "FI save" docs/` would never be
      empty)
- [ ] `awk '/^## Open Questions/{flag=1; next} /^## /{flag=0} flag' docs/TASK.md | grep -F
      "FI save"` returns no lines
- [ ] All layered checks green (`pytest`, `node --test`, `npm test`, `smoke`)
**Commit**: `docs(06): ADR-038, ADR-039, TESTING, TASK, complete`

---

## Testing Requirements

| Layer (TESTING.md) | Tests | Fixture / Gotcha row |
|---|---|---|
| 1 Parse contract | n/a — no parser touched | — |
| 2 Builder golden | n/a — no builder touched; `tests/golden/{bolts,leijonat}.json` read in Layer 5 as fixtures | — |
| 3 Orchestration | n/a — no handler change | — |
| 4 Infra | `cdk synth` and existing `infra/test/` assertions remain green (no CDK change) | — |
| 5 Page logic | `strings.test.js`, `i18n.test.js`, `format.test.js`, `columns.test.js`, `sort.test.js`, `url.test.js`, `data.test.js` (DOM rendering covered by the harness + Layer 7) | every row below |
| 6 Smoke | `scripts/smoke.py` adds `/kiekkokeskus/kk.css` and `/kiekkokeskus/i18n.js` checks | — |
| 7 Manual | Step 11 browser checklist (Safari + Chrome) | Safari Intl parity (Verify item 4) |

### Page-logic gotcha rows (new rows for `docs/TESTING.md`)

| ADR | Gotcha | Fixture must contain | Assert |
|---|---|---|---|
| 015 | null in any column | golden `faceoffPct: null` (bolts McDonagh) | renders `–` (U+2013); sorts last in asc and desc |
| 018 | partial FI name | golden Vasilevskiy (bolts: `lastName.{default,fi,cs,sk}`, `firstName.default` only) | FI: `Andrei Vasilevski`; EN: `Andrei Vasilevskiy` |
| 018 | extra name languages | golden `cs`/`sk`/`sv` keys on Teräväinen (leijonat) | ignored, no crash, object passed through untouched |
| 038 | FI minus and NBSP | synthetic `pm: -1`, `pct1Sign(0.143, 'fi')` | `−1` (U+2212) in EN and FI; FI `14,3 %` has U+00A0 |
| 038 | `rate3` edges | `0.9`, `1.0`, `0.0` | EN `.900`, `1.000`, `.000`; FI `90,00`, `100,00`, `0,00` |
| 038 | goalie season TOI | `toi: 10552` | EN `175:52`, FI `175.52` |
| 038 | date west of UTC | `date('2026-10-02', 'en')` under `TZ=America/Los_Angeles` | `Oct 2, 2026`, not `Oct 1` |
| 038 | stale boundary | `isStale(gen, gen ± 36h)` | `false` at 35h59m, `true` at 36h01m |
| 038 | schema mismatch | stub `fetchFn` returns `{ schemaVersion: 2 }` | returns `{ ok: false, reason: 'schema' }`, no throw |
| 028 | missing i18n key | every key present in `en` is present in `fi`, and reverse | strict parity, failing with the diff list |

The TESTING.md Watch List and Date and Time Boundaries sections stay untouched.

---

## Error Handling and Edge Cases

| Case | Source | Handling | Test |
|---|---|---|---|
| Fetch throws (offline, DNS) | `data.loadData` | `{ ok: false, reason: 'fetch' }`; `console.error`; module does not re-throw | `data.test.js` stub throws |
| HTTP 404 / 5xx | `data.loadData` | `{ ok: false, reason: 'http' }`; `console.error`; module does not re-throw | `data.test.js` stub returns non-2xx |
| Invalid JSON | `data.loadData` | `{ ok: false, reason: 'json' }`; `console.error`; module does not re-throw | `data.test.js` stub returns garbage |
| `schemaVersion` mismatch | `data.loadData` | `{ ok: false, reason: 'schema' }`; **no exception**; caller renders error banner | `data.test.js` |
| Row with any null stat | ADR-015 | formatter → `'–'`; sort places null last in both dirs | `sort.test.js`, `format.test.js` |
| Row with only `lastName.fi`, no `firstName.fi` | ADR-018 | FI: `firstName.default` + ` ` + `lastName.fi` | `i18n.test.js` Vasilevskiy |
| Row with extra `cs`/`sk`/`sv` name keys | ADR-018 | pass through, never deleted or picked | `i18n.test.js` |
| `localStorage` unavailable (private mode, denied) | `i18n.resolveLang` + toggle | try/catch, fall through; language rule continues | `i18n.test.js` stub |
| Unknown `?sort=moonshot` | `url.readState` | drop silently, default to `p` | `url.test.js` |
| Stale JSON (`generatedAt` > 36 h) | `chrome.renderStaleBanner` | banner above tables; tables still render | `data.test.js` + manual |
| `pct1Sign` NBSP missing in Safari | Verify item 4 fallback | manual string construction (`fmt + ' %'`) in that formatter only | manual check |
| CloudFront serves wrong `Content-Type` on JS/CSS | Verify item 2 fallback | second-pass sync with `--content-type` per extension | smoke + live `curl -sI` |

---

## Cost Impact

**None.** Same single daily Lambda run. Shared-asset sync is one deploy-time operation that
uploads a few tens of KB to the existing bucket; no new storage class, no new request pattern.
CloudFront is already paid for by the main site. The browser now makes 2–3 extra same-origin
requests on first page load (`i18n.js`, `kk.css`, Google Fonts) — all cacheable, well under the
PLANNING.md 150 KB-per-page target.

---

## Rollback Plan

1. **Code**: `git revert` the PRP's commits, then `.venv/bin/python scripts/deploy.py --approved`.
   The `page_sync()` placeholder returns, which is a no-op; nothing in `kiekkokeskus/` gets
   deleted (because `--delete` only runs when `page_sync` executes). To **remove** the shared
   assets, run `aws s3 rm s3://jurigregg-static-site/kiekkokeskus/ --recursive --profile default`
   manually (prefix-scoped, allowed by ADR-024).
2. **Data**: no `data/` paths are written in this PRP. `bolts.json` / `leijonat.json` are
   untouched. S3 noncurrent versions kept for 7 days (ADR-023) if a later page-sync somehow
   corrupts them (not possible via this PRP's scope).
3. **Verify**: `.venv/bin/python scripts/smoke.py` passes (the asset-check steps will now 404,
   expected); `/`, `/sports`, `/bolts`-free, `/leijonat`-free, all 200. Pages themselves don't
   exist yet so a rollback cannot visibly break any user-facing page.

---

## Open Questions

(none)

---

## Confidence Scores

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 9 | Spec enumerates every formatter output, every column, every i18n key, every URL param, and every gotcha row. Only ambiguity is the `rate3` FI example `91,57` (clearly for a different input value than EN `.915` — resolved via the explicit gotcha-row edge cases) |
| Feasibility | 9 | Vanilla ES modules, stdlib Python preview, no new infra, no NHL fetch. Node 22's zero-config `.test.js` already verified. No new runtime deps |
| Completeness | 9 | Every field has a source; every gotcha row has a named test; S3 keys, Cache-Control, and `--delete` scoping all documented against ADR-024/039. CI gap for Layer 5 identified and fixed in Step 10 |
| Payload certainty | 10 | No NHL endpoint is called in this PRP. All page-logic tests read `tests/golden/{bolts,leijonat}.json`, which were spot-checked and contain every needed shape (Vasilevskiy partial-FI, Teräväinen multi-lang, McDonagh null `faceoffPct`) |
| **Average** | **9.25** | **Ready to execute** |

### Verification results (surprises, if any)
- **No surprises.** All four spec claims that could have broken were verified live: Node 22
  needs no `package.json`, Intl FI minus is U+2212, Intl FI percent has NBSP, and `new Date` on
  bare `YYYY-MM-DD` does shift the day west of UTC — the fix is a UTC-noon parse.
- One deferred item: CloudFront serving `Cache-Control: public, max-age=300` on CSS, which is a
  live check in Step 11 (ADR-022 suggests it will work; fallback documented).

### Suggested new ADRs
- **ADR-038** (`docs/DECISIONS.md`) — Stat display conventions, EN/FI. Draft text in init-06
  Notes. Settles the TASK.md "FI save %" Open Question.
- **ADR-039** (`docs/DECISIONS.md`) — Shared page assets deploy with their own Cache-Control.
  Draft text in init-06 Notes. Settles why `--cache-control` must be set at sync time (ADR-022's
  "legacy TTL default 3600" would otherwise take over for a full hour per deploy).

Both are listed as **Accepted** in the init draft and will be added verbatim in Step 12.
