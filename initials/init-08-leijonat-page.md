# init-08: /leijonat Page

**Created**: 2026-10-12
**Phase**: 3 Pages
**Depends On**: init-05 (`leijonat.json`), init-07 (shared controller, hero, tiles CSS, deployed)
**ADRs**: ADR-002, 003, 010–012, 015–018, 020–022, 024, 028, 030, 034, 037–040

---

## Problem Statement

`leijonat.json` is published daily, but there's no page for it. init-07 built every shared piece
this page needs: the controller (`page.js`), the hero param, `localName`, `tp`, the tiles and the
cards CSS. init-08 is the second consumer of that layer.

## Goal

`jurigregg.com/leijonat` is live in EN and FI. It has the lion hero, four count tiles, the
"last night" cards, the skater and goalie tables (with team column and rookie marker), the
by-team list, and the footer. It reads `leijonat.json` once per page load.

## Requirements

### Must Have (P0)

0. **Housekeeping (first commit).** In TESTING.md's manual checklist, replace "Sorting each column
   works in both directions" with "Click the same column three times: desc → asc → desc, on both
   tables". The old wording let the stale-closure bug (`4c66c00`) through two manual passes.

1. **Page shell** (`site/leijonat/index.html`, `main.js`, `view.js`). Same structure as `/bolts`:
   - `<title>leijonat · kiekkokeskus</title>`; `kk.css`, `kk-page.css`, Google Fonts; one module
     script.
   - Section order: header with hero → count tiles + definition → last night → skaters (with
     pills) → goalies → by team → footer.
   - `main.js` is thin DOM glue around `mountPage`. `view.js` exports a pure
     `leijonatView(data, lang)` that returns every display string for the page-specific sections.
     It's tested in Node against `tests/golden/leijonat.json` (P0.8).
   - The title is lowercase `leijonat`, same treatment as `bolts`.

2. **Hero** (ADR-040). `site/leijonat/hero.webp` is the all-blue lion in the "SUOMI" ring
   (900×604, 40 KB, attached). The original goes to `art/leijonat-hero-source.jpg`. Rendered
   through `renderHeader`'s `hero` param with the init-07 desktop and phone rules. Nothing new.

3. **Count tiles + definition.** Four `.kk-tile`s using the existing CSS:

   | Tile | Label | Value |
   |---|---|---|
   | Skaters | `count.skaters` | `skaters.length` |
   | Goalies | `count.goalies` | `goalies.length` |
   | Teams | `count.teams` | `teams.length` |
   | Rookies | `count.rookies` | rows (skaters + goalies) with `rookie: true` |

   No sub-line on these tiles. Under the tiles, one muted paragraph, `leijonat.definition`.

4. **Last night** (`lastNight`, ADR-012):
   - **Heading**: `lastNight.title`, plus a sub-line `{date} · {games}` where `date` is
     `date(lastNight.date)` and `games` is `tp('lastNight.games', gamesCompleted)`.
   - **One card per row**: skaters first in JSON order, then goalies. Each card shows:
     - the name (`renderName`) plus the rookie marker (P0.6), and the Finn's team abbrev
     - a big line:
       - skaters: `lastNight.skaterLine` with `g`, `a`
       - goalies: `lastNight.goalieLine` with `saves`, `shotsAgainst` and `rate3(svPct)`. A null
         part renders `–`.
     - a game line: the same result badge, score (`teamScore–oppScore`), OT/SO suffix and
       `opp.home` / `opp.away` as the `/bolts` last-game card. The opponent is shown by its
       abbreviation (`game.opponent` is a string here).
   - The goalie `decision` field is **not shown**. The badge comes from `game.result`
     (ADR-037: never from `decision`).
   - **Empty states**:
     - `gamesCompleted == 0` → `lastNight.noGames`
     - games but no rows → `lastNight.noFinns`
     - `lastNight` missing or null → `lastNight.noGames`
   - Cards use the existing card grid, `auto-fill, minmax(260px, 1fr)`.

5. **Tables**:
   - Both use the full init-06 column sets, **with** the `team` column.
   - Defaults and URL params are the same as `/bolts`.
   - `team` sorts as text, ascending first.

6. **Rookie marker.** A `*` after the name in the tables and the last-night cards. It carries a
   `title` and visually hidden text (`rookie.title`) so screen readers say "Rookie" rather than
   "star". This is Liiga's convention.
   - A legend line under each table, `rookie.legend`, shown only when that table has at least
     one rookie.
   - Needs a small shared change: `renderTable` takes an optional `decorateName(row, lang)` that
     returns `{ suffix, title }`. `/bolts` doesn't pass it, so its output is unchanged.
   - Sorting by name ignores the marker.

7. **By team.** One row per `teams[]` entry. Each row shows:
   - the team name (`localName(team.name)`, so FI shows `default`, since no `fi` key is
     observed)
   - the count, `tp('byTeam.players', skaters + goalies)`
   - the Finns on that team: last names via the FI/EN name rule, alphabetical
     (`localeCompare(…, lang)`), skaters and goalies mixed, joined with `, `

   Order: total players desc, then rendered team name asc. Lay it out as a compact list inside a
   `.kk-card`, not a table. It's for reading, not sorting.

8. **Shared additions**, each with Layer 5 tests:
   - `decorateName` support in `table.js` (P0.6)
   - the strings in P0.9

   `/bolts` must render byte-identical table HTML before and after. Snapshot one rendered row in
   a test using the existing pure helpers, or assert `decorateName` absent → no suffix node.

9. **Strings** added to `strings.js` (parity test still applies):

   | Key | EN | FI |
   |---|---|---|
   | `page.leijonat.title` | leijonat | leijonat |
   | `page.leijonat.subtitle` | Finnish players in the NHL · {season} season | Suomalaiset NHL:ssä · kausi {season} |
   | `page.leijonat.subtitleNoSeason` | Finnish players in the NHL | Suomalaiset NHL:ssä |
   | `count.skaters` | Skaters | Kenttäpelaajat |
   | `count.goalies` | Goalies | Maalivahdit |
   | `count.teams` | Teams | Joukkueet |
   | `count.rookies` | Rookies | Tulokkaat |
   | `leijonat.definition` | A Finn here means Finnish nationality, wherever the player was born. Players appear once they've played a regular-season game this season. | Suomalaiseksi lasketaan Suomen kansalainen syntymäpaikasta riippumatta. Mukana ovat pelaajat, jotka ovat pelanneet tällä kaudella runkosarjaottelun. |
   | `lastNight.title` | Last night | Viime yönä |
   | `lastNight.games.one` / `.other` | {n} game / {n} games | {n} ottelu / {n} ottelua |
   | `lastNight.noGames` | No NHL games last night. | Viime yönä ei pelattu NHL-otteluita. |
   | `lastNight.noFinns` | No Finnish points or starts last night. | Ei suomalaisten pisteitä eikä aloituksia viime yönä. |
   | `lastNight.skaterLine` | {g} G · {a} A | {g} M · {a} S |
   | `lastNight.goalieLine` | {saves}/{sa} saves · {svPct} | {saves}/{sa} torjuntaa · {svPct} |
   | `rookie.title` | Rookie | Tulokas |
   | `rookie.legend` | * Rookie | * Tulokas |
   | `byTeam.title` | By team | Joukkueittain |
   | `byTeam.players.one` / `.other` | {n} player / {n} players | {n} pelaaja / {n} pelaajaa |

   FI `M`/`S` match ADR-038's skater columns.

10. **Deploy** (`scripts/deploy.py`, ADR-024, 039). Add the `leijonat/` sync after `bolts/`:
    `site/leijonat/ → s3://jurigregg-static-site/leijonat/ --delete --exclude "*.test.js"
    --cache-control "public, max-age=300"`. Order is shared, then bolts, then leijonat. Test the
    order and arguments.
    - Before the first real run: `aws s3 ls …/leijonat/ --recursive` and a `--dryrun` with the
      exclude. Any `delete:` line stops the deploy. Afterwards, `aws s3 ls …/leijonat/` must show
      no `*.test.js`.

11. **Smoke** (`scripts/smoke.py`): `/leijonat` and `/leijonat/` return 200 `text/html`
    referencing `/kiekkokeskus/kk.css`; `/leijonat/hero.webp` returns 200 `image/webp` with
    `max-age=300`. Existing checks stay.

### Should Have (P1)

1. If the harness still carries a `/leijonat` preview section with placeholder sections, switch
   it to the real `leijonatView`, or drop that section now that the real page exists. Code's
   call; record which.

### Nice to Have (P2)

1. On the by-team list, each team's Finns link to that table filtered. Skip unless it's trivial.
   There's no team filter today.

## Output / Data Contract

Read-only. **schemaVersion: no change** (expects `1`). Fields consumed beyond the init-06 table
fields:

| Field | Units / type | Nullable | Used by |
|---|---|---|---|
| `season` | string | no | subtitle |
| `skaters[].team`, `goalies[].team` | abbrev | no in practice (verify) | team column, by-team names |
| `skaters[].rookie`, `goalies[].rookie` | bool, non-null (ADR-037) | no | marker, rookies tile |
| `teams[].{abbrev,name,skaters,goalies}` | abbrev, localized object, ints | no | teams tile, by team |
| `lastNight.{date,gamesCompleted}` | ET date, int | object may be missing (verify) | heading, empty states |
| `lastNight.skaters[].{firstName,lastName,team,g,a,game}` | | list may be empty | skater cards |
| `lastNight.goalies[].{firstName,lastName,team,saves,shotsAgainst,svPct,game}` | ints, fraction 0–1 | `saves`/`shotsAgainst`/`svPct` nullable | goalie cards |
| `…game.{home,opponent,teamScore,oppScore,result,decidedIn}` | bool, abbrev, ints, `W`/`L`/`OTL`, `REG`/`OT`/`SO`/null | | game line |

Not shown: `lastNight.*.{pm,sog,pim,toi}`, goalie `decision`, `playerId` (used only as a DOM key
if needed).

- **S3 keys written**: `leijonat/index.html`, `main.js`, `view.js`, `hero.webp`, plus updated
  `kiekkokeskus/{table.js,strings.js}` (and `kk-page.css` if card styles need it).

## Fixtures and Gotchas

No new NHL fixtures. Layer 5 reads `tests/golden/leijonat.json` (dataDate 2026-10-09). Expected
strings:

| View field | EN | FI |
|---|---|---|
| count tiles | `30`, `5`, `19`, `4` | same numbers |
| last night heading | `Last night`, `Oct 9, 2026 · 4 games` | `Viime yönä`, `9.10.2026 · 4 ottelua` |
| Granlund card | `Mikael Granlund`, `ANA`, `1 G · 1 A`, `W`, `5–1`, `at WPG` | `1 M · 1 S`, `V`, `5–1`, `WPG (vieras)` |
| Kakko card | `Kaapo Kakko`, `SEA`, `0 G · 1 A`, `W`, `6–3`, `at DET` | `0 M · 1 S`, `V`, `6–3`, `DET (vieras)` |
| by team, first 4 rows | `Dallas Stars · 6 players · Heiskanen, Hintz, Hyry, Kiviranta, Lindell, Rantanen`; `Florida Panthers · 4 players · Barkov, Luostarinen, Lundell, Mikkola`; `Los Angeles Kings · 3 players`; `Vancouver Canucks · 3 players · Lankinen, Meriläinen, Räty` | `6 pelaajaa` … same names |
| Määttä in skaters table | `Olli Maatta` | `Olli Määttä` |
| rookie marker | rows for Helenius, Hyry, Lambert, Ottavainen carry `*`; legend shown under skaters, hidden under goalies (no rookie goalies) | `Tulokas` |

EN shows the NHL's ASCII spelling (`Maatta`, `Teravainen`), because EN renders `default` and FI
renders `fi ?? default` (ADR-028). That's intended, not a bug. The `Räty` default already
carries the umlaut.

Add to the TESTING.md gotcha matrix (Page logic):

| Gotcha | Input | Assert |
|---|---|---|
| last night: no games | `gamesCompleted: 0`, empty lists | `lastNight.noGames`, no cards |
| last night: games, no Finns | `gamesCompleted: 5`, empty lists | `lastNight.noFinns` |
| last night: goalie with no shots | synthetic goalie card, `saves`/`shotsAgainst`/`svPct` null | `–/– saves · –`, no throw |
| goalie badge from result, not decision | `decision: "W"`, `game.result: "L"` | badge `L` (FI `H`) |
| OT loss card | `game.result: "OTL"`, `decidedIn: "OT"` | `OTL` + `OT` (FI `JH` + `JA`) |
| rookie marker | rookie row vs. non-rookie row | `*` + accessible "Rookie"/"Tulokas" only on the rookie row; legend only when a rookie is present |
| name sort ignores marker | rookie `Helenius` vs. `Heiskanen` | sorted by name only |
| by-team order ties | two teams with equal totals | team name asc (`Los Angeles Kings` before `Vancouver Canucks`) |
| FI vs EN name source | Määttä row | EN `Maatta`, FI `Määttä` |
| `/bolts` unchanged | `renderTable` without `decorateName` | no suffix node, output identical to before |

## UI

- **Strings**: P0.9 plus existing keys.
- **Defaults**: skaters `p` desc, goalies `gp` desc, position `all`, language per ADR-028.
- **URL params**: unchanged (`lang`, `pos`, `sort`, `dir`, `gsort`, `gdir`). Sort keys now
  include `team`.
- **Mobile** (< 600 px, checked at a true 375 px via device emulation, not a resized window):
  hero behind the title; tiles 1 column (2 at tablet); last-night cards 1 column; tables scroll
  with the name column pinned (team column scrolls with the rest); by-team rows wrap the name
  list. No page-level horizontal scroll.
- **Empty / stale / error**: as `/bolts`. On error the tiles show `–`, the last-night and by-team
  sections render empty (the error banner carries the message), and the tables are empty.

## Ownership Check

- **AWS resources created or changed**: none.
- **S3 prefixes written**: `leijonat/` (new) and `kiekkokeskus/` (update).
- **Touches anything owned by the main site?** No.

## Success Criteria

- [ ] `node --test "site/kiekkokeskus/*.test.js" "site/bolts/*.test.js" "site/leijonat/*.test.js"`
      green, covering the golden table and every gotcha row; CI runs all three globs
- [ ] `ruff`, `pytest` (≥ 80%) green, with the deploy order test extended to three syncs
- [ ] `python scripts/preview.py --fresh`, then `/leijonat/` in Chrome at desktop width and at
      375 px via device emulation: every string, name and number switches EN ⇄ FI; tables sort
      desc → asc → desc on the same column (both tables, including `team`); rookie markers and
      legend appear; no page-level horizontal scroll
- [ ] `/bolts` still renders and behaves the same (quick regression pass: toggle, sort ×3, pill)
- [ ] DevTools Network: one `leijonat.json` request across toggling, filtering and sorting
- [ ] Deploy: dry runs show no deletes and no test files; syncs run shared → bolts → leijonat;
      `smoke.py` green
- [ ] `https://jurigregg.com/leijonat` shows the live data in both languages
- [ ] TESTING.md rows added; TASK.md updated (init-08 complete; Up Next is init-09)
- [ ] No code file over 500 lines

## Out of Scope

- History, charts (init-09)
- `bolts.json` runner-up (init-10 candidate, Known Issues)
- A team filter on the tables
- Player headshots, team logos (ADR-003)
- Linking between `/bolts` and `/leijonat` (could be a small follow-up: a shared nav line under
  the breadcrumb)

## Verify in PRP

- [ ] Every live `skaters[]`/`goalies[]` row has `gp ≥ 1`. The definition string claims players
      appear once they've played. If any `gp: 0` row exists, drop the second sentence of
      `leijonat.definition` in both languages and note it in the report.
- [ ] `team` is never null in the live file (bios `currentTeamAbbrev`). If a null shows up, by-team
      groups it under `–` and the team cell shows `–`.
- [ ] `lastNight` is always present in the live file, even on a no-games day. If it can be
      missing, the view treats it as `gamesCompleted: 0`.
- [ ] `teams[]` totals equal the per-team row counts. They do in the golden. If they ever
      disagree, the by-team count uses the row count and logs a console warning.

## Open Questions

(none)

## Notes

- No new ADR. ADR-040 already covers the lion hero, and ADR-037 already says the badge comes from
  `game.result`.
- The design canvas's `/leijonat` artboard used a white Finnish-flag theme. This spec
  deliberately keeps the shared navy theme, so both pages read as one site and the ADR-040 hero
  sits on `--kk-bg`.
