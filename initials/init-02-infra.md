# init-02: Infra

**Created**: 2026-10-03
**Phase**: 1 Foundation
**Depends On**: init-01
**ADRs**: ADR-003, 005, 006 (envelope only), 020, 021, 022, 023, 024, 025, 026, 027, 031; adds ADR-032

---

## Problem Statement

Nothing runs in AWS yet. Before any NHL code exists we need to prove the whole path works: the
schedule fires, the Lambda runs with a role that can write **only** under `data/kiekkokeskus/`,
the object lands with the right headers, CloudFront serves it, and a failure emails someone.
Finding an IAM or caching problem now is cheap. Finding it inside init-03's NHL work is not.

## Goal

`KiekkokeskusStack` is deployed. A stub collector runs daily at 10:00 ET and writes
`data/kiekkokeskus/_health.json`, which is publicly readable at
`https://jurigregg.com/data/kiekkokeskus/_health.json` with `Cache-Control: public, max-age=300`.
An error in the Lambda emails greggjuri@gmail.com. The ADR-023 lifecycle rule is on the bucket,
merged with whatever rules were already there. CI also synthesizes and tests the stack.

## Requirements

### Must Have (P0)

1. **CDK app in `infra/`** (CDK v2, TypeScript, same shape as Pulsar; ADR-026)
   - `infra/package.json`, `tsconfig.json`, `cdk.json`, `bin/kiekkokeskus.ts`,
     `lib/kiekkokeskus-stack.ts`, `test/kiekkokeskus-stack.test.ts` (jest)
   - `.nvmrc` at the repo root pinning Node 22 LTS, used locally and in CI
   - Stack `KiekkokeskusStack` with `env: { account: '490004610151', region: 'us-east-1' }`
     hardcoded, so `cdk synth` needs no credentials and no lookups
   - Every created resource is named or tagged `kiekkokeskus-*`. Add stack-level tags:
     `project=kiekkokeskus`.

2. **Imported, never owned** (ADR-020, 026)
   - The site bucket is imported via `Bucket.fromBucketName(this, 'SiteBucket',
     'jurigregg-static-site')`. No CloudFront constructs at all, imported or otherwise.

3. **Lambda `kiekkokeskus-collector`**
   - Runtime Python 3.13, architecture `ARM_64`, handler `kiekkokeskus.handler.handler`
   - Code asset is `src/` only, so the zip contains the `kiekkokeskus` package and nothing else
     (no tests, `.venv`, or `infra`)
   - Timeout 3 min, memory 256 MB
   - Env: `BUCKET=jurigregg-static-site`, `PREFIX=data/kiekkokeskus/`
   - **Async retry attempts: 0.** The collector retries its own HTTP calls (init-03). Lambda's
     default of 2 async retries would triple a failing run and its alarms.
   - Explicit LogGroup `/aws/lambda/kiekkokeskus-collector`, retention 14 days

4. **IAM, the exact scope**
   - Collector role: AWSLambdaBasicExecutionRole-equivalent logging on its own log group, plus
     `s3:PutObject` on `arn:aws:s3:::jurigregg-static-site/data/kiekkokeskus/*` only. Nothing else
     on S3: no `GetObject`, `ListBucket`, `DeleteObject`, or `Put*Configuration`.
   - The bucket policy is **not** modified. IAM in the same account is sufficient.

5. **Schedule `kiekkokeskus-daily`** (ADR-005)
   - EventBridge **Scheduler**, `cron(0 10 * * ? *)`, `scheduleExpressionTimezone:
     'America/New_York'`, flexible time window OFF
   - Its own execution role, scoped to `lambda:InvokeFunction` on the collector only

6. **Alerting**
   - SNS topic `kiekkokeskus-alerts`, with an email subscription to `greggjuri@gmail.com`
   - CloudWatch alarm `kiekkokeskus-collector-errors`: Lambda `Errors` Sum ≥ 1 over a 5-min
     period, 1 datapoint, missing data = not breaching. The action is the SNS topic.

7. **Stub handler, `src/kiekkokeskus/handler.py`**
   - `handler(event, context)` writes `{PREFIX}_health.json`:
     ```
     {
       "schemaVersion": 1,
       "generatedAt": "<UTC ISO-8601, Z>",
       "status": "ok",
       "version": "<kiekkokeskus.__version__>",
       "trigger": "<'schedule' | 'manual'>"
     }
     ```
     `trigger` is `'schedule'` when the event comes from Scheduler, `'manual'` otherwise. The
     detection rule is decided in the PRP from the real Scheduler event shape.
   - `ContentType: application/json`, `CacheControl: public, max-age=300` (ADR-022)
   - The `put` function is **injected**, defaulting to a boto3 S3 client created lazily inside the
     handler module. Tests pass a fake. `now` is injected too (CLAUDE.md conventions).
   - Returns `{"status": "ok", "key": "<key written>"}` and logs one JSON line.
   - The health file is an ops artifact, **not** a data output: it doesn't carry
     `dataDate`/`season` and isn't read by the pages. Record that in the PLANNING data contract.
   - It stays in place permanently. init-03's collector keeps writing it at the end of every
     successful run.

8. **`scripts/apply_lifecycle.py`** (ADR-023, 027)
   - Rule ID `kiekkokeskus-noncurrent-expiry`, filter prefix `data/kiekkokeskus/`,
     `NoncurrentVersionExpiration: 7 days`, status Enabled
   - Pure function `merge_rules(existing: list[dict], ours: dict) -> list[dict]`: upserts by ID and
     preserves every other rule **verbatim**, including legacy-format rules
   - Handles `NoSuchLifecycleConfiguration`, meaning there are no existing rules
   - **Dry run by default**: prints the current rules, the merged rules, and a diff. Writes only
     with `--apply`.
   - `--profile default` is passed explicitly (ADR-025)
   - boto3 only, as a dev dependency. It's a local script and never ships in the Lambda.

9. **`scripts/deploy.py`**
   - Runs `cdk deploy KiekkokeskusStack --require-approval broadening` with `AWS_PROFILE=default`
     from `infra/`
   - Has a page-sync section that does nothing until `site/` exists (init-06 fills it in). Its
     allowed prefixes are hard-coded to `bolts/`, `leijonat/`, `kiekkokeskus/`, and it refuses
     any other target (ADR-024).

10. **`scripts/smoke.py`** (TESTING.md layer 6; stdlib `urllib` only)
    - `https://jurigregg.com/` → 200, and `https://jurigregg.com/sports` → 200. These prove the
      rest of the site is untouched.
    - `https://jurigregg.com/data/kiekkokeskus/_health.json` → 200, valid JSON, `status == "ok"`,
      `generatedAt` less than 26 h old, response `Cache-Control` contains `max-age=300`
    - Exits non-zero on any failure, and prints one line per check

11. **CI**: a second job, `infra`, in `.github/workflows/ci.yml`. It uses Node from `.nvmrc` and
    runs `npm ci`, `npm test`, `npx cdk synth`, all in `infra/`. No AWS credentials;
    `permissions: contents: read` stays.

12. **Tests**
    - **Layer 3 (pytest)**, handler: correct key under the prefix, body fields and types, both
      headers, `trigger` detection, the injected `now` is used, and nothing is written outside
      `PREFIX`
    - **pytest**, lifecycle merge: empty existing set; existing unrelated rules preserved
      byte-for-byte; our rule replaced, not duplicated, on re-run (idempotent); legacy top-level
      `Prefix` rule preserved
    - **Layer 4 (jest)**, per TESTING.md: zero `AWS::S3::Bucket`, zero
      `AWS::CloudFront::Distribution`, zero `AWS::S3::BucketPolicy`; Scheduler timezone
      `America/New_York`; Lambda `python3.13` + `arm64`; the role's S3 statement is exactly
      `s3:PutObject` on the exact prefix ARN; LogGroup retention 14; alarm and SNS email
      subscription present; async invoke config `MaximumRetryAttempts: 0`

13. **First deploy and verification**
    1. `cdk diff` is read and shown to Juri. Every resource is new and named `kiekkokeskus-*`.
       There are **no** changes to anything else.
    2. `python scripts/deploy.py`
    3. Juri confirms the SNS subscription email (one click).
    4. `aws lambda invoke --function-name kiekkokeskus-collector --profile default out.json`
    5. `python scripts/smoke.py` passes.
    6. `python scripts/apply_lifecycle.py` (dry run): show Juri the merged rules. Run `--apply`
       **only after Juri says go**.
    7. Re-run the dry run: no diff.

### Should Have (P1)

1. **Missed-run alarm**: `kiekkokeskus-collector-missed`, Lambda `Invocations` Sum < 1 over 1 day,
   treat missing as **breaching**. It catches a disabled or broken schedule, which the errors
   alarm can't see.
2. **Force a failure once to prove the alarm**: invoke the stub with a test event
   (`{"forceError": true}`), confirm the alarm fires and the email arrives, then confirm the alarm
   returns to OK. The handler supports `forceError` only for this purpose. Document it in the
   handler docstring.

### Nice to Have (P2)

1. `scripts/invoke.py`, a thin wrapper around `aws lambda invoke` that prints the decoded result and
   the last 20 log lines.

## Output / Data Contract

| Field | Source | Units / type | Nullable | Notes |
|---|---|---|---|---|
| `schemaVersion` | constant | int, `1` | no | |
| `generatedAt` | injected `now` | ISO-8601 UTC string, `Z` suffix | no | |
| `status` | constant | `"ok"` | no | Errors raise; no `"error"` file is ever written |
| `version` | `kiekkokeskus.__version__` | string | no | |
| `trigger` | event shape | `"schedule"` / `"manual"` | no | |

- **S3 key**: `data/kiekkokeskus/_health.json` only
- **Headers**: `Content-Type: application/json`, `Cache-Control: public, max-age=300`
- **schemaVersion change?** n/a, this is a new ops file

## Fixtures and Gotchas

No NHL payloads. One real AWS payload is needed:

| Fixture to capture | Why | Gotcha rows |
|---|---|---|
| `tests/fixtures/scheduler-event__2026-10-03.json` | the actual event the Scheduler target delivers, used for `trigger` detection | none (AWS, not NHL); provenance row in `tests/fixtures/README.md` |

Capture it from the collector's log of the first scheduled run, or from a one-off schedule. Don't
write it by hand.

## Ownership Check

- **AWS resources created**: Lambda, IAM roles, Scheduler schedule, LogGroup, SNS topic plus
  subscription, CloudWatch alarm(s). All `kiekkokeskus-*`.
- **S3 prefixes written**: `data/kiekkokeskus/_health.json` only
- **Touches anything owned by the main site?** **One sanctioned exception:** the bucket's lifecycle
  configuration gets our rule merged in, through `apply_lifecycle.py` only, dry run first, with
  `--apply` after Juri's explicit go (ADR-023, 027). Nothing else: no bucket policy, CORS,
  versioning, distribution, cache policy, or CloudFront Function changes.

## ADR to Add (ADR-032, in `docs/DECISIONS.md`)

**ADR-032: Operational baseline: health file, error alarm, no async retries.** The collector
writes `data/kiekkokeskus/_health.json` at the end of every successful run. It is ops-only, carries
no `dataDate`/`season`, and pages don't read it. The Lambda's async retries are 0, because the
collector owns its own retries and Lambda's defaults would multiply runs and alerts. Errors alarm
to SNS email at greggjuri@gmail.com. Rationale: the health file proves IAM scope, headers, and
CloudFront end to end before any NHL logic exists, and stays as the cheapest "is it alive" check.
Add the missed-run alarm to the ADR if P1 lands.

## Doc Updates in This Spec

- `docs/PLANNING.md` data contract table: add the `_health.json` row (ops-only, not enveloped).
- `CLAUDE.md`, Development Environment:
  - "Never `source .venv/bin/activate`. Call venv binaries directly: `.venv/bin/python`,
    `.venv/bin/pytest`, `.venv/bin/ruff`, `.venv/bin/pip`. CI status via `gh run watch` /
    `gh run list`, not curl polling."
  - "If `python3.13` isn't on PATH (Homebrew keg-only), use
    `/opt/homebrew/opt/python@3.13/bin/python3.13`."
- `CLAUDE.md` Quick Commands: `python scripts/apply_lifecycle.py` (dry run) / `--apply`.
- `docs/TASK.md`: the usual start and complete moves.

## Success Criteria

- [ ] `cdk diff` before the first deploy shows only new `kiekkokeskus-*` resources
- [ ] jest layer-4 assertions pass locally and in CI, and `cdk synth` runs in CI without credentials
- [ ] pytest passes (handler + lifecycle merge), coverage ≥ 80%
- [ ] A manual invoke writes `_health.json`, and `scripts/smoke.py` passes, including `/` and
      `/sports`
- [ ] `curl -sI https://jurigregg.com/data/kiekkokeskus/_health.json` shows
      `cache-control: public, max-age=300`
- [ ] The first **scheduled** run at 10:00 ET updates `generatedAt` with `trigger: "schedule"`
- [ ] The SNS subscription is confirmed, and (P1) a forced error produces an email
- [ ] The lifecycle dry-run diff was shown, `--apply` ran after approval, a re-run shows no diff,
      and every pre-existing rule is still present
- [ ] ADR-032 is added, and PLANNING, CLAUDE.md, and TASK.md are updated
- [ ] No file over 500 lines

## Out of Scope

- Any NHL fetching, the raw archive, or parsing (init-03)
- Page syncs and `site/` (init-06). `deploy.py` only has the guarded placeholder.
- History, backfill (init-09)
- Changing the site's cache policy, even if verification shows it would override our
  Cache-Control. That gets reported, and handled as a separate decision.

## Verify in PRP

- [ ] The CDK bootstrap stack `CDKToolkit` exists in 490004610151/us-east-1 (from Pulsar), and its
      version is compatible with the chosen `aws-cdk-lib`
- [ ] Whether the installed `aws-cdk-lib` has a stable Scheduler L2 (`aws-scheduler` +
      `aws-scheduler-targets`). Use it if so, otherwise `CfnSchedule`.
- [ ] **The CloudFront default behavior's cache policy:** fetch it by ID and check `MinTTL`. If
      `MinTTL > 300`, our `max-age=300` is overridden and ADR-022 doesn't hold as written. Report
      it; don't change the policy.
- [ ] The bucket's current lifecycle configuration (`get-bucket-lifecycle-configuration`): record
      what's there before the merge
- [ ] Bucket Object Ownership / ACL settings don't block a plain `PutObject` from a same-account
      role
- [ ] `/data/kiekkokeskus/_health.json` passes through `add-index-html` untouched, since it
      contains a `.` (ADR-021)
- [ ] The real Scheduler → Lambda event shape, for `trigger` detection

## Open Questions

(none)

## Notes

Suggested commit sequence:
1. `feat(02): stub handler writes health file` (handler + pytest)
2. `infra(02): CDK app and KiekkokeskusStack` (infra + jest, `.nvmrc`)
3. `chore(02): CI infra job`
4. `feat(02): deploy and smoke scripts`, followed by the first deploy and verification
5. `feat(02): lifecycle merge script`, followed by the dry run, approval, and apply
6. `docs(02): ADR-032, PLANNING, CLAUDE, TASK`
