# Kiekkokeskus - Data Decisions (NHL payloads)

Part of the ADR log; numbering is global, see [DECISIONS.md](DECISIONS.md). These entries define
what the data means and where the payloads lie. Every gotcha here is a required fixture case
(TESTING.md): a test that only feeds well-formed rows passes and means nothing.

Unless an entry says otherwise, every payload claim is from a real response fetched 2026-10-02.

---

## ADR-010: A "Finn" is `nationalityCode == "FIN"`

**Date**: 2026-10-02
**Status**: Accepted

### Context
`birthCountryCode` is the wrong field: Oliver Kapanen (MTL) is `nationalityCode: FIN`,
`birthCountryCode: SWE`.

### Decision
Use nationality, which matches how Finnish media counts NHL players. The page states the
definition in one line.

---

## ADR-011: The Finn roster comes from the stats REST bios endpoints

**Date**: 2026-10-02
**Status**: Accepted

### Decision
Make two queries, paginating with `limit`/`start` and reading `total` from each response:
- `api.nhle.com/stats/rest/en/skater/bios?cayenneExp=seasonId=<id> and nationalityCode="FIN"`
- the same query against `goalie/bios`. Goalies are a separate endpoint.

Observed totals: 55 skaters for 2025-26, and 4 goalies so far in 2026-27.

### Consequences
**Negative:** only players who have **appeared this season** are listed, so a Finn who is injured
or scratched all season is invisible. That is accepted and documented so it isn't rediscovered as
a bug.

---

## ADR-012: "Last night" is boxscores joined against the Finn set

**Date**: 2026-10-02
**Status**: Accepted

### Context
Boxscores carry no nationality.

### Decision
1. Get yesterday's games (ET date) from the schedule.
2. Keep only completed games (ADR-013).
3. Fetch `gamecenter/{id}/boxscore`.
4. Walk `playerByGameStats.{awayTeam,homeTeam}.{forwards,defense,goalies}`.
5. Join on `playerId` against the ADR-011 set.

Example: Eeli Tolvanen (NYR) scored 2026-10-01 against TBL. That game appears on both pages.

---

## ADR-013: Completed means `gameState ∈ {OFF, FINAL}`

**Date**: 2026-10-02
**Status**: Accepted

### Context
Observed values are `FUT`, `FINAL` (preseason), and `OFF` (the 2026-10-01 regular-season game).
Community docs also list `PRE`, `LIVE`, and `CRIT`, which are unverified.

### Decision
`OFF` and `FINAL` both mean done. Anything else is treated as not done, and an unrecognized value
is logged rather than guessed at.

---

## ADR-014: Regular season only, `gameType == 2`

**Date**: 2026-10-02
**Status**: Accepted

### Decision
The season schedule includes preseason games (`gameType: 1`), so every aggregate filters on type 2.
Playoffs (presumably type 3) get their own ADR when they matter.

---

## ADR-015: Absent fields are missing, not null

**Date**: 2026-10-02
**Status**: Accepted

### Context
- **Standings, teams with 0 GP:** `pointPctg`, `winPctg`, `regulationWinPctg`,
  `goalDifferentialPctg`, `goalsForPctg`, `streakCode`, and `streakCount` are omitted entirely.
- **Boxscore, goalies who faced no shots:** `savePctg` and `decision` are omitted.

### Decision
Parsers use `.get()` with explicit defaults. Our own output always emits the key, with `null` when
the value is absent (PLANNING data contract). Real early-October fixtures cover both cases.

---

## ADR-016: Several `*Pctg` fields are not percentages

**Date**: 2026-10-02
**Status**: Accepted

### Context
| Field | Actually is | Example |
|---|---|---|
| `goalsForPctg` | goals for per game | EDM 14 GF / 2 GP = `7.0` |
| `goalDifferentialPctg` | goal differential per game | |
| `pointPctg`, `winPctg`, `savePercentage`, `shootingPctg` | fractions 0–1 | |

### Decision
Nothing is ever ×100 in the data. Formatting happens once, in the page.

---

## ADR-017: Time on ice comes in two formats

**Date**: 2026-10-02
**Status**: Accepted

### Context
`club-stats` reports `avgTimeOnIcePerGame` as float **seconds** (`1447.0`). The boxscore reports
`toi` as a `"MM:SS"` **string** (`"24:07"`).

### Decision
Normalize both to integer seconds at parse time.

---

## ADR-018: Names are localized objects

**Date**: 2026-10-02
**Status**: Accepted

### Context
Names look like `{"default": "Kucherov", "fi": "Kutsherov", "cs": …}`, and most carry only
`default`. Boxscores give initials only (`"N. Kucherov"`).

### Decision
Full names come from club-stats or bios. Builders pass `{default, fi?}` through unchanged and never
pick a language (ADR-028).

---

## ADR-019: `/leijonat` language and name rendering

**Date**: 2026-10-02
**Status**: Superseded by ADR-028

### Context
Rendering `name.fi ?? name.default` fits a Finnish page. On an English page, Kucherov would show as
"Kutsherov", which is wrong there.

---

## ADR-033: Season from the schedule's games (and standings fallback), not `currentSeason`

**Date**: 2026-10-03
**Status**: Accepted. **Partially supersedes ADR-008**.

### Context
ADR-008 directs the collector to resolve the season from `currentSeason` in a schedule payload.
Fetching `schedule/{YYYY-MM-DD}` (`api-web.nhle.com/v1`) on 2026-10-03 (and verified across
multiple dates) shows that payload has **no `currentSeason` field**. Its top-level keys are
`nextStartDate`, `previousStartDate`, `gameWeek`, `oddsPartners`, `preSeasonStartDate`,
`regularSeasonStartDate`, `regularSeasonEndDate`, `playoffEndDate`, `numberOfGames`. The returned
`gameWeek` is a **7-day window** starting at the requested date, not just that date.

### Decision
Resolve the season from the payloads we already fetch, in this order:
1. **Schedule**: `gameWeek[].games[].season` of any game whose `gameWeek.date == dataDate`.
2. **Standings fallback**: `standings[0].seasonId` from `standings/{dataDate}`. Standings is
   dated and doesn't need the season to fetch, so this fallback is cheap and reliable through
   short in-season gaps (e.g. All-Star break, bye days).
3. If both yield nothing: log, write `_manifest.json` with `season: null` and the error, raise.

For the boxscore join (ADR-012), filter `gameWeek` to the entry whose `date == dataDate` before
reading `games[]`.

### Partial supersession of ADR-008
ADR-008 remains in force on **method**: resolve from a payload, never compute; dated URLs,
never `/now`. ADR-033 only amends the **field name**: it is `games[].season` /
`standings[0].seasonId`, not `currentSeason`. CLAUDE.md Rule 2 and PLANNING update in the same
commit so later PRPs don't chase a field that doesn't exist.

### Consequences
**Positive:** reliable season resolution without a dedicated endpoint; a short in-season gap
doesn't fire an error alarm.
**Negative:** we rely on two payloads (schedule + standings) instead of one. Both are already
required by the collector, so no extra request.

### References
init-03-collector-core.md, prps/prp-03-collector-core.md

---

## ADR-035: Field sources for `bolts.json`

**Date**: 2026-10-09
**Status**: Accepted

### Context
`bolts.json` composes a single page view from multiple NHL endpoints. We fix the source of every
field once so future PRPs don't have to re-decide, and so init-05 can reuse the same parsers.

### Decision — source map

| Section / field | Source payload | Field |
|---|---|---|
| `team.abbrev` | constant | `"TBL"` |
| `team.name` | standings | row `teamName` (localized) |
| `standing.{gp,w,l,otl,pts,gf,ga}` | standings | TBL row integers |
| `standing.pointPct` | standings | `pointPctg` (fraction 0–1 or `null` at 0 GP, ADR-015) |
| `standing.streak` | standings | `{code, count}` from `streakCode`/`streakCount`; `null` at 0 GP |
| `standing.{division,conference}` | standings | `{abbrev, rank}` from `*Abbrev` + `*Sequence` |
| `standing.leagueRank` | standings | `leagueSequence` |
| `standing.divisionLead` | standings | ADR-036 definition |
| `standing.playoffLine` | standings | ADR-036 definition |
| `lastGame.*` | club-schedule-season | last game with `gameType==2` and `gameState∈{OFF,FINAL}` and `date≤dataDate`; `decidedIn` from `gameOutcome.lastPeriodType` |
| `nextGames[]` | club-schedule-season | first 3 games with `gameType==2` and `date>dataDate`, ascending |
| `specialTeams.ppPct`/`pkPct` | team-summary | `powerPlayPct`/`penaltyKillPct` (fractions 0–1) |
| `specialTeams.ppRank`/`pkRank` | team-summary | standard competition ranking (1-2-2-4) over teams with `gp>0`, 1=best |
| skater integers (`gp,g,a,p,pm,pim,sog,ppg,shg,gwg`) | club-stats | passed through |
| `shootingPct` | club-stats | `shootingPctg` (`null` when `shots==0`, ADR-015) |
| `toiPerGame` | club-stats | `avgTimeOnIcePerGame` → int seconds (ADR-017) |
| `ppp` | stats REST `skater/summary` | `ppPoints`; `null` when the player is missing from summary |
| `hits`, `blocks` | stats REST `skater/realtime` | `hits`, `blockedShots`; `null` when missing |
| `faceoffPct` | stats REST `skater/faceoffpercentages` | **`null` when `totalFaceoffs == 0`**, else `faceoffWinPct` |
| goalie integers (`gp,gs,w,l,otl,so`) | club-stats | `overtimeLosses` → `otl` |
| `svPct`, `gaa`, `toi` | club-stats | `savePercentage`, `goalsAgainstAverage`, `timeOnIce` (int total seconds, ADR-017). `null` for goalies who faced no shots (ADR-015). |

### Faceoff rule
`skater/faceoffpercentages` carries `totalFaceoffs` (attempts). This is the only field that
distinguishes "took no faceoffs" from "won 0 %". **Rule**: `faceoffPct = null` when
`totalFaceoffs == 0`; else `faceoffWinPct` as-is (fraction 0–1).
**Fallback** (if the endpoint disappears): `null` when `positionCode == 'D'` OR
`faceoffWinPctg == 0.0`.

### Traded players (asymmetry)
club-stats returns **TBL-only** stats for every TBL skater. The three TBL-filtered stats REST
endpoints (summary/realtime/faceoff) may include **other-team season totals** for a player who
played elsewhere earlier in the season — the `teamAbbrevs` filter chooses rows, not stat
subsets. On 2026-10-09 there were no mid-season trades to confirm this against. **Re-verify at
first TBL trade** (TASK.md Known Issue).

### Join resilience
`club_stats.skaters(...)` is authoritative on the row set. A player missing from any stats REST
side keeps the row, with `ppp`/`hits`/`blocks`/`faceoffPct` as `null`. Never drop a row.

### Pagination guard
`stats_rest.check_complete(payload, slug)` raises `StatsRestTruncated` when
`total > len(data)`. Called after each stats REST fetch. The TBL roster (~20) and 32-team
league are well under `limit=1000`; the guard fails loudly if NHL ever returns a partial page.

### Dropped fields
- `headshot`, `teamLogo`, `teamLogoDark`: ADR-003 (browser never calls NHL hosts).
- Goal scorers for the last game: needs the game's `landing`/play-by-play; deferred.

### References
init-04-bolts-json.md, prps/prp-04-bolts-json.md

---

## ADR-036: Standings definitions for `bolts.json`

**Date**: 2026-10-09
**Status**: Accepted

### Decision

**Division lead** (`standing.divisionLead`): the team with `divisionSequence == 1` in TBL's
division. Fields:
- `leader`: that team's `teamAbbrev.default` (equal to `"TBL"` when TBL leads).
- `leaderPts`: that team's `points`.
- `gap`: `leaderPts - TBL.pts`. **Signed int.** `0` when TBL leads by tiebreaker with equal
  points. **Never `abs()`-ed.**
- `gamesInHand`: `leaderGP - TBL.gp`. Negative when TBL has played more.

**Playoff line** (`standing.playoffLine`): depends on whether TBL holds a playoff position.
- *In position* (`divisionSequence ≤ 3` OR `wildcardSequence ∈ {1, 2}`): reference team is the
  conference's `wildcardSequence == 3` team.
  - `inPosition: true`
  - `gap = TBL.pts - reference.pts`. Signed; positive = cushion.
- *Out of position*: reference team is the conference's `wildcardSequence == 2` team.
  - `inPosition: false`
  - `gap = reference.pts - TBL.pts`. Signed; positive = deficit.
- Either case: `gamesInHand = reference.gp - TBL.gp`. **Signed; never `abs()`-ed.**

**Both `gap` values can be `≤ 0`** when standings order comes from tiebreakers (equal points
but the other team ranks higher by a tiebreaker, or TBL ranks higher despite trailing on points).
Preserve the sign; the page renders a signed `+N / 0 / -N` string.

### Observed 2026-10-09
Across all four divisions, `divisionSequence ∈ {1, 2, 3}` → `wildcardSequence == 0`;
`divisionSequence ∈ {4, ...}` → `wildcardSequence ∈ {1, 2, 3, ...}`. TBL (Atlantic #2) today has
`divisionLead.gap = 0, gamesInHand = 0` behind OTT; `playoffLine.inPosition = true` with
reference NYI (`wildcardSequence == 3`), `gap = +2` cushion.

**Special-teams ranks** (`specialTeams.ppRank`/`pkRank`): standard competition ranking
(1-2-2-4) over teams with `gamesPlayed > 0`. Rank 1 = best. Ties share a rank; the next rank
skips.

### References
init-04-bolts-json.md, prps/prp-04-bolts-json.md

---

## ADR-037: Field sources for `leijonat.json`

**Date**: 2026-10-10
**Status**: Accepted

### Context
`/leijonat` lists every Finnish player in the NHL — their season rows across all teams, plus
last night's performances. The naming is tricky: stats REST ASCII-fies most Finnish names
(`Olli Maatta`, `Teuvo Teravainen`) with occasional umlauts (`Aatu Räty`), so we need a reliable
source for `Määttä`/`Teräväinen`/`Meriläinen` etc. The rookie flag has no inline field but
`isRookie=1` works as a cayenneExp filter.

### Decision — source map

| Section / field | Source | Notes |
|---|---|---|
| Row set | `skater/bios` + `goalie/bios` with `nationalityCode="FIN"` (ADR-011) | ADR-030 full rows; never drop a Finn |
| Season skater integers (`gp,g,a,p,pm,pim,sog,ppg,shg,gwg,ppp`) | FIN-filtered `skater/summary` | fractions / `None` on absent fields per ADR-015 |
| `toiPerGame` | summary `timeOnIcePerGame` → **int seconds** | float input, ADR-017 |
| `shootingPct` | summary `shootingPct` | fraction 0–1 (ADR-016) |
| `faceoffPct` | FIN-filtered `skater/faceoffpercentages` → `null` when `totalFaceoffs == 0` | ADR-035 rule reused |
| `hits`, `blocks` | FIN-filtered `skater/realtime` → `hits`, `blockedShots` | |
| `rookie` | separate 1-page fetch with `cayenneExp ... and isRookie=1` → ID set; `playerId in rookie_ids` | **non-null bool**; failed rookie fetch fails the run (CLAUDE.md "never silently catch") |
| `team` | **bios `currentTeamAbbrev`** | string; summary `teamAbbrevs` not used (see "Traded Finns" below) |
| `positionCode` | bios | C/L/R/D |
| Goalie integers (`gp,gs,w,l,otl,so`) | FIN-filtered `goalie/summary` | field names on NHL side are literal |
| `svPct`, `gaa`, `toi` | goalie summary `savePct`, `goalsAgainstAverage`, `timeOnIce` | fraction / float / int total seconds |
| `teams[].name` | standings `teamName` (localized `{default, fr?}`, no `fi` observed) | |
| `lastNight.gamesCompleted` | **`schedule.gameWeek` filtered to `date == dataDate`** first (ADR-033 — 7-day window), then `gameType == 2 and gameState ∈ {OFF, FINAL}` | Fix 6 |
| `lastNight.skaters[]` | boxscore skaters ⋈ Finn set, `points ≥ 1` (ADR-012) | |
| `lastNight.goalies[]` | boxscore goalies ⋈ Finn set, `starter == True` (ADR-012) | relief goalies excluded |
| `game.result` | **derived from score + `gameOutcome.lastPeriodType`**: `me > opp` → W; `me < opp` and `lastPeriodType ∈ {OT, SO}` → OTL; else L | **Never from goalie `decision`** — that field is passed through raw |
| `game.decidedIn` | `gameOutcome.lastPeriodType` | REG / OT / SO / None |

### Name resolution per `playerId` (Fix 4)
Primary stats REST sources ASCII-fy most Finnish names. Resolve names in this order:

1. **Scan every club-stats payload** in `bodies["club-stats-by-team"]` (not just the Finn's
   current team's) — catches a just-traded Finn who still sits in the old team's roster.
   club-stats carries `firstName` and `lastName` as localized objects with `fi`/`cs`/`sk`/`sv`
   keys where available (verified: `MIN.Maatta → {default: "Maatta", fi: "Määttä"}`;
   `CHI.Teravainen → fi: "Teräväinen"`).
2. **Fallback** via bios: use `bios.lastName` as `{default}`; take `*FullName` and check that it
   ends with `" " + lastName`; if so, strip that suffix and emit `firstName: {default: stripped}`.
   Log a warning with the `playerId` and `source: "bios_suffix_strip"`.
3. **Suffix mismatch** → raise `NameSuffixMismatch`. Payload surprise; whole run fails;
   same posture as `BiosDuplicateError` (ADR-011).

Resolved names are localized `{default, fi?, ...}` objects (ADR-018). Builder never picks a
language (ADR-028).

### Fan-out failure trade-off
The 24 extra fetches init-05 adds (4 FIN stats REST + 2 rookie + ~18 club-stats fan-out) are
**each a new way the whole run can fail**: any single failed fetch marks the manifest row with
an error, which short-circuits the `had_error` check so **neither builder runs** and neither
page updates. Accepted for now because:
- The collector retries 3× with exponential backoff on each endpoint (ADR-035).
- A full-run failure fires the alarm (ADR-032) and yesterday's `bolts.json`/`leijonat.json`
  stay live (versioning + `max-age=300` cache).

**Revisit** if a single team's club-stats regularly fails a run — a candidate change is to let
the name fallback cover a missing team's payload instead, but today that risks silent
wrong-name output on a trade day.

### Traded Finns
Season totals **across all teams** (opposite of ADR-035's TBL-only stance on `/bolts`). The
natural reading for a per-player page is "what did this player do this season". `team` field
is `bios.currentTeamAbbrev`. The multi-team shape of stats REST `teamAbbrevs` (e.g.
`"A,B"` for a traded player, or multiple rows) is **unknown today** — no FIN mid-season trade
to confirm. Watch item in TASK.md Known Issues; re-verify at the first FIN trade.

### Preseason-only Finns
Verified 2026-10-10: bios **without** `gameTypeId` filter returns the same 30 FIN skaters as
with `gameTypeId=2`. Explicit `gameTypeId=1` returns 0. No URL change needed.

### Reference fixtures
- **OT**: real captured boxscore `2026020025__2026-10-10.json.gz` (CAR @ PHI, 2026-10-03;
  `gameOutcome.lastPeriodType == "OT"`).
- **SO**: real captured boxscore `2026020065__2026-10-10.json.gz` (TOR @ VGK, 2026-10-08;
  `gameOutcome.lastPeriodType == "SO"`).

No hand-mutated variants for OT/SO.

### Bios pagination
A duplicate `playerId` across pages raises `BiosDuplicateError` (ADR-011) — no silent dedupe.

### References
init-05-leijonat-json.md, prps/prp-05-leijonat-json.md

---

## ADR-041: Division runner-up in `bolts.json`

**Date**: 2026-10-12 · **Status**: Accepted · **extends ADR-036**

### Decision
- `standing.divisionLead.runnerUp` is the team with `divisionSequence == 2` in Tampa's
  division. Fields: `team` (abbrev), `pts` (int), `gamesInHand` (`runnerUp.gp − TBL.gp`,
  signed, same orientation as ADR-036's other `gamesInHand` fields; never `abs()`-ed).
- Always populated in-season (divisionSequence runs 1..n with no gaps across every captured
  standings fixture, verified 2026-10-12). When Tampa is at seq=2, `runnerUp.team == 'TBL'`
  and the page uses that as the signal to fall back to today's rendering.
- **No `gap` field inside `runnerUp`.** The page computes `standing.pts − runnerUp.pts`
  itself. This avoids introducing a third sign convention alongside ADR-036's two
  (`divisionLead.gap = leader − TBL` and `playoffLine.gap` whose sign depends on
  `inPosition`).
- Additive field — no `schemaVersion` bump (ADR-035 convention).

### Verified live 2026-10-12
After the manual invoke, `https://jurigregg.com/data/kiekkokeskus/bolts.json` carries
`standing.divisionLead.runnerUp: { team: 'OTT', pts: 8, gamesInHand: 0 }`. TBL is tied with
OTT on points (both 8/5), first by tiebreaker, so the live tile renders value `'0'` + sub
`'OTT · 8 pts'` (EN) / `'OTT · 8 p'` (FI) — meaningful information instead of the previous
tautology `'TBL · 8 pts'`.

### Consequences
**Positive:** the `/bolts` division tile has a meaningful value in every standings state —
including the common "team leads its division" case that pre-init-10 showed as a tautology.
**Negative:** none observed. Adding a field doesn't break readers (the only consumer today
is `/bolts/view.js`, which reads it optionally).

### References
initials/init-10-bolts-runner-up.md, prps/prp-10-bolts-runner-up.md,
src/kiekkokeskus/parse/standings.py (`division_runner_up`),
src/kiekkokeskus/build_bolts.py (`_division_lead`),
site/bolts/view.js (`divisionLeadTile`), ADR-036

---

These are not decisions. They give the first fixtures context.
- Season `20262027` started 2026-10-01.
- TBL is 0-1-0 after losing 5-1 at NYR, and sits 30th in the league.
- The Lightning arena is listed as "Benchmark International Arena".
- The TBL season schedule is large (about 82 games, each with ticket, radio, and promo links).
  Store it raw and extract the few fields used.
