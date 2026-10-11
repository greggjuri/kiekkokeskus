# init-06: Shared UI

**Created**: 2026-10-11
**Phase**: 3 Pages
**Depends On**: init-04 (`bolts.json`), init-05 (`leijonat.json`), init-02 (`scripts/deploy.py`)
**ADRs**: ADR-002, 003, 015–018, 020–022, 024, 028, 030, 034, 035, 037; adds ADR-038 (stat display
conventions) and ADR-039 (shared assets: deploy and Cache-Control), both in DECISIONS.md

---

## Problem Statement

Both pages need the same machinery: language toggle, number and name formatting, the sortable and
filterable player tables, URL state, the stale and error banners, the disclaimer footer, and one
look. Building it inside `/bolts` and then copying it into `/leijonat` would give two drifting
copies. This spec builds it once under `site/kiekkokeskus/`, so init-07 and init-08 only do layout
and page-specific sections.

## Goal

`site/kiekkokeskus/` holds tested, framework-free ES modules and one stylesheet. A local dev
harness renders both golden JSON files through them, with the toggle, both tables, the banners and
the footer working. `scripts/deploy.py --approved` syncs the shared assets to
`s3://jurigregg-static-site/kiekkokeskus/` with their own Cache-Control. `node --test` is green.
No page is published yet.

## Requirements

### Must Have (P0)

1. **Module layout** (`site/kiekkokeskus/`, each file under 500 lines, ADR-034):

   | File | Pure? | Does |
   |---|---|---|
   | `strings.js` | yes | `{ en: {...}, fi: {...} }` dictionary, every key in both (table below) |
   | `i18n.js` | mostly | language resolution, `t(key, vars)`, name rendering, toggle wiring, `<html lang>` |
   | `format.js` | yes | every number, time and date formatter (P0.4) |
   | `columns.js` | yes | skater and goalie column definitions (P0.5) |
   | `sort.js` | yes | sort and position filter over row arrays |
   | `url.js` | yes + thin DOM | parse and serialize view state; `history.replaceState` |
   | `data.js` | yes + fetch | fetch one JSON, check `schemaVersion`, compute staleness |
   | `table.js` | DOM | render a sortable table from columns + rows + state |
   | `chrome.js` | DOM | header (breadcrumb, toggle), banners, position pills, footer |
   | `kk.css` | n/a | tokens and components (P0.8) |

   Pure modules take `lang` and `now` as arguments rather than reading globals, so Node can test
   them. No npm, no build, no dependencies (CLAUDE.md JavaScript rules).

2. **Language** (ADR-028, unchanged): `?lang=fi|en` wins, then `localStorage` key `kk.lang`, then
   `navigator.language` starting `fi`, then EN. Every `localStorage` read and write is wrapped in
   try/catch; a failure falls through to the next rule. Toggling re-renders every string, name and
   number in place (no reload), updates `<html lang>`, stores the choice, and writes `?lang=`.

3. **Names** (ADR-018, 028). Rows carry `firstName` and `lastName` as localized objects, and the
   builders pass through every language key they get (`cs`, `sk`, `fr` and so on), not only
   `{default, fi}`. Rendering:
   - EN: `firstName.default + " " + lastName.default`
   - FI: each part separately, `part.fi ?? part.default`, so a row with only `lastName.fi`
     (Vasilevskiy → "Andrei Vasilevski") still works
   - Team names (`team.name`, `teams[].name`, `opponent.name`) follow the same rule. In practice
     they carry no `fi` key, so FI shows `default`.
   - The name column sorts by rendered last name, then rendered first name, using
     `localeCompare(…, lang)`, so Ä and Ö sort after Z in FI.

4. **Formatters** (`format.js`). Data stays raw (ADR-016, 017); this is the only place units change.
   Every formatter returns `–` (U+2013) for `null` or `undefined`.

   | Kind | Used for | Input | EN | FI |
   |---|---|---|---|---|
   | `int` | GP, G, A, P, PIM, SOG, PPG, … | int | `12` | `12` |
   | `signed` | +/- | int | `+2`, `−1`, `0` | `+2`, `−1`, `0` |
   | `rate3` | SV%, point % | fraction 0–1 | `.915`, `1.000` | `91,57`, `100,00` |
   | `pct1` | S%, FO%, PP%, PK% in tables | fraction 0–1 | `14.3` | `14,3` |
   | `pct1Sign` | PP%, PK% in tiles (init-07) | fraction 0–1 | `14.3%` | `14,3 %` (NBSP) |
   | `dec2` | GAA | float | `2.05` | `2,05` |
   | `toi` | TOI/GP, goalie TOI | int seconds | `16:03`, `175:52` | `16.03`, `175.52` |
   | `date` | `dataDate`, game dates | `YYYY-MM-DD` | `Oct 2, 2026` | `2.10.2026` |
   | `gameTime` | `startTimeUTC` | ISO UTC | viewer's local time zone, short zone name | same, `klo 19.30` style |
   | `position` | `positionCode` | C/L/R/D/G | `C`, `L`, `R`, `D`, `G` | `KH`, `VL`, `OL`, `P`, `MV` |

   - Negative numbers use U+2212 in both languages. `Intl` gives U+2212 for `fi-FI` but a hyphen
     for `en-US`, so the formatter normalizes.
   - Decimals go through `Intl.NumberFormat` with fixed fraction digits. `rate3` in EN strips the
     leading `0` only (`0.915` → `.915`, `1.000` stays).
   - `date` parses `YYYY-MM-DD` as a calendar date (UTC noon), never as local midnight, so it can't
     shift a day west of UTC.
   - No `%` sign inside table cells in either language. The header carries it (`S%`, `L%`). This
     matches both NHL.com and liiga.fi.

5. **Columns** (`columns.js`, ADR-030). Keys are the JSON field names, which are also the URL sort
   values (ADR-038). Order follows the design canvas. `team` is present only when the page asks for
   it (`/leijonat`).

   Skaters:

   | Key | EN | EN title | FI | FI title | Format | First-click dir |
   |---|---|---|---|---|---|---|
   | name | Player | Player | Pelaaja | Pelaaja | name | asc |
   | `team` | Team | Team | Joukkue | Joukkue | text | asc |
   | `positionCode` | Pos | Position | PP | Pelipaikka | position | asc |
   | `gp` | GP | Games played | O | Ottelut | int | desc |
   | `g` | G | Goals | M | Maalit | int | desc |
   | `a` | A | Assists | S | Syötöt | int | desc |
   | `p` | P | Points | P | Pisteet | int | desc |
   | `pm` | +/- | Plus/minus | +/− | Plus-miinus | signed | desc |
   | `pim` | PIM | Penalty minutes | R | Rangaistusminuutit | int | desc |
   | `toiPerGame` | TOI/GP | Time on ice per game | Aika/O | Peliaika ottelua kohden | toi | desc |
   | `sog` | SOG | Shots on goal | L | Laukaukset | int | desc |
   | `shootingPct` | S% | Shooting percentage | L% | Laukausprosentti | pct1 | desc |
   | `ppg` | PPG | Power-play goals | YV | Ylivoimamaalit | int | desc |
   | `ppp` | PPP | Power-play points | YVP | Ylivoimapisteet | int | desc |
   | `shg` | SHG | Short-handed goals | AV | Alivoimamaalit | int | desc |
   | `gwg` | GWG | Game-winning goals | VM | Voittomaalit | int | desc |
   | `faceoffPct` | FO% | Faceoff win percentage | A% | Aloitusprosentti | pct1 | desc |
   | `hits` | HIT | Hits | TAK | Taklaukset | int | desc |
   | `blocks` | BLK | Blocked shots | BL | Blokatut laukaukset | int | desc |

   Goalies:

   | Key | EN | EN title | FI | FI title | Format | First-click dir |
   |---|---|---|---|---|---|---|
   | name | Goalie | Goalie | Maalivahti | Maalivahti | name | asc |
   | `team` | Team | Team | Joukkue | Joukkue | text | asc |
   | `gp` | GP | Games played | PO | Pelatut ottelut | int | desc |
   | `gs` | GS | Games started | AK | Avauskokoonpanossa | int | desc |
   | `w` | W | Wins | V | Voitot | int | desc |
   | `l` | L | Losses | H | Häviöt | int | desc |
   | `otl` | OTL | Overtime and shootout losses | JH | Jatkoaika- ja voittomaalikilpailuhäviöt | int | desc |
   | `svPct` | SV% | Save percentage | T% | Torjuntaprosentti | rate3 | desc |
   | `gaa` | GAA | Goals-against average | KA | Päästettyjen maalien keskiarvo | dec2 | **asc** |
   | `so` | SO | Shutouts | NP | Nollapelit | int | desc |
   | `toi` | TOI | Time on ice | Aika | Peliaika | toi | desc |

   The FI abbreviations and titles come from the official liiga.fi glossary
   (`liiga.fi/fi/tilastot/sanasto`, read 2026-10-11), except five that Liiga doesn't have: `Aika/O`
   (built on Liiga's `RM/O` pattern), `TAK`, `BL`, `AK` and `JH`. Those are ours and are marked as
   such in ADR-038.

6. **Sorting and filtering** (`sort.js`, TESTING Layer 5):
   - Numeric compare for numbers, `localeCompare(…, lang)` for text.
   - `null` sorts last in **both** directions.
   - Stable: ties keep JSON order.
   - Clicking the active column flips direction. Clicking a new column uses its first-click
     direction from P0.5.
   - Position filter: `all` (default), `f` = C+L+R, `d` = D. It applies to skaters only. Goalies
     are never in the skater table.

7. **URL state** (`url.js`). Skater and goalie tables sort independently:

   | Param | Values | Default (omitted from URL) |
   |---|---|---|
   | `lang` | `en`, `fi` | per P0.2 |
   | `pos` | `all`, `f`, `d` | `all` |
   | `sort` | a skater column key | `p` |
   | `dir` | `asc`, `desc` | `desc` |
   | `gsort` | a goalie column key | `gp` |
   | `gdir` | `asc`, `desc` | `desc` |

   Unknown or invalid values fall back to the default silently. Changes use `replaceState`, so
   sorting doesn't fill the back button. Default values are dropped from the URL, so a fresh view
   is a clean URL. `?pos=d&sort=toiPerGame&dir=desc&lang=fi` round-trips exactly.

8. **Look** (`kk.css`), taken from the "Kiekkokeskus page layouts" design canvas:
   - Tokens as CSS custom properties on `:root`: `--kk-bg #071A3A`, `--kk-surface #0E2550`,
     `--kk-hover #13306A`, `--kk-text #FFFFFF`, `--kk-muted #B6C3DD`, `--kk-faint #7F90B3`
     (null cells), `--kk-line rgba(255,255,255,.18)`, `--kk-line-soft rgba(255,255,255,.07)`.
   - Type: Barlow Condensed 600/700 for the page title and big numbers, IBM Plex Sans 400/500/600
     for everything else, from Google Fonts with `display=swap`. Tabular numerals in tables.
   - Components: `.kk-table` (sticky name column, right-aligned numbers, sorted-column tint, row
     hover), `.kk-scroll` (horizontal scroll box), `.kk-pill` (position filter, `aria-pressed`),
     `.kk-lang` (toggle), `.kk-card` (surface panel), `.kk-banner` (stale and error), footer.
   - Dark only. Touch targets ≥ 44 px. Visible `:focus-visible` outlines. Header buttons are real
     `<button>`s inside `<th>` with `aria-sort` on the `<th>`.
   - Layout container `max-width: 1180px`, 24 px gutter, 16 px below 600 px.

9. **Data loading and banners** (`data.js`, `chrome.js`):
   - `loadData(path, expectedSchemaVersion)` fetches same-origin `/data/kiekkokeskus/…` only
     (ADR-003). One fetch per page load.
   - Fetch failure, non-2xx, invalid JSON, or a `schemaVersion` mismatch shows the **error banner**
     and leaves the tables in their empty state. The cause goes to `console.error`.
   - **Stale banner** when `now − generatedAt > 36 h` (PLANNING, CLAUDE.md). `isStale(generatedAt,
     now)` is pure and tested at 35 h 59 m and 36 h 01 m.
   - While loading, tables show the loading string. An empty row array shows the empty string. A
     filter that matches nothing shows the no-match string.

10. **Footer**: the not-affiliated disclaimer (ADR-002) and the "data through" line, both
    languages. The EN disclaimer matches the README verbatim.

11. **Dev harness**: `site/kiekkokeskus/_dev/harness.html` (never deployed) loads both data files
    and renders, for each: header with toggle, banners, position pills, the skater table, the goalie
    table, and the footer. `/leijonat` data renders with the team column, and `/bolts` data without.
    It's the reference that init-07/08 lift from. It is not a page.

12. **Local preview**: `scripts/preview.py`, stdlib only.
    - Serves `site/` at `/` on `127.0.0.1:8006` (flag `--port`).
    - Maps `/data/kiekkokeskus/{bolts,leijonat}.json` to `tests/golden/` by default, or to
      `--data DIR` (for example a copy pulled with `aws s3 cp`).
    - `--fresh` rewrites `generatedAt` to now on the way out, so the stale banner can be seen both
      ways (the golden files are always stale).
    - `--break bolts` serves `schemaVersion: 999` for that file, to show the error banner.
    - Never writes to disk and never calls AWS or the NHL.

13. **Deploy** (`scripts/deploy.py`, ADR-024, 039). Fill in the `page_sync()` placeholder for the
    shared prefix only:
    - `aws s3 sync site/kiekkokeskus/ s3://jurigregg-static-site/kiekkokeskus/ --delete
      --exclude "*.test.js" --exclude "_dev/*" --exclude "package.json"
      --cache-control "public, max-age=300" --profile default`
    - `--delete` is scoped to the `kiekkokeskus/` prefix, which ADR-024 allows. The existing
      allowed-prefix guard must accept this destination and still refuse anything else (there's a
      test for both).
    - `bolts/` and `leijonat/` syncs stay commented. init-07 and init-08 enable them.

14. **Smoke** (`scripts/smoke.py`): `/kiekkokeskus/kk.css` and `/kiekkokeskus/i18n.js` return 200,
    the JS has a JavaScript `Content-Type` (module scripts refuse anything else), and both carry
    `max-age=300`. The existing site-untouched checks (`/`, `/sports`) stay.

### Should Have (P1)

1. `chrome.js` exposes the header in a form init-07/08 can pass a page title and subtitle key to,
   so the header markup lives in one place.
2. The harness has a `?now=` override (ISO timestamp) that feeds `isStale`, so the stale banner
   can be checked without editing JSON.

### Nice to Have (P2)

1. Keyboard: arrow keys move between header buttons in a table.

## Output / Data Contract

Page code reads only. Nothing in the collector changes. **schemaVersion change: no.** Expected
`schemaVersion` is `1` for both files.

| Field | File | Units / type | Nullable | Used by |
|---|---|---|---|---|
| `schemaVersion`, `generatedAt`, `dataDate`, `season` | both | int, ISO UTC, `YYYY-MM-DD`, string | no | `data.js`, footer |
| `skaters[].firstName`, `.lastName` | both | localized object | no | name rendering |
| `skaters[].positionCode` | both | `C`/`L`/`R`/`D` | no | filter, `position` |
| `skaters[].team` | leijonat | abbrev | no | team column |
| `skaters[].{gp,g,a,p,pm,pim,sog,ppg,ppp,shg,gwg,hits,blocks}` | both | int | yes (ADR-015) | int / signed |
| `skaters[].toiPerGame` | both | int seconds | yes | `toi` |
| `skaters[].shootingPct`, `.faceoffPct` | both | fraction 0–1 | yes (`faceoffPct` null for non-takers, ADR-035) | `pct1` |
| `goalies[].{gp,gs,w,l,otl,so}` | both | int | yes | int |
| `goalies[].svPct` | both | fraction 0–1 | yes | `rate3` |
| `goalies[].gaa` | both | float | yes | `dec2` |
| `goalies[].toi` | both | int seconds (season total) | yes | `toi` |
| `goalies[].team` | leijonat | abbrev | no | team column |

- **S3 keys written**: `kiekkokeskus/*` (shared assets) only, by `deploy.py`. Nothing under
  `data/`.

## Fixtures and Gotchas

No new NHL fixtures. Layer 5 tests read `tests/golden/{bolts,leijonat}.json` directly. Add these
rows to the TESTING.md gotcha matrix under a new "Page logic" heading:

| Gotcha | Input | Assert |
|---|---|---|
| null in any column (ADR-015) | golden `faceoffPct: null` | renders `–`; sorts last asc and desc |
| partial FI name (ADR-018) | golden Vasilevskiy (`lastName.fi` only) | FI: "Andrei Vasilevski"; EN: "Andrei Vasilevskiy" |
| extra name languages | golden `cs`/`sk` keys | ignored, no crash |
| FI minus and NBSP | `pm: -1`, `pct1Sign(0.143)` | `−1` (U+2212) in EN and FI; `14,3 %` with U+00A0 |
| `rate3` edges | `0.9`, `1.0`, `0.0` | EN `.900`, `1.000`, `.000`; FI `90,00`, `100,00`, `0,00` |
| goalie season TOI | `toi: 10552` | EN `175:52`, FI `175.52` |
| date west of UTC | `2026-10-02` with `TZ=America/Los_Angeles` | `Oct 2, 2026`, not Oct 1 |
| stale boundary | `generatedAt` ± 36 h | false at 35:59, true at 36:01 |
| schema mismatch | `schemaVersion: 2` | error state, no throw |
| missing i18n key | every key in `en` | exists in `fi`, and the reverse |

## UI

- **Strings** (in `strings.js`; init-07/08 add page-specific keys to the same file):

  | Key | EN | FI |
  |---|---|---|
  | `nav.crumb` | jurigregg.com / kiekkokeskus | jurigregg.com / kiekkokeskus |
  | `lang.group` | Language | Kieli |
  | `pos.group` | Position | Pelipaikka |
  | `pos.all` | All | Kaikki |
  | `pos.f` | Forwards | Hyökkääjät |
  | `pos.d` | Defense | Puolustajat |
  | `table.skaters` | Skaters | Kenttäpelaajat |
  | `table.goalies` | Goalies | Maalivahdit |
  | `table.sortBy` | Sort by {title} | Lajittele: {title} |
  | `table.loading` | Loading… | Ladataan… |
  | `table.empty` | No games played yet. | Ei vielä pelattuja otteluita. |
  | `table.noMatch` | No players match this filter. | Ei pelaajia tällä suodattimella. |
  | `banner.stale` | Data may be out of date. Last updated {date} at {time}. | Tiedot voivat olla vanhentuneita. Päivitetty viimeksi {date} klo {time}. |
  | `banner.error` | Stats couldn't be loaded. Try again later. | Tilastoja ei voitu ladata. Yritä myöhemmin uudelleen. |
  | `footer.through` | Data through {date} · updated daily at 10:00 ET | Tiedot {date} asti · päivittyy päivittäin klo 10.00 (ET) |
  | `footer.disclaimer` | Kiekkokeskus is a personal, non-commercial project. It is not affiliated with, endorsed by, or sponsored by the National Hockey League, the Tampa Bay Lightning, or any NHL team. Team and league names are trademarks of their respective owners. Data comes from publicly accessible NHL endpoints. | Kiekkokeskus on henkilökohtainen, ei-kaupallinen projekti. Se ei ole sidoksissa NHL:ään, Tampa Bay Lightningiin tai mihinkään NHL-joukkueeseen, eivätkä ne ole hyväksyneet tai tukeneet sitä. Joukkueiden ja liigan nimet ovat omistajiensa tavaramerkkejä. Tiedot ovat peräisin NHL:n julkisista rajapinnoista. |
  | `col.*` / `colTitle.*` | per P0.5 | per P0.5 |
  | `posCode.*` | C, L, R, D, G | KH, VL, OL, P, MV |

- **Defaults**: skaters by `p` desc, goalies by `gp` desc, position `all`, language per ADR-028.
- **URL params**: `lang`, `pos`, `sort`, `dir`, `gsort`, `gdir` (P0.7).
- **Mobile**: tables scroll horizontally inside `.kk-scroll` with the name column pinned. Header
  and pills wrap. Nothing is hidden. Below 600 px the gutter drops to 16 px and cell padding to
  8 px.
- **Empty / stale / error states**: P0.9. The stale banner sits above the first section and
  doesn't hide data. The error banner replaces the tables' content with the error string.

## Ownership Check

- **AWS resources created or changed**: none.
- **S3 prefixes written**: `kiekkokeskus/` only (deploy). `bolts/` and `leijonat/` untouched until
  init-07/08.
- **Touches anything owned by the main site?** No. Google Fonts is a third-party request from the
  browser, not an NHL call (ADR-003 holds).

## Success Criteria

- [ ] `node --test site/kiekkokeskus/` green, covering every gotcha row above
- [ ] `ruff check .`, `ruff format --check .`, `pytest --cov=kiekkokeskus` green (≥ 80%), with
      tests for `preview.py` mapping and the `deploy.py` prefix guard
- [ ] `python scripts/preview.py --fresh`, then the harness in Safari and Chrome: EN ⇄ FI switches
      every string, name and number; both tables sort both ways with nulls last; pills filter;
      reload restores the view from the URL
- [ ] `--break bolts` shows the error banner; without `--fresh` the stale banner shows
- [ ] Phone width (375 px): tables scroll, name column pinned, no page-level horizontal scroll
- [ ] `scripts/deploy.py --approved` syncs `kiekkokeskus/` only; `aws s3 ls
      s3://jurigregg-static-site/kiekkokeskus/ --profile default` shows no `*.test.js` or `_dev/`
- [ ] `scripts/smoke.py` green, including the new asset checks and `/`, `/sports`
- [ ] ADR-038 and ADR-039 in DECISIONS.md; TESTING.md matrix gains the page-logic rows;
      the FI save % Open Question is removed from TASK.md
- [ ] No code file over 500 lines

## Out of Scope

- `/bolts` and `/leijonat` pages, their sections (standings tiles, last game, last night, by-team)
  and their syncs (init-07, init-08)
- Rookie marker on `/leijonat` (init-08; liiga.fi marks rookies with `*`, worth copying)
- Charts and history (init-09)
- Light theme, print styles
- Self-hosting fonts

## Verify in PRP

- [ ] Node 22 on the MacBook runs `site/kiekkokeskus/*.test.js` as ES modules with no
      `package.json` (syntax detection; works on 22.22 in the planning sandbox). If it warns or
      fails, add a one-line `site/kiekkokeskus/package.json` `{"type": "module"}` marker, excluded
      from sync, not an npm project.
- [ ] `aws s3 sync` on the Mac uploads `.js` as `text/javascript` (or `application/javascript`) and
      `.css` as `text/css`. If not, add `--content-type` per extension with separate sync passes.
- [ ] CloudFront passes the object's `Cache-Control: public, max-age=300` for the shared assets
      (it does for JSON per ADR-022, but confirm on `kk.css` with `curl -sI`).
- [ ] Safari's `Intl` `fi-FI` output matches Node's for `pct1Sign` (NBSP) and `gameTime`
      (`la 10.10. klo 19.30`). Manual check in the harness.

## Open Questions

(none)

## Notes

### Draft ADR-038: Stat display conventions (EN/FI)

**Date**: 2026-10-11 · **Status**: Accepted · settles the TASK.md "FI save % format" question

**Decision**
- FI follows liiga.fi, EN follows NHL.com. Evidence: liiga.fi player and goalie tables and its
  glossary (`/fi/tilastot/sanasto`), read 2026-10-11. Liiga shows `T%` as `95,68`, `KA` as
  `1,06`, `L%` as `14,3`, and time on ice as `18.18`.
- Save % and point %: EN `.915`, FI `91,57` (a percentage with two decimals and no sign). Neither
  of the earlier candidates (`,915` or `91,5 %`) is what Finnish readers see on Liiga.
- Shooting %, faceoff %, PP%, PK% in tables: one decimal, no `%` in the cell, in both languages.
  The `%` appears only in headers and in standalone tiles (`14,3 %` with NBSP in FI).
- TOI: EN `MM:SS`, FI `MM.SS`.
- Minus is U+2212 in both languages. Null is `–`.
- FI abbreviations: from the Liiga glossary (`O`, `PO`, `M`, `S`, `P`, `R`, `L`, `L%`, `YV`,
  `YVP`, `AV`, `VM`, `A%`, `V`, `H`, `T%`, `KA`, `NP`, `Aika`, `PP`, positions `KH`/`VL`/`OL`/
  `P`/`MV`). Ours, because Liiga has no equivalent: `Aika/O`, `TAK`, `BL`, `AK`, `JH`.
- Watch-outs from the glossary: `T` is ties in Liiga, not losses (losses are `H`); `PO` is games
  actually played by a goalie, which matches the NHL's goalie GP, while `O` counts lineup
  appearances.
- URL sort values are JSON field names (`sort=toiPerGame`, `gsort=svPct`), not display
  abbreviations. ADR-030's `sort=toi` example reads as `toiPerGame` for skaters.

**Consequences**: FI and EN show different precision for save % (`91,57` vs `.915`). Accepted:
each matches what its readers already know. Sorting uses raw values, so it's unaffected.

### Draft ADR-039: Shared page assets deploy with their own Cache-Control

**Date**: 2026-10-11 · **Status**: Accepted

**Context**: Site objects without `Cache-Control` get the distribution's legacy `DefaultTTL=3600`
(ADR-022 verified note). A JS fix would take up to an hour to reach visitors, and module files can
go out of sync with each other.

**Decision**: `deploy.py` syncs `site/kiekkokeskus/` to `kiekkokeskus/` with
`--cache-control "public, max-age=300"` and a prefix-scoped `--delete`, excluding tests, `_dev/`
and any `package.json`. Page HTML (init-07/08) uses the same header. No cache-busting query
strings and no invalidations.

**Consequences**: a deploy is fully visible within about 5 minutes. A visitor inside that window
might get a mixed set of old and new modules. Accepted for a personal site; revisit only if a
deploy ever breaks a page for that window.
