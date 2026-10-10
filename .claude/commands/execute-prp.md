# Execute PRP

Execute a Project Requirement Plan step by step.

## Arguments
- `$ARGUMENTS`: the PRP path, e.g. `prps/prp-04-bolts-json.md`

## Instructions

You are executing a PRP for **Kiekkokeskus**.

### Step 0: Pre-flight

1. `$ARGUMENTS` matches `prps/prp-nn-{slug}.md`, and `initials/init-nn-{slug}.md` exists.
2. Read `CLAUDE.md`, the PRP in full, and every ADR it lists. If it touches data, also read
   `docs/DECISIONS-DATA.md`.
3. Dependencies are complete in `docs/TASK.md`.
4. The PRP's status is Ready, confidence is ≥ 7 on average with no score below 5, and Open
   Questions are resolved. Otherwise, stop and report.
5. Working tree is clean (`git status`), the venv is active, and `pytest` is green **before**
   starting.
6. Update `docs/TASK.md`: move this spec to In Progress. Commit: `docs(nn): start`.

### Step 1: Execute Each Implementation Step

For each step, in order:
1. **Announce** the step.
2. **Implement** following CLAUDE.md conventions: pure parsers, injected `now`, `.get()` with
   explicit defaults for optional keys, no new runtime deps.
3. **Validate** the touched layers:
   ```bash
   pytest                                # always
   cd infra && npm test && AWS_PROFILE=default npx cdk synth   # if infra/ touched
   node --test site/kiekkokeskus/        # if site/ touched
   ```
4. **Commit** only when green: `git add <specific paths>` (never `git add .` blindly), then
   `git commit -m "{type}(nn): {description}"`.

Fixtures are captured with `scripts/fetch_fixture.py`, never typed. A payload that differs from
what the PRP expected is a **new fact**: add an ADR to DECISIONS-DATA.md, then a fixture and a
test, and only then the fix.

### Step 2: Handle Failures

- Diagnose from evidence (test output, the raw payload, logs), make the minimal fix, then
  re-validate.
- If a step can't pass without deviating from the PRP, stop and report. Don't improvise around an
  ADR.

### Step 3: Deploy (only if the PRP includes a deploy step)

1. `cd infra && AWS_PROFILE=default npx cdk diff`, then **read the diff**.
   - If it changes, replaces, or deletes **anything not named `kiekkokeskus-*`**, STOP, show the
     diff, and wait for the user.
   - If it would replace the Lambda or schedule, say so before deploying.
2. `python scripts/deploy.py`
3. `python scripts/smoke.py`, which must pass, including `/` and `/sports` returning 200.
4. If the collector changed: `aws lambda invoke --function-name kiekkokeskus-collector --profile default out.json`,
   then check the logs and the new `generatedAt` on the JSON.
5. Work through the PRP's manual checklist items and report each result.

### Step 4: Final Validation

- Full suite green: pytest (coverage ≥ 80% on `src/kiekkokeskus/`), infra tests, page tests.
- Every success criterion checked, with the test or check that proves it.
- Golden-file diffs reviewed and explained.
- No code file over 500 lines (ADR-034; docs exempt): `wc -l` on code files touched.

### Step 5: Update Documentation

1. `docs/TASK.md`: move the spec to Recently Completed with a one-line outcome. Resolve or add Open
   Questions.
2. New ADRs, with the next global number, in the right file:
   - payload facts and data definitions → `docs/DECISIONS-DATA.md`, plus a row in TESTING.md's
     gotcha matrix
   - everything else → `docs/DECISIONS.md`
3. PRP status → Complete.
4. Commit: `docs(nn): complete`.

### Step 6: Report

```
## PRP-nn Execution Complete

**PRP**: prps/prp-nn-{slug}.md
**Status**: Complete / Partial / Blocked

### Commits
- {hash} {message}

### Tests
- pytest: X passed, coverage Y%
- infra: X passed | pages: X passed
- smoke: pass/fail | manual: X/Y

### Success Criteria
- [x] … (proved by …)

### New Facts / ADRs
- ADR-0xx: …

### Issues Encountered
### Follow-ups (candidates for new init specs; next free number in TASK.md)
```

## Emergency Stop

Stop and report before continuing if:
- Any action would write, delete, or modify outside `bolts/`, `leijonat/`, `kiekkokeskus/`, or
  `data/kiekkokeskus/`, or touch the site bucket config, the distribution, or `add-index-html`
  (CLAUDE.md Rule 1)
- `cdk diff` shows non-`kiekkokeskus-*` changes, or any deletion or replacement you didn't expect
- A step would contradict an ADR
- An NHL payload contradicts DECISIONS-DATA.md in a way that changes meaning
- Current-state JSON could be overwritten by a failed or partial run
- Credentials, or anything that looks like a secret, would be committed

## Notes

- Deviating from the PRP for a better approach is fine. Document why in the commit and report.
- Leave the fixtures richer than you found them. That's what makes the next PRP safe.
