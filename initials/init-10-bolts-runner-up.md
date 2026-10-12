# init-10: Division Runner-Up for /bolts

**Created**: 2026-10-12
**Phase**: 3 Pages (follow-up)
**Depends On**: init-04 (`bolts.json` builder), init-07 (`/bolts` page)
**ADRs**: ADR-006, 015, 029, 035, 036, 039; adds ADR-041 (DECISIONS-DATA.md)

---

## Problem Statement

When Tampa leads its division, the division-lead tile on `/bolts` shows `0` and `TBL · 8 pts`,
which says nothing (TASK.md Known Issue from PRP-07). The useful number is Tampa's lead over
second place, but `bolts.json` doesn't carry the second-place team.

## Goal

`bolts.json` carries `standing.divisionLead.runnerUp`. When Tampa leads, the tile shows the lead
over that team, e.g. `+2` with `FLA · 6 pts`. When Tampa doesn't lead, the tile is unchanged.

## Requirements

### Must Have (P0)

0. **Spec number.** This is the first unplanned spec. Bump TASK.md's "next free number" from `10`
   to `11` in the first commit (ADR-029).

1. **Builder** (`build_bolts.py`, `parse/standings.py`). Add
   `standing.divisionLead.runnerUp`:
   - It's the team with `divisionSequence == 2` in Tampa's division, from the same `standings`
     payload the rest of `standing` uses. It's always populated, even when Tampa isn't first. If
     Tampa is second, `runnerUp` is Tampa itself. The data stays dumb; the page decides when to
     use it.
   - Fields: `team` (abbrev), `pts` (int), and `gamesInHand` (`runnerUp.gp − TBL.gp`, signed,
     never `abs()`-ed; same orientation as ADR-036's other `gamesInHand` fields).
   - **No `gap` field.** The page computes `standing.pts − runnerUp.pts`. That avoids adding a
     fourth sign convention next to ADR-036's two.
   - `null` only if no team has `divisionSequence == 2` in that division, which should never
     happen. The tile then falls back to today's rendering.

2. **Page** (`site/bolts/view.js`, `divisionLeadTile`). When `divisionLead.leader == "TBL"` and
   `runnerUp` is present and isn't `TBL`:
   - label: `tile.divLeader` (unchanged)
   - value: `signed(standing.pts − runnerUp.pts)`. It's `+N`, or `0` when Tampa leads on a
     tiebreaker with equal points.
   - sub: `{runnerUp.team} · {pts}` + games-in-hand clause from `runnerUp.gamesInHand`, using the
     existing `gihClause` (positive = Tampa has games in hand).

   Every other case (Tampa not leading, `runnerUp` null) renders exactly as today. **No new
   strings.**

3. **schemaVersion stays `1`.** Adding a field doesn't break readers: `/bolts` reads it
   optionally, and nothing else consumes `bolts.json`.

4. **Fixtures** (TESTING.md rules). A real standings payload where Tampa leads the Atlantic. Copy
   it from the production raw archive (rule 5), e.g. `raw/2026-10-10/standings__2026-10-10.json.gz`
   (live `/bolts` showed TBL leading on that data), into
   `tests/fixtures/standings__2026-10-10__<captureDate>.json.gz`. No hand edits. The existing
   golden (`standings__2026-10-08`, OTT leading, TBL second) stays as the "Tampa not leading"
   case.

5. **Golden.** `tests/golden/bolts.json` gains `runnerUp` (with today's golden that's TBL itself,
   since TBL is second). Review the diff in the commit. Nothing else in the golden changes.

6. **Deploy.** `cdk diff` should show only the Lambda code asset. `deploy.py --approved` deploys
   the Lambda, then runs the page syncs; only `bolts/view.js` should upload (dry run first, as
   always). After the next scheduled run, or a manual invoke, the live `bolts.json` carries
   `runnerUp`.

### Should Have (P1)

1. Remove the TASK.md Known Issue "Division-leader tile shows nothing useful when TBL leads" in
   the close-out commit.

## Output / Data Contract

| Field | Source → path | Units / type | Nullable |
|---|---|---|---|
| `standing.divisionLead.runnerUp.team` | standings → row with `divisionSequence == 2` in TBL's `divisionAbbrev` → `teamAbbrev.default` | abbrev | object nullable |
| `standing.divisionLead.runnerUp.pts` | same row → `points` | int | no (within object) |
| `standing.divisionLead.runnerUp.gamesInHand` | that row's `gamesPlayed` − TBL `gamesPlayed` | signed int | no (within object) |

- **schemaVersion change?** No (additive; see P0.3).
- **S3 keys written**: `data/kiekkokeskus/bolts.json` (Lambda, unchanged path); `bolts/view.js`
  (deploy).

## Fixtures and Gotchas

| Fixture to capture | Why | Gotcha rows (ADR) |
|---|---|---|
| `standings__2026-10-10__<capture>.json.gz` from the raw archive | Tampa leads the Atlantic; runner-up is another team | 036, 041 |
| existing `standings__2026-10-08__2026-10-09.json.gz` | Tampa second; `runnerUp` is TBL itself; tile unchanged | 041 |

New gotcha-matrix rows:

| Layer | Gotcha | Input | Assert |
|---|---|---|---|
| 1/2 builder | runner-up when Tampa leads | 2026-10-10 fixture | `runnerUp.team` ≠ `TBL`, `pts`/`gamesInHand` ints, `gamesInHand` signed |
| 1/2 builder | runner-up when Tampa is second | golden fixture | `runnerUp.team == "TBL"` |
| 5 page | lead over runner-up | synthetic: TBL leads, `standing.pts 8`, `runnerUp {FLA, 6, 0}` | value `+2`, sub `FLA · 6 pts` (FI `FLA · 6 p`) |
| 5 page | tied on points, Tampa first by tiebreaker | `runnerUp.pts == standing.pts` | value `0`, never `−0` |
| 5 page | runner-up has played fewer games | `runnerUp.gamesInHand: -1` | sub ends `· 1 more game played` |
| 5 page | `runnerUp` null or TBL itself while leading | defensive | today's rendering (`0`, `TBL · {pts}`) |
| 5 page | Tampa not leading | golden | tile byte-identical to today |

## UI

- **Strings**: none new.
- Everything else is unchanged.

## Ownership Check

- **AWS resources created or changed**: Lambda code only.
- **S3 prefixes written**: `data/kiekkokeskus/` (Lambda), `bolts/` (deploy).
- **Touches anything owned by the main site?** No.

## Success Criteria

- [ ] `pytest` (≥ 80%) green, with the builder tests for both fixtures; golden diff shows only
      the added `runnerUp`
- [ ] `node --test` (all three globs) green, with the page rows above
- [ ] `cdk diff` shows only the Lambda asset change; dry runs show only `bolts/view.js` uploading
- [ ] After a manual invoke, the live `bolts.json` has `runnerUp`, and `/bolts` in Chrome shows
      the lead tile correctly in EN and FI (compare against the live JSON, not the golden)
- [ ] ADR-041 in DECISIONS-DATA.md; TASK.md next free number is `11`; the Known Issue is removed
- [ ] No code file over 500 lines

## Out of Scope

- Any other tile change
- A "runner-up" or "lead" concept on `/leijonat`
- History of the lead (init-09)

## Verify in PRP

- [ ] `divisionSequence` values within a division are unique and run 1..n in the fixtures (ADR-036
      observed this; confirm for the new fixture).
- [ ] The 2026-10-10 raw standings really has TBL at `divisionSequence == 1`. If not, pick the
      latest raw date where it does and note it.

## Open Questions

(none)

## Notes

### Draft ADR-041: Division runner-up in `bolts.json`

**Date**: 2026-10-12 · **Status**: Accepted · extends ADR-036

**Decision**
- `standing.divisionLead.runnerUp` is the team with `divisionSequence == 2` in Tampa's
  division. Fields: `team`, `pts`, `gamesInHand` (`runnerUp.gp − TBL.gp`, signed).
- It's always populated, including when Tampa is second (then it's Tampa itself). The page
  decides when to show it.
- No `gap` field. The page computes `standing.pts − runnerUp.pts`. That avoids a third
  orientation alongside ADR-036's `divisionLead.gap` (leader − TBL) and `playoffLine.gap`
  (in/out-of-position dependent).
- Additive field, no `schemaVersion` bump.

**Consequences**: the `/bolts` division tile has a meaningful value in every standings state.
