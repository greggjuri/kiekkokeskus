# Kiekkokeskus - Project Instructions

## What This Is

Two static NHL stat pages on jurigregg.com. `/bolts` covers the Tampa Bay Lightning, and
`/leijonat` covers every Finnish player in the NHL. A daily Lambda pulls the NHL's undocumented
API and writes JSON into the site's S3 bucket, and the pages read only that JSON. It's a sibling of
Tilastokeskus.

**Live URLs**: jurigregg.com/bolts, jurigregg.com/leijonat
**Repository**: github.com/greggjuri/kiekkokeskus

## Tech Stack

- **Collector**: Python 3.13 on Lambda (arm64), stdlib only
- **Pages**: hand-written HTML + vanilla JS modules + CSS, no build; EN/FI toggle
- **Data**: S3 JSON (current state, dated history, gzipped raw archive), no database
- **Hosting**: the existing jurigregg.com S3 bucket + CloudFront, imported and never owned
- **IaC**: CDK v2 TypeScript, one stack (the same shape as Pulsar)
- **Dev machine**: MacBook ("Claudebook"), AWS profile `default`, always passed explicitly

## Critical Constraints

1. **Never touch what this project doesn't own.** The site bucket, the distribution, the
   `add-index-html` function, and the rest of jurigregg.com are off-limits. Writes go only under
   `data/kiekkokeskus/`, `bolts/`, `leijonat/`, `kiekkokeskus/` (ADR-020, 024).
2. **Real payloads first.** No data rule gets decided from community docs or memory. If a spec
   depends on a field's shape, it cites a fetched payload or says "verify in PRP".
3. **The browser never calls the NHL** (ADR-003).
4. **Budget is about $0/month.** One run a day, no database, nothing that scales with traffic.
5. **500-line limit per file, docs included.** Split by module or subject.
6. **Small working commits**, in conventional format with the spec number: `feat(04): …`.

## File Naming Conventions

- Feature specs: `initials/init-nn-{slug}.md`, with a two-digit running number from `01`
  (ADR-029)
- Implementation plans: `prps/prp-nn-{slug}.md`, using the same `nn` and slug as the spec
- Numbers are never reused. **Before writing a new spec, check TASK.md for the next free number.**
- kebab-case everywhere, with consistent casing (the Mac filesystem is case-insensitive and CI is
  not)

## Workflow: Claude.ai ↔ Claude Code

| Claude.ai (this project) | Claude Code (MacBook) |
|--------------------------|-----------------------|
| Discuss and settle decisions | Write code and tests |
| Write `init-nn-*` specs | `/generate-prp`, `/execute-prp` |
| Draft and record ADRs | pytest, `cdk diff`/`deploy`, smoke tests |
| Review PRPs before execution | Capture real fixtures |
| Troubleshoot from logs and payloads the user pastes | Git |

### To Start a New Feature
1. **Here**: write `initials/init-nn-{slug}.md` from `initials/template/init-template.md`, citing the ADRs it
   depends on.
2. **Claude Code**: `/generate-prp initials/init-nn-{slug}.md`
3. **Here** (optional): review `prps/prp-nn-{slug}.md`
4. **Claude Code**: `/execute-prp prps/prp-nn-{slug}.md`
5. Update TASK.md, and bring back new ADRs and gotchas to this project.

## Key Project Files

The repo is the source of truth. The copies attached to this project can lag behind it.
- `docs/PLANNING.md`: architecture, data contract, phases
- `docs/DECISIONS.md`: architecture, hosting, tooling, and UI ADRs
- `docs/DECISIONS-DATA.md`: NHL data definitions and payload gotchas
- `docs/TASK.md`: current status, reserved spec numbers, and the next free one
- `docs/TESTING.md`: the test layers and the gotcha matrix
- `CLAUDE.md`: Claude Code conventions and the hard rules

## When Starting a New Chat

1. Read TASK.md for where things stand and which spec is next.
2. Read the DECISIONS files before proposing anything. ADRs are binding, so contradicting one means
   writing a new ADR that supersedes it, deliberately.
3. If an attached doc looks older than what the user describes, ask for the current repo version
   rather than reasoning from a stale copy.
4. NHL API calls may not be reachable from this chat's tools. When a payload matters, ask the user
   to fetch it, or mark it "verify in PRP".

## Writing Init Specs: House Rules

- **One spec, one working commit-sized outcome.** If it needs two PRPs, it's two specs.
- **List every output field** that a builder spec touches, with its source endpoint and units
  (fractions 0–1, TOI seconds, localized names). Pages can only sort on what the JSON has
  (ADR-030).
- **Name the gotcha fixtures** the spec must add (TESTING.md gotcha matrix).
- **Page specs** list every user-visible string (both EN and FI), the sort and filter defaults,
  the URL params, and the mobile behavior.
- Mark anything unverified explicitly. Don't paper over it.

## Quick Reference

- **Schedule**: 10:00 America/New_York, EventBridge Scheduler (ADR-005)
- **A Finn**: `nationalityCode == "FIN"` (ADR-010)
- **Completed game**: `gameState ∈ {OFF, FINAL}`, `gameType == 2` (ADR-013, 014)
- **Output envelope**: `schemaVersion`, `generatedAt`, `dataDate`, `season`
- **Data paths**: `/data/kiekkokeskus/{bolts,leijonat}.json`, `history/YYYY-MM-DD/`, `raw/YYYY-MM-DD/`
- **Infra IDs**: bucket `jurigregg-static-site`, distribution `E1ZSW9COVAPN92`, account `490004610151`
- **NHL API**: `api-web.nhle.com/v1`, `api.nhle.com/stats/rest/en`, `records.nhl.com/site/api`;
  community reference github.com/Zmalski/NHL-API-Reference (our fixtures win)
- **Commit format**: `feat(nn):`, `fix(nn):`, `test:`, `docs:`, `infra:`, `chore:`
