# PRP-10: Division Runner-Up for /bolts

**Created**: 2026-10-12
**Initial**: `initials/init-10-bolts-runner-up.md`
**Status**: Complete
**ADRs relied on**: ADR-006, 015, 029, 035, 036, 039
**New ADRs this PRP adds**: **ADR-041** (`docs/DECISIONS-DATA.md`) — Division runner-up in `bolts.json`

---

## Overview

### Problem Statement
When Tampa leads its division, the `/bolts` division-lead tile shows `0` + `TBL · 8 pts`, which
is a tautology (TASK.md Known Issue, carried from PRP-07). The useful number is Tampa's lead
over the team that's second — but `bolts.json` doesn't carry that team today.

### Proposed Solution
Add `standing.divisionLead.runnerUp = { team, pts, gamesInHand }` to `bolts.json`, sourced
from the row with `divisionSequence == 2` in Tampa's division (same `standings` payload the
rest of `standing` already uses). The field is always populated — when Tampa is second it's
Tampa itself, and the page uses that as the signal to fall back to today's rendering.
`/bolts` adds one branch in `divisionLeadTile`: when `leader === 'TBL'` and `runnerUp.team !==
'TBL'`, render `signed(standing.pts − runnerUp.pts)` and `{runnerUp.team} · {pts}` plus the
existing games-in-hand clause. No new strings, no `schemaVersion` bump.

### Success Criteria
- [ ] `pytest` (≥ 80%) green, with new parser + builder tests for both fixtures; `tests/golden/
      bolts.json` diff shows **only** the added `runnerUp`
- [ ] `node --test` across all three globs green, with the new /bolts view gotcha rows
- [ ] `cdk diff` shows only the Lambda code asset change; pre-deploy dry-runs show only
      `site/bolts/view.js` uploading (shared sync has no leftovers; `leijonat/` is unchanged)
- [ ] After a manual invoke, `https://jurigregg.com/data/kiekkokeskus/bolts.json` has
      `standing.divisionLead.runnerUp` and `/bolts` renders the new lead tile correctly in
      Chrome against the LIVE JSON (not the golden)
- [ ] ADR-041 added to `docs/DECISIONS-DATA.md`; TESTING.md gets the gotcha rows below;
      TASK.md's "next free number" is `11`; the "Division-leader tile" Known Issue is removed
- [ ] No code file over 500 lines (ADR-034)

---

## Context

### Related Documentation
- `docs/PLANNING.md`: data contract (envelope + no `schemaVersion` bump for additive fields),
  cost budget
- `docs/DECISIONS.md`: ADR-006 (raw-before-parse), ADR-015 (missing-at-0-GP → null — tangential
  here, but `pts`/`gp` are present when a team has played), ADR-029 (`init-nn` numbering: this
  is the first unplanned spec, bumps the next free number from 10 to 11), ADR-039 (shared-asset
  Cache-Control)
- `docs/DECISIONS-DATA.md`: **ADR-035** (`bolts.json` field sources), **ADR-036** (standings
  definitions — `divisionLead.gap = leader - TBL`, `playoffLine.gap` sign conventions, both
  signed, never `abs()`-ed). ADR-036 observed `divisionSequence ∈ {1,2,3}` for teams with
  `wildcardSequence == 0` and documents the ordering invariants
- `docs/TESTING.md`: Layer 1 (parser), Layer 2 (builder golden), Layer 5 (page logic), gotcha
  matrix row-per-ADR rule

### Dependencies
- **Required**:
  - PRP-04 complete (`bolts.json` builder, `parse/standings.py`, builder golden)
  - PRP-07 complete (`/bolts` page, `view.js`'s `divisionLeadTile`, `gihClause`, deploy chain)
- **Optional**: none

### Files to Modify/Create
```
docs/TASK.md                            MODIFY: P0.0 bump "next free number" from 10 → 11;
                                                 start marker; close-out removes Known Issue
src/kiekkokeskus/parse/standings.py     MODIFY: + division_runner_up(rs, division)
tests/test_parse_standings.py           MODIFY: + 2 cases (TBL first; TBL second)
src/kiekkokeskus/build_bolts.py         MODIFY: _division_lead() adds runnerUp field
tests/test_build_bolts.py               MODIFY: + case that builds against the new fixture
                                                 (TBL-first standings) and asserts runnerUp
tests/fixtures/standings__2026-10-10__2026-10-11.json.gz
                                        NEW: copied from raw archive
                                             (s3://.../raw/2026-10-11/standings__2026-10-10.json.gz)
tests/golden/bolts.json                 MODIFY: runnerUp key added under divisionLead (today's
                                                 golden has TBL at seq=2, so runnerUp = TBL)
site/bolts/view.js                      MODIFY: divisionLeadTile branches on
                                                 leader=='TBL' && runnerUp.team!='TBL'
site/bolts/view.test.js                 MODIFY: + 7 gotcha rows (table in Testing Requirements);
                                                 add runnerUp to synthetic defaults; comment
                                                 existing "TBL leads division" as the
                                                 "runnerUp null / TBL itself" defensive case
docs/DECISIONS-DATA.md                  MODIFY: append ADR-041 (spec draft verbatim)
docs/TESTING.md                         MODIFY: + Layer 1/2/5 rows under "init-10 additions"
```
Expected post-change sizes: `parse/standings.py` ~130, `build_bolts.py` ~275, `view.js` ~155,
`view.test.js` ~290. All well under 500. Docs are exempt (ADR-034).

---

## Verification of Unconfirmed Facts

| Assumption | Checked how | Result | Follow-up |
|---|---|---|---|
| `divisionSequence` within a division is unique and runs 1..n (ADR-036 noted it; init-10 Verify item 1) | Python probe of `/tmp/kk-scratch/standings__2026-10-10.json.gz` grouped by `divisionAbbrev` | **Confirmed.** All 4 divisions (A/M/C/P) have 8 teams with sequences 1..8, all distinct | None. New parser helper assumes uniqueness; no fallback needed |
| 2026-10-10 raw standings has TBL at `divisionSequence == 1` (Verify item 2) | Python probe on raw payload | **Confirmed.** TBL at `divisionSequence: 1`, `points: 8`, `gamesPlayed: 5`. Atlantic Division top-3: TBL (seq=1, 8pts, 5gp), OTT (seq=2, 8pts, 5gp), BOS (seq=3, 8pts, 6gp) | None — fixture captures this cleanly |
| Raw archive path: the spec's example `raw/2026-10-10/standings__2026-10-10.json.gz` was off | `aws s3 ls` across `raw/2026-10-09..12/` | **Clarified.** Correct path is `s3://jurigregg-static-site/data/kiekkokeskus/raw/2026-10-11/standings__2026-10-10.json.gz` — the raw dir groups by **capture-run** date (2026-10-11), while the filename `__2026-10-10` is the standings **dataDate**. The fixture filename follows the project convention `{slug}__{dataDate}__{captureDateET}.json.gz`, so the committed file is `tests/fixtures/standings__2026-10-10__2026-10-11.json.gz` | Spec P0.4's example path updated in Step 0 fixture-capture command |
| Spec example: "TBL leads with 8 pts, runnerUp FLA 6 pts → `+2`" | Live probe | **Slight divergence from spec.** The actual 2026-10-10 fixture has runnerUp **OTT** (not FLA), and both TBL and OTT have `pts: 8` on `gp: 5`. So the fixture's natural rendering is `0` (ties on points — TBL first via tiebreaker). The spec's `+2` example was illustrative. **The fixture doubles as the "tied on points, Tampa first by tiebreaker" gotcha** — a nice two-for-one. The `+2` case still gets a synthetic test | Fine; `view.test.js` keeps a synthetic `+2` case for the "lead over runner-up" row, and the fixture gives us a live-grounded `0` case |
| Golden fixture (`standings__2026-10-08`) has TBL at `divisionSequence == 2` so `runnerUp.team` is `'TBL'` itself and the page falls back | Python probe | **Confirmed.** Golden Atlantic top-3: OTT (seq=1, 6pts, 4gp), TBL (seq=2, 6pts, 4gp), FLA (seq=3, 6pts, 4gp). After the builder change, golden `runnerUp` is `{ team: 'TBL', pts: 6, gamesInHand: 0 }` — the "Tampa not leading" branch stays byte-identical to today's render | None |
| Builder: `_division_lead` is the only place that needs to grow a field | Read `build_bolts.py:32-44` + `parse/standings.py:63-68` | **Confirmed.** `_division_lead` is self-contained. Adding `runnerUp` to its return dict is the whole builder change | None |
| View: `divisionLeadTile` is the only place that reads `divisionLead` on the page | Grep `divisionLead` under `site/` | **Confirmed.** `site/bolts/view.js:1` function; no other consumer. `/leijonat` and the harness don't touch this field | None |
| CloudFront no-cache-busting is needed for `bolts.json` after the Lambda runs | ADR-022 verified note | **Confirmed.** `bolts.json` carries origin `Cache-Control: public, max-age=300`. Live `bolts.json` updates within 5 min of the Lambda write | None |

---

## Technical Specification

### Output Schema
Additive — `schemaVersion` stays `1` (ADR-035's additive field rule; init-10 P0.3).

```json
{
  "standing": {
    "divisionLead": {
      "leader": "TBL",             // unchanged (ADR-036)
      "leaderPts": 8,              // unchanged
      "gap": 0,                    // unchanged, signed, never abs()
      "gamesInHand": 0,            // unchanged, signed
      "runnerUp": {                // NEW (ADR-041)
        "team": "OTT",             // teamAbbrev.default of the divisionSequence==2 row
        "pts": 8,                  // int; the row's `points` field
        "gamesInHand": 0           // signed: runnerUp.gp − TBL.gp (same convention as ADR-036)
      }
    }
  }
}
```

- **`runnerUp` is always populated** when a team at `divisionSequence == 2` exists in Tampa's
  division. In practice that's always true in-season (verified: all 4 divisions have unique
  1..n sequences). It's `null` only in the pathological case the parser helper returns `None`.
- **When Tampa is second**, `runnerUp.team === 'TBL'` and the page's fallback branch keeps
  rendering today's output. The data stays dumb.
- **No `gap` field inside `runnerUp`** — the page computes `standing.pts − runnerUp.pts` to
  avoid introducing a third sign convention alongside ADR-036's two (`divisionLead.gap =
  leader − TBL`; `playoffLine.gap` sign depends on `inPosition`).

### Module Design

```python
# src/kiekkokeskus/parse/standings.py — new helper

def division_runner_up(
    rs: list[dict[str, Any]],
    division: str,
) -> dict[str, Any] | None:
    """Team with `divisionSequence == 2` in the given division (ADR-041).

    Returns None only if no such row exists. In-season this is always populated — see the
    PRP-10 Verification table: all 4 divisions have unique 1..n sequences in every captured
    standings fixture.
    """
    for r in rs:
        if r.get("divisionAbbrev") == division and r.get("divisionSequence") == 2:
            return r
    return None
```

```python
# src/kiekkokeskus/build_bolts.py — _division_lead additions

def _division_lead(rows: list[dict[str, Any]], tbl_row: dict[str, Any]) -> dict[str, Any]:
    """ADR-036 (leader + gap) and ADR-041 (runnerUp)."""
    division = tbl_row.get("divisionAbbrev") or ""
    leader = standings.division_leader(rows, division)
    leader_pts = (leader.get("points") if leader else None) or 0
    leader_gp = (leader.get("gamesPlayed") if leader else None) or 0
    tbl_pts = tbl_row.get("points") or 0
    tbl_gp = tbl_row.get("gamesPlayed") or 0

    runner_up_row = standings.division_runner_up(rows, division)
    runner_up: dict[str, Any] | None = None
    if runner_up_row is not None:
        ru_pts = runner_up_row.get("points") or 0
        ru_gp = runner_up_row.get("gamesPlayed") or 0
        runner_up = {
            "team": runner_up_row.get("team"),
            "pts": ru_pts,
            "gamesInHand": ru_gp - tbl_gp,   # same orientation as ADR-036's gamesInHand
        }

    return {
        "leader": (leader or {}).get("team"),
        "leaderPts": leader_pts,
        "gap": leader_pts - tbl_pts,
        "gamesInHand": leader_gp - tbl_gp,
        "runnerUp": runner_up,
    }
```

```javascript
// site/bolts/view.js — divisionLeadTile branches on TBL-leads + non-TBL runnerUp

function divisionLeadTile(s, lang) {
  const dl = s.divisionLead;
  const tblLeads = dl.leader === "TBL";
  const ru = dl.runnerUp;

  // ADR-041: when Tampa leads AND the runnerUp exists AND isn't Tampa itself, show the lead
  // over second place from Tampa's view (positive = ahead; 0 when tied on points but first
  // by tiebreaker).
  if (tblLeads && ru && ru.team !== "TBL") {
    const diff = (s.pts ?? 0) - (ru.pts ?? 0);
    return {
      label: t("tile.divLeader", null, lang),
      value: signed(diff, lang),
      sub:
        `${ru.team} · ${tp("unit.pts", ru.pts, lang)}` +
        gihClause(ru.gamesInHand, lang),
    };
  }

  // Fallback: Tampa not leading, OR runnerUp missing, OR runnerUp == TBL (Tampa second).
  // Byte-identical to today's rendering.
  return {
    label: tblLeads ? t("tile.divLeader", null, lang) : t("tile.divLead", null, lang),
    value: tblLeads ? "0" : signed(-dl.gap, lang),
    sub:
      `${dl.leader} · ${tp("unit.pts", dl.leaderPts, lang)}` +
      gihClause(dl.gamesInHand, lang),
  };
}
```

### Page Changes
Only `/bolts` reads `divisionLead`. No new strings — `tile.divLeader` + `unit.pts.one/.other`
+ `gih.ahead.one/.other` + `gih.behind.one/.other` all already exist from PRP-07's `Step 1
strings`. `/leijonat` is unaffected.

### Infra Changes
`cdk diff` is expected to show **only the Lambda code asset hash change** (because
`parse/standings.py` and `build_bolts.py` are inside the Lambda zip). No new resources, no
schedule change, no role change. If `cdk diff` touches anything beyond the Lambda's code asset
and `AssetParameters*`, **stop and report** per the emergency-stop rule.

---

## Implementation Steps

Each step is one validated commit: `{type}(10): {description}`.

### Step 0: Start + bump "next free number" + capture the fixture
**Files**: `docs/TASK.md`, `initials/init-10-bolts-runner-up.md`, `prps/prp-10-bolts-runner-up.md`,
`tests/fixtures/standings__2026-10-10__2026-10-11.json.gz`

- Move init-10 to **In Progress** in `docs/TASK.md`.
- Bump TASK.md's "next free number" from `10` → `11` (ADR-029; init-10 is the first unplanned
  spec).
- Capture the TBL-leads fixture from the production raw archive (not re-fetched; TESTING.md
  rule 5):
  ```bash
  aws s3 cp s3://jurigregg-static-site/data/kiekkokeskus/raw/2026-10-11/standings__2026-10-10.json.gz \
    tests/fixtures/standings__2026-10-10__2026-10-11.json.gz \
    --profile default
  ```
  Add a `tests/fixtures/README.md` row recording provenance (raw archive, 2026-10-11 run,
  TBL at Atlantic seq=1 / 8pts / 5gp, used for ADR-041 gotchas).
- Add the init + PRP files to git (same pattern as `docs(04-08): start`).

**Validation**:
- [ ] `.venv/bin/pytest -q` green (baseline 191 passed)
- [ ] `node --test "site/kiekkokeskus/*.test.js" "site/bolts/*.test.js" "site/leijonat/*.test.js"`
      green (baseline 154)
- [ ] `grep -nF "next free number" docs/TASK.md` shows `11`
- [ ] `file tests/fixtures/standings__2026-10-10__2026-10-11.json.gz` reports a valid gzip; probe
      confirms `TBL divisionSequence == 1`

**Commit**: `docs(10): start`

### Step 1: Parser helper
**Files**: `src/kiekkokeskus/parse/standings.py`, `tests/test_parse_standings.py`

Add `division_runner_up(rs, division)` next to `division_leader`. Pure, no I/O.

**Validation**:
- [ ] `.venv/bin/pytest tests/test_parse_standings.py -q` green with new cases:
  - **TBL leads** (new fixture): `division_runner_up(rows, 'A')['team'] == 'OTT'`;
    `points == 8`; `gamesPlayed == 5`
  - **TBL second** (golden fixture): `division_runner_up(rows, 'A')['team'] == 'TBL'`;
    `points == 6`; `gamesPlayed == 4`
  - Unknown division: `division_runner_up(rows, 'X') is None`
- [ ] `parse/standings.py` under 140 lines

**Commit**: `feat(10): standings.division_runner_up helper`

### Step 2: Builder + golden
**Files**: `src/kiekkokeskus/build_bolts.py`, `tests/test_build_bolts.py`,
`tests/golden/bolts.json`

Add `runnerUp` to `_division_lead`'s return dict. Regenerate golden with `UPDATE_GOLDEN=1
pytest tests/test_build_bolts.py` and review the diff — **the ONLY change should be the new
`runnerUp` key under `standing.divisionLead`**. If any other key changes, stop.

Extend `test_build_bolts.py` with a parametrized or additional case that builds against the
new fixture (TBL-first standings) and asserts `runnerUp.team == 'OTT'` + `pts == 8` + the
signed `gamesInHand`. The new case needs its own `data_date` (2026-10-10) and `now_iso`
(matching the capture) but reuses the rest of the payload set (club-stats / schedule etc. can
reuse the same fixtures — they aren't under test for this case; only the standings-derived
section is).

**Validation**:
- [ ] `.venv/bin/pytest tests/test_build_bolts.py -q` green on both cases
- [ ] `git diff tests/golden/bolts.json` shows **only** the added `runnerUp` key
- [ ] Golden `runnerUp == { team: 'TBL', pts: 6, gamesInHand: 0 }` (TBL at seq=2 in the
      golden fixture — Tampa itself)
- [ ] `build_bolts.py` under 280 lines

**Commit**: `feat(10): bolts.json carries divisionLead.runnerUp`

### Step 3: Page tile
**Files**: `site/bolts/view.js`, `site/bolts/view.test.js`

Update `divisionLeadTile` with the new branch (code in Module Design above). Update the
existing "TBL leads division" test's comment to note it now exercises the "runnerUp null"
defensive case (the synthetic data has no `runnerUp`, so the fallback branch fires).

**Add 7 new tests** (full table in Testing Requirements). Each uses the existing `synth`
helper + sets `standing.divisionLead.runnerUp` in the override:
- **lead over runner-up (EN + FI)**: TBL leads with `standing.pts: 8`, `runnerUp: { team:
  'FLA', pts: 6, gamesInHand: 0 }` → value `+2`, sub `FLA · 6 pts` / `FLA · 6 p`
- **tied on points, Tampa first by tiebreaker**: `standing.pts: 8`, `runnerUp.pts: 8` → value
  `'0'` (not `'-0'`, not `'+0'`; locked by the `signed(-0)` test from init-07)
- **runner-up has played fewer games**: `runnerUp.gamesInHand: -1` → sub ends `· 1 more game
  played`
- **runner-up has games in hand**: `runnerUp.gamesInHand: 2` → sub ends `· 2 games in hand`
- **runnerUp null while Tampa leads**: fallback renders today's `'0'` + `TBL · {pts}` →
  byte-identical
- **runnerUp == TBL while Tampa leads** (pathological): fallback renders today's output
- **Tampa not leading (golden-like)**: `leader: 'OTT'`, `runnerUp: { team: 'TBL', pts: 6, ...
  }` → tile byte-identical to today (`−{gap}` + `OTT · 6 pts`)

Also update the "golden view EN/FI" tests at the top of the file: when the golden's
`divisionLead` gains `runnerUp: { team: 'TBL', pts: 6, gamesInHand: 0 }`, the view output is
unchanged — but add a one-liner asserting that `v.tiles.divisionLead` matches the pre-init-10
rendering byte-for-byte (easier: assert `value === '0'` and `sub === 'OTT · 6 pts'` as today).

**Validation**:
- [ ] `node --test "site/bolts/view.test.js"` green on new + updated cases
- [ ] `view.js` under 160 lines

**Commit**: `feat(10): /bolts shows lead over runner-up when Tampa leads`

### Step 4: Deploy and verify
```bash
# 1. CI green on the branch
gh run watch

# 2. cdk diff — expect ONLY the Lambda code asset change
cd infra && PATH="/opt/homebrew/opt/node@22/bin:$PATH" AWS_PROFILE=default npx cdk diff
# Expected: a single AWS::Lambda::Function resource with a changed Code.S3Key (new asset
# hash). AssetParameters* in the output are tolerable. Anything else — stop.

# 3. Pre-deploy dry runs — shared and leijonat should be no-ops; bolts should show only view.js.
aws s3 sync site/kiekkokeskus/ s3://jurigregg-static-site/kiekkokeskus/ --delete \
  --exclude "*.test.js" --exclude "_dev/*" --exclude "package.json" --dryrun --profile default
# expected: no uploads
aws s3 sync site/bolts/ s3://jurigregg-static-site/bolts/ --delete --exclude "*.test.js" \
  --dryrun --profile default
# expected: 1 upload — site/bolts/view.js
aws s3 sync site/leijonat/ s3://jurigregg-static-site/leijonat/ --delete --exclude "*.test.js" \
  --dryrun --profile default
# expected: no uploads

# 4. Deploy
.venv/bin/python scripts/deploy.py                # cdk diff + exit
.venv/bin/python scripts/deploy.py --approved     # cdk deploy (Lambda update) + page syncs

# 5. Force a fresh bolts.json by invoking the collector now (don't wait for the scheduler)
aws lambda invoke --function-name kiekkokeskus-collector \
  --profile default --region us-east-1 out.json && cat out.json
# expected: non-zero built list including "bolts"; manifest 0 errored

# 6. Smoke + live checks
.venv/bin/python scripts/smoke.py
curl -s https://jurigregg.com/data/kiekkokeskus/bolts.json | .venv/bin/python -c \
  "import sys,json; d=json.load(sys.stdin); import pprint; pprint.pp(d['standing']['divisionLead'])"
# expected: includes a runnerUp object with team/pts/gamesInHand
```

**Live Chrome manual (Chrome only; PRP-07 dropped Safari parity)**:
Fetch the LIVE JSON once in the console, then verify against **LIVE**, not the golden:
```javascript
const LIVE = await fetch('/data/kiekkokeskus/bolts.json').then(r => r.json());
```
- [ ] `LIVE.standing.divisionLead.runnerUp` exists with `team`, `pts`, `gamesInHand`
- [ ] If `LIVE.standing.divisionLead.leader === 'TBL'` and `LIVE.standing.divisionLead.runnerUp.team
      !== 'TBL'`:
  - [ ] The division-lead tile value equals `signed(LIVE.standing.pts − LIVE.standing.divisionLead.runnerUp.pts)`
        (expect `+N`, or `0` on tiebreaker)
  - [ ] The sub reads `{runnerUp.team} · {pts} pts/pt` with the games-in-hand clause from
        `runnerUp.gamesInHand` (same orientation as the other gih fields)
- [ ] If `LIVE.standing.divisionLead.leader !== 'TBL'` OR `runnerUp.team === 'TBL'`:
  - [ ] The tile is byte-identical to the pre-init-10 render (`−gap` or `0` + `leader · leaderPts`)
- [ ] FI toggle: `tile.divLeader` label is still `'Divisioonan kärjessä'`; `pts` plural in FI
      is `'{n} p'`; `+N`/`−N` use U+2B / U+2212
- [ ] DevTools Network: still exactly 1 `bolts.json` request across the toggle (fetch-once
      contract from PRP-07 untouched)

**Validation**:
- [ ] `cdk diff` touched only the Lambda code asset
- [ ] Shared + leijonat dry-runs showed 0 uploads; bolts dry-run showed exactly 1 upload (`view.js`)
- [ ] Manual invoke returned a 0-error `_manifest.json` and `built` includes `'bolts'`
- [ ] `smoke.py` green
- [ ] Every Layer 7 item above verified against LIVE JSON

**Commit**: no new commit unless a live surprise forces a `fix(10): ...` follow-up.

### Step 5: Documentation and close-out
**Files**: `docs/DECISIONS-DATA.md`, `docs/TESTING.md`, `docs/TASK.md`,
`prps/prp-10-bolts-runner-up.md`

- Append **ADR-041** to `docs/DECISIONS-DATA.md` using the spec's draft text verbatim
  (Date 2026-10-12; Status Accepted; extends ADR-036).
- Add the Layer 1 / Layer 2 / Layer 5 gotcha rows below to `docs/TESTING.md` under a new
  "init-10 additions" subsection.
- `docs/TASK.md`:
  - Move init-10 to Recently Completed with a one-line outcome.
  - **Remove the Known Issue** "Division-leader tile shows nothing useful when TBL leads"
    (PRP-07 TASK.md Known Issues section).
  - Confirm "next free number" line still reads `11`.
  - Update Last-updated date.
- Flip PRP status Ready → Complete.

**Validation**:
- [ ] `grep -c "ADR-041" docs/DECISIONS-DATA.md` ≥ 1
- [ ] `grep -F "Division-leader tile shows nothing useful" docs/TASK.md` returns no lines
- [ ] All layered checks green locally and in CI

**Commit**: `docs(10): ADR-041, TESTING, TASK, complete`

---

## Testing Requirements

| Layer (TESTING.md) | Tests | Fixture / Gotcha row |
|---|---|---|
| 1 Parse contract | `tests/test_parse_standings.py` adds 3 cases around `division_runner_up` | ADR-041 rows below |
| 2 Builder golden | `tests/test_build_bolts.py` builds against both fixtures (TBL-first via new fixture + TBL-second via golden); golden diff review is the sign-off | ADR-041 "runner-up in bolts.json" |
| 3 Orchestration | n/a — handler change is implicit (Lambda code bundle); no new orchestration branch | — |
| 4 Infra | `cdk diff` touches only the Lambda code asset; `infra/test/` assertions remain green | — |
| 5 Page logic | `site/bolts/view.test.js` adds 7 rows | ADR-041 rows below |
| 6 Smoke | existing `scripts/smoke.py` is sufficient (no new paths; `/bolts` still 200 text/html, `bolts.json` still 200 with `max-age=300` and `schemaVersion: 1`) | — |
| 7 Manual | Step 4 live Chrome checks against LIVE JSON (desktop; mobile is unaffected — the tile's narrow-viewport rules already handle +N / 0 / −N) | — |

### Gotcha-matrix rows (new in `docs/TESTING.md` under "init-10 additions")

| ADR | Layer | Gotcha | Input | Assert |
|---|---|---|---|---|
| 041 | 1 | parser: runner-up when Tampa leads | `standings__2026-10-10__2026-10-11` fixture | `division_runner_up(rows, 'A')['team'] == 'OTT'`, `points == 8`, `gamesPlayed == 5` |
| 041 | 1 | parser: runner-up when Tampa second | existing golden fixture `standings__2026-10-08__2026-10-09` | `division_runner_up(rows, 'A')['team'] == 'TBL'` |
| 041 | 1 | parser: unknown division | synthetic | `division_runner_up(rows, 'X') is None` |
| 041 | 2 | builder: runner-up populated when Tampa leads | new fixture → build | `standing.divisionLead.runnerUp` has `team: 'OTT'`, `pts: 8`, `gamesInHand: 0` (TBL and OTT both 5 gp) |
| 041 | 2 | builder: runner-up populated when Tampa second | golden → build | `runnerUp.team == 'TBL'`, `pts == 6`, `gamesInHand == 0` |
| 041 | 5 | page: lead over runner-up | synthetic TBL leads, `pts: 8`, `runnerUp: {team:'FLA', pts:6, gamesInHand:0}` | value `'+2'`, sub `FLA · 6 pts` (EN) / `FLA · 6 p` (FI) |
| 041 | 5 | page: tied on points, Tampa first by tiebreaker | `runnerUp.pts == standing.pts` | value `'0'` — never `'-0'`, never `'+0'` (reuses the init-07 `signed(-0)` guarantee via `Intl.NumberFormat` + `exceptZero`) |
| 041 | 5 | page: runner-up has played fewer games | `runnerUp.gamesInHand: -1` | sub ends `' · 1 more game played'` |
| 041 | 5 | page: runner-up has games in hand | `runnerUp.gamesInHand: 2` | sub ends `' · 2 games in hand'` |
| 041 | 5 | page: runnerUp null while TBL leads | synthetic defensive | fallback render: value `'0'`, sub `TBL · {pts}` (today's output) |
| 041 | 5 | page: runnerUp == TBL while TBL leads | pathological | same fallback render — Tampa second case |
| 041 | 5 | page: Tampa not leading (byte-identity) | golden-shape input with `runnerUp: {team:'TBL',...}` | tile value `'0'` or `signed(-gap)`, sub `{leader} · {leaderPts} pts` — byte-identical to pre-init-10 |

---

## Error Handling and Edge Cases

| Case | Source | Handling | Test |
|---|---|---|---|
| TBL row missing from standings | existing | `build()` already raises `ValueError("TBL row missing from standings")` | existing test (unchanged) |
| No row at `divisionSequence == 2` | ADR-041 | `division_runner_up` returns `None`; builder emits `runnerUp: null`; page falls back | parser "unknown division" + page "runnerUp null while TBL leads" |
| `runnerUp.team == 'TBL'` (Tampa is 2nd) | normal in-season | Page's `ru.team !== 'TBL'` guard keeps today's rendering | page "runnerUp == TBL while TBL leads" |
| `runnerUp.pts == standing.pts` (points tie, Tampa first on tiebreaker) | ADR-036 ordering | `signed(0)` renders `'0'` via `Intl.NumberFormat` + `exceptZero` (locked in init-07's `signed(-0)` test) | page "tied on points" |
| `runnerUp.gamesInHand < 0` (Tampa has played fewer games than runner-up) | ADR-036 orientation | `gihClause(-1, lang)` → `' · 1 more game played'` (EN) via `tp('gih.behind', 1, lang)` | page "runner-up has played fewer games" |
| `standing.pts` or `runnerUp.pts` are `null` (0-GP) | ADR-015 | `?? 0` fallback — only matters pre-season; league-leader rendering is informative-only | implicit via `_division_lead` existing `or 0` pattern |
| Golden diff reveals an unexpected change | ADR-034 golden review | Stop; investigate; a diff beyond the single new `runnerUp` key means something else moved | manual review in Step 2 |

---

## Cost Impact

**None.** Lambda compute is unaffected (one extra `.get(...)` loop and a tiny dict add per
run). No new HTTP requests. `bolts.json` grows by ~60 bytes (new `runnerUp` sub-object) —
still well under 1 KB and well inside the `max-age=300` cache budget. No new storage class,
no new request pattern.

---

## Rollback Plan

1. **Code**: `git revert` the PRP's commits, then `.venv/bin/python scripts/deploy.py
   --approved`. The reverted Lambda stops emitting `runnerUp`. `/bolts/view.js` falls back to
   its pre-init-10 branch (also reverted), so there's no "undefined field" asymmetry even for
   the ~5 minutes between the view update and the next Lambda run.
2. **Data**: no `data/kiekkokeskus/*` prefix changes required for a rollback — the next
   scheduled Lambda run (10:00 ET) overwrites `bolts.json` with the reverted schema.
   S3 noncurrent versions kept 7 days (ADR-023) if the pre-init-10 JSON is needed sooner:
   `aws s3api list-object-versions --bucket jurigregg-static-site --prefix
   data/kiekkokeskus/bolts.json --profile default` and restore the earlier version.
3. **Verify**: `.venv/bin/python scripts/smoke.py`; `/bolts` tile reverts to showing `0` +
   `TBL · {pts}` when Tampa leads (which is the problem init-10 solved; a rollback restores
   the tautology).

---

## Open Questions

(none)

---

## Confidence Scores

| Dimension | Score (1-10) | Notes |
|-----------|--------------|-------|
| Clarity | 9 | Spec enumerates every field with source + units + nullability + the exact fallback branch. Only ambiguity was the raw archive path (clarified in Verification above) |
| Feasibility | 9 | Small, well-scoped: one helper, one builder field, one view-tile branch, two new fixtures (one captured from the raw archive, no re-fetch). Everything else — strings, `signed()`, `gihClause`, deploy chain, smoke — exists from PRP-04/07 |
| Completeness | 9 | Every output field has a source and nullability. 12 gotcha rows named across 3 layers. Rollback covers code + data via S3 versioning. 7/7 Verify items probed and confirmed clean |
| Payload certainty | 10 | No NHL fetch needed — raw archive copied as fixture. divisionSequence uniqueness proved across all 4 divisions. TBL at seq==1 on 2026-10-10 proved via Python probe |
| **Average** | **9.25** | **Ready to execute** |

### Verification results (one surprise, documented)
- **Spec example `+2 FLA 6 pts` doesn't match the fixture**: the real 2026-10-10 standings
  has runnerUp **OTT** at 8 pts (tied with TBL), so the fixture-grounded render is `0` + `OTT
  · 8 pts`, not `+2` + `FLA · 6 pts`. The spec's example was illustrative. The `+2` case gets
  its own synthetic test, and the fixture doubles as the "tied on points, Tampa first by
  tiebreaker" gotcha — a nice two-for-one.
- **Raw archive path differed from spec**: spec said `raw/2026-10-10/...`; actual is
  `raw/2026-10-11/standings__2026-10-10.json.gz` (raw dirs group by capture-run date, not
  dataDate). Step 0's `aws s3 cp` command uses the correct path. The committed fixture
  filename follows project convention `{slug}__{dataDate}__{captureDateET}.json.gz`.
- **No other surprises.** All other claims (divisionSequence uniqueness, TBL at seq=1,
  builder's `_division_lead` is the only place to grow, view's `divisionLeadTile` is the only
  consumer, no `schemaVersion` bump) held exactly as the spec described.

### Suggested new ADRs
- **ADR-041** (`docs/DECISIONS-DATA.md`) — Division runner-up in `bolts.json`. Spec provides a
  draft; Step 5 appends it verbatim with next global number 041. Extends ADR-036 by adding a
  signed `gamesInHand` field with the same `reference.gp − TBL.gp` orientation and
  deliberately **no** `gap` field (page computes `standing.pts − runnerUp.pts`). Additive —
  no `schemaVersion` bump.
