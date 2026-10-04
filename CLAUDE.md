# CLAUDE.md - Claude Code Instructions

Project-specific instructions for Claude Code. Claude.ai is where things get thought through; this
repo is where they get done (`/generate-prp`, `/execute-prp`, tests, deploys, git).

## Project Overview

**Kiekkokeskus**: two static NHL stat pages on jurigregg.com. `/bolts` covers the Tampa Bay
Lightning, and `/leijonat` covers every Finnish player in the NHL. A Lambda fetches the NHL's
undocumented API once a day at 10:00 ET, archives the raw responses, and writes JSON into the
site's S3 bucket. The pages read only that JSON.

**Tech Stack**: Python 3.13 stdlib collector (Lambda arm64) | vanilla HTML/JS/CSS pages, no build |
S3 JSON, no database | CDK v2 TypeScript

## Read Before Working

| Before you… | Read |
|---|---|
| anything | `docs/PLANNING.md` (architecture, data contract, phases), `docs/TASK.md` |
| touch a parser, builder, or fixture | `docs/DECISIONS-DATA.md` (**every NHL payload gotcha**) |
| touch infra, S3, deploy, or the pages' URLs | `docs/DECISIONS.md` (ADR-020–027) |
| write a test | `docs/TESTING.md` |

ADRs are binding. If a task seems to need contradicting one, stop and say so. Don't work around it.

## Development Environment

Development happens on the MacBook ("Claudebook", macOS, Apple Silicon), not the Debian box.

- **Python 3.13 in `.venv`**, always. It's pinned to the Lambda runtime. Never use system Python.
  If `python3.13` isn't on `PATH` (Homebrew keg-only), create the venv with
  `/opt/homebrew/opt/python@3.13/bin/python3.13 -m venv .venv`.
- **Call venv binaries directly, don't `source .venv/bin/activate`.** Use `.venv/bin/python`,
  `.venv/bin/pytest`, `.venv/bin/ruff`, `.venv/bin/pip`. Keeps each command self-contained and
  survives subprocess invocation.
- **CI status via `gh run watch` / `gh run list`**, not curl polling (install with `brew install gh`;
  the public GitHub Actions API also works unauthenticated).
- **BSD userland.** No `sed -i ''`/`sed -i` portability games and no `date -d`. Anything beyond a
  one-liner is a Python script in `scripts/`.
- **Case-insensitive filesystem.** Keep filename casing exact and consistent, because CI on Linux is
  case-sensitive and will disagree. Never rename by changing case alone.
- **AWS profile `default`, always passed explicitly**: `--profile default` on every CLI call,
  `AWS_PROFILE=default` for CDK and boto3 (ADR-025). Never rely on ambient credentials.
- Region `us-east-1`. Account `490004610151`.
- **arm64 Lambda.** The collector is stdlib-only, so there are no wheels to mismatch. Do not add
  runtime dependencies (PLANNING, Key Constraint 3). `boto3` is provided by the Lambda runtime and
  is a dev dependency locally.

## Quick Commands

```bash
# Setup (once)
/opt/homebrew/opt/python@3.13/bin/python3.13 -m venv .venv   # or `python3.13` if on PATH
.venv/bin/pip install -e '.[dev]'
cd infra && PATH="/opt/homebrew/opt/node@22/bin:$PATH" npm ci && cd ..

# Test
.venv/bin/pytest                                   # all
.venv/bin/pytest --cov=kiekkokeskus --cov-report=term-missing
.venv/bin/ruff check .                             # lint
.venv/bin/ruff format --check .                    # formatting (use `ruff format .` to fix)
cd infra && PATH="/opt/homebrew/opt/node@22/bin:$PATH" npm test   # CDK assertions
node --test site/kiekkokeskus/                     # page logic, Node built-in runner
.venv/bin/python scripts/smoke.py                  # after every deploy (TESTING.md layer 6)

# Lifecycle (ADR-023, ADR-027)
.venv/bin/python scripts/apply_lifecycle.py            # dry run (prints merged rules)
.venv/bin/python scripts/apply_lifecycle.py --apply    # write merged rules (ADR-027)

# Infra
cd infra && PATH="/opt/homebrew/opt/node@22/bin:$PATH" AWS_PROFILE=default npx cdk synth
cd infra && PATH="/opt/homebrew/opt/node@22/bin:$PATH" AWS_PROFILE=default npx cdk diff   # ALWAYS run before deploy

# Deploy — gate lives in --approved, not CDK's TTY prompt (ADR-032)
.venv/bin/python scripts/deploy.py              # cdk diff and exit
.venv/bin/python scripts/deploy.py --approved   # cdk deploy --require-approval never

# Run the collector now, in AWS
aws lambda invoke --function-name kiekkokeskus-collector --profile default --region us-east-1 out.json && cat out.json

# Capture a real payload as a test fixture (filename date is ET capture date; ADR-033)
.venv/bin/python scripts/fetch_fixture.py <url>    # writes tests/fixtures/<slug>__<captureDateET>.json.gz

# Look at what the pages see
aws s3 cp s3://jurigregg-static-site/data/kiekkokeskus/bolts.json - --profile default | python -m json.tool
```

Scripts that don't exist yet are created by the init spec that needs them (see PLANNING phases).

## File Structure

```
kiekkokeskus/
├── CLAUDE.md
├── README.md                 # includes the not-affiliated disclaimer (ADR-002)
├── pyproject.toml
├── docs/                     # PLANNING, TASK, DECISIONS, DECISIONS-DATA, TESTING
├── initials/                 # init-nn-*.md (written in Claude.ai, not here)
├── prps/                     # prp-nn-*.md, nn matches its init (ADR-029)
├── .claude/commands/         # generate-prp.md, execute-prp.md
├── examples/
├── src/kiekkokeskus/         # collector package (handler, nhl, season, archive, parse/, build_*)
├── tests/                    # pytest; tests/fixtures/ = REAL archived payloads
├── site/
│   ├── bolts/                # → s3://jurigregg-static-site/bolts/
│   ├── leijonat/             # → …/leijonat/
│   └── kiekkokeskus/         # → …/kiekkokeskus/ (shared JS, CSS, i18n)
├── infra/                    # CDK v2 TS, one stack
└── scripts/                  # Python only
```

## Critical Rules

### 1. Never touch what this project doesn't own
The S3 bucket `jurigregg-static-site` and CloudFront distribution `E1ZSW9COVAPN92` belong to the
main site, and the whole of jurigregg.com lives there.
- CDK **imports** them (`fromBucketName` etc.) and never creates, modifies, or owns them (ADR-026).
- The Lambda writes only under `data/kiekkokeskus/`.
- Deploys sync only `bolts/`, `leijonat/`, and `kiekkokeskus/`. **Never run `aws s3 sync` or
  `aws s3 rm` against the bucket root, and never use `--delete` outside those three prefixes**
  (ADR-024).
- Never modify the `add-index-html` CloudFront Function, the bucket policy, or the distribution
  config (ADR-021).
- Never `put-bucket-lifecycle-configuration` directly, since it replaces every rule. Use
  `scripts/apply_lifecycle.py` (ADR-027).
- Never run `cdk destroy` without explicit instruction in the current conversation.

### 2. NHL API rules
- **Raw before parse** (ADR-006). Archive the response first, then parse. A parse error must never
  lose the fetch.
- **Dated URLs only**, never `/now` (ADR-008). The season comes from `currentSeason` and is never
  computed.
- Sequential requests, a descriptive `User-Agent`, and retry with backoff on 429/5xx (3 attempts).
- **On failure, never overwrite current state.** If the build fails, `bolts.json`/`leijonat.json`
  keep yesterday's data.
- The browser never calls the NHL (ADR-003). Pages fetch only `/data/kiekkokeskus/…`.

### 3. Data contract
- Every output carries the envelope `schemaVersion`, `generatedAt`, `dataDate`, `season`
  (PLANNING).
- Fractions stay 0–1. TOI is integer seconds. Names stay localized objects. Missing means explicit
  `null` (ADR-015–018).
- A breaking change to an output shape bumps `schemaVersion` and updates the pages in the same
  commit.
- Current-state JSON is written with `Cache-Control: public, max-age=300` (ADR-022).

### 4. File size
- **500 lines maximum per file, docs included.** Split by module, or by subject for docs (that's
  why DECISIONS is two files).

### 5. Commits
- One working, tested step per commit, in conventional format: `feat:`, `fix:`, `refactor:`,
  `docs:`, `test:`, `chore:`, `infra:`.
- Reference the spec number when there is one: `feat(04): standings gaps in bolts.json`.
- Run `pytest` before every commit. Run `cdk synth` before any commit that touches `infra/`.

### 6. Testing
- Fixtures are **real archived payloads**, never hand-written JSON. Hand-edited variants are
  allowed only to inject a documented gotcha, and they are named so (`…__no-shots-goalie.json.gz`).
- Every gotcha in DECISIONS-DATA.md has a test fed by a fixture that contains it.
- Coverage is at least 80% on `src/kiekkokeskus/`. Coverage is not the goal; the contract is
  (TESTING.md).

### 7. Documentation
- Update `docs/TASK.md` when starting and finishing a spec.
- New architectural choices or payload discoveries get an ADR in the right DECISIONS file, with the
  next global number.
- A surprise found while debugging gets written down where the next session will look for it.

## Coding Conventions

### Python (collector)

```python
from __future__ import annotations
import logging
from typing import Any

log = logging.getLogger(__name__)

def parse_standings_row(row: dict[str, Any]) -> dict[str, Any]:
    """Parse one standings row. Keys absent at 0 GP become None (ADR-015)."""
    return {
        "team": row["teamAbbrev"]["default"],            # required: KeyError is a real bug
        "gamesPlayed": row.get("gamesPlayed", 0),
        "pointPctg": row.get("pointPctg"),               # fraction 0-1 or None, never x100
        "streak": _streak(row.get("streakCode"), row.get("streakCount")),
    }
```

- Type hints everywhere. Plain functions and dicts or `dataclasses`, with no runtime deps.
- `parse/` is pure: dict in, dict out, no I/O, no clock. Pass "today" in explicitly; never call
  `date.today()` inside logic. ET dates use `zoneinfo.ZoneInfo("America/New_York")`.
- `handler.py` orchestrates and holds no logic worth testing on its own.
- Required keys use `row["k"]` and fail loudly. Optional keys use `.get()` with an explicit
  default. Unknown enum values (e.g. `gameState`) are logged and treated as the safe default
  (ADR-013).
- Logging is one JSON object per line: `log.info(json.dumps({"event": "fetch", "url": u,
  "status": s}))`.

### JavaScript (pages)

- Vanilla ES modules (`<script type="module">`). No framework, no bundler, no npm in `site/`.
- Each page fetches its single JSON file. History charts lazy-load.
- All user-visible text goes through the i18n module, and numbers and dates through `Intl`
  formatters (ADR-028). No string literals in markup or render code.
- Render `null` as "–". Check `schemaVersion`. Show the stale banner when `generatedAt` is more
  than 36 h old.
- The not-affiliated disclaimer appears in every page footer (ADR-002).

### CDK (infra)

- One stack, `KiekkokeskusStack`. Resource names are prefixed `kiekkokeskus-`.
- The site bucket is imported by name. IAM policies use exact ARNs with the
  `data/kiekkokeskus/*` prefix, with no wildcards beyond that.
- The schedule uses EventBridge Scheduler with `scheduleExpressionTimezone: 'America/New_York'`
  (ADR-005).
- Set log retention explicitly (14 days).
- Comment anything non-obvious with its ADR number.

## PRP Workflow

```bash
/generate-prp initials/init-04-bolts-json.md    # → prps/prp-04-bolts-json.md
/execute-prp prps/prp-04-bolts-json.md
```

The PRP keeps the spec's number and slug (ADR-029). Init specs are written in Claude.ai. If one is
ambiguous, ask; don't invent the missing decision.

## Debugging Checklist

1. **Lambda logs**: `aws logs tail /aws/lambda/kiekkokeskus-collector --since 1d --profile default`
2. **Raw archive**: check what the NHL actually sent with
   `aws s3 ls s3://jurigregg-static-site/data/kiekkokeskus/raw/<date>/ --profile default`. Re-parse
   locally from it before assuming the parser is wrong.
3. **Payload drift**: diff today's raw payload against the fixture. A new or missing key means a
   new ADR in DECISIONS-DATA.md and a new fixture.
4. **Pages**: open the browser Network tab, check the JSON's `generatedAt`, and check whether
   CloudFront served a cached copy (`x-cache`).
5. **Recent changes**: `git log --oneline -15`.

## DO NOT

- Write anything outside the prefixes in Rule 1, or run an unscoped `s3 sync`/`s3 rm`/`--delete`.
- Add runtime Python dependencies to the collector.
- Write hand-crafted fixture JSON in place of a real payload.
- Call `/now` endpoints or compute the season ID.
- Multiply a fraction by 100 anywhere except the page formatter.
- Use default AWS credentials implicitly.
- Contradict an ADR without raising it first.
- Create files over 500 lines.
- Commit `.venv/`, `cdk.out/`, `node_modules/`, or `out.json`.

## Reference Documents

- `docs/PLANNING.md`: architecture, data contract, phases, constraints
- `docs/DECISIONS.md`: architecture, hosting, and tooling ADRs
- `docs/DECISIONS-DATA.md`: NHL data definitions and payload gotchas
- `docs/TASK.md`: current work
- `docs/TESTING.md`: testing standards
- `examples/`: code patterns to follow
- Community API reference: https://github.com/Zmalski/NHL-API-Reference (unofficial; our own
  fixtures win when they disagree)
