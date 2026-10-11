# init-07: /bolts Page

**Created**: 2026-10-11
**Phase**: 3 Pages
**Depends On**: init-04 (`bolts.json`), init-06 (shared UI, deployed)
**ADRs**: ADR-002, 003, 015–018, 020–022, 024, 028, 030, 034–036, 038, 039; adds ADR-040 (page
hero art) in DECISIONS.md

---

## Problem Statement

`bolts.json` is published daily and the shared UI layer is live, but there's no page. The init-06
harness also exposed a design gap. Each page owned its own state glue (toggle, pills, sort, URL),
and that glue produced the `langExplicit` bug. Worse, the harness re-fetched the JSON on every
re-render. Copying that pattern into two pages would mean two copies of both bugs.

## Goal

`jurigregg.com/bolts` is live. It has the all-blue hero, the four standings tiles, last game,
next games, special teams, the skater and goalie tables, and the footer, in EN and FI. State and
data loading live in one shared controller (`page.js`) that `/leijonat` reuses in init-08. The JSON
is fetched once per page load.

## Requirements

### Must Have (P0)

0. **Housekeeping (first commit).** In CLAUDE.md and TESTING.md, change
   `node --test site/kiekkokeskus/` to `node --test "site/kiekkokeskus/*.test.js"`. The directory
   form fails on Node 22 (PRP-06 finding). This matches what CI already runs.

1. **Shared page controller** (`site/kiekkokeskus/page.js`, new). It owns everything that isn't
   page-specific:
   - Language via `resolveLang`, state via `readState`, with `langExplicit` stored **in state**.
   - A pure reducer `pageReducer(state, action)` with actions `setLang`, `setPos`, `setSort`,
     `setGsort`. `setLang` sets `langExplicit: true`. The others leave it unchanged.
   - After every action: `writeState` (with `state.langExplicit`), `<html lang>`, and re-render
     **from the cached data**. `setLang` also writes `localStorage` `kk.lang`, wrapped in
     try/catch.
   - `loadData` is called **exactly once** per page load. Banners (stale, error), header, pills,
     both tables and the footer are rendered by the controller.
   - The page supplies its config (data path, schema version, column sets, hero) and one callback,
     `renderSections({ data, lang, slots })`, for its own sections.
   - Exact API is the PRP's call. The behavior above is the contract.
   - The dev harness is rewritten to use `page.js` for both sections, so it stops carrying its own
     glue.

2. **Bolts view model** (`site/bolts/view.js`, new, pure). `boltsView(data, lang)` returns every
   display string for the page-specific sections, so they're testable in Node against
   `tests/golden/bolts.json` (P0.8). The DOM code in `site/bolts/main.js` only places those strings.

3. **Page shell** (`site/bolts/index.html`). Served at `/bolts` and `/bolts/` through the existing
   `add-index-html` function (ADR-021, untouched).
   - `<title>bolts · kiekkokeskus</title>` in both languages, `<html lang>` updated by the
     controller, viewport meta, `kk.css` and the Google Fonts link, and one module script.
   - Section order follows the design canvas: header with hero → standings tiles → last game, next
     games, special teams (one row, wrapping) → skaters (with pills) → goalies → footer.
   - No points-pace chart. That's init-09, and nothing is reserved for it on the page.
   - The skater and goalie tables use the init-06 column sets without the `team` column.

4. **Hero** (ADR-040). `site/bolts/hero.webp` is the all-blue skyline-and-monogram sketch (900×604,
   52 KB, attached to this spec). The original photo is committed as `art/bolts-hero-source.jpg`,
   which is never deployed.
   - Rendered through `renderHeader` with a new optional `hero: { src, width, height }` param, so
     `/leijonat` reuses it in init-08.
   - Decorative, so `alt=""`. `width`/`height` attributes are set to avoid layout shift.
     `decoding="async"`. **Not** lazy-loaded, because it's above the fold.
   - Desktop: right side of the header, the title block on the left, image height about the header
     height.
   - Below 600 px: the image sits behind the title block at about 25% opacity and centered. The
     title stays fully legible.
   - The image is pre-flattened onto `--kk-bg`, so it must sit on the page background, never on a
     `.kk-card` surface.

5. **Standings tiles** (from `standing`, ADR-036). Every value is shown from Tampa's point of view:
   positive means ahead, negative means behind.

   | Tile | Label | Value | Sub-line |
   |---|---|---|---|
   | Record | `tile.record` | `w–l–otl` (U+2013) | `{pts} · {streakLabel} {streak}`, streak part omitted when `streak` is null |
   | Division | division name from `division.abbrev` | `ordinal(division.rank)` | `tile.divisionSub` with conference ordinal and league ordinal |
   | Division lead | `tile.divLead` | `signed(−divisionLead.gap)`, or `0` when `leader == "TBL"` | `{leader} · {leaderPts}` + games-in-hand clause; `tile.divLeader` when TBL leads |
   | Playoff line | `tile.playoffIn` or `tile.playoffOut` by `inPosition` | `inPosition ? signed(+gap) : signed(−gap)` | `{team} · {teamPts}` + games-in-hand clause |

   - **Games-in-hand clause**: `gamesInHand` (reference GP − TBL GP) > 0 means Tampa has games in
     hand, < 0 means Tampa has played more, and 0 omits the clause. Plural forms per P0.9.
   - `pts` uses plural forms (EN `1 pt` / `6 pts`, FI `6 p` always).
   - Streak code `W` / `L` / `OT` → EN `W3` / `L3` / `OT3`, FI `V3` / `H3` / `JH3`.

6. **Game cards**:
   - **Last game**: result badge (`W`/`L`/`OTL` → FI `V`/`H`/`JH`), score `tblScore–oppScore`
     (Tampa first, U+2013), a suffix when `decidedIn` is `OT`/`SO` (FI `JA`/`VL`), nothing for
     `REG`. Then the opponent line (`vs`/`at` + opponent name, FI `(koti)`/`(vieras)`), then
     `date(lastGame.date)`. If `lastGame` is null, show `table.empty`.
   - **Next games**: up to 3 rows of `gameTime(startTimeUTC)` + opponent line, in the viewer's time
     zone (ADR-038). If the list is empty, show `nextGames.none`.
   - Opponent name comes from `opponent.name` through the name rule (`fi ?? default`). Today that's
     the team's common name ("Wild"), which is what we show.

7. **Special teams**: PP and PK as `pct1Sign` (EN `6.3%`, FI `6,3 %`) with
   `special.rank` + `ordinal(rank)`. Both values are nullable: show `–` and drop the rank line.

8. **Shared additions** to `format.js` / `i18n.js`, each with Layer 5 tests:
   - `ordinal(n, lang)`: EN `1st 2nd 3rd 4th 11th 12th 13th 21st 22nd 101st 111th` via
     `Intl.PluralRules({type: 'ordinal'})`; FI `n.`
   - `season("20262027")` → `2026–27`
   - `tp(key, n, lang, vars)`: plural lookup (`key.one` / `key.other`) via `Intl.PluralRules`,
     with `{n}` filled in

9. **Strings** added to `strings.js` (parity test still applies):

   | Key | EN | FI |
   |---|---|---|
   | `page.bolts.title` | bolts | bolts |
   | `page.bolts.subtitle` | Tampa Bay Lightning · {season} season | Tampa Bay Lightning · kausi {season} |
   | `bolts.standings` | Standings | Sarjatilanne |
   | `tile.record` | Record | Saldo |
   | `tile.streak` | streak | putki |
   | `unit.pts.one` / `.other` | {n} pt / {n} pts | {n} p / {n} p |
   | `streak.W` / `.L` / `.OT` | W{n} / L{n} / OT{n} | V{n} / H{n} / JH{n} |
   | `div.A` | Atlantic Division | Atlantin divisioona |
   | `div.M` | Metropolitan Division | Metropolitanin divisioona |
   | `div.C` | Central Division | Keskinen divisioona |
   | `div.P` | Pacific Division | Tyynenmeren divisioona |
   | `conf.E` / `conf.W` | East / West | Itä / Länsi |
   | `tile.divisionSub` | {confRank} {conf} · {leagueRank} NHL | {conf} {confRank} · NHL {leagueRank} |
   | `tile.divLead` | To division lead | Ero divisioonan kärkeen |
   | `tile.divLeader` | Division leader | Divisioonan kärjessä |
   | `tile.playoffIn` | Above the playoff line | Pudotuspeliviivan yläpuolella |
   | `tile.playoffOut` | Below the playoff line | Pudotuspeliviivan alapuolella |
   | `gih.ahead.one` / `.other` | {n} game in hand / {n} games in hand | {n} ottelu vähemmän pelattuna / {n} ottelua vähemmän pelattuna |
   | `gih.behind.one` / `.other` | {n} more game played / {n} more games played | {n} ottelu enemmän pelattuna / {n} ottelua enemmän pelattuna |
   | `lastGame.title` | Last game | Edellinen ottelu |
   | `result.W` / `.L` / `.OTL` | W / L / OTL | V / H / JH |
   | `decided.OT` / `.SO` | OT / SO | JA / VL |
   | `opp.home` | vs {opp} | {opp} (koti) |
   | `opp.away` | at {opp} | {opp} (vieras) |
   | `nextGames.title` | Next games | Seuraavat ottelut |
   | `nextGames.none` | No upcoming games scheduled. | Ei tulevia otteluita. |
   | `special.title` | Special teams | Erikoistilanteet |
   | `special.pp` | Power play | Ylivoima |
   | `special.pk` | Penalty kill | Alivoima |
   | `special.rank` | {rank} in NHL | NHL:n {rank} |

   FI division names follow Finnish NHL coverage; `JA` and `VL` follow Liiga (ADR-038).

10. **Deploy** (`scripts/deploy.py`, ADR-024, 039). Enable the `bolts/` sync:
    `site/bolts/ → s3://jurigregg-static-site/bolts/ --delete --cache-control "public,
    max-age=300"`, running **after** the `kiekkokeskus/` sync. That way a new page never points at
    shared modules that haven't arrived yet. `art/` is outside `site/`, so it never deploys. Test
    the order and arguments the same way PRP-06 tested the shared sync.
    - Before the first real run: an `aws s3 ls …/bolts/ --recursive` and a `--dryrun`. Any
      `delete:` line stops the deploy.

11. **Smoke** (`scripts/smoke.py`):
    - `/bolts` and `/bolts/` return 200 with `text/html` and the body references
      `/kiekkokeskus/kk.css`
    - `/bolts/hero.webp` returns 200 `image/webp` with `max-age=300`
    - Existing checks stay. **No `/leijonat` page check yet** (init-08 adds it).

### Should Have (P1)

1. The `jurigregg.com` part of the breadcrumb links to `https://jurigregg.com/`.
2. Lighthouse (Chrome DevTools, mobile) on the live page: no layout shift from the hero (CLS
   < 0.1) and no console errors. Record the scores in the PRP report. They aren't a gate.

### Nice to Have (P2)

1. A `<link rel="preload">` for `hero.webp`, if Lighthouse flags it as the late LCP element.

## Output / Data Contract

Read-only. **schemaVersion change: no** (expects `1`). Fields consumed beyond init-06's table
fields:

| Field | Units / type | Nullable | Used by |
|---|---|---|---|
| `season` | `YYYYYYYY` string | no | subtitle via `season()` |
| `standing.{gp,w,l,otl,pts}` | int | no | record tile |
| `standing.streak.{code,count}` | `W`/`L`/`OT`, int | yes (0 GP) | record sub-line |
| `standing.division.{abbrev,rank}`, `conference.{abbrev,rank}`, `leagueRank` | string, int | no | division tile |
| `standing.divisionLead.{leader,leaderPts,gap,gamesInHand}` | string, ints (signed, ADR-036) | no | division lead tile |
| `standing.playoffLine.{inPosition,team,teamPts,gap,gamesInHand}` | bool, string, ints (signed) | no | playoff tile |
| `lastGame.{date,home,opponent,tblScore,oppScore,result,decidedIn}` | ET date, bool, object, ints, enum, enum | object nullable; `decidedIn` nullable | last game card |
| `nextGames[].{startTimeUTC,home,opponent}` | ISO UTC, bool, object | list may be empty | next games card |
| `specialTeams.{ppPct,pkPct}` | fraction 0–1 | yes | special teams |
| `specialTeams.{ppRank,pkRank}` | int | yes | special teams |

`standing.pointPct`, `gf`, `ga` and `team.name` aren't shown on this page.

- **S3 keys written**: `bolts/index.html`, `bolts/main.js`, `bolts/view.js`, `bolts/hero.webp`,
  plus updated `kiekkokeskus/*` (new `page.js`, changed `chrome.js`, `format.js`, `i18n.js`,
  `strings.js`, `kk.css`).

## Fixtures and Gotchas

No new NHL fixtures. Layer 5 reads `tests/golden/bolts.json`. Expected strings for the golden
(2026-10-08 data):

| View field | EN | FI |
|---|---|---|
| record | `3–1–0`, `6 pts · streak W3` | `3–1–0`, `6 p · putki V3` |
| division | `Atlantic Division`, `2nd`, `4th East · 8th NHL` | `Atlantin divisioona`, `2.`, `Itä 4. · NHL 8.` |
| division lead | `0`, `OTT · 6 pts` | `0`, `OTT · 6 p` |
| playoff line | `Above the playoff line`, `+2`, `NYI · 4 pts` | `Pudotuspeliviivan yläpuolella`, `+2`, `NYI · 4 p` |
| last game | `W`, `3–2`, `vs Wild`, `Oct 8, 2026` | `V`, `3–2`, `Wild (koti)`, `8.10.2026` |
| power play | `6.3%`, `30th in NHL` | `6,3 %`, `NHL:n 30.` |
| penalty kill | `77.8%`, `19th in NHL` | `77,8 %`, `NHL:n 19.` |

Add these to the TESTING.md gotcha matrix (Page logic):

| Gotcha | Input | Assert |
|---|---|---|
| signed gaps from Tampa's view (ADR-036) | synthetic: `divisionLead.gap: 4`; `playoffLine` out of position, `gap: 2` | `−4`; `Below the playoff line`, `−2` |
| TBL leads division | `leader: "TBL"`, `gap: 0` | `0`, `Division leader` |
| negative zero | `signed(-0)` (what `−gap` gives when `gap` is 0, as in the golden) | `0`, never `−0` or `+0` |
| games in hand both signs + zero | `gamesInHand` `1`, `-2`, `0` | `1 game in hand`; `2 more games played`; clause omitted |
| 0 GP state | `streak: null`, `lastGame: null`, `nextGames: []`, PP/PK `null` | no `streak` text, `table.empty`, `nextGames.none`, `–` with no rank |
| OT / SO suffix | `decidedIn` `OT`, `SO`, `REG` | `OT`/`SO` (FI `JA`/`VL`); nothing |
| ordinals | 1, 2, 3, 4, 11, 12, 13, 21, 22, 101, 111 | EN `1st…111th`; FI `n.` |
| plural units | `pts` 1 and 6 | `1 pt`, `6 pts`; FI `1 p`, `6 p` |
| fetch once | stub `fetchFn`, then `setLang`, `setPos`, `setSort`, `setGsort` | fetch call count stays `1` |
| langExplicit survives | `setLang('fi')` then `setPos('d')` | URL keeps `lang=fi` |

## UI

- **Strings**: P0.9 plus the existing init-06 keys.
- **Defaults**: skaters `p` desc, goalies `gp` desc, position `all`, language per ADR-028.
- **URL params**: unchanged from init-06 (`lang`, `pos`, `sort`, `dir`, `gsort`, `gdir`).
- **Mobile** (< 600 px): hero behind the title (P0.4); tiles stack in one column (two at tablet
  width); the three cards stack; tables scroll with the name column pinned. No page-level
  horizontal scroll at 375 px.
- **Empty / stale / error**: per init-06. On error, the tiles and cards show `–` and the tables are
  empty, the hero and header still render, and the error banner replaces the stale banner.

## Ownership Check

- **AWS resources created or changed**: none.
- **S3 prefixes written**: `bolts/` (new) and `kiekkokeskus/` (update).
- **Touches anything owned by the main site?** No. `add-index-html` is used as-is.

## Success Criteria

- [ ] `node --test "site/kiekkokeskus/*.test.js" "site/bolts/*.test.js"` green, covering every row
      above and the golden expected-strings table; CI runs both globs
- [ ] `ruff`, `pytest` (≥ 80%) green, with a deploy test for sync order and arguments
- [ ] `python scripts/preview.py --fresh`, then `/bolts/` in Chrome at desktop and 375 px: every
      string, name and number switches EN ⇄ FI; tiles, cards and tables match the golden table;
      the hero sits behind the title on phone; no page-level horizontal scroll
- [ ] Testing is Chrome-only: TESTING.md's manual checklist line "Safari and Chrome" becomes
      "Chrome", and init-06 Verify item 4 (Safari `Intl` parity) is recorded as dropped in the
      PRP-07 report, not left open
- [ ] DevTools Network: exactly one `bolts.json` request across toggling, filtering and sorting
- [ ] Deploy: the dry run shows no deletes; `deploy.py --approved` syncs `kiekkokeskus/` then
      `bolts/`; `smoke.py` green
- [ ] `https://jurigregg.com/bolts` renders the live data in both languages
- [ ] ADR-040 in DECISIONS.md; TESTING.md gains the rows above; TASK.md updated
- [ ] No code file over 500 lines

## Out of Scope

- `/leijonat` page (init-08, which reuses `page.js`, the hero param and the tiles' CSS)
- Points pace vs. cut line chart (init-09)
- Goal scorers on the last-game card (not in `bolts.json`; it would need a builder change)
- Links to player pages on NHL.com
- Rookie markers

## Verify in PRP

- [ ] `standing.streak.code` values: confirm `W`, `L`, `OT` are the only ones in the raw
      standings archive (search a few dated `standings__*` files). If another code shows up (for
      example `SO`), add a string for it.
- [ ] `Intl.PluralRules('en-US', {type: 'ordinal'})` and `('fi-FI')` exist in Node 22 and give
      the expected categories (`one`/`two`/`few`/`other` for EN ordinals).
- [ ] `aws s3 ls s3://jurigregg-static-site/bolts/ --recursive` is empty before the first sync.

## Open Questions

(none)

## Notes

### Draft ADR-040: Page hero art

**Date**: 2026-10-11 · **Status**: Accepted

**Decision**
- Each page has one decorative hero drawn by Juri: `/bolts` the storm-over-Tampa skyline with the
  monogram, `/leijonat` the lion in the "SUOMI" ring (init-08).
- **All-blue treatment**: the pencil sketch is converted offline to pale lines on `--kk-bg`
  navy and saved as a flattened WebP (no alpha) at 900 px wide. That's about 40–55 KB, against
  100–140 KB with an alpha channel.
- The skyline needed an extra pass. Inverting the tones makes the white lightning dark, so the
  bolts were traced separately and laid back on top as the brightest strokes with a slight glow.
- Original photos are kept in `art/` (not deployed), so the conversion can be redone.
- Rejected: a navy-to-paper gradient showing the original drawing in its own colours (too harsh
  against the dark page); the earlier wordmark sketches ("Tampa Bay Lightning Hockey", "Leijonat
  Suomi Hockey"), which read as official team branding next to an ADR-002 disclaimer.

**Consequences**
- The heroes only work on the page background colour, never on a card surface.
- A redraw means re-running the conversion. It's a manual step, not part of the build.
