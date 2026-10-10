# init-04: bolts.json Builder

**Created**: 2026-10-09
**Phase**: 2 Data
**Depends On**: init-03 (collector core, raw archive, `__` slugs)
**ADRs**: ADR-003, 006, 008/033, 012–018, 020, 022, 030, 032; adds ADR-035, ADR-036 (DECISIONS-DATA.md)

---

## Problem Statement

The collector archives raw NHL data every morning, but nothing turns it into what `/bolts` needs.
The page layout is sketched in the "Kiekkokeskus page layouts" canvas. This spec produces the one
JSON file that page reads, with every field sourced and every unit fixed, so init-07 is pure
rendering.

## Goal

Each successful daily run writes `data/kiekkokeskus/bolts.json`. It's built from that run's
already-archived payloads and contains standings position and gaps, last game, next three games,
special teams with league rank, and full skater and goalie rows with the ADR-030 columns. A build
failure fails the run loudly and leaves yesterday's `bolts.json` in place.

## Requirements

### Must Have (P0)

1. **New endpoints in the manifest.** Exact URLs and filters to be verified in the PRP. All are
   archived raw before parsing (ADR-006), with `__` slugs.

   | Slug | Endpoint | Why |
   |---|---|---|
   | `skater-summary-TBL__{season}` | stats REST `skater/summary`, TBL, `gameTypeId=2`, season | PPP (and cross-check of club-stats) |
   | `skater-realtime-TBL__{season}` | stats REST `skater/realtime`, same filter | hits, blocks |
   | `team-summary__{season}` | stats REST `team/summary`, all teams, `gameTypeId=2`, season | PP%, PK% and league rank |

   Existing endpoints this spec reads: `standings__{dataDate}`, `club-stats-TBL__{season}__2` and
   `club-schedule-season-TBL__{season}`.

2. **Parsers** (`src/kiekkokeskus/parse/`, pure, one module per endpoint family):
   - **`standings.py`**: extend it to return one normalized row per team. Fields: `team`,
     `gamesPlayed`, `wins`, `losses`, `otLosses`, `points`, `pointPctg`, `goalFor`, `goalAgainst`,
     `divisionAbbrev`, `conferenceAbbrev`, `divisionSequence`, `conferenceSequence`,
     `leagueSequence` and `wildcardSequence`. Any field missing at 0 GP becomes `None` (ADR-015).
   - **`club_stats.py`**: skater and goalie rows from `club-stats`. TOI floats become int seconds
     (ADR-017). Names stay localized objects (ADR-018).
   - **`stats_rest.py`**: summary, realtime and team-summary rows, keyed by `playerId` or team. It
     must be reusable by init-05 for the FIN filter.
   - **`club_schedule.py`**: regular-season games (`gameType == 2`, ADR-014), each with id, ET
     date, start time UTC, home/away, opponent, state and score. The OT/SO outcome comes from
     whatever field the payload carries (verify).

3. **Builder** (`src/kiekkokeskus/build_bolts.py`, pure: parsed inputs + `dataDate` → dict). It
   does no I/O and never reads the clock.

4. **Handler**: a **build phase** after archiving and the manifest, before `_health.json`.
   - It builds from the bodies fetched in **this run**, held in memory, and doesn't re-read S3.
   - If the build succeeds, it writes `bolts.json` with `Cache-Control: public, max-age=300`
     (ADR-022). Then it writes the health file, which gains `built: ["bolts"]`. That addition is
     additive, so the schemaVersion stays 1.
   - **On build failure it doesn't write `bolts.json` or the health file, logs the error and
     raises.** Raw data and the manifest are already safe, so the day can be rebuilt.
   - The build must not run if any fetch failed. That's existing behaviour, and it stays.

5. **Smoke** (`scripts/smoke.py`): `bolts.json` returns 200, `schemaVersion == 1`, `dataDate` is
   the health file's `dataDate`, the `Cache-Control` header contains `max-age=300`, and there's at
   least one skater row.

6. **ADRs** (DECISIONS-DATA.md):
   - **ADR-035: field sources for `bolts.json`.** It's the table below, as verified, including
     anything dropped and why.
   - **ADR-036: standings definitions.** "Gap to division lead", "playoff line" and the
     special-teams rank rule, exactly as below.

### Should Have (P1)

1. **`scripts/build_local.py --raw-dir <dir> --out <file>`** builds `bolts.json` from a local
   folder of raw objects, either copied from S3 or from the fixtures. init-06 and init-07 use this
   for page work without touching AWS.
2. **`scripts/rebuild.py --date YYYY-MM-DD`** re-invokes the collector for a date (ADR-009 makes
   standings for that date fetchable). It only exists if `scripts/rerun.py` from init-03 doesn't
   already cover it; if it does, document that and skip.

## Output / Data Contract: `data/kiekkokeskus/bolts.json`

Envelope: `schemaVersion: 1`, `generatedAt` (UTC Z), `dataDate` (ET date), `season`.

### `team`
| Field | Source → path | Units / type | Nullable |
|---|---|---|---|
| `abbrev` | constant `TBL` | string | no |
| `name` | standings `teamName` (localized) | `{default, fi?}` | no |

### `standing` (TBL row + derived; ADR-036)
| Field | Source → path | Units / type | Nullable |
|---|---|---|---|
| `gp`, `w`, `l`, `otl`, `pts` | standings → TBL row | int | no |
| `pointPct` | standings `pointPctg` | fraction 0–1 | yes (0 GP) |
| `gf`, `ga` | standings `goalFor`, `goalAgainst` | int | no |
| `streak` | standings `streakCode` + `streakCount` → `{code, count}` | object | yes (0 GP) |
| `division` | `{abbrev, rank}` from `divisionAbbrev`, `divisionSequence` | | no |
| `conference` | `{abbrev, rank}` from `conferenceAbbrev`, `conferenceSequence` | | no |
| `leagueRank` | `leagueSequence` | int | no |
| `divisionLead` | `{leader, leaderPts, gap, gamesInHand}` | ints; `gap` = leader pts − TBL pts (0 if TBL leads) | no |
| `playoffLine` | `{inPosition, team, teamPts, gap, gamesInHand}` (ADR-036) | | no |

**ADR-036 definitions:**
- *Division lead*: the team with `divisionSequence == 1` in TBL's division.
  `gamesInHand` = leader GP − TBL GP. It's negative when TBL has played more.
- *Playoff line*:
  - If TBL holds a playoff position (division rank ≤ 3, or `wildcardSequence` ∈ {1, 2}), then
    `inPosition: true`. The reference team is the conference's `wildcardSequence == 3` team, and
    `gap` = TBL pts − that team's pts, a positive cushion.
  - Otherwise `inPosition: false`. The reference team is the `wildcardSequence == 2` team, and
    `gap` = that team's pts − TBL pts, a positive deficit.
  - Either way `gamesInHand` = reference GP − TBL GP.
  - Verify in the PRP that `wildcardSequence` is 0 for division top-3 teams, as observed on
    2026-10-02.

### `lastGame` (null before TBL's first completed game)
| Field | Source | Units / type | Nullable |
|---|---|---|---|
| `gameId`, `date` (ET), `home` (bool), `opponent` `{abbrev, name}` | club schedule | | no |
| `tblScore`, `oppScore` | club schedule | int | no |
| `result` | derived: `W` / `L` / `OTL` | string | no |
| `decidedIn` | `REG` / `OT` / `SO` from the payload's last-period field | string | yes |

It's the latest regular-season game with `gameState ∈ {OFF, FINAL}` and date ≤ `dataDate`.

### `nextGames` (up to 3, may be empty)
| Field | Source | Units / type | Nullable |
|---|---|---|---|
| `gameId`, `date` (ET), `startTimeUTC` (ISO Z), `home`, `opponent` `{abbrev, name}` | club schedule | | no |

These are regular-season games with date > `dataDate`, in date order. Pages format the time and
language.

### `specialTeams`
| Field | Source | Units / type | Nullable |
|---|---|---|---|
| `ppPct`, `pkPct` | team summary → TBL | fraction 0–1 | yes (0 GP) |
| `ppRank`, `pkRank` | computed across teams with GP > 0; 1 = best; ties share a rank, standard competition ranking 1-2-2-4 (ADR-036) | int | yes |

### `skaters[]` (every skater in TBL club-stats; ADR-030, full rows)
| Field | Source → path | Units / type | Nullable |
|---|---|---|---|
| `playerId` | club-stats | int | no |
| `firstName`, `lastName` | club-stats (localized, ADR-018) | `{default, fi?}` | no |
| `positionCode` | club-stats | `C`/`L`/`R`/`D` | no |
| `gp`, `g`, `a`, `p`, `pm`, `pim` | club-stats | int | no |
| `toiPerGame` | club-stats `avgTimeOnIcePerGame` | **int seconds** | no |
| `sog` | club-stats `shots` | int | no |
| `shootingPct` | club-stats `shootingPctg` | fraction 0–1 | yes (0 shots) |
| `ppg`, `shg`, `gwg` | club-stats | int | no |
| `ppp` | skater summary `ppPoints` | int | yes (not in source) |
| `faceoffPct` | club-stats or summary, whichever distinguishes "took none" from 0 % (verify) | fraction 0–1 | **yes: null if no faceoffs taken** |
| `hits`, `blocks` | skater realtime `hits`, `blockedShots` | int | yes (not in source) |

The join is on `playerId`. club-stats defines the row set. A player missing from summary or
realtime gets `null` for those fields and is never dropped.

### `goalies[]` (every goalie in TBL club-stats)
| Field | Source | Units / type | Nullable |
|---|---|---|---|
| `playerId`, `firstName`, `lastName` | club-stats | | no |
| `gp`, `gs`, `w`, `l`, `otl`, `so` | club-stats | int | no |
| `svPct` | club-stats `savePercentage` | fraction 0–1 | yes (no shots, ADR-015) |
| `gaa` | club-stats `goalsAgainstAverage` | float | yes |
| `toi` | club-stats goalie TOI | **int seconds total** | yes |

- **No headshots or logos.** Image URLs point at NHL hosts, and ADR-003 means the browser never
  fetches from the NHL.
- **schemaVersion**: new file, `1`.
- **S3 keys written**: `data/kiekkokeskus/bolts.json`, plus the new raw objects under `raw/`.

## Fixtures and Gotchas

Copy **one real run's raw archive** (one `raw/<runDate>/` folder, so every payload is from the
same day) into fixtures with the `__captureDateET` suffix. Then add the variants below.

| Fixture | Why | Gotcha rows (ADR) |
|---|---|---|
| one day's `standings`, `club-stats-TBL`, `club-schedule-season-TBL`, three stats REST payloads | golden build | 014, 016, 017, 018 |
| `standings__2026-10-02__2026-10-03` (existing) | 0-GP teams with missing keys (OTT) | 015 |
| club-stats variant `__goalie-no-shots` (a goalie with `savePercentage`/`goalsAgainstAverage` removed) | null handling | 015 |
| realtime variant `__player-missing` (one TBL skater removed) | join keeps the row, `hits`/`blocks` null | 035 |
| club schedule from the current archive | preseason games present and excluded; FUT games feed `nextGames` | 014 |

**Golden test (layer 2):** the fixture set plus a fixed `dataDate` produce
`tests/golden/bolts.json`. Review any diff in the commit.

**Unit assertions:** every fraction is between 0 and 1 or null, every TOI is an `int`, every name
is an object, and no `bolts.json` field is ever the NHL's raw float TOI.

## Ownership Check

- **AWS resources created or changed**: Lambda code only
- **S3 prefixes written**: `data/kiekkokeskus/bolts.json`, `data/kiekkokeskus/raw/…`,
  `data/kiekkokeskus/_health.json`
- **Touches anything owned by the main site?** No

## Success Criteria

- [ ] All three new endpoints verified, archived, and listed in the manifest
- [ ] ADR-035 (field sources, as verified) and ADR-036 (definitions) are in DECISIONS-DATA.md,
      with gotcha-matrix rows added to TESTING.md
- [ ] Layer-1 tests for each new parser and layer-2 golden `bolts.json` pass, with coverage ≥ 80%
- [ ] Orchestration test: a build failure leaves no `bolts.json` and no health write, and raises
- [ ] `cdk diff` shows only the Lambda code change
- [ ] After a manual invoke, `https://jurigregg.com/data/kiekkokeskus/bolts.json` serves with
      `max-age=300`, and its numbers spot-check against NHL.com for record, rank, last game and
      one skater line
- [ ] `smoke.py` checks `bolts.json`
- [ ] TASK.md open question "hits and blocks source" is resolved, and "traded players" is
      updated with what the payloads showed
- [ ] No code file over 500 lines (ADR-034)

## Out of Scope

- Goal scorers for the last game. The mockup shows them, but they need the game's `landing` or
  play-by-play endpoint. Leave them for a later spec and drop them from the init-07 layout unless
  that spec lands first.
- Points-pace and cut-line history (init-09)
- Player headshots and team logos (ADR-003, and the trademark posture from ADR-002)
- `leijonat.json` (init-05). The `stats_rest.py` parser is built to be reused there.
- Rookie flags

## Verify in PRP

- [ ] The exact stats REST URLs and filter syntax for TBL-only `skater/summary` and
      `skater/realtime`: `teamAbbrevs` or `franchiseId` in `cayenneExp`, plus `gameTypeId=2` and
      `seasonId`. Record each response's `total`.
- [ ] Field names: `ppPoints` (summary), `hits` and `blockedShots` (realtime), `powerPlayPct` and
      `penaltyKillPct` (team summary). Check whether these come as fractions or ×100.
- [ ] How **traded players** appear: does club-stats show TBL-only stats, and does the team filter
      on summary/realtime give TBL-only stats or season totals? If they disagree, club-stats wins
      and the mismatch becomes an ADR.
- [ ] How faceoffs read: can a player who took none be told apart from one who won 0 %?
      (`faceoffWinPctg` 0 vs absent; is there a faceoffs-taken count anywhere?)
- [ ] The goalie TOI field name and units in club-stats
- [ ] Club schedule: the field that gives the OT/SO outcome, how home/away is expressed, the ET
      date field (`gameDate`), and the opponent name field
- [ ] Standings: that `wildcardSequence` is 0 for division top-3 teams, and the shape of the
      `teamName` localized object

## Open Questions

(none)

## Notes

- Suggested commits:
  1. `feat(04): stats REST endpoints in manifest`
  2. `feat(04): standings, club-stats, club-schedule, stats-rest parsers`
  3. `feat(04): build_bolts + golden`
  4. `feat(04): build phase in handler`
  5. `feat(04): smoke checks bolts.json`

  Then deploy and invoke, followed by `docs(04): ADR-035/036, TESTING, TASK`.
- Expect about 3 extra requests per run, so cost doesn't change.
