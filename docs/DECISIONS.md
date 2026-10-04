# Kiekkokeskus - Architecture Decisions

Append-only. A reversed decision keeps its entry and is marked Superseded, with a link.
Numbering is global. ADR numbers match the original D-nn numbering from the planning chat
(D-14 → ADR-014).

Split by subject, so neither file passes 500 lines:
- **This file:** scope, architecture, hosting, deploy, tooling, UI (ADR-001–009, 020+)
- **[DECISIONS-DATA.md](DECISIONS-DATA.md):** NHL data definitions and payload gotchas
  (ADR-010–019). **Read it before touching any parser.**

New ADRs go in whichever file fits the subject and take the next global number.

Unless an entry says otherwise, every payload claim is from a real response fetched 2026-10-02.

---

## ADR-001: Two static pages on jurigregg.com, refreshed daily

**Date**: 2026-10-02
**Status**: Accepted

### Context
The project needs Lightning coverage and Finnish-player coverage without becoming a live-score app.

### Decision
`/bolts` (Tampa Bay Lightning) and `/leijonat` (Finns across the NHL) are standalone pages,
separate from `/sports`. Data refreshes once a day. There are no live scores and no intra-game
updates.

### Consequences
**Positive:** one scheduled job, static output, nothing to scale.
**Negative:** "last night" is up to ~9 h old when a visitor wakes up. That's acceptable.

---

## ADR-002: Republishing NHL data on a public page is a deliberate call

**Date**: 2026-10-02
**Status**: Accepted (confirmed by owner 2026-10-02)

### Context
The NHL endpoints are undocumented and publish no terms for third-party use.

### Decision
Republish anyway, under three conditions: personal site, no ads or commercial use, and a "not
affiliated with the NHL" disclaimer on both pages **and** in the repo README.

### Rationale
This is a judgment, not a permission. It's recorded so it stays visible.

### Consequences
**Negative:** if the NHL ever objects, the response is to take the pages down. No argument.

---

## ADR-003: The browser never talks to the NHL

**Date**: 2026-10-02
**Status**: Accepted

### Decision
EventBridge Scheduler → Lambda → S3 JSON → static page. Pages read only same-origin JSON.

### Rationale
- CORS on `api-web.nhle.com` is unverified, and this design makes it irrelevant.
- Rate limits stay off the visitor's path.
- An NHL schema change breaks one Lambda run, not every page load.

### Alternatives Considered
| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| Browser fetches NHL directly | No backend | CORS unknown, churn hits visitors | Rejected |
| Lambda + S3 JSON | Isolates churn, cacheable | One small backend | Selected |

---

## ADR-004: Not hosted on debian-dev

**Date**: 2026-10-02
**Status**: Accepted

### Context
debian-dev is triple-boot and goes dark whenever it's in another OS.

### Decision
The job runs in AWS. A flaky host is fine for a LAN dashboard and not fine for a public page.

---

## ADR-005: Schedule in America/New_York, not UTC

**Date**: 2026-10-02
**Status**: Accepted

### Decision
Run at 10:00 ET using EventBridge **Scheduler** with `ScheduleExpressionTimezone`, not a classic UTC
cron rule.

### Rationale
- Late West Coast games end around 01:30 ET, which leaves a wide margin.
- Classic rules drift an hour at each DST change. The season crosses DST: `easternUTCOffset` goes
  from `-04:00` to `-05:00` in the schedule payload on 2026-11-01.

---

## ADR-006: Store raw responses before parsing

**Date**: 2026-10-02
**Status**: Accepted

### Decision
Gzipped raw JSON goes to `raw/YYYY-MM-DD/` before any parsing (Tilastokeskus D-20).

### Rationale
The endpoints are community-reverse-engineered and change without notice. With raw stored, a
parse bug costs a re-parse, not a lost day.

---

## ADR-007: History is dated JSON in S3, not a database

**Date**: 2026-10-02
**Status**: Accepted

### Decision
Each run writes `history/YYYY-MM-DD/{bolts,leijonat}.json`. Trend charts read N small files.

### Consequences
**Positive:** no database, no cost, and everything is inspectable with `aws s3 cp`.
**Negative:** a chart covering a full season reads about 200 files. Revisit only if that hurts.
ADR-009 reduces how much depends on snapshots.

---

## ADR-008: Use dated endpoints, not `/now`

**Date**: 2026-10-02
**Status**: Accepted. **Partially superseded by ADR-033** on the season **source** only
(payload field `currentSeason` isn't present in `schedule/{date}` — use `games[].season` /
`standings[0].seasonId` instead). The method (resolve from payload, dated URLs, never `/now`) still holds.

### Context
`/now` URLs are 307 redirects:

| Requested | Resolves to |
|---|---|
| `standings/now` | `standings/2026-10-02` |
| `club-stats/TBL/now` | `club-stats/TBL/20262027/2` |
| `club-schedule-season/TBL/now` | `club-schedule-season/TBL/20262027` |

### Decision
Resolve the season once from a dated payload, then request explicit URLs so every raw archive
records exactly what was asked for. Season is **never computed**. (Field: see ADR-033.)

---

## ADR-009: Standings history is backfillable by date

**Date**: 2026-10-02
**Status**: Accepted (re-verified from raw 2026-10-03)

### Context
`standings/{YYYY-MM-DD}` exists. The question was whether a past date returns standings as of that
date.

### Decision
Yes. `standings/2026-04-01` returns season `20252026` with TBL at 74 GP and 98 pts (46-22-6), which
is as of that date, not the final state. `standings/2026-10-01` has TBL at 1 GP, so a date includes
that date's games.

### Re-verified 2026-10-03 (raw diff)
Captured fixtures `standings-{2026-04-01,2026-10-01,2026-10-02}__2026-10-03.json.gz` match the
summarizing fetch: 2026-04-01 → `20252026`, TBL 74 GP, 98 pts (46-22-6); 2026-10-01/02 →
`20262027`, TBL 1 GP. Caveat removed.

### Consequences
**Positive:** rank and points-pace history, including the cut line, can be rebuilt for any date or
past season, and a missed run is a re-fetch. ADR-007 snapshots remain for data with no dated
endpoint (player and club stats).

---

## ADR-020: Pages and data live in the existing site bucket

**Date**: 2026-10-02
**Status**: Accepted

### Context
jurigregg.com is S3 bucket `jurigregg-static-site` (us-east-1, REST endpoint, `server: AmazonS3`)
behind CloudFront `E1ZSW9COVAPN92`, with DNS in Route 53. Account `490004610151`.

### Decision
Write into that bucket and create no new bucket, distribution, or DNS record.

| Prefix | Owner | Contents |
|---|---|---|
| `bolts/`, `leijonat/` | deploy | pages |
| `kiekkokeskus/` | deploy | shared JS, CSS, i18n |
| `data/kiekkokeskus/{bolts,leijonat}.json` | Lambda | current state |
| `data/kiekkokeskus/history/YYYY-MM-DD/` | Lambda | ADR-007 snapshots |
| `data/kiekkokeskus/raw/YYYY-MM-DD/` | Lambda | ADR-006 archive |

The Lambda role gets `s3:PutObject` on `data/kiekkokeskus/*` only.

### Consequences
**Positive:** zero new hosting, same origin, existing TLS.
**Negative:** `raw/` is publicly readable through CloudFront. That's harmless, since it is the
NHL's own public data. If that ever matters, move it to a non-served bucket.

---

## ADR-021: Clean URLs come from the existing `add-index-html` function

**Date**: 2026-10-02
**Status**: Accepted

### Context
The site's viewer-request CloudFront Function appends `index.html` to URIs ending in `/`, and
`/index.html` to URIs with no `.`.

### Decision
`/bolts` and `/bolts/` both resolve to `bolts/index.html`. JSON paths contain a `.` and pass through
untouched. Never modify the function, because it serves the whole site.

---

## ADR-022: Current-state JSON sets its own Cache-Control

**Date**: 2026-10-02
**Status**: Accepted

### Context
Site objects carry no `Cache-Control`, so CloudFront applies the cache policy default (24 h if
`CachingOptimized`).

### Decision
The Lambda writes `{bolts,leijonat}.json` and `history/index.json` with
`Cache-Control: public, max-age=300`. History and raw objects are write-once and cached long.

### Alternatives Considered
| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| Invalidate after each run | Works with any TTL | Extra API call, extra IAM | Rejected |
| Per-object Cache-Control | No extra calls | None | Selected |

### Verified 2026-10-03
Distribution `E1ZSW9COVAPN92` uses the **legacy TTL config** (no `CachePolicyId`): `MinTTL=0`,
`DefaultTTL=3600`, `MaxTTL=86400`. Origin `max-age=300` wins; live `_health.json` through
CloudFront advertises `cache-control: public, max-age=300`.

---

## ADR-023: Expire noncurrent versions on the data prefix

**Date**: 2026-10-02
**Status**: Accepted

### Context
Bucket versioning is on (`x-amz-version-id` present). Daily overwrites would pile up versions
forever.

### Decision
A lifecycle rule on `data/kiekkokeskus/` expires noncurrent versions after 7 days. It is applied
per ADR-027.

---

## ADR-024: Deploys are prefix-scoped, and nothing runs `--delete` at bucket root

**Date**: 2026-10-02
**Status**: Accepted

### Decision
Pages live in this repo and deploy independently, e.g.
`aws s3 sync site/bolts/ s3://jurigregg-static-site/bolts/ --profile default`.

### Rationale
A root-level `s3 sync --delete` from the main site's repo would wipe `bolts/`, `leijonat/`,
`kiekkokeskus/`, and all Lambda data. The same rule therefore goes into the main site repo's
CLAUDE.md.

---

## ADR-025: AWS profile is `default`, always stated explicitly

**Date**: 2026-10-02
**Status**: Accepted

### Decision
The MacBook's only profile is `default` (IAM user `juri-dev`), which is the intended dev identity.
Every script and IaC config still names it (`--profile default` / `AWS_PROFILE=default`), so
nothing relies on ambient credentials and it stays greppable.

---

## ADR-026: IaC is CDK v2 in TypeScript, matching Pulsar

**Date**: 2026-10-02
**Status**: Accepted

### Context
Pulsar is the only personal project confirmed to use IaC. It uses CDK v2 TS in `infra/` with its
own package.json, one stack, and a deploy script. Metronome and ghost are probably console-built.

### Decision
Use the same shape: a single `KiekkokeskusStack` holding the collector Lambda (Python 3.13, arm64),
its role, the `kiekkokeskus-daily` schedule (`ScheduleExpressionTimezone: America/New_York`), log
retention, and an error alarm. The account is already CDK-bootstrapped in us-east-1. The collector
stays Python, and TypeScript exists only in `infra/`.

The site bucket and distribution are **imported** (`Bucket.fromBucketName`) and never owned, so
`cdk destroy` can't touch the site.

### Alternatives Considered
| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| CDK TS | Matches Pulsar, known workflow | Two languages in repo | Selected |
| CDK Python | One language | Diverges from Pulsar | Rejected |
| SAM | Small, native ScheduleV2 | New tool for this account | Rejected |

---

## ADR-027: The ADR-023 lifecycle rule is applied by a merging script, not by CDK

**Date**: 2026-10-02
**Status**: Accepted

### Context
CDK can't manage an imported bucket's lifecycle, and `PutBucketLifecycleConfiguration` **replaces
the whole rule set**. A naive put silently deletes any existing site rules.

### Decision
`scripts/apply_lifecycle.py` reads the current configuration, upserts our rule by ID, and puts the
merged result back. It is idempotent and safe to re-run.

---

## ADR-028: EN/FI toggle on both pages

**Date**: 2026-10-02
**Status**: Accepted (supersedes ADR-019)

### Decision
Each page has an EN | FI toggle at the top, built as one shared module.
- **Names:** FI renders `name.fi ?? name.default`. EN renders `name.default`.
- **UI strings:** come from a per-language dictionary. Nothing is hardcoded in markup.
- **Numbers and dates:** use `Intl` with `en-US` / `fi-FI`. Hockey conventions (`.915` vs
  `91,5 %`) are settled in the page specs.
- **Choosing a language:** `?lang=fi|en` wins, then the stored choice (`localStorage`), then
  `navigator.language` (`fi*` gives FI), then EN.
- `<html lang>` updates on toggle.

### Consequences
**Positive:** shareable links in either language. Kucherov stays Kucherov in English.
**Negative:** every UI string needs two translations, which is accepted.

---

## ADR-029: Init specs and PRPs are numbered `init-nn-*` / `prp-nn-*`

**Date**: 2026-10-02
**Status**: Accepted

### Decision
- Specs are `initials/init-nn-{slug}.md`, with a two-digit running number starting at `01`.
- Each PRP takes its spec's number and slug: `init-04-bolts-json.md` → `prps/prp-04-bolts-json.md`.
- Numbers are never reused or renumbered. A spec that is dropped keeps its number (mark it in TASK.md),
  and a spec added later takes the next free number, whatever phase it belongs to.
- Templates are exempt: `initials/template/init-template.md` and `prps/template/prp-template.md`.

### Rationale
- `ls` gives build order for free.
- Init and PRP pair up at a glance, and commits and TASK.md can say "04" unambiguously.

### Consequences
**Negative:** number order stops matching phase order once specs get inserted later. Accepted;
PLANNING.md phases are the source of truth for grouping.

---

## ADR-030: Player tables are sortable and filterable in the browser

**Date**: 2026-10-02
**Status**: Accepted

### Decision
- Both pages show player tables that the visitor can **filter by position** and **sort by any
  column**.
- Sorting and filtering are client-side over the full rows in the JSON, with no extra requests.
- **Builders emit full player rows, not pre-cut "leader" lists.** Every rostered skater and goalie
  with this season's stats goes in. Top-N views are a page concern.
- Each row carries `positionCode` (`C`/`L`/`R`/`D`/`G`). The filter groups are All / F (C+L+R) /
  D. Goalies are a separate table with their own columns.
- **Both pages use the same column set.** `/leijonat` adds a team column, which `/bolts` hides.
  - Skaters: GP, G, A, P, +/-, PIM, TOI/GP, PPG, PPP, SHG, GWG, SOG, S%, FO% (blank for non-faceoff
    takers), hits, blocks.
  - Goalies: GP, GS, W, L, OTL, SV%, GAA, SO, TOI.
  - Which endpoint supplies each field is settled in init-04/05. Hits and blocks are expected from
    the stats REST `realtime` reports and are **unverified**. If a field can't be sourced, it is
    dropped here explicitly, not silently.
- Sort and filter state lives in the URL (`?pos=D&sort=toi&dir=desc`), alongside `?lang=`, so a
  view can be shared.

### Rationale
The data is small: about 30 TBL skaters, and roughly 60 Finns before goalies. Shipping full rows
costs a few KB and leaves every view question to the page.

### Consequences
**Positive:** new views and columns need no collector change, provided the field is already in the
row.
**Negative:** the builder specs must list every column the pages might sort on, because missing
fields need a collector change and a `schemaVersion` bump.

---

## ADR-031: Python tooling is hatchling + ruff + pytest, pinned to 3.13

**Date**: 2026-10-02
**Status**: Accepted

### Decision
- **Build**: hatchling, `src/` layout, editable installs.
- **Lint + format**: ruff, one tool for both. Rules `E`, `F`, `W`, `I`, `UP`, `B`, `SIM`;
  `line-length = 100`; `target-version = "py313"`. `extend-exclude = ["*.md"]` so ruff 0.16's
  default behavior of reformatting Python inside markdown doesn't rewrite the illustrative
  snippets in CLAUDE.md and `prps/template/prp-template.md`.
- **Tests**: pytest + pytest-cov, with `fail_under = 80` on `src/kiekkokeskus/`.
- **Pin**: `.python-version` holds `3.13`, matching the Lambda runtime.
- **CI**: GitHub Actions runs `ruff check`, `ruff format --check`, and `pytest`. Workflow top
  declares `permissions: contents: read`; it never holds AWS credentials.

### Alternatives Considered
| Option | Pros | Cons | Verdict |
|---|---|---|---|
| setuptools | ubiquitous | heavier config for no gain in a tiny stdlib package | Rejected |
| black + flake8 + isort | mature, familiar | three tools where ruff does the job | Rejected |

### References
initials/init-01-repo-scaffold.md, prps/prp-01-repo-scaffold.md

---

## ADR-032: Operational baseline — health file, alarms, no async retries, deploy gate

**Date**: 2026-10-03
**Status**: Accepted

### Decision
- **`_health.json` is ops-only** (ADR-002 posture). Carries `schemaVersion`, `generatedAt`,
  `status`, `version`, `trigger`, `dataDate`, `rawCount`. Not read by pages; written on success
  only.
- **Alarms** (CW → SNS `kiekkokeskus-alerts` → greggjuri@gmail.com):
  `kiekkokeskus-collector-errors` (`Errors Sum ≥ 1` / 5 min, missing = not-breaching) +
  `kiekkokeskus-collector-missed` (`Invocations Sum < 1` / 24 h, missing = breaching — catches a
  schedule that stops firing silently).
- **Lambda async retries = 0** (`CfnEventInvokeConfig MaximumRetryAttempts: 0`). The collector
  owns HTTP retries; Lambda's default would triple failing runs and alarm emails.
- **Scheduler Target `Input='{"source":"scheduled"}'`.** Handler reads
  `event.get("source") == "scheduled"` → `trigger="schedule"`. Live-captured in
  `tests/fixtures/scheduler-event__2026-10-04.json`: AWS passes Input verbatim, no envelope.
- **Deploy gate**: `scripts/deploy.py` runs `cdk diff` and exits by default; `--approved` runs
  `cdk deploy --require-approval never`. Gate lives in the human workflow, not CDK's TTY prompt
  (which doesn't survive subprocess invocation).

### Verified live (2026-10-04)
Forced-error invoke raised `RuntimeError`; errors alarm OK → ALARM within 2 min; SNS email
delivered; alarm returned to OK after one period.

### References
initials/init-02-infra.md, prps/prp-02-infra.md

---

## Template for New Decisions

```markdown
## ADR-XXX: Title
**Date**: YYYY-MM-DD · **Status**: Proposed/Accepted/Deprecated/Superseded
### Context / Decision / Rationale / Alternatives (optional) / Consequences / References
```

Status values: **Proposed**, **Accepted**, **Deprecated**, **Superseded** (link the replacement).
Numbers never reused. Create an ADR when choosing between valid approaches, making a hard-to-reverse
call, setting a pattern, or learning a payload fact that later code must respect.

## Key Principles

1. **Real payloads first.** Every data rule here came from a fetched response, never from docs.
2. **Raw before parse.** Undocumented endpoints change, and the archive makes that survivable.
3. **The browser never calls the NHL.** Same-origin JSON only.
4. **Never touch what we don't own.** Import the site bucket and distribution, write only under our
   prefixes, and never `--delete` at root.
5. **Formatting happens once, in the page.** Data stays raw units: fractions, seconds, localized
   name objects.
