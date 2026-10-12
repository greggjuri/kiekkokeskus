# PRP-08: /leijonat Page

**Created**: 2026-10-12
**Initial**: `initials/init-08-leijonat-page.md`
**Status**: Ready
**ADRs relied on**: ADR-002, 003, 010–012, 015–018, 020–022, 024, 028, 030, 034, 037–040
**New ADRs this PRP adds**: **none** (ADR-040 already covers the lion hero; ADR-037 already
says the badge comes from `game.result`, never `decision`)

---

## Overview

### Problem Statement
`leijonat.json` is published daily, but no page reads it. init-07 built every shared piece this
page needs: the controller (`page.js`/`controller.js`), the hero param, `localName`, `tp`, the
tiles layout and card styles. init-08 is the second consumer of that layer.

### Proposed Solution
Build `/leijonat` as a thin shell exactly like `/bolts`: `site/leijonat/view.js` is a pure
view model, `main.js` is DOM glue around `mountPage`, `index.html` is a 10-slot shell. The
page shows the lion hero, four count tiles + a definition line, the "last night" cards (one
per Finn who scored or started), the skater and goalie tables **with** the team column and a
rookie marker, and a compact by-team list. One shared change lands in `table.js`: an
optional `decorateName` callback that adds the rookie `*` to the player-name cell. `/bolts`
passes no `decorateName`, so its output is byte-identical. Deploy chains shared → bolts →
leijonat.

### Success Criteria
- [ ] `node --test "site/kiekkokeskus/*.test.js" "site/bolts/*.test.js" "site/leijonat/*.test.js"`
      green, covering the golden expected-strings table and every gotcha row below
- [ ] CI runs all three globs
- [ ] `ruff`, `pytest` (≥ 80%) green, with the deploy test extended to three syncs
- [ ] `python scripts/preview.py --fresh`, then `/leijonat/` in Chrome at desktop and 375 px
      via DevTools device emulation: every string / name / number switches EN⇄FI; both tables
      sort desc → asc → desc on the same column (including `team`); rookie markers and legend
      appear; no page-level horizontal scroll
- [ ] `/bolts` still renders and behaves the same (regression pass: toggle, sort ×3, pill)
- [ ] DevTools Network: exactly one `leijonat.json` request across toggling, filtering,
      sorting
- [ ] Deploy: dry runs show no deletes and no test files on either prefix; syncs fire
      shared → bolts → leijonat; `smoke.py` green including `/leijonat` + `/leijonat/hero.webp`
- [ ] `https://jurigregg.com/leijonat` shows live data in both languages
- [ ] TESTING.md Page-logic matrix gains the init-08 rows; manual-checklist line updated per
      P0.0; TASK.md moves init-08 to Recently Completed; Up Next is init-09
- [ ] No code file over 500 lines (ADR-034; docs exempt)

---

## Context

### Related Documentation
- `docs/PLANNING.md`: data contract (fractions 0–1, int-second TOI, localized names, 36-h
  stale rule, S3 prefix layout, cost budget)
- `docs/DECISIONS.md`: ADR-002 (not-affiliated), ADR-003 (same-origin only), ADR-020 (prefix
  layout), ADR-021 (`add-index-html` untouched), ADR-022 (own Cache-Control on current JSON;
  legacy TTL 3600), ADR-024 (prefix-scoped syncs, no `--delete` at bucket root), ADR-028
  (EN/FI toggle), ADR-030 (sortable + filterable tables), ADR-034 (500-line code limit),
  ADR-038 (EN/FI display conventions — FI abbreviations `M`/`S` match `lastNight.skaterLine`),
  ADR-039 (shared assets deploy + `max-age=300`), ADR-040 (page hero art — the lion hero
  uses the same desktop + <600 px rules)
- `docs/DECISIONS-DATA.md`: ADR-010 (a Finn is `nationalityCode == FIN`), ADR-011 (bios +
  pagination; `BiosDuplicateError`), ADR-012 (`lastNight` = boxscores ⋈ Finn set; "registered
  a point or started"), ADR-015 (null for missing), ADR-016 (fractions 0–1), ADR-017 (TOI
  int seconds), ADR-018 (localized names), ADR-037 (`leijonat.json` field sources; **`rookie`
  is a non-null bool**; **`game.result` is derived from score + `lastPeriodType`, never from
  goalie `decision`**; traded Finns watch item)
- `docs/TESTING.md`: Layer 5 (`node --test`), Layer 6 (smoke), Layer 7 (manual — the "sort
  the same column three times" line gets strengthened per P0.0)

### Dependencies
- **Required**:
  - PRP-05 complete (`leijonat.json` builder, golden committed at
    `tests/golden/leijonat.json`)
  - PRP-07 complete (shared UI deployed): `page.js` + `controller.js` + `mountPage`,
    `renderHeader(hero)`, `localName`, `tp`, `format.{ordinal,season}`, `kk-page.css` with
    `.kk-hero` + `.kk-tiles` + `.kk-card-grid`, `scripts/deploy.py` with
    `_bolts_sync_cmd()` and the shared/bolts ordering, `scripts/smoke.py` with the `/bolts`
    + hero checks
- **Optional**: none

### Files to Modify/Create
```
docs/TESTING.md                             MODIFY: P0.0 manual-checklist line + Page-logic rows
site/kiekkokeskus/strings.js                MODIFY: + ~15 keys for page.leijonat.*, count.*,
                                                     leijonat.definition, lastNight.*, rookie.*,
                                                     byTeam.*
site/kiekkokeskus/strings.test.js           MODIFY: pin FI count/rookie/byTeam/lastNight terms;
                                                     parity still holds
site/kiekkokeskus/table.js                  MODIFY: + optional decorateName(row, lang) →
                                                     {suffix, title}; new pure nameCellParts
                                                     helper; /bolts path byte-identical
site/kiekkokeskus/table.test.js             MODIFY: new tests — decorateName renders suffix
                                                     + sr-only title; absent → no suffix node
                                                     (/bolts regression lock)
site/kiekkokeskus/_dev/harness.html         MODIFY: drop the /leijonat preview section (P1.1,
                                                     Code's call: the real page now exists and
                                                     is served by scripts/preview.py)
site/kiekkokeskus/kk-page.css               MODIFY (small): .kk-byteam list rows; .kk-rookie
                                                     marker + sr-only utility if not already
                                                     present
site/leijonat/index.html                    NEW: shell (lion hero, tiles, lastNight, skaters,
                                                   goalies, byTeam, footer)
site/leijonat/main.js                       NEW: thin DOM glue — mountPage with leijonatView
site/leijonat/view.js                       NEW: pure leijonatView(data, lang) → tiles +
                                                 lastNight cards + byTeam rows + legend flags
site/leijonat/view.test.js                  NEW: golden-driven assertions + gotcha rows
site/leijonat/hero.webp                     GIT-TRACK: 900×604, 40 KB (file already in place)
art/leijonat-hero-source.jpg                GIT-TRACK: never deployed (art/ sits outside site/)
scripts/deploy.py                           MODIFY: add _leijonat_sync_cmd() + 3rd chain
tests/test_deploy_leijonat.py               NEW: shape + ordering (shared → bolts → leijonat)
                                                   + env + exclude; mirrors test_deploy_bolts.py
scripts/smoke.py                            MODIFY: + /leijonat + /leijonat/ + /leijonat/hero.webp
tests/test_smoke_leijonat.py                NEW: thin — the pure helpers are shared, but
                                                   locks the leijonat path constants
.github/workflows/ci.yml                    MODIFY: run all three globs in the pages job
docs/TASK.md                                MODIFY: move init-08 to Recently Completed; next=init-09
```
Code files stay under 500 lines (ADR-034). Expected sizes: `view.js` ~200, `main.js` ~140,
`index.html` ~55, `view.test.js` ~230, `table.js` ~210 after addition, `strings.js` ~170 after
~15 keys per lang. `kk-page.css` grows ~40 lines (should stay well under 500).

---

## Verification of Unconfirmed Facts

| Assumption | Checked how | Result | Follow-up |
|---|---|---|---|
| Every live `skaters[]`/`goalies[]` row has `gp ≥ 1` (Verify item 1) | `python` probe over `tests/golden/leijonat.json` | **Confirmed.** 0 rows with `gp < 1` on either list — definition's second sentence stays | None |
| `team` is never null (Verify item 2) | Same probe | **Confirmed.** 0 skaters and 0 goalies with falsy `team`. (Fallback to `–` is still coded for safety; untested path for now) | None (ADR-037 Known-Issue traded-Finns watch stays) |
| `lastNight` is always present in the live file (Verify item 3) | Probe golden + ADR-012 | **Confirmed in the golden** (`lastNight: { date: '2026-10-09', gamesCompleted: 4, skaters: [2], goalies: [0] }`). ADR-012 does not promise `lastNight` is always present, so the view defensively treats a missing object as `gamesCompleted: 0` (empty-state branch) | None |
| `teams[]` totals equal per-team row counts (Verify item 4) | Counter-compare in the probe | **Confirmed.** 0 mismatches across all 19 teams | None. View uses `t.skaters + t.goalies` as the authoritative count (matches row count today); will log a `console.warn` only if a future payload breaks parity |
| Count tile values match spec exactly | Golden length / rookie counter | **Confirmed.** 30 skaters / 5 goalies / 19 teams / 4 rookies (all skaters: Helenius, Hyry, Lambert, Ottavainen — no goalie rookies, so the goalie-table legend is hidden in today's data) | Lock in `view.test.js` |
| Granlund and Kakko card data matches spec | Probe `lastNight.skaters` | **Confirmed byte-for-byte.** `{ Mikael Granlund, ANA, g: 1, a: 1, game: W 5-1 away vs WPG, decidedIn: REG }` and `{ Kaapo Kakko, SEA, g: 0, a: 1, game: W 6-3 away vs DET, decidedIn: REG }` | Lock in `view.test.js` |
| DAL's 6 Finns (Heiskanen, Hintz, Hyry, Kiviranta, Lindell, Rantanen) match spec | Group-by-team + sort probe | **Confirmed** exactly | Lock in `view.test.js` |
| Hero assets exist pre-execution (ADR-040) | `ls -la art/ site/leijonat/` + `file site/leijonat/hero.webp` | **Confirmed.** `site/leijonat/hero.webp` is `RIFF Web/P VP8 900×604`, 40,176 bytes; `art/leijonat-hero-source.jpg` is 429,961 bytes. Both currently untracked | Git-add both in Step 3 (`feat(08): leijonat view, shell, hero, CSS`) |
| `s3://jurigregg-static-site/leijonat/` is empty before first sync | `aws s3api list-objects-v2 … --prefix leijonat/` | **Confirmed empty** (`list-objects-v2` returned no `Contents` key). First dry-run must show exactly 4 uploads, 0 deletes | Step 7 will re-check before the real sync |
| CI runs the bolts glob | Grep `.github/workflows/ci.yml` | **No.** CI currently only runs `site/kiekkokeskus/*.test.js`. The bolts tests have been running locally since PRP-07 but **not in CI** — gap unnoticed because they stayed green. init-08 adds the third glob and quietly adds the bolts glob too | Step 6 wires all three in one shot |

**No NHL fetch** is required. All Layer 5 tests read `tests/golden/leijonat.json` or
synthesize gotcha inputs inline.

---

## Technical Specification

### Output Schema
Page is **read-only**. `schemaVersion` unchanged (expects `1`). No builder change.

**S3 keys written** by `deploy.py --approved`:
- `s3://jurigregg-static-site/kiekkokeskus/*` with `Cache-Control: public, max-age=300`
  (updated: `table.js`, `strings.js`, plus `kk-page.css` if the byteam/rookie CSS lands there)
- `s3://jurigregg-static-site/bolts/*` — no new objects this PRP, but the shared sync may
  touch it indirectly if `kk.css`/`kk-page.css` change (today they do not — only
  `kk-page.css` grows)
- `s3://jurigregg-static-site/leijonat/*` with `Cache-Control: public, max-age=300`
  (NEW: `index.html`, `main.js`, `view.js`, `hero.webp`), `--delete` scoped to the
  `leijonat/` prefix (allowed by ADR-024), `*.test.js` excluded

Fields consumed beyond the init-06 table set (all from `tests/golden/leijonat.json`):

| Field | Units / type | Nullable | Rendered as |
|---|---|---|---|
| `season` | 8-char string | no | subtitle via `season()` |
| `skaters[].team`, `goalies[].team` | abbrev | no in practice (ADR-037, verified above) | team column, by-team names |
| `skaters[].rookie`, `goalies[].rookie` | bool (non-null per ADR-037) | no | `*` marker + legend + rookies tile |
| `teams[].{abbrev, name, skaters, goalies}` | abbrev, {default,fi?}, int, int | no | teams tile + by-team list |
| `lastNight.{date, gamesCompleted}` | ET date, int | object may be absent → empty state | heading + sub-line |
| `lastNight.skaters[].{firstName, lastName, team, g, a, game}` | localized obj × 2, abbrev, int, int, obj | list may be empty | skater cards |
| `lastNight.goalies[].{firstName, lastName, team, saves, shotsAgainst, svPct, game}` | — / ints / fraction 0–1 | `saves`, `shotsAgainst`, `svPct` nullable (ADR-015) | goalie cards |
| `lastNight.*.game.{home, opponent, teamScore, oppScore, result, decidedIn}` | bool, **string abbrev**, int, int, `W`/`L`/`OTL`, `REG`/`OT`/`SO`/null | `decidedIn` nullable | result badge + score + OT suffix + `opp.home`/`opp.away` |

**Explicitly not shown**: `lastNight.*.{pm, sog, pim, toi}`, goalie `decision`, `playerId`
(used only as a DOM key where needed), `standing.pointPct` (which doesn't exist in
`leijonat.json`).

### Module Design

```javascript
// site/kiekkokeskus/table.js — add optional decorateName
//
// decorateName(row, lang): { suffix?: string, title?: string } | null
//   suffix is appended after the player name as a <span class="kk-mark"> with the suffix
//   text and an accompanying sr-only <span class="kk-sr-only">{title}</span> so screen
//   readers say "Rookie"/"Tulokas" instead of "star". Omitting decorateName (or returning
//   nullish) renders no extra node — /bolts output is byte-identical to today.
export function renderTable({ root, columns, rows, state, lang, onSortChange, decorateName }) { … }

// site/leijonat/view.js — NEW (pure)
export function leijonatView(data, lang) {
  return {
    pageTitle, subtitle, hero: { src: '/leijonat/hero.webp', width: 900, height: 604, alt: '' },
    tiles: {                       // 4 count tiles, no sub-line
      skaters:  { label: t('count.skaters', null, lang),  value: `${data.skaters.length}` },
      goalies:  { label: t('count.goalies', null, lang),  value: `${data.goalies.length}` },
      teams:    { label: t('count.teams',   null, lang),  value: `${data.teams.length}` },
      rookies:  { label: t('count.rookies', null, lang),  value: `${countRookies(data)}` },
    },
    definition: t('leijonat.definition', null, lang),
    lastNight: lastNightSection(data, lang),  // → { heading, subLine, cards, emptyMessage|null }
    byTeam: byTeamRows(data, lang),           // → [{ name, playersLabel, finnNames }]
    skaterRookieLegend: hasRookie(data.skaters), // boolean → render legend line
    goalieRookieLegend: hasRookie(data.goalies), // boolean → render legend line (hidden today)
  };
}

// lastNightSection returns:
//   { empty: false, heading, subLine, cards: [{ ...rowView }] }
//   | { empty: true,  heading, subLine, message: 'noGames'|'noFinns' }
//
// A card view (skater or goalie):
//   { kind: 'skater'|'goalie', name, team, rookie: bool, big: '…', badge, score, suffix, oppLine }
//
// All strings come from t()/tp()/format.*; the view is pure.

// site/leijonat/main.js — thin DOM glue
//
// mountPage({
//   dataPath: '/data/kiekkokeskus/leijonat.json',
//   expectedSchemaVersion: 1,
//   columns: SKATER_COLUMNS,          // full set, team column kept
//   goalieColumns: GOALIE_COLUMNS,
//   defaults: { pos: 'all', sort: 'p', dir: 'desc', gsort: 'gp', gdir: 'desc' },
//   titleKey: 'page.leijonat.title',
//   subtitle: (data, lang) => data
//     ? t('page.leijonat.subtitle', { season: season(data.season) }, lang)
//     : t('page.leijonat.subtitleNoSeason', null, lang),
//   hero: { src: '/leijonat/hero.webp', width: 900, height: 604, alt: '' },
//   slots,
//   // Pass decorateName down to BOTH tables so the rookie * appears in skaters AND goalies.
//   decorateName: (row, lang) => row?.rookie
//     ? { suffix: ' *', title: t('rookie.title', null, lang) }
//     : null,
//   renderSections: ({ data, lang, slots }) => {
//     if (!data) { /* placeholders — tiles '–', lastNight/byTeam empty */ return; }
//     const view = leijonatView(data, lang);
//     renderCountTiles(slots.tiles, view.tiles);
//     slots.definition.textContent = view.definition;
//     renderLastNight(slots.lastNight, view.lastNight, lang);
//     renderByTeam(slots.byTeam, view.byTeam, lang);
//     slots.skaterRookieLegend.hidden = !view.skaterRookieLegend;
//     slots.goalieRookieLegend.hidden = !view.goalieRookieLegend;
//   },
// });
```

**`mountPage` change**: `decorateName` is a new optional parameter threaded through
`createController`'s render adapter down to both `renderTable` calls. /bolts/main.js does
not pass it. Spec P0.6 → "Needs a small shared change: `renderTable` takes an optional
`decorateName(row, lang)` that returns `{ suffix, title }`. `/bolts` doesn't pass it, so its
output is unchanged." I'll pin that in a regression test.

**Sorting by name ignores the marker** (P0.6): the sort comparator keys off
`nameSortKey(row, lang)` from `i18n.js`, which reads the raw name parts — the `*` is only
added by the renderer. No code change needed; a test asserts `renderName(row).trim()` and
`nameSortKey(row)` ignore `row.rookie`.

**By-team order** (P0.7): total players desc, then rendered team name asc using
`localeCompare(…, lang)`. In today's golden, two teams tie at 3 players (LAK + VAN), so
`Los Angeles Kings` sorts before `Vancouver Canucks`. Gotcha-matrix row locks it.

### Page Changes
`/leijonat` is new. `/bolts` is **unchanged**. `/leijonat` section order:
1. header (hero + title + subtitle + toggle, identical layout to `/bolts`)
2. 4 count tiles (`.kk-tiles` grid)
3. one-paragraph definition under the tiles
4. **last night**: heading `Last night` + sub-line `{date} · {games}`, then a card grid
   (`auto-fill, minmax(260px, 1fr)`). Each card = name (+ rookie marker) · team · big stats
   line · result badge + score + opp line
5. skaters table (pills + rookie markers in name column + legend line under table when
   `skaterRookieLegend`)
6. goalies table (same)
7. by-team list (compact `.kk-card`, not a table — total desc then name asc)
8. footer (unchanged)

### Infra Changes
**None.** `cdk diff` must show "no differences" at Step 7. Ownership Check: AWS resources
created or changed → none. S3 prefixes written: `leijonat/` (new) and `kiekkokeskus/`
(update). Main site untouched (ADR-021 `add-index-html` stays untouched).

---

## Implementation Steps

Each step is one validated commit: `{type}(08): {description}`.

### Step 0: Housekeeping + start
**Files**: `docs/TASK.md`, `docs/TESTING.md`, `initials/init-08-leijonat-page.md`,
`prps/prp-08-leijonat-page.md`

- Move init-08 to **In Progress** in `docs/TASK.md`; next-up stays init-09.
- In `docs/TESTING.md`'s manual checklist (Layer 7), replace the "Sorting each column works
  in both directions" line with:
  **"Click the same column three times: desc → asc → desc, on both tables"** (P0.0 —
  the old wording let the stale-closure bug through two manual passes).
- Add the init + PRP files to git (same shape as `docs(0{1..7}): start`).

**Validation**:
- [ ] `grep -nF "Sorting each column works in both directions" docs/TESTING.md` returns no
      lines
- [ ] `grep -nF "desc → asc → desc" docs/TESTING.md` returns the new line
- [ ] `.venv/bin/pytest -q` green (baseline, 180 passed)
- [ ] `node --test "site/kiekkokeskus/*.test.js" "site/bolts/*.test.js"` green (baseline,
      116 passed)

**Commit**: `docs(08): start`

### Step 1: Strings (plus parked `tile.record` FI rename)
**Files**: `site/kiekkokeskus/strings.js`, `site/kiekkokeskus/strings.test.js`,
`site/bolts/view.test.js`

Add every key from the P0.9 table in both languages — ~15 new keys. Including plural pairs
(`lastNight.games.one`/`.other`, `byTeam.players.one`/`.other`). Keep `col.*` out
(single-source in `columns.js`, as always).

**Also land the parked `tile.record` FI rename**: `Saldo` → `Tilanne`. Update the FI pin in
`strings.test.js` and the golden FI expected string in `site/bolts/view.test.js`
(`v.tiles.record.label === 'Tilanne'` and the row cell in the FI "golden view" test). `/bolts`
picks it up in the same deploy — one text change, zero behavioral risk.

**Validation**:
- [ ] `node --test "site/kiekkokeskus/strings.test.js" "site/bolts/view.test.js"` green:
  - Parity still passes (every new key in both langs)
  - Pin FI: `count.skaters='Kenttäpelaajat'`, `count.goalies='Maalivahdit'`,
    `count.teams='Joukkueet'`, `count.rookies='Tulokkaat'`
  - Pin FI: `tile.record='Tilanne'` (was `Saldo`)
  - Pin FI: `rookie.title='Tulokas'`, `rookie.legend='* Tulokas'`
  - Pin FI: `byTeam.title='Joukkueittain'`
  - Pin FI: `lastNight.title='Viime yönä'`, `lastNight.noGames` and `lastNight.noFinns`
    exact strings
  - `page.leijonat.subtitle` contains `{season}`; `page.leijonat.subtitleNoSeason` contains
    **no `{`** in either language (same guardrail as PRP-07)
  - `lastNight.skaterLine.{one,other}` not applicable (not a plural pair) — this is a
    single template with `{g}` and `{a}`. Just assert the template contains both placeholders
    in both langs
- [ ] `strings.js` under 200 lines (currently ~140; +15 keys per lang ≈ 170)

**Commit**: `feat(08): strings for /leijonat page`

### Step 2: `nameCellParts` + `decorateName` in `renderTable`
**Files**: `site/kiekkokeskus/table.js`, `site/kiekkokeskus/table.test.js`

Pull the "what goes in the name cell" decision into a pure helper so the Node tests stay
DOM-free (same reason PRP-06 and PRP-07 skipped hand-rolled `Document` stubs):

```javascript
// Pure. No DOM. Returns the three parts that the DOM renderer places into the <td>.
//   decorateName is (row, lang) => { suffix, title } | null — same signature used by
//   mountPage, Module Design, and site/leijonat/main.js.
export function nameCellParts(row, lang, decorateName) {
  const name = renderName(row, lang);
  if (!decorateName) return { name, suffix: null, title: null };
  const deco = decorateName(row, lang);
  if (!deco || !deco.suffix) return { name, suffix: null, title: null };
  return { name, suffix: deco.suffix, title: deco.title ?? null };
}
```

The DOM path in `renderTable`:
- When `suffix === null`: the name cell stays a **bare text node** — exactly what `/bolts`
  renders today. No wrapping `<span>`, no extra elements. This is the /bolts byte-identity
  guarantee.
- When `suffix !== null`: append `<span class="kk-mark" aria-hidden="true">{suffix}</span>`
  plus `<span class="kk-sr-only">{title}</span>` (sr-only — see Step 3 CSS). The name itself
  stays a text node preceding those spans.

Signature is `decorateName(row, lang)` everywhere — Module Design, `main.js`, and this
helper agree (not the `{ row, lang }` destructured form that slipped into the first draft).

**Validation**:
- [ ] `node --test "site/kiekkokeskus/table.test.js"` green with new **pure** cases:
  - `nameCellParts({firstName:{default:'Olli'}, lastName:{default:'Maatta'}}, 'en', null)` →
    `{ name: 'Olli Maatta', suffix: null, title: null }` (no decorateName → both null)
  - Same row with `decorateName: () => null` → both null
  - `rookie: true` row with `decorateName: (r,l) => r.rookie ? { suffix:' *', title:'Rookie' } : null`
    → `{ name:'…', suffix:' *', title:'Rookie' }`
  - `rookie: false` row with the same decorateName → both null
  - FI lang threaded through: `decorateName: (r,l) => r.rookie ? { suffix:' *', title: l==='fi'?'Tulokas':'Rookie' } : null` → `title: 'Tulokas'` when `lang='fi'`
  - **Name sort ignores marker** (pure, uses `nameSortKey` from `i18n.js`): build two rows
    (rookie Helenius, non-rookie Heiskanen), assert `sortRows([…], nameCol, {dir:'asc', lang})`
    puts Heiskanen first regardless of `rookie`
- [ ] **No fake DOM.** Any DOM assertion (bare text node, `.kk-mark` presence) is deferred
      to the Chrome manual pass in Step 7
- [ ] `table.js` under 300 lines (currently 189; +~25)

**Commit**: `feat(08): nameCellParts + decorateName in renderTable`

### Step 3: Leijonat view model + shell + hero + CSS
**Files**: `site/leijonat/index.html`, `site/leijonat/main.js`, `site/leijonat/view.js`,
`site/leijonat/view.test.js`, `site/leijonat/hero.webp` (git-add existing),
`art/leijonat-hero-source.jpg` (git-add existing), `site/kiekkokeskus/kk-page.css` (small
additions)

`view.js` structure (pure, no DOM):

```javascript
import { t, tp, localName, renderName } from "../kiekkokeskus/i18n.js";
import { date, rate3, season } from "../kiekkokeskus/format.js";

const EN_DASH = "–";

function countRookies(data) { … }                       // sum rookie:true across both lists
function hasRookie(rows) { … }                          // for the per-table legend flag

function lastNightCard(row, kind, lang) {
  const { g, a, saves, shotsAgainst, svPct, game, team, rookie } = row;
  const name = renderName(row, lang);
  const badge = t(`result.${game.result}`, null, lang);
  const suffix = game.decidedIn && game.decidedIn !== "REG"
    ? t(`decided.${game.decidedIn}`, null, lang) : "";
  const oppLine = t(game.home ? "opp.home" : "opp.away", { opp: game.opponent }, lang);
  const score = `${game.teamScore}${EN_DASH}${game.oppScore}`;
  const big = kind === "skater"
    ? t("lastNight.skaterLine", { g, a }, lang)
    : t("lastNight.goalieLine", {
        saves: saves ?? "–",
        sa:    shotsAgainst ?? "–",
        svPct: rate3(svPct, lang),       // '–' when svPct is null
      }, lang);
  return { kind, name, team, rookie, big, badge, score, suffix, oppLine };
}

function lastNightSection(data, lang) {
  const ln = data?.lastNight;
  const games = ln?.gamesCompleted ?? 0;
  const dateStr = ln?.date ? date(ln.date, lang) : "–";
  const heading = t("lastNight.title", null, lang);
  const subLine = `${dateStr} · ${tp("lastNight.games", games, lang)}`;
  const rows = [
    ...(ln?.skaters ?? []).map(r => lastNightCard(r, "skater", lang)),
    ...(ln?.goalies ?? []).map(r => lastNightCard(r, "goalie", lang)),
  ];
  if (!ln || games === 0) return { empty: true, heading, subLine, message: "noGames" };
  if (rows.length === 0)  return { empty: true, heading, subLine, message: "noFinns" };
  return { empty: false, heading, subLine, cards: rows };
}

function byTeamRows(data, lang) {
  const perTeamNames = {};
  for (const list of [data.skaters ?? [], data.goalies ?? []]) {
    for (const row of list) {
      (perTeamNames[row.team] ??= []).push(row);
    }
  }
  const rows = (data.teams ?? []).map(t2 => {
    const names = (perTeamNames[t2.abbrev] ?? [])
      // Sort on the DISPLAYED label, not fi ?? default. Today they only differ for the
      // handful of Finns whose fi key differs from default (Teräväinen, Määttä, Vasilevski)
      // — so sorting on fi ?? default would misorder them under EN once an EN-displayed
      // surname and its FI spelling start with different letters.
      .map(r => {
        const label = lang === "fi"
          ? (r.lastName?.fi ?? r.lastName?.default ?? "")
          : (r.lastName?.default ?? "");
        return { label, sortKey: label.toLocaleLowerCase(lang) };
      })
      .sort((a, b) => a.sortKey.localeCompare(b.sortKey, lang))
      .map(x => x.label)
      .join(", ");
    const total = (t2.skaters ?? 0) + (t2.goalies ?? 0);
    return {
      name: localName(t2.name, lang),
      total,
      playersLabel: tp("byTeam.players", total, lang),
      finnNames: names,
    };
  });
  rows.sort((a, b) =>
    (b.total - a.total) || a.name.localeCompare(b.name, lang)
  );
  return rows;
}

export function leijonatView(data, lang) { /* assembles everything above */ }
```

`main.js` — thin DOM glue:

```javascript
import { SKATER_COLUMNS, GOALIE_COLUMNS } from "/kiekkokeskus/columns.js";
import { t } from "/kiekkokeskus/i18n.js";
import { season } from "/kiekkokeskus/format.js";
import { mountPage } from "/kiekkokeskus/page.js";
import { leijonatView } from "./view.js";

const section = document.querySelector("main");
const slots = { … };   // same shape as /bolts, plus tiles, definition, lastNight, byTeam,
                       // skaterRookieLegend, goalieRookieLegend

mountPage({
  dataPath: "/data/kiekkokeskus/leijonat.json",
  expectedSchemaVersion: 1,
  columns: SKATER_COLUMNS,         // includes `team`
  goalieColumns: GOALIE_COLUMNS,   // includes `team`
  defaults: { pos: "all", sort: "p", dir: "desc", gsort: "gp", gdir: "desc" },
  titleKey: "page.leijonat.title",
  subtitle: (data, lang) => data
    ? t("page.leijonat.subtitle", { season: season(data.season) }, lang)
    : t("page.leijonat.subtitleNoSeason", null, lang),
  hero: { src: "/leijonat/hero.webp", width: 900, height: 604, alt: "" },
  slots,
  decorateName: (row, lang) => row?.rookie
    ? { suffix: " *", title: t("rookie.title", null, lang) }
    : null,
  renderSections: ({ data, lang, slots }) => { /* tiles, definition, lastNight cards,
                                                  byTeam rows, legend hidden/visible */ },
});
```

`index.html` — 10-slot shell (title `leijonat · kiekkokeskus`, both `kk.css` + `kk-page.css`,
Google Fonts, one module script). Mirror /bolts, add `[data-slot="tiles"]`,
`[data-slot="definition"]`, `[data-slot="lastNight"]`, `[data-slot="byTeam"]`,
`[data-slot="skaterRookieLegend"]` and `[data-slot="goalieRookieLegend"]`.

**CSS additions** in `kk-page.css`:
- `.kk-mark` — small superscript `*`, same color as text (shared across tables and cards)
- `.kk-sr-only` — standard sr-only utility (position:absolute; width:1px; height:1px;
  margin:-1px; padding:0; overflow:hidden; clip:rect(0 0 0 0); white-space:nowrap; border:0)
- `.kk-byteam` list rows (grid: name · count · names, wrap below 600 px)
- `.kk-ln-card` tweaks on top of `.kk-card` (team pill, big line, result row)
- `.kk-rookie-legend` muted single-line

**Harness** (P1.1 Code's call): **drop** the `/leijonat` preview section from
`site/kiekkokeskus/_dev/harness.html`. The real `/leijonat` is served by
`scripts/preview.py` and visually inspectable there; keeping a placeholder section was
duplication. The `/bolts` section stays as the "shared controller demo" entry point.

**Git-add existing hero assets**:
```bash
git add site/leijonat/hero.webp art/leijonat-hero-source.jpg
```

**Validation**:
- [ ] `node --test "site/leijonat/*.test.js"` green:
  - **count tiles**: `view.tiles.{skaters,goalies,teams,rookies}.value === '30','5','19','4'`
  - **lastNight heading EN** = `Last night` + sub-line `Oct 9, 2026 · 4 games`
  - **lastNight heading FI** = `Viime yönä` + sub-line `9.10.2026 · 4 ottelua`
  - **Granlund EN card**: `Mikael Granlund`, `ANA`, big `1 G · 1 A`, badge `W`, score
    `5–1` (U+2013), `opp.home: false → oppLine 'at WPG'`, `decidedIn 'REG' → suffix ''`
  - **Granlund FI card**: big `1 M · 1 S`, badge `V`, score `5–1`, oppLine `WPG (vieras)`
  - **Kakko EN/FI**: big `0 G · 1 A` / `0 M · 1 S`, badge `W` / `V`, score `6–3`, oppLine
    `at DET` / `DET (vieras)`
  - **Byteam EN first 4 rows**: DAL (6, "Heiskanen, Hintz, Hyry, Kiviranta, Lindell, Rantanen"),
    FLA (4, "Barkov, Luostarinen, Lundell, Mikkola"), LAK (3), VAN (3,
    "Lankinen, Meriläinen, Räty")
  - **Byteam FI**: team names from `localName` (today same as `default` — no FI key on team
    objects); `players` plural renders `pelaajaa`
  - **Byteam LAK before VAN**: both have total 3 → name asc tiebreaker
  - **Rookie counting**: `countRookies` = 4; `hasRookie(data.skaters) === true`;
    `hasRookie(data.goalies) === false`
  - **Gotcha — no games**: synthetic `{ gamesCompleted: 0, skaters: [], goalies: [] }` →
    `view.lastNight.empty === true` and `message === 'noGames'`
  - **Gotcha — games, no Finns**: synthetic `{ gamesCompleted: 5, skaters: [], goalies: [] }`
    → `message === 'noFinns'`
  - **Gotcha — goalie no shots**: synthetic goalie card with `saves/shotsAgainst/svPct = null`
    → `big` contains `'–/– saves · –'` (EN) / `'–/– torjuntaa · –'` (FI); no throw
  - **Gotcha — goalie badge from `game.result`, not `decision`**: `decision: 'W'`,
    `game.result: 'L'` → `badge === 'L'` (EN) / `'H'` (FI). (We never read `decision`.)
  - **Gotcha — OT loss card**: `game.result: 'OTL'`, `decidedIn: 'OT'` → badge `OTL`/`JH`,
    suffix `OT`/`JA`
  - **Gotcha — FI vs EN name source**: Määttä row renders `Olli Maatta` in EN, `Olli
    Määttä` in FI
  - **Gotcha — missing `lastNight` object**: `data: { ...golden, lastNight: undefined }` →
    treated as `gamesCompleted: 0`, `message: 'noGames'`
  - **No `{` placeholder leaks** (same backstop as /bolts): flatten every string in the
    view, assert none contains `{` or `}`
- [ ] `view.js` under 300 lines; `main.js` under 200; `index.html` under 100
- [ ] `kk-page.css` under 500 (currently 183; expect ~230)
- [ ] `site/leijonat/hero.webp` and `art/leijonat-hero-source.jpg` tracked by git

**Commit**: `feat(08): leijonat view, shell, hero, CSS`

### Step 4: Deploy — chain the `leijonat/` sync after `bolts/`
**Files**: `scripts/deploy.py`, `tests/test_deploy_leijonat.py`

```python
LEIJONAT_SYNC_DEST = "s3://jurigregg-static-site/leijonat/"
LEIJONAT_SYNC_SOURCE = "site/leijonat/"

def _leijonat_sync_cmd() -> list[str]:
    # --exclude "*.test.js" mandatory for the same reason bolts has it: site/leijonat/view.test.js
    # lives next to the real page modules and must not deploy.
    return [
        "aws", "s3", "sync", LEIJONAT_SYNC_SOURCE, LEIJONAT_SYNC_DEST,
        "--delete",
        "--exclude", "*.test.js",
        "--cache-control", "public, max-age=300",
        "--profile", "default",
    ]

def page_sync() -> None:
    """Shared → bolts → leijonat. Order matters: pages must never reference modules the
    shared prefix doesn't carry yet (PRP-07 rationale), and leijonat follows bolts for the
    same reason it was placed after shared."""
    _check_allowed(SHARED_SYNC_DEST)
    subprocess.run(_shared_sync_cmd(), cwd=REPO_ROOT, env=_subprocess_env(), check=True)
    _check_allowed(BOLTS_SYNC_DEST)
    subprocess.run(_bolts_sync_cmd(), cwd=REPO_ROOT, env=_subprocess_env(), check=True)
    _check_allowed(LEIJONAT_SYNC_DEST)
    subprocess.run(_leijonat_sync_cmd(), cwd=REPO_ROOT, env=_subprocess_env(), check=True)
```

Update docstring to document the three-step order and the leijonat pre-deploy inspection
(same shape as the bolts one that landed in PRP-07).

`tests/test_deploy_leijonat.py`:
- `_leijonat_sync_cmd()` has `--delete`, `--exclude "*.test.js"`, `--cache-control`,
  `--profile default`, nothing else (no `_dev/*` exclude — leijonat has no dev dir)
- `page_sync()` with `subprocess.run` monkeypatched fires **three** calls in order:
  `_shared_sync_cmd()` → `_bolts_sync_cmd()` → `_leijonat_sync_cmd()`. Assert `len(captured) == 3`
  and each `cmd` in order
- `env` on every call is `_subprocess_env()` (same monkeypatch pattern)
- `_check_allowed` monkeypatched to reject the leijonat dest aborts before firing the third
  subprocess (ran twice: shared + bolts)
- Also extend existing `test_deploy_bolts.py::test_page_sync_runs_shared_first_then_bolts`
  to use `len(captured) == 3` (or at least `>= 2` for bolts assertion) — safer: add
  `len(captured) >= 2` and keep the bolts-specific test tight

**Validation**:
- [ ] `.venv/bin/pytest tests/test_deploy_leijonat.py tests/test_deploy_bolts.py tests/test_deploy_shared.py -q`
      green
- [ ] `scripts/deploy.py` without `--approved` still prints `cdk diff` and exits 0
- [ ] File still under 250 lines

**Commit**: `feat(08): deploy syncs leijonat/`

### Step 5: Smoke — `/leijonat`, `/leijonat/`, `/leijonat/hero.webp`
**Files**: `scripts/smoke.py`, `tests/test_smoke_leijonat.py`

Mirror the `/bolts` block exactly. New constants `LEIJONAT_PAGE = '/leijonat'`,
`LEIJONAT_PAGE_SLASH = '/leijonat/'`, `LEIJONAT_HERO = '/leijonat/hero.webp'`. Same
assertions: both page paths return 200 text/html with the body referencing
`/kiekkokeskus/kk.css`; hero returns 200 image/webp with `max-age=300`.

`tests/test_smoke_leijonat.py` is thin — pure helpers are shared with `test_smoke_bolts.py`
(the matchers aren't duplicated), so this file just imports `smoke` and asserts the four
new path constants exist and that the body matcher works against a minimal fake leijonat HTML
body. No network.

**Validation**:
- [ ] `.venv/bin/pytest tests/test_smoke_leijonat.py tests/test_smoke_bolts.py tests/test_smoke_assets.py -q`
      green
- [ ] `smoke.py` under 350 lines (currently 266; +~45)

**Commit**: `feat(08): smoke checks /leijonat and hero`

### Step 6: CI — run the pages tests across all three globs
**Files**: `.github/workflows/ci.yml`

```yaml
  pages:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version-file: .nvmrc
      - run: node --test "site/kiekkokeskus/*.test.js" "site/bolts/*.test.js" "site/leijonat/*.test.js"
```

Also backfills a PRP-07 CI gap: `site/bolts/*.test.js` was passing locally but **not** in
CI (ci.yml only ran the kiekkokeskus glob). PRP-07's completion report said CI ran both
globs — that was wrong. The commit body **must** call this out so git history is accurate.

**Validation**:
- [ ] `gh run watch` on the push shows the `pages` job running all three globs
- [ ] Combined test count on CI matches local: `kiekkokeskus (116) + bolts (10) + leijonat (~15)`

**Commit**: `ci(08): run leijonat tests (and backfill bolts tests) in CI`
**Commit body must include**: "PRP-07's completion report claimed CI ran the bolts glob;
it didn't. ci.yml only ran site/kiekkokeskus/*.test.js. This commit adds both
site/bolts/*.test.js and site/leijonat/*.test.js — correcting PRP-07's report in the same
breath as closing the gap for init-08."

### Step 7: Deploy and verify
```bash
# 1. CI must be green on the branch before deploy
gh run watch

# 2. cdk diff — expect no differences
cd infra && PATH="/opt/homebrew/opt/node@22/bin:$PATH" AWS_PROFILE=default npx cdk diff

# 3. Pre-deploy inspections
aws s3 ls s3://jurigregg-static-site/leijonat/ --recursive --profile default
aws s3 sync site/leijonat/ s3://jurigregg-static-site/leijonat/ --delete \
  --exclude "*.test.js" --dryrun --profile default
# expect: 0 delete: lines, exactly 4 (dryrun) upload: lines
#         (index.html, main.js, view.js, hero.webp). NO view.test.js.
aws s3 sync site/bolts/ s3://jurigregg-static-site/bolts/ --delete \
  --exclude "*.test.js" --dryrun --profile default
# expect: 0 or at most a kk-page.css-side-effect-free upload (there are no bolts source
# changes this PRP; if 0, this is a true no-op)
aws s3 sync site/kiekkokeskus/ s3://jurigregg-static-site/kiekkokeskus/ --delete \
  --exclude "*.test.js" --exclude "_dev/*" --exclude "package.json" --dryrun --profile default
# expect: table.js, strings.js, kk-page.css updates; 0 delete: lines; no _dev/* or test files

# 4. Deploy
.venv/bin/python scripts/deploy.py                 # cdk diff + exit
.venv/bin/python scripts/deploy.py --approved      # cdk no-op + shared + bolts + leijonat

# 5. Smoke + live checks
.venv/bin/python scripts/smoke.py
curl -sI https://jurigregg.com/leijonat | grep -iE 'HTTP|content-type|cache-control|x-cache'
curl -sI https://jurigregg.com/leijonat/ | grep -iE 'HTTP|content-type'
curl -sI https://jurigregg.com/leijonat/hero.webp | grep -iE 'HTTP|content-type|cache-control'

# 6. Post-deploy guard — no test file leaked
aws s3 ls s3://jurigregg-static-site/leijonat/ --recursive --profile default | grep -F '.test.js' \
  && { echo "FAIL: test file in leijonat/ — delete immediately"; exit 1; } || echo "OK: no test files"
```

**Live Layer 7 manual (Chrome only; PRP-07 dropped Safari parity)**:
- [ ] Open `https://jurigregg.com/leijonat` in Chrome desktop
- [ ] Hero visible on the right at 358 × 240 (ADR-040 lion in SUOMI ring)
- [ ] Title "leijonat" (lowercase); subtitle "Finnish players in the NHL · 2026–27 season"
**Compare the live page against the LIVE JSON, not the golden.** The golden was captured
2026-10-10; by execution time Finns have played more games and the lastNight list has
rotated. Fetch `https://jurigregg.com/data/kiekkokeskus/leijonat.json` in the Chrome console
once and reuse it for every live assertion below. The golden values belong in `view.test.js`
only (locked by Step 3). (Same slip PRP-07's live checklist made — this time we don't
repeat it.)

Fetch once:
```javascript
const LIVE = await fetch('/data/kiekkokeskus/leijonat.json').then(r => r.json());
```

Then verify against `LIVE`:
- [ ] Count tiles equal the array lengths: `tiles.skaters == LIVE.skaters.length`,
      `tiles.goalies == LIVE.goalies.length`, `tiles.teams == LIVE.teams.length`,
      `tiles.rookies == (LIVE.skaters.filter(r=>r.rookie).length + LIVE.goalies.filter(r=>r.rookie).length)`
- [ ] Definition paragraph visible under tiles
- [ ] Last night heading: EN `Last night · {date(LIVE.lastNight.date)} · {games} games/game`,
      FI mirror. Date formatter output must match the page
- [ ] For **every** `LIVE.lastNight.skaters[]` row there is a card whose rendered line matches
      `{g} G · {a} A` (EN) / `{g} M · {a} S` (FI) with the game badge from `game.result`
      (never `decision`), score `{teamScore}–{oppScore}`, OT/SO suffix from `decidedIn`, and
      `opp.home`/`opp.away` text with `game.opponent` as a string. Same for `lastNight.goalies`
- [ ] If `LIVE.lastNight.gamesCompleted == 0`, no cards and `lastNight.noGames` message
- [ ] For every rookie row in `LIVE.skaters.filter(r => r.rookie)`, the skaters table shows
      the `*` marker in that player's name cell; legend line present under the skaters
      table. Same for goalies — legend hidden iff no goalie rookies in LIVE
- [ ] Skaters table has the `Team` column (header visible, cells populated with abbrevs
      matching the JSON); goalies table too
- [ ] By-team list: for each `LIVE.teams[]` entry, the row shows the team name
      (`localName(team.name, lang)`), the count (`tp('byTeam.players', team.skaters +
      team.goalies, lang)`), and the sorted Finn surnames from
      `LIVE.skaters.filter(s => s.team === team.abbrev)` + `goalies.filter(…)`. Order: total
      desc, then name asc
- [ ] Click `g` three times → desc → asc → desc (skater and goalie numeric columns)
- [ ] Click `team` column → text sort, asc first; click again → desc
- [ ] Toggle FI: every string flips (Kenttäpelaajat `{n}`, Maalivahdit `{n}`, …);
      fetch-once contract holds — `performance.getEntriesByType('resource').filter(e =>
      e.name.includes('leijonat.json')).length === 1` before and after the toggle
- [ ] DevTools device emulation at **375 px** (not just resize): no page-level horizontal
      scroll; hero sits behind title at 25% opacity; tiles stack 1-up; last-night cards
      stack 1-up; tables scroll with the name column pinned; by-team rows wrap name lists
- [ ] `/bolts` regression pass: toggle (FI label now reads `Tilanne`, not `Saldo`), sort
      ×3 on G, pill filter — otherwise still correct (no behavior change expected)

**Validation**:
- [ ] `cdk diff` → no differences
- [ ] Leijonat dry-run: 0 delete lines, exactly 4 uploads
- [ ] Post-deploy guard: no `.test.js` on either prefix
- [ ] Smoke: all checks pass (expect roughly 44/44: 35 existing + 9 new for leijonat page +
      leijonat/ + hero + optional)
- [ ] Every Layer 7 item above verified

**Commit**: no new commit unless a content-type fix is needed (reserve `fix(08): per-ext
content-type on leijonat sync` for the same pattern PRP-07 kept warm).

### Step 8: Documentation and close-out
**Files**: `docs/TESTING.md`, `docs/TASK.md`, `prps/prp-08-leijonat-page.md` (status flip)

- Add the Page-logic gotcha rows below to `docs/TESTING.md`'s matrix.
- `docs/TASK.md`: move init-08 to Recently Completed with a one-line outcome; set
  `init-09-history` as the next Up Next item; update Last-updated date.
- Flip PRP status Ready → Complete.

**Validation**:
- [ ] `grep -c "init-08" docs/TASK.md` ≥ 1 under Recently Completed
- [ ] All layered checks green locally and in CI

**Commit**: `docs(08): TESTING, TASK, complete`

---

## Testing Requirements

| Layer (TESTING.md) | Tests | Fixture / Gotcha row |
|---|---|---|
| 1 Parse contract | n/a — no parser touched | — |
| 2 Builder golden | n/a — `tests/golden/leijonat.json` used as Layer 5 input only | — |
| 3 Orchestration | n/a — no handler change | — |
| 4 Infra | `cdk diff` prints `no differences`; `infra/test/` assertions remain green | — |
| 5 Page logic | `strings.test.js` (parity + FI pins), `table.test.js` (decorateName), `site/leijonat/view.test.js` (golden table + 10 gotcha rows) | every row below |
| 6 Smoke | `scripts/smoke.py` extends to `/leijonat`, `/leijonat/`, `/leijonat/hero.webp` | — |
| 7 Manual | Step 7 live checklist (Chrome only, desktop + 375 px via device emulation) | — |

### Page-logic gotcha rows (new in `docs/TESTING.md`)

| ADR | Gotcha | Fixture / input | Assert |
|---|---|---|---|
| 015 | lastNight: no games | synthetic `{ gamesCompleted: 0, skaters: [], goalies: [] }` | `view.lastNight.empty === true`; `message === 'noGames'`; no cards |
| 012 | lastNight: games, no Finns | synthetic `{ gamesCompleted: 5, skaters: [], goalies: [] }` | `view.lastNight.empty === true`; `message === 'noFinns'` |
| 015 | lastNight: goalie with no shots | synthetic card, `saves`/`shotsAgainst`/`svPct` null | big line reads `'–/– saves · –'` (EN) / `'–/– torjuntaa · –'` (FI); no throw |
| 037 | goalie badge from `game.result`, not `decision` | `decision: 'W'`, `game.result: 'L'` | badge `L` (EN) / `H` (FI). The view never reads `decision` |
| 037 | OT loss card | `game.result: 'OTL'`, `decidedIn: 'OT'` | badge `OTL`/`JH` + suffix `OT`/`JA` |
| 040 | rookie marker (nameCellParts) | `rookie: true` row with `decorateName` → `{suffix:' *', title}` | pure `nameCellParts` returns `{ name, suffix:' *', title }` (EN: `'Rookie'`, FI: `'Tulokas'`); non-rookie row returns `{ name, suffix:null, title:null }` |
| 040 | /bolts unchanged | `nameCellParts(row, lang, null)` and `nameCellParts(row, lang, () => null)` | both return `{ name, suffix:null, title:null }`. DOM renderer leaves the name cell as a bare text node when suffix is null — /bolts markup is byte-identical (verified in the Chrome regression pass, Step 7) |
| 040 | name sort ignores marker | rookie Helenius vs. non-rookie Heiskanen | asc sort → Heiskanen first; the `*` doesn't affect comparison |
| 040 | by-team order ties | two teams at the same total | team name asc tiebreaker (LAK before VAN today) |
| 018 | FI vs EN name source | Määttä row | EN cell renders `Olli Maatta`; FI cell renders `Olli Määttä` |
| 040 | missing `lastNight` object | `data: { …golden, lastNight: undefined }` | treated as `gamesCompleted: 0`; `message: 'noGames'` |
| 040 | no `{` placeholder leaks | flatten every string from `leijonatView(golden, lang)` | none contains `{` or `}` — backstop for subtitle/plural regressions |

The existing TESTING.md row **038 — missing i18n key** continues to apply through the parity
test; the 15 new keys are covered.

---

## Error Handling and Edge Cases

| Case | Source | Handling | Test |
|---|---|---|---|
| Fetch throws / 404 / invalid JSON / schema mismatch | `data.loadData` → `createController` | `render(state, null, { error })` → error banner; tiles show `–`, lastNight shows empty state, byTeam shows nothing | existing `controller.test.js` cases + manual |
| `lastNight` object missing | spec P0.4 | `lastNightSection` returns `{ empty: true, message: 'noGames' }` | view.test.js |
| `lastNight.gamesCompleted = 0` with populated lists (impossible?) | spec P0.4 | empty branch wins — `noGames` message, no cards | view.test.js (synthetic) |
| `lastNight` games but 0 Finnish rows | spec P0.4 | `noFinns` message | view.test.js (synthetic) |
| Goalie row with `saves/shotsAgainst/svPct` all null (no shots faced) | ADR-015 | big line reads `'–/– saves · –'` (EN) / `'–/– torjuntaa · –'` (FI) | view.test.js |
| `rookie` missing on a row | ADR-037 (shouldn't happen; non-null bool) | `decorateName` returns null; no `*` | table.test.js |
| `team` null on a row (verify item 2 failed) | spec P0.5 fallback | by-team groups under `–`; team cell shows `–` | not tested (confirmed clean in golden); add if ever observed |
| `teams[]` totals disagree with per-team row counts | spec Verify item 4 | render using `t.skaters + t.goalies` (today agrees); `console.warn` on parity break | not tested (confirmed clean) |
| Two teams tie in total | by-team sort | team-name asc (`localeCompare(…, lang)`) | gotcha row |
| CloudFront serves wrong MIME on new assets | ADR-039 fallback | second-pass sync with `--content-type` per ext + `fix(08): per-ext content-type` | reserved; not expected |

---

## Cost Impact

**None.** No Lambda change, no new storage class, no new request pattern. First-time
`/leijonat` load: `index.html` + `main.js` + `view.js` + `hero.webp` + already-cached
shared modules + `leijonat.json`. The hero at 40 KB plus the shell < 90 KB total — well
inside PLANNING.md's 150 KB-per-page target.

---

## Rollback Plan

1. **Code**: `git revert` the PRP's commits, then `.venv/bin/python scripts/deploy.py
   --approved`. The reverted `page_sync` drops the leijonat sync; `kiekkokeskus/*` objects
   revert to their PRP-07 versions.
2. **Data**: no `data/` paths written in this PRP. `bolts.json`/`leijonat.json` untouched.
   S3 noncurrent versions kept 7 days (ADR-023) if needed.
3. **Visible rollback**: with `index.html` deleted, `/leijonat` 404s cleanly through
   `add-index-html`. To force-remove without waiting for a reverted deploy:
   `aws s3 rm s3://jurigregg-static-site/leijonat/ --recursive --profile default`
   (prefix-scoped, allowed by ADR-024).
4. **Verify**: `.venv/bin/python scripts/smoke.py`; `/`, `/sports`, `/bolts`, `/data/*`
   remain 200. If `/leijonat` was rolled back fully, its smoke checks will fail — remove
   those too in the same revert.

---

## Open Questions

(none)

---

## Confidence Scores

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 9 | Spec enumerates every string, every tile, every card line, every by-team row with FI/EN expected values. The only wiggle room is the exact DOM structure inside each last-night card — a style call this PRP freezes |
| Feasibility | 9 | Vanilla HTML/CSS/JS; no new runtime deps. Every shared piece exists from PRP-07 (`page.js`/`controller.js`, `renderHeader(hero)`, `localName`, `tp`, `kk-page.css`). Only new shared code is `decorateName` in `renderTable` — one optional param + two new element types |
| Completeness | 9 | Every output field has a source, nullability, and renderer. 12 gotcha rows with named tests. Hero asset ready. 4/4 Verify items probed and confirmed |
| Payload certainty | 10 | No NHL endpoint called. All tests read `tests/golden/leijonat.json` or synthetic inputs. The golden was captured 2026-10-10 and is static |
| **Average** | **9.25** | **Ready to execute** |

### Verification results (no surprises)
- **No surprises.** All four Verify-in-PRP items resolved cleanly against the golden:
  every row has `gp ≥ 1`, no null `team` fields, `lastNight` present on golden with
  `gamesCompleted: 4`, and `teams[]` totals equal per-team row counts.
- Hero assets already in place (`site/leijonat/hero.webp` 900×604 40 KB; source JPG 430 KB).
  Step 3 git-adds both; `art/` sits outside `site/` and is never deployed.
- `s3://jurigregg-static-site/leijonat/` is confirmed empty (`list-objects-v2` no `Contents`).
- CI gap confirmed via `grep`: `ci.yml` only runs `site/kiekkokeskus/*.test.js`. PRP-07's
  completion report incorrectly claimed CI covered both the kiekkokeskus and bolts globs —
  it didn't. Step 6 adds both the bolts and leijonat globs and the commit body states the
  correction so git history is accurate.

### Suggested new ADRs
**None.** Spec Notes explicitly say no new ADR is needed: ADR-040 already covers the lion
hero and ADR-037 already says the badge comes from `game.result`, never `decision`.
