# Kiekkokeskus - Project Planning

## Project Vision

Two static NHL stat pages on jurigregg.com: `/bolts` follows the Tampa Bay Lightning, and
`/leijonat` follows every Finnish player in the league. Data refreshes once a day from the NHL's
public (undocumented) API. The point of the project is the things a box score app doesn't give
you: points pace against the playoff cut line, and a single "last night" view of every Finn.

Personal, ad-free, with a not-affiliated disclaimer (ADR-002).

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│  EventBridge Scheduler: kiekkokeskus-daily                       │
│  cron 10:00, ScheduleExpressionTimezone America/New_York (ADR-005)  │
└──────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│  Lambda: kiekkokeskus-collector (Python 3.13, arm64, stdlib)     │
│   1. resolve season from schedule `currentSeason` (ADR-008)         │
│   2. fetch dated endpoints, never /now (ADR-008)                    │
│   3. write raw/YYYY-MM-DD/*.json.gz BEFORE parsing (ADR-006)        │
│   4. build bolts.json, leijonat.json                             │
│   5. write history/YYYY-MM-DD/ snapshots (ADR-007)                  │
└──────────────────────────────────────────────────────────────────┘
          │ fetch                                 │ PutObject (data/kiekkokeskus/* only)
          ▼                                       ▼
┌────────────────────────┐        ┌─────────────────────────────────────┐
│ NHL API (no auth)      │        │ S3 jurigregg-static-site (imported) │
│ api-web.nhle.com/v1    │        │  bolts/  leijonat/  kiekkokeskus/   │
│ api.nhle.com/stats/... │        │  data/kiekkokeskus/{current,        │
│ records.nhl.com/...    │        │    history/, raw/}                  │
└────────────────────────┘        └─────────────────────────────────────┘
                                                  │
                                                  ▼
                                  ┌─────────────────────────────────────┐
                                  │ CloudFront E1ZSW9COVAPN92 (imported)│
                                  │ add-index-html fn → clean URLs      │
                                  │ jurigregg.com/bolts, /leijonat      │
                                  └─────────────────────────────────────┘
                                                  │ same-origin JSON only (ADR-003)
                                                  ▼
                                              Browser
```

The browser never calls the NHL. The site bucket and distribution belong to the main site and
are imported by name, never owned by this stack (ADR-020, ADR-026).

## Cost Budget: ~$0/month (hard ceiling $2)

| Service | Est. Cost | Notes |
|---------|-----------|-------|
| Lambda | $0 | 1 invocation/day, < 1 min, free tier |
| EventBridge Scheduler | $0 | 30 invocations/month, free tier |
| S3 storage | < $0.05 | raw gz + history, few MB/season; noncurrent versions expire (ADR-023) |
| S3 requests | < $0.05 | ~50 PUTs/day |
| CloudFront | $0 | marginal on existing distribution |
| CloudWatch Logs | < $0.10 | 14-day retention set in stack |
| **Total** | **≈ $0** | |

Cost protection: fixed schedule (no fan-out), log retention, lifecycle on versions. Nothing scales
with traffic except CloudFront, which is already paid for by the site.

## Tech Stack

### Collector (`src/kiekkokeskus/`)
- **Runtime**: Python 3.13 on Lambda arm64; local venv pinned to 3.13 (pyenv or Homebrew)
- **Dependencies**: stdlib only at runtime (`urllib`, `json`, `gzip`, `datetime`, `zoneinfo`).
  `boto3` comes from the Lambda runtime and is a dev-only dependency locally.
- **Validation**: hand-written parsers using `.get()` with explicit defaults (ADR-015). No pydantic,
  which keeps the zip dependency-free.
- **Logging**: stdlib `logging` emitting one JSON line per event, read in CloudWatch
- **Tests**: pytest, run against archived real payloads (see TESTING.md)

### Pages (`site/`)
- **Approach**: hand-written HTML + vanilla JS ES modules + CSS. No framework and no build step,
  matching the rest of jurigregg.com.
- **i18n**: shared EN/FI module (ADR-028), `Intl` for numbers and dates
- **Charts**: OPEN — hand-rolled SVG vs. a single vendored small library. Decide in init-09-history.

### Infrastructure (`infra/`)
- **IaC**: CDK v2, TypeScript, one stack `KiekkokeskusStack` (ADR-026), same shape as Pulsar
- **AWS profile**: `default`, always passed explicitly (ADR-025)
- **Region**: us-east-1
- **CI**: GitHub Actions runs pytest and `cdk synth` on push. No CI deploys; deploys run from the
  MacBook via `scripts/deploy.py`.
- **Domain**: jurigregg.com (existing Route 53 zone, nothing new)

## Data Contract (S3 → pages)

This is the project's only "API". Pages read these paths and nothing else.

| Path | Writer | Cache-Control | Purpose |
|------|--------|---------------|---------|
| `/data/kiekkokeskus/bolts.json` | Lambda | `max-age=300` | current /bolts state |
| `/data/kiekkokeskus/leijonat.json` | Lambda | `max-age=300` | current /leijonat state |
| `/data/kiekkokeskus/history/YYYY-MM-DD/{bolts,leijonat}.json` | Lambda | long, immutable | trend charts |
| `/data/kiekkokeskus/history/index.json` | Lambda | `max-age=300` | list of available dates |
| `/data/kiekkokeskus/raw/YYYY-MM-DD/*.json.gz` | Lambda | `max-age=31536000, immutable` | re-parse source, not read by pages |
| `/data/kiekkokeskus/raw/YYYY-MM-DD/_manifest.json` | Lambda | `max-age=300` | per-run metadata; written on success **and** failure |
| `/data/kiekkokeskus/_health.json` | Lambda | `max-age=300` | **ops only** — no `dataDate`/`season` as a data contract; pages don't read it (ADR-032) |

Every output file has this envelope:

```
{
  "schemaVersion": 1,
  "generatedAt": "2026-10-02T14:00:12Z",   # UTC
  "dataDate": "2026-10-01",                # ET game date the data covers
  "season": "20262027",
  ...payload
}
```

Conventions (see DECISIONS-DATA.md):
- Fractions stay 0–1 and are never ×100 (ADR-016). Pages format.
- TOI is integer seconds (ADR-017).
- Names are passed through as localized objects `{default, fi?}`. Builders never pick a
  language (ADR-018, ADR-028).
- Missing values are `null` in OUR output, even when the NHL omits the key (ADR-015). Pages render
  `null` as "–".
- `schemaVersion` bumps on any breaking change. Pages check it and show a stale/error banner on
  a mismatch.

Detailed payload shapes are defined per builder in `init-04-bolts-json.md` and
`init-05-leijonat-json.md`. They are not frozen here.

## Project Structure

```
kiekkokeskus/
├── CLAUDE.md
├── README.md                     # includes not-affiliated disclaimer (ADR-002)
├── pyproject.toml                # package + pytest config, python = "3.13"
├── docs/
│   ├── PLANNING.md               # this file
│   ├── TASK.md
│   ├── DECISIONS.md              # ADRs: architecture, hosting, tooling
│   ├── DECISIONS-DATA.md         # ADRs: NHL data definitions, payload gotchas
│   └── TESTING.md
├── initials/                     # init-nn-*.md specs (written in Claude.ai)
│   └── template/init-template.md
├── prps/                         # prp-nn-*.md, nn matches its init (ADR-029)
│   └── template/prp-template.md
├── .claude/commands/             # generate-prp.md, execute-prp.md
├── examples/
├── src/kiekkokeskus/
│   ├── handler.py                # Lambda entry: orchestration only
│   ├── nhl.py                    # HTTP fetch, retry, URL builders
│   ├── season.py                 # currentSeason resolution, ET date logic
│   ├── archive.py                # raw gz writes, S3 put helpers
│   ├── parse/                    # one module per endpoint family (standings, boxscore, bios…)
│   ├── build_bolts.py
│   ├── build_leijonat.py
│   └── history.py
├── tests/
│   ├── fixtures/                 # REAL archived payloads, gz, named by endpoint+date
│   └── test_*.py
├── site/
│   ├── bolts/index.html          # → s3://…/bolts/
│   ├── leijonat/index.html       # → s3://…/leijonat/
│   └── kiekkokeskus/             # → s3://…/kiekkokeskus/ shared js, css, i18n
├── infra/                        # CDK v2 TS: bin/, lib/kiekkokeskus-stack.ts, cdk.json
└── scripts/                      # Python, not bash (BSD userland, see CLAUDE.md)
    ├── deploy.py                 # cdk deploy + prefix-scoped page syncs (ADR-024)
    ├── apply_lifecycle.py        # merge-not-replace lifecycle rule (ADR-027)
    ├── backfill_standings.py     # rebuild standings history by date (ADR-009)
    └── fetch_fixture.py          # pull a real payload into tests/fixtures/
```

The shared asset prefix `kiekkokeskus/` joins the ADR-020 layout. It is deploy-owned, not written by
the Lambda.

## Development Phases

Each bullet is one `init-nn-*.md` → `prp-nn-*.md` → commit cycle. Numbers are a running sequence
(ADR-029). Specs added later take the next free number, even when they land in an earlier phase.

### Phase 1: Foundation
- [ ] `init-01-repo-scaffold`: structure, pyproject, venv, pytest, GitHub Actions, README + disclaimer
- [ ] `init-02-infra`: CDK stack (Lambda stub, role scoped to `data/kiekkokeskus/*`, schedule, log
      retention, error alarm), lifecycle script, first deploy
- [ ] `init-03-collector-core`: season resolution, fetch with retry, raw archive, dated URLs, first
      real fixtures captured

### Phase 2: Data
- [ ] `init-04-bolts-json`: standings position and gaps, schedule (last result, next 3), full
      skater and goalie rows (ADR-030), special teams with rank
- [ ] `init-05-leijonat-json`: bios pagination for skaters and goalies, the last-night boxscore join
      (ADR-012), team clusters, rookie flag

### Phase 3: Pages
- [ ] `init-06-shared-ui`: i18n module, formatters, base CSS, disclaimer footer, stale-data banner
- [ ] `init-07-bolts-page`
- [ ] `init-08-leijonat-page`

### Phase 4: History
- [ ] `init-09-history`: daily snapshots, `history/index.json`, standings backfill (ADR-009), points
      pace vs. cut line chart

### Future
- Milestone watch from the records API, cached weekly
- GSAx for goalies
- Playoffs (`gameType == 3`, ADR-014 follow-up)
- Last-season comparison overlay on the pace chart (free, thanks to ADR-009)

## Key Constraints

1. **The browser never calls the NHL** (ADR-003). Pages fetch same-origin JSON only.
2. **Raw before parse** (ADR-006). A parse failure must never lose the day's data.
3. **Stdlib-only collector.** This avoids arm64 wheel issues and keeps the zip trivial.
4. **Never touch what this stack doesn't own.** Import the site bucket and distribution; write only
   under `data/kiekkokeskus/`; deploy only `bolts/`, `leijonat/`, `kiekkokeskus/`; never run
   `--delete` at bucket root (ADR-024).
5. **Explicit AWS profile everywhere** (ADR-025).
6. **500-line file limit.** Split into modules as a file approaches it.
7. **Small working commits** in conventional-commit format.
8. **Be polite to the NHL:** sequential requests, a descriptive User-Agent, backoff on 429/5xx,
   about 50 requests per run.

## Success Criteria

1. [ ] At 10:05 ET on a game day, `/leijonat` lists every Finn who scored or started in goal the
       night before, with no manual step.
2. [ ] `/bolts` shows correct standings position, division gap, wildcard gap, and next 3 games,
       matching NHL.com.
3. [ ] The pace-vs-cut-line chart covers the season to date, including days before the first
       deploy (via backfill).
4. [ ] An NHL schema change breaks at most one run, and the previous day's pages stay up.
5. [ ] The EN/FI toggle switches every string, name, and number format on both pages.
6. [ ] The monthly AWS bill stays effectively $0.

## Non-Functional Requirements

### Freshness & Reliability
- Data lands by 10:05 ET daily. The pages show `generatedAt` and display a stale banner when it is
  more than 36 h old.
- **Failure mode:** if a fetch or parse fails, the run does NOT overwrite the current
  `bolts.json`/`leijonat.json`. Yesterday's data stays live, and the raw archive is still written
  for whatever was fetched.
- A CloudWatch alarm on Lambda `Errors >= 1` emails via SNS.
- Lambda timeout 3 min, memory 256 MB. Retries: 3 attempts, exponential backoff.

### Security
- No auth and no secrets. The NHL API is keyless.
- The Lambda role can only `s3:PutObject` on `arn:aws:s3:::jurigregg-static-site/data/kiekkokeskus/*`.
- No bucket policy changes. OAC/bucket policy stays owned by the main site.

### Performance
- Pages total < 150 KB including JSON, with one JSON fetch per page load (history charts
  lazy-load).

### Scalability
- Not applicable: one run per day, about 200 game days per season, static output.
