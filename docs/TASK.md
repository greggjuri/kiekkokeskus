# Kiekkokeskus - Task Tracker

**Spec numbers:** `01`–`09` are reserved by the backlog below. **The next free number for a new,
unplanned spec is `10`.** Bump it whenever an unplanned spec is created (ADR-029).

## Current: Phase 1, Foundation

### In Progress
- [ ] `init-03-collector-core` - PRP-03 Steps 0–7 done; Step 8 docs tidy next

### Up Next
- [ ] `init-04-bolts-json` — standings + gaps, last/next games, full skater/goalie rows, special teams

---

## Recently Completed

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
- **Hits and blocks source**: unverified; expected from stats REST `realtime` (init-04, ADR-030)
- **Chart rendering**: hand-rolled SVG vs. a single vendored library (init-09)
- **FI save % format**: `,915` vs `91,5 %` (init-06)
- **`raw/` publicly served**: accepted for now (ADR-020); revisit only if it matters
- **Traded players**: how bios/club-stats represent them (init-04/05, TESTING watch list)
- **Off-season gap**: PRP-03 falls back to `standings[0].seasonId` when schedule has no games on
  `dataDate`, so short in-season gaps don't alarm. **True off-season** (both schedule *and*
  standings return no useful fields) still fails loudly — do we want the collector paused during
  known off-season windows (July–Sept), or is a daily alarm then acceptable? Settle before the
  2027 off-season.

## Known Issues

- ADR-009 was verified through a summarizing fetch, not a raw diff. Re-verify in init-03.
- Main site repo needs the same "no `--delete` at bucket root" rule in its CLAUDE.md (ADR-024).
  Owner: Juri.

## Notes

- AWS: account `490004610151`, profile `default`, us-east-1
- Site: bucket `jurigregg-static-site`, distribution `E1ZSW9COVAPN92`
- Cost: about $0/month; ceiling $2

---

*Last updated: 2026-10-04 (init-02 complete; init-03 Steps 0–7 done, docs tidy next)*

---

## Update Rules

- Status flow: Backlog → Up Next → In Progress → Recently Completed → Completed
- Starting a spec: move it to In Progress and note its PRP.
- Finishing a spec: Recently Completed, with its PRP number and a one-line outcome.
- New phase: move Recently Completed into Completed.
- Learnings go into DECISIONS / DECISIONS-DATA as ADRs, not here.
- Creating an unplanned init file: bump the next free number in the same commit.
