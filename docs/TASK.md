# Kiekkokeskus - Task Tracker

**Spec numbers:** `01`–`09` are reserved by the backlog below. **The next free number for a new,
unplanned spec is `11`.** Bump it whenever an unplanned spec is created (ADR-029).

## Current: Phase 3 → Phase 4

### In Progress
- [ ] `init-10-bolts-runner-up` — add `divisionLead.runnerUp` to `bolts.json`, update `/bolts` tile (PRP-10)

### Up Next
- [ ] `init-09-history` (Phase 4)

---

## Recently Completed

### init-08-leijonat-page (2026-10-12)
- [x] `jurigregg.com/leijonat` live. Reused everything init-07 built: `page.js`/`controller.js`,
      `renderHeader(hero)`, `localName`, `tp`, `kk-page.css`. Only shared addition is a pure
      `nameCellParts(row, lang, decorateName)` in `table.js` plus `decorateName` forwarding
      through `mountPage` to both tables — `/bolts` passes nothing, so its markup stays
      byte-identical (regression-locked). `/leijonat` has the lion hero (ADR-040), four count
      tiles (Skaters/Goalies/Teams/Rookies), last-night cards (name + rookie `*` + team + big
      stats line + game result badge), skater and goalie tables **with** team column, rookie
      marker + per-table legend, by-team compact list. Also: parked `Saldo`→`Tilanne` FI
      rename on `tile.record` landed in the same deploy. Mid-execution removed the
      `leijonat.definition` paragraph entirely (both langs; guard tests assert it stays gone).
      CI gap backfilled: ci.yml now runs all three Node globs (PRP-07's report wrongly claimed
      it already ran the bolts glob — corrected in `ci(08)` commit body). Live verified
      against LIVE JSON (not golden — PRP-08 locked that discipline): tiles equal array
      lengths, 7 last-night cards (data has rotated — 2 skaters + 5 goalies now including a
      Heiskanen OTL/SO), rookie `*` on Konsta Helenius / Arttu Hyry / Brad Lambert / Ville
      Ottavainen, by-team 19 rows, fetch-once confirmed. Harness `/leijonat` placeholder
      section dropped (P1.1). ADR-040 unchanged (PRP-08)

### init-07-bolts-page (2026-10-11)
- [x] `jurigregg.com/bolts` live. Shared page controller split cleanly: `controller.js` (pure,
      no DOM — reducer + single `loadData` + `writeState` + localStorage try/catch, tested with
      a recording `render` stub) and `page.js` (`mountPage` DOM adapter). `view.js` is a pure
      view model; `main.js` is thin DOM glue plus the renderers for tiles / lastGame /
      nextGames / special. 4 standings tiles from Tampa's point of view (signed gaps,
      TBL-leader branch), 3-card row, hero (`ADR-040`, pre-flattened WebP on `--kk-bg`).
      `strings.js` gained ~30 keys (page title + subtitle + `subtitleNoSeason` for pre-fetch
      renders, division/conference names, plural units + games-in-hand, result/decided,
      opp.home/away). New helpers: `format.ordinal` / `format.season` + `i18n.tp` plural lookup
      + `i18n.localName` team-name helper (replaces the `renderName` hack for teams). Deploy
      wired shared-first then bolts, with `--exclude "*.test.js"` on `bolts/`. Smoke extended
      to `/bolts` + `/bolts/hero.webp`. CI runs Node tests across both `site/kiekkokeskus/`
      and `site/bolts/` globs. Fetch-once contract verified live on `jurigregg.com/bolts` via
      `performance.getEntriesByType('resource')` — 1 request before and after toggling,
      filtering, sorting. Today's live data has TBL leading the Atlantic — the "Division
      leader / Divisioonan kärjessä" tile renders authentically. Housekeeping: CLAUDE.md and
      TESTING.md's `node --test` command fixed to the glob form (PRP-06 finding). ADR-040 added
      (PRP-07)

### init-06-shared-ui (2026-10-11)
- [x] 10 framework-free ES modules under `site/kiekkokeskus/` + `kk.css` + dev harness +
      `scripts/preview.py`. Node 22's built-in test runner covers every gotcha row (strings
      parity, partial-FI name, rate3/pct1 ×100, FI minus+NBSP, UTC-noon date parse,
      gameTime day rollover, nulls-last sort, URL round-trip, schema mismatch,
      35h59/36h01 stale boundary). `scripts/deploy.py:page_sync()` wired for the
      `kiekkokeskus/` prefix with `--delete` scoped, `*.test.js`/`_dev/*`/`package.json`
      excluded, and `--cache-control: public, max-age=300`. Smoke now hits `kk.css` and
      `i18n.js`; CI runs Layer 5 (`node --test`). Live deploy: 10 objects, 35.9 KiB,
      content-type correct natively (no second-pass needed). ADR-038 (EN/FI display
      conventions) and ADR-039 (shared-asset deploy + Cache-Control) added. Mid-execution
      fix for mobile header overflow (`minmax(0, 1fr)` on `.kk-header`) and harness
      `langExplicit` propagation (PRP-06)

### init-05-leijonat-json (2026-10-10)
- [x] 4 FIN stats REST endpoints + 2 isRookie filter fetches + 18-team club-stats fan-out for
      Finnish `fi` names. New `parse/bios.py` and `parse/boxscore.py`. `build_leijonat.py`
      composes 30 Finn skaters + 5 goalies + lastNight join + teams block. Handler extracted
      into `build_phase.py` for two-independent-builder control flow. Live spot-check: Määttä
      and Teräväinen carry `fi` keys; Granlund + Kakko in lastNight; 4 FIN rookies flagged
      authoritatively via `isRookie=1`. Lambda duration 20.2s / 180s timeout; 39 raw / 0
      errors / `built: ["bolts", "leijonat"]`. ADR-037 added (PRP-05)

### init-04-bolts-json (2026-10-09)
- [x] 4 new endpoints (summary/realtime/faceoff/team-summary) + 4 parsers + build phase +
      golden `bolts.json`. Live spot-check against NHL.com matched. ADR-035 (field sources,
      faceoff rule, pagination guard, traded-player asymmetry) and ADR-036 (signed gaps,
      playoff-line definition, PP%/PK% ranks) added (PRP-04)

### init-03-collector-core (2026-10-04)
- [x] Dates, fetch+retry, raw+manifest, orchestration. 11-request archive on manual invoke;
      19-request archive on first scheduled run. ADR-033 added (season source), ADR-009
      re-verified from raw and caveat struck, ADR-008 marked partially superseded (PRP-03)

### init-02-infra (2026-10-04)
- [x] CDK stack deployed; health file served through CloudFront with correct Cache-Control;
      missed-run alarm live; forced error produced an SNS email; ADR-032 added, ADR-022 Verified
      note added (legacy TTL config, MinTTL=0) (PRP-02)

### init-01-repo-scaffold (2026-10-03)
- [x] Scaffold green locally and in CI; ADR-031 added (PRP-01)

### Setup (2026-10-02)
- [x] Created `greggjuri/kiekkokeskus` repo and pushed planning docs (f427ea0 → a799225)

### Planning (Claude.ai, 2026-10-02)
- [x] Real payloads fetched and NHL gotchas recorded (ADR-008–018)
- [x] Hosting settled: existing site bucket + CloudFront, imported (ADR-020–024)
- [x] IaC: CDK v2 TS, matching Pulsar (ADR-026, 027)
- [x] Standings backfill confirmed by date (ADR-009)
- [x] EN/FI toggle (ADR-028), init/PRP numbering (ADR-029), sortable tables (ADR-030)
- [x] Templates adapted: PLANNING, DECISIONS, DECISIONS-DATA, TESTING, CLAUDE.md,
      PROJECT-INSTRUCTIONS, TASK

---

## Backlog

Spec numbers below are reserved in this order. A spec inserted later takes the next free number,
whichever phase it belongs to.

### Phase 1 - Foundation
- [ ] `init-02-infra` - CDK stack: Lambda stub, scoped role, schedule, log retention, error alarm;
      lifecycle script; first deploy
- [ ] `init-03-collector-core` - season resolution, fetch + retry, raw archive, dated URLs, first
      real fixtures, re-verify ADR-009 with raw diffs

### Phase 2 - Data
- [ ] `init-04-bolts-json` - standings + gaps, last/next games, full skater and goalie rows,
      special teams + rank
- [ ] `init-05-leijonat-json` - bios pagination, last-night boxscore join, team clusters, rookie
      flag

### Phase 3 - Pages
- [ ] `init-06-shared-ui` - i18n, formatters, sortable/filterable table, base CSS, disclaimer,
      stale banner, local preview
- [ ] `init-07-bolts-page`
- [ ] `init-08-leijonat-page`

### Phase 4 - History
- [ ] `init-09-history` - snapshots, `history/index.json`, standings backfill, pace vs. cut line
      chart

### Future (unnumbered until specced)
- Milestone watch (records API, weekly cache)
- GSAx
- Playoffs
- Last-season overlay on the pace chart

---

## Completed

(Specs move here when a new phase starts.)

---

## Open Questions

Each one is settled in the spec named. When it's settled, record it as an ADR and delete it here.
- **Chart rendering**: hand-rolled SVG vs. a single vendored library (init-09)
- **`raw/` publicly served**: accepted for now (ADR-020); revisit only if it matters
- **Off-season gap**: PRP-03 falls back to `standings[0].seasonId` when schedule has no games on
  `dataDate`, so short in-season gaps don't alarm. **True off-season** (both schedule *and*
  standings return no useful fields) still fails loudly — do we want the collector paused during
  known off-season windows (July–Sept), or is a daily alarm then acceptable? Settle before the
  2027 off-season.

## Known Issues

- Main site repo needs the same "no `--delete` at bucket root" rule in its CLAUDE.md (ADR-024).
  Owner: Juri.
- **Traded players (ADR-035)**: `ppp`/`hits`/`blocks`/`faceoffPct` come from `teamAbbrevs`-filtered
  stats REST endpoints and may include **other-team season totals** for a player who played
  elsewhere earlier in the season, while club-stats columns are TBL-only. No mid-season trade
  has occurred yet to confirm; **re-verify at the first TBL trade** and, if confirmed, either
  switch to club-stats fallbacks for those fields or document the asymmetry on the page.
- **FIN traded players (ADR-037)**: `teamAbbrevs` in nationality-filtered stats REST may become
  multi-team (e.g. `"A,B"`) for a Finn who played for more than one team this season — or the
  endpoint may return one row per team instead. No mid-season FIN trade yet to confirm the
  shape. The builder uses `bios.currentTeamAbbrev` as the authoritative `team` field, so the
  current output is stable, but **re-verify at the first FIN mid-season trade** and update
  ADR-037 with the observed shape (summing per-team rows, or passing through, or similar).
- **Division-leader tile shows nothing useful when TBL leads** (PRP-07 live finding): the
  tile currently renders `0` + `TBL · {pts}`, which is a tautology. The useful value when
  TBL leads is the lead over **second place**. `bolts.json` doesn't carry the runner-up team,
  so this needs a builder change. Candidate: **init-10 — bolts.json runnerUp**, adding
  `standing.divisionLead.runnerUp: { team, pts, gamesInHand }` populated from `standings`
  (the team with `divisionSequence == 2` in TBL's division). Field addition, no shape break,
  no `schemaVersion` bump. Then the tile shows `signed(TBL.pts − runnerUp.pts)` + `{runnerUp.team}
  · {runnerUp.pts}` + games-in-hand clause. Until init-10, the tile stays as it is.

## Notes

- AWS: account `490004610151`, profile `default`, us-east-1
- Site: bucket `jurigregg-static-site`, distribution `E1ZSW9COVAPN92`
- Cost: about $0/month; ceiling $2

---

*Last updated: 2026-10-12 (init-08 complete; next: init-09)*

---

## Update Rules

- Status flow: Backlog → Up Next → In Progress → Recently Completed → Completed
- Starting a spec: move it to In Progress and note its PRP.
- Finishing a spec: Recently Completed, with its PRP number and a one-line outcome.
- New phase: move Recently Completed into Completed.
- Learnings go into DECISIONS / DECISIONS-DATA as ADRs, not here.
- Creating an unplanned init file: bump the next free number in the same commit.
