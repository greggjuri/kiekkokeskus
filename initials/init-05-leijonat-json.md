# init-05: leijonat.json Builder

**Created**: 2026-10-10
**Phase**: 2 Data
**Depends On**: init-03 (bios + boxscores already archived), init-04 (`stats_rest.py`, build phase)
**ADRs**: ADR-003, 006, 010–018, 022, 028, 030, 033, 035; adds ADR-037 (DECISIONS-DATA.md)

---

## Problem Statement

The collector already archives the Finn bios and last night's boxscores every morning, but nothing
turns them into what `/leijonat` needs. This spec produces the one JSON file that page reads, so
init-08 is pure rendering, the same way init-04 did for `/bolts`.

## Goal

Each daily run writes `data/kiekkokeskus/leijonat.json` from that run's in-memory payloads. It
holds last night's Finnish performances, full season rows for every Finnish skater and goalie with
the same ADR-030 columns as `/bolts` plus team and rookie, and a by-team count. A build failure
fails the run loudly and leaves yesterday's file in place.

## Requirements

### Must Have (P0)

1. **New endpoints in the manifest.** These are league-wide stats REST reports filtered by
   nationality instead of team. Exact filter syntax is verified in the PRP. All are archived raw
   before parsing (ADR-006), with `__` slugs and the `check_complete` pagination guard (ADR-035).

   | Slug | Endpoint | Why |
   |---|---|---|
   | `skater-summary-FIN__{season}` | stats REST `skater/summary`, `nationalityCode="FIN"`, `gameTypeId=2`, season | core skater columns, PPP |
   | `skater-realtime-FIN__{season}` | `skater/realtime`, same filter | hits, blocks |
   | `skater-faceoff-FIN__{season}` | `skater/faceoffpercentages`, same filter | `totalFaceoffs` for the ADR-035 faceoff rule |
   | `goalie-summary-FIN__{season}` | `goalie/summary`, same filter | goalie columns |

   Existing payloads this spec reads: `skater-bios-FIN__{season}__p{n}`,
   `goalie-bios-FIN__{season}__p{n}`, `boxscore__{gameId}` (all of them for `dataDate`),
   `schedule__{dataDate}` and `standings__{dataDate}` (team names).

   That's 4 extra requests per run. With the conditional name fetch in P0.6, a worst case is
   about 50, which is within the PLANNING budget.

2. **URL builder.** Add a nationality-filtered sibling of `_stats_rest_team_url` in `nhl.py`.
   `nationality` is a parameter, so nothing is hard-coded to FIN beyond the call site. It must
   never emit `/now` (existing test).

3. **Parsers** (`src/kiekkokeskus/parse/`, pure):
   - **`stats_rest.py`**: reuse `by_player_id`, `check_complete`. Add whatever row shaping the
     goalie summary needs. Don't fork the module.
   - **`bios.py`** (new): merge all bios pages into one Finn set, keyed by `playerId`, with
     skater vs goalie kept apart. Duplicate `playerId` across pages → error, not a silent dedupe.
     The page count must reach `total` (ADR-011).
   - **`boxscore.py`** (new): per game, return the game context (id, home/away abbrevs, scores,
     state, decidedIn) and one row per player from `playerByGameStats.{awayTeam,homeTeam}.
     {forwards,defense,goalies}`. TOI `"MM:SS"` becomes int seconds (ADR-017). An absent goalie
     `savePctg`/`decision` becomes `None` (ADR-015).

4. **Builder** (`src/kiekkokeskus/build_leijonat.py`, pure: parsed inputs + `dataDate` → dict).
   No I/O, no clock.

5. **Handler build phase.** Run `build_leijonat` next to `build_bolts`:
   - **The two builders are independent.** Each runs in its own try. A builder that succeeds has
     its file written. If either fails, the error is logged with the builder name, the health
     file is **not** written, and the run raises after both were attempted (the alarm fires).
     One broken builder must not freeze the other page.
   - On full success, the health file carries `built: ["bolts", "leijonat"]`.
   - `leijonat.json` is written with `Cache-Control: public, max-age=300` (ADR-022).
   - Existing rule unchanged: no build runs if any fetch failed.
   - Update `test_build_failure_skips_bolts_and_health_and_raises` to the new behaviour, and add
     the mirror case (leijonat fails → `bolts.json` written, no health, raises).

6. **Names with umlauts.** The API's `default` names drop umlauts (Maatta, Teravainen,
   Merilainen). That's wrong on a Finnish page. The PRP checks the sources in this order and
   implements the **first** one that gives `Määttä`/`Teräväinen`/`Meriläinen`:
   1. the stats REST rows themselves (bios or summary name fields)
   2. the `fi` key of the localized names in `club-stats/{team}` (ADR-018)
   3. the boxscore name objects

   - If (1) works: no extra requests.
   - If only (2) works: fetch `club-stats/{team}/{season}/2` for each distinct current team of a
     Finn (≤ 32, likely ~20) and use them **for names only**. Stats still come from stats REST.
     Slug `club-stats-{TEAM}__{season}__2`, the same as TBL's (TBL's fetch is reused, not
     repeated).
   - If none works: ship the ASCII names, log a TASK.md Known Issue, and stop there. **No
     hand-maintained name map** in this spec.

   Whichever source wins, names in the output are localized objects `{default, fi?}` (ADR-018)
   and the builder never picks a language (ADR-028).

7. **Smoke** (`scripts/smoke.py`): `leijonat.json` returns 200, `schemaVersion == 1`, the
   `Cache-Control` contains `max-age=300`, `dataDate` equals `bolts.json`'s `dataDate`, at least
   one skater row, and the health file has `built` containing `"leijonat"`.

8. **ADR-037** (DECISIONS-DATA.md): field sources for `leijonat.json` as verified, the
   last-night inclusion rule, the name-source outcome from P0.6, the rookie definition, and the
   traded-player behaviour.

### Should Have (P1)

1. `scripts/build_local.py` gains `leijonat` (it exists from init-04 if PRP-04 built it; if not,
   add it here for both builders). init-08 uses it for page work without AWS.

## Output / Data Contract: `data/kiekkokeskus/leijonat.json`

Envelope: `schemaVersion: 1`, `generatedAt` (UTC Z), `dataDate` (ET date), `season`.

### `teams` (the "by team" block)
| Field | Source | Units / type | Nullable |
|---|---|---|---|
| `abbrev` | player rows' `team` | string | no |
| `name` | standings `teamName` | `{default, fr?}` (no `fi` exists) | no |
| `skaters`, `goalies` | count of Finn rows on that team | int | no |

Sorted by `skaters + goalies` desc, then `abbrev` asc. Only teams with at least one Finn appear.

### `lastNight`
| Field | Source | Units / type | Nullable |
|---|---|---|---|
| `date` | `dataDate` | ET date | no |
| `gamesCompleted` | schedule: games on `dataDate` with `gameType == 2`, state ∈ {OFF, FINAL} | int | no |
| `skaters[]` | boxscores ⋈ Finn set | see below | empty list allowed |
| `goalies[]` | boxscores ⋈ Finn set | see below | empty list allowed |

`gamesCompleted` lets the page tell "no games last night" from "no Finn points".

**Inclusion (ADR-012):** a Finnish skater with `points ≥ 1`, and a Finnish goalie who **started**
(the boxscore's starter field, verify). A Finn with 0 points is not listed. A relief goalie who
didn't start is not listed.

`lastNight.skaters[]`:
| Field | Source | Units / type | Nullable |
|---|---|---|---|
| `playerId` | boxscore | int | no |
| `firstName`, `lastName` | P0.6 name source, joined by `playerId` (boxscore names are initials, ADR-018) | `{default, fi?}` | no |
| `team` | boxscore side | abbrev | no |
| `g`, `a`, `p`, `pm`, `sog`, `pim` | boxscore | int | no (`sog`, `pim`: yes if absent) |
| `toi` | boxscore `toi` | **int seconds** | yes |
| `game` | see `game` object below | object | no |

`lastNight.goalies[]`:
| Field | Source | Units / type | Nullable |
|---|---|---|---|
| `playerId`, `firstName`, `lastName`, `team` | as above | | no |
| `saves`, `shotsAgainst` | boxscore (verify field names; may be a `"SV/SA"` string) | int | yes |
| `svPct` | boxscore `savePctg` | fraction 0–1 | yes (no shots, ADR-015) |
| `decision` | boxscore `decision` | `W`/`L`/`O` as given (verify values) | yes (ADR-015) |
| `toi` | boxscore | **int seconds** | yes |
| `game` | see below | object | no |

`game` object (the same game appears once per Finn in it):
| Field | Source | Units / type | Nullable |
|---|---|---|---|
| `gameId` | boxscore `id` | int | no |
| `home` | Finn's team is the home side | bool | no |
| `opponent` | other side `abbrev` | string | no |
| `teamScore`, `oppScore` | boxscore | int | no |
| `result` | derived from the Finn's team: `W` / `L` / `OTL` | string | no |
| `decidedIn` | `REG` / `OT` / `SO` from the boxscore's last-period field (verify) | string | yes |

Row order: skaters by `p` desc, `g` desc, `lastName.default` asc; goalies by `svPct` desc (nulls
last), then `lastName.default`. The page re-sorts as it likes.

### `skaters[]` (every Finnish skater in the bios set; ADR-030, the same columns as `/bolts`)
| Field | Source → path | Units / type | Nullable |
|---|---|---|---|
| `playerId` | bios | int | no |
| `firstName`, `lastName` | P0.6 name source | `{default, fi?}` | no |
| `team` | current team (verify field: bios `currentTeamAbbrev`, or the last of summary `teamAbbrevs`) | abbrev | yes (unsigned/free agent) |
| `positionCode` | bios | `C`/`L`/`R`/`D` | no |
| `rookie` | see Rookie below | bool | yes |
| `gp`, `g`, `a`, `p`, `pm`, `pim` | skater summary `gamesPlayed`, `goals`, `assists`, `points`, `plusMinus`, `penaltyMinutes` | int | yes (not in summary) |
| `toiPerGame` | summary `timeOnIcePerGame` | **int seconds** (verify units) | yes |
| `sog` | summary `shots` | int | yes |
| `shootingPct` | summary `shootingPct` | fraction 0–1 (verify not ×100) | yes (0 shots) |
| `ppg`, `shg`, `gwg` | summary `ppGoals`, `shGoals`, `gameWinningGoals` | int | yes |
| `ppp` | summary `ppPoints` | int | yes |
| `faceoffPct` | faceoff report; `null` when `totalFaceoffs == 0` (ADR-035) | fraction 0–1 | yes |
| `hits`, `blocks` | realtime `hits`, `blockedShots` | int | yes |

**Bios defines the row set** (ADR-011). A Finn missing from summary, realtime or faceoff keeps the
row with those fields `null`. Never drop a row (ADR-030, ADR-035 join rule).

### `goalies[]` (every Finnish goalie in the goalie bios set)
| Field | Source | Units / type | Nullable |
|---|---|---|---|
| `playerId`, `firstName`, `lastName`, `team`, `rookie` | as skaters | | as skaters |
| `gp`, `gs`, `w`, `l`, `otl`, `so` | goalie summary `gamesPlayed`, `gamesStarted`, `wins`, `losses`, `otLosses`, `shutouts` (verify names) | int | yes |
| `svPct` | goalie summary `savePct` | fraction 0–1 | yes (no shots) |
| `gaa` | goalie summary `goalsAgainstAverage` | float | yes |
| `toi` | goalie summary `timeOnIce` | **int seconds total** (verify units) | yes |

### Rookie
Prefer an NHL-provided rookie field or filter (e.g. `isRookie` in the stats REST rows or in
`cayenneExp`; verify). If none exists, fall back to `firstSeasonForGameType == season` from bios,
and ADR-037 records that this means "first NHL regular season", which is close to but not the
NHL's official rookie rule. Either way the output field is `rookie: bool | null`.

### Traded Finns
On this page a player's stats are **season totals across all teams**. That's the natural reading
for a per-player page, and it's the opposite of `/bolts`, where club-stats is TBL-only (ADR-035).
`team` is the player's current team. The PRP confirms what league-wide summary rows look like for
a traded player (one aggregated row with `teamAbbrevs: "A,B"`, or one row per team). If it's one
row per team, sum them and take `team` from the current team, and say so in ADR-037.

- **No headshots or logos** (ADR-003).
- **schemaVersion**: new file, `1`.
- **S3 keys written**: `data/kiekkokeskus/leijonat.json`, the new raw objects under `raw/`, and
  `_health.json` (now with `"leijonat"` in `built`).

## Fixtures and Gotchas

Copy **one real run's raw archive** from a game day where a Finn scored, so every payload is from
the same day. Add the variants below.

| Fixture | Why | Gotcha rows (ADR) |
|---|---|---|
| one day's bios (both), four new FIN stats REST payloads, schedule, standings, every boxscore | golden build | 011, 014, 017, 018, 030 |
| bios row for Kapanen (`FIN`/`SWE`), present in the real bios | included as a Finn | 010 |
| bios forced to small `limit` (multi-page), or a synthetic two-page split | all `total` rows, no dupes; a duplicate `playerId` raises | 011 |
| boxscore with a Finn skater who scored (Tolvanen, 2026-10-01, existing if captured) | Finn found by `playerId`; non-Finns excluded | 012 |
| boxscore with a Finn skater on 0 points and a Finnish starting goalie (real if the archive has one, else a variant) | skater excluded, goalie included | 012 |
| boxscore variant `__goalie-no-shots` (existing per TESTING) | `svPct`/`decision` → `null` | 015 |
| boxscore whose game went to OT or SO (real if available, else a variant) | `decidedIn` and `result: OTL` | 037 |
| summary variant `__player-missing` (one Finn removed) | row kept, stats `null` | 035 |
| summary variant `__traded` (synthetic, in whichever shape the PRP observed) | totals summed or passed through; `team` = current | 037 |
| a schedule for a date with no completed regular-season games | `lastNight` empty, `gamesCompleted: 0`, no crash | 012, 014 |

**Golden test (layer 2):** the fixture set plus a fixed `dataDate` produce
`tests/golden/leijonat.json`. Review any diff in the commit.

**Unit assertions:** every fraction is 0–1 or null, every TOI is an `int`, every name is an
object, every `skaters[]`/`goalies[]` row has `positionCode`, and the count of output rows equals
the bios `total`s.

## Ownership Check

- **AWS resources created or changed**: Lambda code only
- **S3 prefixes written**: `data/kiekkokeskus/leijonat.json`, `data/kiekkokeskus/raw/…`,
  `data/kiekkokeskus/_health.json`
- **Touches anything owned by the main site?** No

## Success Criteria

- [ ] The four FIN endpoints are verified, archived, guarded by `check_complete`, and in the
      manifest
- [ ] ADR-037 is in DECISIONS-DATA.md, with gotcha-matrix rows added to TESTING.md
- [ ] Layer-1 tests for `bios.py`, `boxscore.py` and the stats REST additions, and the layer-2
      golden `leijonat.json`, pass with coverage ≥ 80%
- [ ] Orchestration tests: bolts fails → `leijonat.json` written, no health, raises; leijonat
      fails → `bolts.json` written, no health, raises
- [ ] `cdk diff` shows only the Lambda code change
- [ ] After a manual invoke, `https://jurigregg.com/data/kiekkokeskus/leijonat.json` serves with
      `max-age=300`. Spot-check against NHL.com: the Finn count, one last-night line, one skater
      season line, and one goalie line
- [ ] Umlaut names are present (or the Known Issue is logged, per P0.6)
- [ ] `smoke.py` checks `leijonat.json`
- [ ] No code file over 500 lines (ADR-034). `handler.py` is the one to watch; split the build
      phase into its own module if it gets close

## Out of Scope

- The `/leijonat` page (init-08)
- History and trends (init-09)
- Finns who haven't appeared this season, e.g. injured all year (ADR-011, accepted)
- Finns outside the NHL (AHL, Liiga)
- Goal-by-goal detail for last night (who assisted on what, game-winning goal flags)
- Headshots and logos (ADR-003)
- A hand-maintained name map (P0.6)

## Verify in PRP

- [ ] `nationalityCode="FIN"` works in `cayenneExp` on `skater/summary`, `skater/realtime`,
      `skater/faceoffpercentages` and `goalie/summary` together with `gameTypeId=2` and
      `seasonId`. Record each `total` and check it against the bios `total`
- [ ] Bios today have no `gameTypeId` filter. Does that let in Finns who only played preseason?
      If yes, add `gameTypeId=2` to the bios URL and record it in ADR-037
- [ ] Name sources, in the P0.6 order: which one gives Määttä/Teräväinen/Meriläinen
- [ ] The current-team field (bios `currentTeamAbbrev`? summary `teamAbbrevs`?) and how a traded
      player's summary rows look
- [ ] Rookie: an `isRookie` field or filter, or only `firstSeasonForGameType`
- [ ] Summary units: `timeOnIcePerGame` (seconds?), `shootingPct` (fraction?), goalie `savePct`
      and `timeOnIce`
- [ ] Boxscore: the goalie starter field, the saves/shots-against shape, `decision` values, the
      OT/SO field, and skater `sog`/`pim` field names

## Open Questions

(none)

## Notes

- Suggested commits:
  1. `feat(05): FIN stats REST endpoints in manifest`
  2. `feat(05): bios and boxscore parsers`
  3. `feat(05): build_leijonat + golden`
  4. `feat(05): independent builders in handler`
  5. `feat(05): smoke checks leijonat.json`

  P0.6's club-stats fan-out, if it's needed, is its own commit after 1. Then deploy and invoke,
  followed by `docs(05): ADR-037, TESTING, PLANNING, TASK`.
- Finnish players on TBL appear on both pages with possibly different numbers after a trade
  (season totals here, TBL-only there). That's by design; see "Traded Finns".
