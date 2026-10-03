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

Example: Eetu Tolvanen (NYR) scored 2026-10-01 against TBL. That game appears on both pages.

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

## Appendix: Observed State, 2026-10-02

These are not decisions. They give the first fixtures context.
- Season `20262027` started 2026-10-01.
- TBL is 0-1-0 after losing 5-1 at NYR, and sits 30th in the league.
- The Lightning arena is listed as "Benchmark International Arena".
- The TBL season schedule is large (about 82 games, each with ticket, radio, and promo links).
  Store it raw and extract the few fields used.
