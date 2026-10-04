# PRP-02: Infra

**Created**: 2026-10-03
**Initial**: `initials/init-02-infra.md`
**Status**: Complete
**ADRs**: ADR-003, 005, 006, 020, 021, 022, 023, 024, 025, 026, 027, 031; adds ADR-032 (ops baseline)

---

## Overview

### Problem Statement

Nothing runs in AWS yet. Prove the whole path — schedule → Lambda → scoped IAM → CloudFront with
right headers → error email — before any NHL code. Finding an IAM/cache/ownership bug now is
cheap; finding it inside init-03 is not.

### Proposed Solution

CDK v2 TS stack `KiekkokeskusStack`: collector Lambda stub (py3.13 arm64), scoped role, L1
`CfnSchedule` (L2 is still alpha) at 10:00 America/New_York, 14-day log group, SNS alert topic +
email, errors alarm, missed-run alarm. Stub writes `data/kiekkokeskus/_health.json` with
`Cache-Control: max-age=300`. Site bucket + distribution **imported**, never owned.
`scripts/apply_lifecycle.py` merges our noncurrent-expiry rule into existing rules (today: none).
`scripts/deploy.py` and `scripts/smoke.py` complete the ops path. CI gets a second job (`infra`)
that `cdk synth`s with no creds.

### Success Criteria

- [ ] `cdk diff` shows only new `kiekkokeskus-*` resources before first deploy (Step 6)
- [ ] jest layer-4 passes locally + CI; `cdk synth` runs in CI without creds (Steps 3–4)
- [ ] pytest green (handler + lifecycle), coverage ≥ 80% (Steps 2, 7)
- [ ] Manual invoke writes `_health.json`; smoke passes `/`, `/sports`, headers (Step 6)
- [ ] First scheduled run on 2026-10-04 updates `generatedAt`, `trigger: "schedule"`; event fixture captured (Step 8)
- [ ] SNS confirmed; forced error produces email; alarm returns OK (Step 8)
- [ ] Lifecycle dry-run shown → user go → `--apply` → re-run no diff; pre-existing rules preserved (Step 7)
- [ ] ADR-032 added, ADR-022 Verified note added, PLANNING + CLAUDE.md + TASK.md updated (Step 9)
- [ ] No file over 500 lines

---

## Context

### Related Documentation

- `docs/PLANNING.md`: Architecture Overview, Data Contract table, Non-Functional §Freshness/Security
- `docs/DECISIONS.md`: ADR-003, 005, 006, 020–027, 031
- `docs/TESTING.md`: Layer 3 (handler orchestration), Layer 4 (infra), Layer 6 (smoke)
- `docs/DECISIONS-DATA.md`: n/a (no NHL payloads)

### Dependencies — init-01 complete (ADR-031, `src/kiekkokeskus` package).

### Files to Modify/Create

```
.nvmrc                                          # NEW: 22 — pinned at repo root (one file, not per-dir)
infra/package.json                              # NEW
infra/package-lock.json                         # NEW (generated)
infra/tsconfig.json                             # NEW
infra/cdk.json                                  # NEW
infra/bin/kiekkokeskus.ts                       # NEW
infra/lib/kiekkokeskus-stack.ts                 # NEW (~220 lines)
infra/test/kiekkokeskus-stack.test.ts           # NEW (jest + CDK Template)
infra/jest.config.js                            # NEW
src/kiekkokeskus/handler.py                     # NEW (~70 lines)
tests/test_handler.py                           # NEW
scripts/apply_lifecycle.py                      # NEW (~140 lines)
scripts/deploy.py                               # NEW (~60 lines)
scripts/smoke.py                                # NEW (~60 lines)
tests/test_apply_lifecycle.py                   # NEW
.github/workflows/ci.yml                        # MODIFY: add `infra` job
docs/DECISIONS.md                               # MODIFY: append ADR-032
docs/PLANNING.md                                # MODIFY: data contract table + ops `_health.json`
docs/TASK.md                                    # MODIFY: In Progress in Step 1, Completed in Step 9
CLAUDE.md                                       # MODIFY: Development Environment + Quick Commands
tests/fixtures/scheduler-event__YYYY-MM-DD.json # NEW (captured after first scheduled run)
tests/fixtures/README.md                        # MODIFY: provenance row for the scheduler event
```

Every file stays under 500 lines. The stack TS is the largest at ~220 lines.

---

## Verification of Unconfirmed Facts

| Assumption | Result | Follow-up |
|---|---|---|
| CDKToolkit in 490004610151/us-east-1 | **Yes.** BootstrapVersion 30, `UPDATE_COMPLETE`. | compatible with aws-cdk-lib 2.272 |
| Stable Scheduler L2 | **No — still alpha** (`@aws-cdk/aws-scheduler-alpha@2.186.0-alpha.0`). | Use **`CfnSchedule`** (L1) + plain IAM role |
| CloudFront MinTTL ≤ 300 | **MinTTL 0**, DefaultTTL 3600, MaxTTL 86400, **no CachePolicyId** (legacy TTL config, `ForwardedValues`). | ADR-022 holds; record "Verified 2026-10-03" on ADR-022 in Step 9 |
| Bucket lifecycle today | `NoSuchLifecycleConfiguration` — no rules. | merge script's empty-existing branch is the first-run path |
| Bucket Ownership / ACL / PAB | `BucketOwnerEnforced`, PAB all-four-on, versioning Enabled. | same-account `PutObject` clean; ADR-023 premise confirmed |
| `/data/kiekkokeskus/_health.json` through `add-index-html` | Function appends `index.html` only when URI ends `/` or has no `.`; our path has `.` → passes through. (URL probes 403, not a rewrite.) | — |
| Scheduler → Lambda event shape | Deferred to Step 8 (needs deployed stack). | **Design**: Scheduler Target `Input='{"source":"scheduled"}'`; handler reads `event.get("source")=="scheduled"` → `"schedule"`. Fixture confirms shape. |

Additional pre-check: Node 22 not installed locally (brew has Node 25). Step 0 adds the install.

---

## Technical Specification

### Output Schema (`data/kiekkokeskus/_health.json`)

```json
{
  "schemaVersion": 1,
  "generatedAt": "2026-10-03T14:00:12Z",
  "status": "ok",
  "version": "0.1.0",
  "trigger": "schedule"
}
```

- All fields non-nullable. No `dataDate`/`season` — this is **ops**, not data (recorded in PLANNING).
- Headers: `Content-Type: application/json`, `Cache-Control: public, max-age=300` (ADR-022).
- `schemaVersion`: new file, no change elsewhere.

### Module Design — `src/kiekkokeskus/handler.py`

```python
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Callable
import json
import logging
import os

from kiekkokeskus import __version__

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

PutObject = Callable[[str, bytes, str, str], None]   # (key, body, content_type, cache_control)


def _default_put() -> PutObject:
    import boto3   # lazy — tests inject a fake and never hit boto3
    client = boto3.client("s3")
    bucket = os.environ["BUCKET"]
    def put(key: str, body: bytes, content_type: str, cache_control: str) -> None:
        client.put_object(Bucket=bucket, Key=key, Body=body,
                          ContentType=content_type, CacheControl=cache_control)
    return put


def _now_default() -> datetime:
    return datetime.now(timezone.utc)


def handler(event: dict[str, Any], context: Any,
            *, put: PutObject | None = None,
            now: Callable[[], datetime] | None = None) -> dict[str, Any]:
    """Writes _health.json. forceError=True raises for alarm testing (ADR-032)."""
    log.info(json.dumps({"event": "invoked", "payload": event}))
    if event.get("forceError"):
        raise RuntimeError("forced error for alarm test")
    put = put or _default_put()
    now = now or _now_default                 # callable, NOT invoked here
    prefix = os.environ["PREFIX"]             # e.g. "data/kiekkokeskus/"
    key = f"{prefix}_health.json"
    trigger = "schedule" if event.get("source") == "scheduled" else "manual"
    payload = {
        "schemaVersion": 1,
        "generatedAt": now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "ok",
        "version": __version__,
        "trigger": trigger,
    }
    body = json.dumps(payload, separators=(",", ":")).encode()
    put(key, body, "application/json", "public, max-age=300")
    log.info(json.dumps({"event": "health_written", "key": key, "trigger": trigger}))
    return {"status": "ok", "key": key}
```

**Two bug guards baked in**:
- `now = now or _now_default` (no parens). Calling `_now_default()` here then `now()` below would
  invoke a `datetime` instance → `TypeError` on every real run. Tests that always inject `now`
  would miss it; see the required default-path test below.
- The event is logged once at entry, so the scheduler-event fixture in Step 8 can be captured
  from the CloudWatch log line with `event: "invoked"`.

Tests cover (name every row):
1. injected `put` + injected fixed `now` → key, body, headers, `trigger="manual"` on `{}` event
2. injected `put` + injected `now` + `event={"source":"scheduled"}` → `trigger="schedule"`
3. injected `put` + injected `now` + `event={"forceError":True}` → `RuntimeError`
4. **only `put` injected, `now` default** — asserts the default-callable path runs and
   `generatedAt` matches ISO-8601 `YYYY-MM-DDTHH:MM:SSZ`. This is the test that catches a future
   regression of the parens bug.
5. Exactly one `put` call per invocation; nothing written outside `PREFIX`.

### Infra — resources in `KiekkokeskusStack` (TypeScript)

- Import `Bucket.fromBucketName(this, 'SiteBucket', 'jurigregg-static-site')`. No `BucketPolicy`,
  no CloudFront constructs.
- `aws_lambda.Function` `kiekkokeskus-collector`:
  - Runtime `PYTHON_3_13`, Architecture `ARM_64`, handler `kiekkokeskus.handler.handler`
  - Code: `Code.fromAsset(path.join(__dirname, '..', '..', 'src'), { exclude: ['**/__pycache__', '**/*.pyc', '**/*.pyo'] })` — zip is the `kiekkokeskus/` package only (no tests, infra, venv, caches).
  - Timeout 180s, memory 256 MiB
  - Env: `BUCKET=jurigregg-static-site`, `PREFIX=data/kiekkokeskus/`
  - `logGroup`: explicit `new LogGroup(this, 'LogGroup', { logGroupName: '/aws/lambda/kiekkokeskus-collector', retention: RetentionDays.TWO_WEEKS, removalPolicy: RemovalPolicy.RETAIN })`
  - **`CfnEventInvokeConfig`** (or `fn.configureAsyncInvoke({ retryAttempts: 0 })`) with
    `MaximumRetryAttempts: 0` (ADR-032)
- Role for collector: `AWSLambdaBasicExecutionRole` managed policy, plus one inline statement:
  `s3:PutObject` on `arn:aws:s3:::jurigregg-static-site/data/kiekkokeskus/*`. Nothing else.
- Scheduler, L1:
  ```ts
  const schedulerRole = new iam.Role(this, 'SchedulerRole', { assumedBy: new iam.ServicePrincipal('scheduler.amazonaws.com') });
  fn.grantInvoke(schedulerRole);
  new scheduler.CfnSchedule(this, 'DailySchedule', {
    name: 'kiekkokeskus-daily',
    flexibleTimeWindow: { mode: 'OFF' },
    scheduleExpression: 'cron(0 10 * * ? *)',
    scheduleExpressionTimezone: 'America/New_York',
    target: { arn: fn.functionArn, roleArn: schedulerRole.roleArn, input: '{"source":"scheduled"}' },
  });
  ```
- SNS topic `kiekkokeskus-alerts` with `EmailSubscription('greggjuri@gmail.com')`.
- Alarm `kiekkokeskus-collector-errors`: metric `AWS/Lambda Errors Sum`, period 5 min, 1 datapoint,
  threshold ≥ 1, `treatMissingData: NOT_BREACHING`, `addAlarmAction(new SnsAction(topic))`.
- Alarm `kiekkokeskus-collector-missed` (added in Step 8): `AWS/Lambda Invocations Sum`, period 1 day, threshold < 1, `treatMissingData: BREACHING`.
- Stack tags: `project=kiekkokeskus`. Hardcoded `env: { account: '490004610151', region: 'us-east-1' }`.

### Expected `cdk diff` (first deploy)

All resources new; imported `SiteBucket` doesn't appear. **Any** non-`kiekkokeskus-*` change → STOP.

---

## Implementation Steps

Each step is one validated commit, pushed, with CI (where applicable) green before the next.

### Step 0: Prereqs (no commit)

- **Node 22**: `brew install node@22` (keg-only; access via `/opt/homebrew/opt/node@22/bin/node`
  or add to `PATH`). Do **not** `brew link --overwrite node@22` — same risk as the python@3.13
  case. Verify: `/opt/homebrew/opt/node@22/bin/node --version` → `v22.x.x`.
- **AWS creds**: `aws sts get-caller-identity --profile default` already works (user `juri-dev`).
- **No fixtures to capture yet.** The scheduler-event fixture is captured in Step 8 after the first
  scheduled run.

### Step 1: `docs(02): start`

Move `init-02-infra` In Progress in `docs/TASK.md`; move the `init-01` entry only if not already;
update `*Last updated:*`. **Commit + push.** No CI gates this one (no code touched).

### Step 2: `feat(02): stub handler writes health file`

**Files**: `src/kiekkokeskus/handler.py`, `tests/test_handler.py`

Handler as in Module Design. Test cases are listed in that section (five rows, including the
critical default-`now` path).

**Validation** (dev venv binaries directly, no `source`; see Step 9 CLAUDE.md update):
```bash
.venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/pytest --cov=kiekkokeskus
```
- [ ] coverage ≥ 80% on `src/kiekkokeskus/`
- [ ] `pytest tests/test_handler.py -v` passes with `forceError` test
- [ ] No new runtime deps (`dependencies = []` unchanged)

**Commit + push**; wait for CI green on this SHA.

### Step 3: `infra(02): CDK app and KiekkokeskusStack`

**Files**: `.nvmrc` (`22\n`), `infra/package.json`, `infra/tsconfig.json`, `infra/cdk.json`,
`infra/jest.config.js`, `infra/bin/kiekkokeskus.ts`, `infra/lib/kiekkokeskus-stack.ts`,
`infra/test/kiekkokeskus-stack.test.ts`.

`infra/package.json` dependencies: `aws-cdk-lib` ~2.272, `constructs` ^10, `typescript` ^5, `ts-node`,
`jest`, `ts-jest`, `@types/jest`, `@types/node`. **Do not** add Scheduler alpha modules.

`cdk.json`: `"app": "npx ts-node --prefer-ts-exts bin/kiekkokeskus.ts"`,
`"@aws-cdk/core:*"` feature flags per CDK v2 current defaults.

Jest layer-4 (`Template.fromStack(stack)`) — one assertion each:
- `resourceCountIs('AWS::S3::Bucket', 0)`, `AWS::CloudFront::Distribution`, `AWS::S3::BucketPolicy`
- `AWS::Scheduler::Schedule`: `ScheduleExpressionTimezone: 'America/New_York'`, `FlexibleTimeWindow.Mode: 'OFF'`
- `AWS::Lambda::Function`: `Runtime: 'python3.13'`, `Architectures: ['arm64']`
- `AWS::Lambda::EventInvokeConfig`: `MaximumRetryAttempts: 0`
- `AWS::Logs::LogGroup`: name `/aws/lambda/kiekkokeskus-collector`, retention `14`
- `AWS::SNS::Subscription`: Protocol `email`, Endpoint `greggjuri@gmail.com`
- `AWS::CloudWatch::Alarm`: MetricName `Errors`, Namespace `AWS/Lambda`, Threshold `1`
- `AWS::IAM::Policy`: has a statement with `Action: 's3:PutObject'`, `Resource: 'arn:aws:s3:::jurigregg-static-site/data/kiekkokeskus/*'` (exact, no wildcards beyond the prefix)

**Validation**:
```bash
cd infra
/opt/homebrew/opt/node@22/bin/npm ci
/opt/homebrew/opt/node@22/bin/npm test
AWS_PROFILE=default /opt/homebrew/opt/node@22/bin/npx cdk synth > /dev/null
```
- [ ] jest green: every assertion above passes
- [ ] `cdk synth` produces a template under `infra/cdk.out/`; no credentials prompt (hardcoded env)
- [ ] `wc -l infra/lib/kiekkokeskus-stack.ts` < 500

**Commit + push.**

### Step 4: `chore(02): CI infra job`

**Files**: `.github/workflows/ci.yml`

Add a second job `infra` with `actions/setup-node@v4 node-version-file: .nvmrc`, `cache: npm`,
`cache-dependency-path: infra/package-lock.json`. Steps: `npm ci`, `npm test`, `npx cdk synth`,
all `working-directory: infra`. No AWS creds. `permissions: contents: read` remains at the top.

**Validation**:
- [ ] CI run on this SHA shows both `lint-and-test` **and** `infra` jobs green
- [ ] No `AWS_*` env, no OIDC, no `secrets.*` in `ci.yml`: `grep -E 'AWS_|secrets\.' .github/workflows/ci.yml` returns nothing

**Commit + push**; verify CI green.

### Step 5: `feat(02): deploy and smoke scripts`

**Files**: `scripts/deploy.py`, `scripts/smoke.py`

`scripts/deploy.py`:
- Builds subprocess env with **Node 22 on front of PATH** (keg-only). Errors clearly if the dir
  is missing. Always sets `AWS_PROFILE=default`.
- **Default run** → `cdk diff KiekkokeskusStack` and exits. No deploy.
- **`--approved`** → `cdk deploy KiekkokeskusStack --require-approval never` (ADR-032). The
  approval gate lives in the human workflow (/execute-prp: show diff → get go → run with
  `--approved`), not in CDK's TTY prompt, which doesn't survive subprocess invocation.
- **Guarded placeholder** page sync: `ALLOWED_PREFIXES = ('bolts/', 'leijonat/', 'kiekkokeskus/')`.
  init-06 fills in the loop. Any `s3 sync` destination not starting with one of these exits.

`scripts/smoke.py` (stdlib `urllib` only): `/` → 200; `/sports` → 200;
`/data/kiekkokeskus/_health.json` → 200, `Cache-Control` contains `max-age=300`, JSON parses,
`status=="ok"`, `schemaVersion==1`, `generatedAt` within 26h of now (UTC). One line per check;
non-zero on any failure.

**Validation**:
- [ ] `.venv/bin/pytest` still green (scripts aren't under coverage; this just checks nothing regressed)
- [ ] `.venv/bin/python -m py_compile scripts/deploy.py scripts/smoke.py` (syntax check)

**Commit + push.**

### Step 6: Deploy, invoke, smoke (no commit)

Interactive — needs user approval.

1. `python scripts/deploy.py` → prints `cdk diff` and exits. **Show the diff to the user.** If
   **anything** not `kiekkokeskus-*` changes, STOP (CLAUDE.md Rule 1).
2. On user `go`: `python scripts/deploy.py --approved` → runs `cdk deploy --require-approval never`.
3. User confirms the SNS subscription email (one click; AWS sends it immediately).
4. `aws lambda invoke --function-name kiekkokeskus-collector --profile default /tmp/out.json && cat /tmp/out.json` → should print `{"status":"ok","key":"data/kiekkokeskus/_health.json"}`.
5. `python scripts/smoke.py` → every check passes, including `/` and `/sports`.
6. `curl -sI https://jurigregg.com/data/kiekkokeskus/_health.json` → confirm `cache-control: public, max-age=300`.

- [ ] Each check logged in the execution report
- [ ] If smoke fails for any reason that touches `/` or `/sports`, **do not** proceed to lifecycle; roll back

### Step 7: `feat(02): lifecycle merge script`

**Files**: `scripts/apply_lifecycle.py`, `tests/test_apply_lifecycle.py`

```python
RULE = {
    "ID": "kiekkokeskus-noncurrent-expiry",
    "Status": "Enabled",
    "Filter": {"Prefix": "data/kiekkokeskus/"},
    "NoncurrentVersionExpiration": {"NoncurrentDays": 7},
}

def merge_rules(existing: list[dict], ours: dict) -> list[dict]:
    """Upsert by ID; preserve every other rule verbatim (incl. legacy `Prefix`)."""
    out = [r for r in existing if r.get("ID") != ours["ID"]]
    out.append(ours)
    return out
```

CLI: default = dry run (fetch existing, catching `NoSuchLifecycleConfiguration` → `[]`; print
current, merged, diff; exit 0). `--apply` calls `put_bucket_lifecycle_configuration`. Session built
with hardcoded `profile_name='default'` (ADR-025). boto3-only, no runtime deps.

**pytest** (`tests/test_apply_lifecycle.py`): pure `merge_rules` unit tests —
- empty existing → `[ours]`
- unrelated rule preserved byte-for-byte
- re-run of merge is idempotent (no duplication)
- legacy top-level `Prefix` rule preserved
- our rule replaces, not appends, on re-run with a different NoncurrentDays value

Teach pytest to import from `scripts/` by adding `pythonpath = ["scripts"]` under
`[tool.pytest.ini_options]` in `pyproject.toml`. Then `from apply_lifecycle import merge_rules`
works in the test.

**Validation**:
- [ ] `.venv/bin/pytest tests/test_apply_lifecycle.py -v` green
- [ ] `.venv/bin/pytest --cov=kiekkokeskus` ≥ 80% (unchanged — scripts aren't under coverage; the pure merge_rules tests still prove behavior)
- [ ] Dry run against prod: `python scripts/apply_lifecycle.py` prints the merged rules with only our rule added (existing config is empty today, per the pre-check). **Show user.**
- [ ] After user `go`: `python scripts/apply_lifecycle.py --apply`.
- [ ] Re-run dry run: zero diff.
- [ ] `aws s3api get-bucket-lifecycle-configuration --bucket jurigregg-static-site --profile default` shows exactly our rule.

**Commit + push** (scripts + tests). Any user-facing live apply happens **after** the commit so the script is traceable.

### Step 8: Missed-run alarm + force-error proof + scheduler fixture (`feat(02): P1 alarms + force-error smoke`)

**Required.** Without the missed-run alarm, a schedule that silently stops firing is the one
failure nothing would surface. The forced-error test is also the only proof that the alert email
actually reaches the inbox. **Hold this step until after the first scheduled run on 2026-10-04.**

- Add `kiekkokeskus-collector-missed` alarm in `lib/kiekkokeskus-stack.ts` and a jest assertion
  (`AWS/Lambda Invocations Sum < 1` over 1 day, `treatMissingData: BREACHING`).
- `cdk diff` → only the new alarm. `cdk deploy`.
- `aws lambda invoke --function-name kiekkokeskus-collector --payload '{"forceError":true}' --profile default --cli-binary-format raw-in-base64-out /tmp/err.json`.
- Wait ≤ 10 min for the errors alarm to fire; confirm email arrival; alarm returns to OK.
- From the 10:00 ET scheduled run on 2026-10-04, extract the `event: "invoked"` log line, save
  the `payload` object as `tests/fixtures/scheduler-event__2026-10-04.json`, add a provenance row.

**Validation**: email received; `tests/fixtures/README.md` has the new row; fixture file is the
captured object (not hand-written).

**Commit + push.**

### Step 9: `docs(02): ADR-032, PLANNING, CLAUDE, TASK` + `docs(02): complete`

**Files**: `docs/DECISIONS.md`, `docs/PLANNING.md`, `CLAUDE.md`, `docs/TASK.md`,
`prps/prp-02-infra.md` (status → Complete).

- Append **ADR-032** (ops baseline + deploy gate):
  - `_health.json` is ops-only (no `dataDate`/`season`); errors alarm → SNS email to greggjuri@gmail.com;
    missed-run alarm (`Invocations Sum < 1` / day, treat-missing-as-breaching).
  - Lambda async retries = 0 — the collector owns its own retries, Lambda defaults would
    multiply runs and alerts.
  - **Deploy gate**: `scripts/deploy.py` default is `cdk diff` and exit; `--approved` runs
    `cdk deploy --require-approval never`. The gate lives in the human workflow (show diff →
    get go → `--approved`), not in CDK's TTY prompt (which doesn't survive subprocess
    invocation and would silently fail-open on security-sensitive changes).
- Append a one-line **"Verified 2026-10-03"** note to **ADR-022** recording the legacy TTL finding
  (MinTTL=0, DefaultTTL=3600, MaxTTL=86400, no CachePolicyId — origin `max-age` wins). Keeps the
  cache question in the ADR where it lives; ADR-032 stays about ops.
- `docs/PLANNING.md` Data Contract table: add the `_health.json` row with a note "ops-only, not enveloped with dataDate/season".
- `CLAUDE.md` Development Environment: add the two bullets per spec (venv binaries directly, no `source`; `python3.13` keg-only path). Quick Commands: add `python scripts/apply_lifecycle.py` dry/`--apply`.
- `docs/TASK.md`: `init-02-infra` → Recently Completed; `*Last updated:*`.

**Commit + push**; wait for CI green; then flip PRP status: `docs(02): complete`.

---

## Testing Requirements

| Layer | Tests | Fixture |
|---|---|---|
| 3 Handler | `tests/test_handler.py` — key, headers, body, trigger (`source=="scheduled"`), injected `now`, **default-path with only `put` injected**, `forceError`, nothing outside `PREFIX` | — (Step-8 fixture confirms real event) |
| 4 Infra | `infra/test/kiekkokeskus-stack.test.ts` — 11 assertions per Technical Spec | — |
| 6 Smoke | `scripts/smoke.py` — `/`, `/sports`, `_health.json` headers | — |
| 7 Manual | SNS confirm, forced-error email arrival, scheduler event capture | — |

Layers 1, 2, 5 n/a (no NHL parsers/builders/pages yet). Coverage ≥ 80% on `src/kiekkokeskus/`.

---

## Error Handling and Edge Cases

| Case | Handling | Tested in |
|---|---|---|
| Unexpected event shape | `event.get("source")` safe; non-match → `"manual"` | handler test |
| boto3 import at test time | Lazy inside `_default_put`; injected `put` never imports boto3 | handler test (offline) |
| Lifecycle: no existing rules | `NoSuchLifecycleConfiguration` → `existing = []` | lifecycle test empty case |
| Lifecycle: legacy `Prefix` rule | Preserved verbatim; merge touches by ID only | lifecycle test legacy case |
| `cdk diff` shows non-`kiekkokeskus-*` | STOP + show diff (Emergency Stop) | Step 6 |
| Smoke fails on `/` or `/sports` | STOP, roll back; do not touch lifecycle | Step 6 |

---

## Cost Impact

Still ~$0/month. One Lambda invocation/day, 14-day log retention, SNS topic (free until used), one
CloudWatch alarm (first 10 free). Noncurrent versions expire after 7 days, keeping S3 flat.

---

## Rollback Plan

1. **Infra**: **Only on Juri's explicit instruction**, `cd infra && AWS_PROFILE=default npx cdk destroy KiekkokeskusStack`. Imports leave site bucket + distribution untouched; LogGroup is `RETAIN` so logs survive. Do not pass `--force` and do not run without the instruction.
2. **Lifecycle**: always `apply_lifecycle.py` with our rule removed from the merge. **Never** `delete_bucket_lifecycle` and never a bare `put` that drops rules — those would wipe anything the main site added.
3. **Data**: `_health.json` noncurrent versions kept 7 days; restore via `s3api copy-object` from a prior VersionId.
4. **Code**: `git revert` the PRP's commits in reverse order and push.
5. **SNS subscription**: `aws sns unsubscribe` with the subscription ARN.

---

## Open Questions — none

---

## Confidence Scores

| Dimension | Score | Notes |
|---|---|---|
| Clarity | 9 | Explicit, payload-free; sentinel-input design justified in-line. |
| Feasibility | 8 | More surface area than init-01; CDKToolkit v30 current, Scheduler L1 well-trodden. |
| Completeness | 9 | Every requirement mapped; every Verify-in-PRP resolved. P1 is now required (Step 8). |
| Payload certainty | 9 | No NHL payloads; AWS event design is sentinel-based, fixture confirms shape. |
| **Average** | **8.75** | **Ready** |
