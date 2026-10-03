# PRP-01: Repo Scaffold

**Created**: 2026-10-02
**Initial**: `initials/init-01-repo-scaffold.md`
**Status**: Ready
**ADRs**: ADR-002 (disclaimer), ADR-025 (AWS profile), ADR-029 (naming); adds ADR-031 (Python tooling)

---

## Overview

### Problem Statement

The repo holds only planning docs — no package, no tests, no linter, no CI — so init-02 and
init-03 have nothing to build on.

### Proposed Solution

Minimal Python 3.13 package in `src/` layout (hatchling), ruff as sole linter/formatter, pytest
with 80% coverage floor, GitHub Actions workflow for lint/format/tests on push. Full README with
the ADR-002 disclaimer. ADR-031 records the tooling choice. No AWS, no fixtures, no NHL calls.

### Success Criteria

- [ ] Quickstart runs clean from a fresh clone → Step 2 local run
- [ ] `ruff check .` and `ruff format --check .` pass → Step 3 CI run
- [ ] `pytest --cov=kiekkokeskus` ≥ 80% → `tests/test_package.py` + coverage config
- [ ] GitHub Actions CI is green on each pushed step
- [ ] README contains the disclaimer verbatim → `grep -F "not affiliated with" README.md`
- [ ] `pip install -e .` (no `[dev]`) installs **zero** third-party packages → Step 2 zero-dep
      check in `/tmp/kk-bare` venv
- [ ] ADR-031 in `docs/DECISIONS.md`, `docs/TASK.md` fully updated → Steps 1 + 5 diffs
- [ ] No file over 500 lines → `wc -l` on every file touched

---

## Context

### Related Documentation

- `docs/PLANNING.md`: Tech Stack, Key Constraints 3/6/7, Project Structure
- `docs/DECISIONS.md`: ADR-002 (disclaimer), ADR-025 (CI must never hold AWS creds), ADR-029 (naming)
- `docs/TESTING.md`: Layer 1 (pytest wiring)
- `docs/DECISIONS-DATA.md`: n/a (no parser/builder/fixture work)

### Dependencies

None (this is the first spec).

### Files to Modify/Create

```
pyproject.toml                                  # NEW: hatchling, ruff, pytest, coverage config
.python-version                                 # NEW: "3.13"
src/kiekkokeskus/__init__.py                    # NEW: __version__ = "0.1.0"
tests/__init__.py                               # NEW: empty (pytest finds tests/ via testpaths)
tests/test_package.py                           # NEW: smoke test on import + __version__
tests/fixtures/README.md                        # NEW: provenance table stub
.github/workflows/ci.yml                        # NEW: lint, format-check, tests
README.md                                       # MODIFY: replace stub with full README + disclaimer
examples/README.md                              # NEW: placeholder note
CLAUDE.md                                       # MODIFY: add ruff commands to Quick Commands
docs/DECISIONS.md                               # MODIFY: append ADR-031 (Step 5)
docs/TASK.md                                    # MODIFY: In Progress in Step 1, Completed in Step 5
```

Every file stays under 500 lines (expected sizes: pyproject ~50, CI ~35, README ~60–80, ADR-031 ~25).

---

## Verification of Unconfirmed Facts

| Assumption | Checked | Result | Follow-up |
|---|---|---|---|
| Python 3.13 installed on MacBook | `python3.13 --version`, pyenv check, Homebrew keg path | **Not installed.** No `python3.13` on PATH, no pyenv, no `python@3.13` keg. System `python3` is 3.14.5. | Step 0 installs via `brew install python@3.13`. 3.13 pin stays (matches Lambda runtime). |

No payload or NHL endpoint work in this PRP, so no fixture verification is required.

---

## Technical Specification

### Output Schema

Not applicable (no JSON output). This PRP produces source files, config, and docs.

- `schemaVersion`: n/a
- S3 keys: none written

### Module Design

```python
# src/kiekkokeskus/__init__.py
__version__ = "0.1.0"
```

No logic yet. Everything else is config.

### pyproject.toml — complete content

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "kiekkokeskus"
version = "0.1.0"
description = "Daily NHL stats collector for /bolts and /leijonat on jurigregg.com"
readme = "README.md"
requires-python = ">=3.13,<3.14"
dependencies = []

[project.optional-dependencies]
dev = [
  "pytest",
  "pytest-cov",
  "ruff",
  "boto3",         # provided by Lambda runtime; dev-only locally
]

[tool.hatch.build.targets.wheel]
packages = ["src/kiekkokeskus"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--strict-markers"

[tool.coverage.run]
source = ["kiekkokeskus"]

[tool.coverage.report]
fail_under = 80
show_missing = true

[tool.ruff]
target-version = "py313"
line-length = 100
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B", "SIM"]
```

### CI Workflow — `.github/workflows/ci.yml`

```yaml
name: ci
on:
  push:
  pull_request:

permissions:
  contents: read

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version-file: .python-version
          cache: pip
          cache-dependency-path: pyproject.toml
      - run: pip install -e '.[dev]'
      - run: ruff check .
      - run: ruff format --check .
      - run: pytest --cov=kiekkokeskus
```

The top-level `permissions: contents: read` is required: without it the workflow token inherits
the repository's default permissions, which may be write. Declaring read-only makes the "CI holds
nothing it shouldn't" claim true, not aspirational. No AWS secrets, no deploy step. Init-02 will
add infra tests (its own job or workflow); init-06 adds page tests.

### Infra Changes

None. No CDK, no AWS, no `cdk diff` expected.

---

## Implementation Steps

Each step is one validated commit. Commit type is `chore(01):` or `docs(01):` as noted.

### Step 0: Install Python 3.13 locally (prerequisite, no commit)

```bash
brew install python@3.13
/opt/homebrew/opt/python@3.13/bin/python3.13 --version   # must print 3.13.x
```

Do **not** `brew link --overwrite python@3.13` — it can repoint system `python3` from 3.14 to
3.13 and break anything expecting 3.14. The keg's binary lives at
`/opt/homebrew/opt/python@3.13/bin/python3.13` whether or not it's on `PATH`. If it isn't, create
the venv with that full path: `.../python3.13 -m venv .venv`.

**Validation**:
- [ ] `/opt/homebrew/opt/python@3.13/bin/python3.13 --version` prints 3.13.x
- [ ] System `python3 --version` is unchanged from before this step

### Step 1: Mark init-01 In Progress (`docs(01): start`)

Per execute-prp Step 0: TASK.md flips before any implementation.

**Files**: `docs/TASK.md`

- Move "Create `greggjuri/kiekkokeskus` repo and commit the planning docs" from **In Progress**
  to **Recently Completed** (outcome: "repo + planning docs pushed 2026-10-02, f427ea0 → a799225").
- Move `init-01-repo-scaffold` from **Up Next** to **In Progress** (note: "executing PRP-01").
- Update `*Last updated:*` to `2026-10-02 (init-01 in progress)`.

**Commit + push** (no CI yet — workflow lands in Step 3):
```bash
git add docs/TASK.md
git commit -m "docs(01): start"
git push origin main
```

### Step 2: Package skeleton, pyproject, pytest (`chore(01): scaffold python package`)

**Files**: `pyproject.toml`, `.python-version`, `src/kiekkokeskus/__init__.py`,
`tests/__init__.py`, `tests/test_package.py`

- `.python-version` contains exactly `3.13` (one line, no trailing content beyond a newline).
- `src/kiekkokeskus/__init__.py`:
  ```python
  __version__ = "0.1.0"
  ```
- `tests/__init__.py`: empty file (keeps `tests/` from being treated as an implicit namespace
  package).
- `tests/test_package.py`:
  ```python
  import kiekkokeskus


  def test_package_imports() -> None:
      assert isinstance(kiekkokeskus.__version__, str)
      assert kiekkokeskus.__version__ == "0.1.0"
  ```
- `pyproject.toml`: exactly as in Technical Specification above.

**Validation**:

Primary (dev venv in-repo):
```bash
python3.13 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
ruff check .
ruff format --check .
pytest --cov=kiekkokeskus
python -c "import kiekkokeskus; print(kiekkokeskus.__version__)"   # 0.1.0
```

Zero-dep check (in a **separate** throwaway venv so the dev extras are not present):
```bash
deactivate 2>/dev/null || true
python3.13 -m venv /tmp/kk-bare
/tmp/kk-bare/bin/pip install -e .
/tmp/kk-bare/bin/pip list
rm -rf /tmp/kk-bare
```
Expected `pip list` output: only `kiekkokeskus` and `pip` (plus `setuptools` on some
Python/pip versions). Nothing else — no `pytest`, `ruff`, `boto3`, hatchling, etc.

- [ ] `ruff check .` green
- [ ] `ruff format --check .` green
- [ ] `pytest` passes 1 test, coverage ≥ 80% (trivially; `__init__.py` has one statement)
- [ ] `/tmp/kk-bare` venv shows only `kiekkokeskus` + pip (± setuptools) in `pip list`
- [ ] `python -c "import kiekkokeskus"` prints `0.1.0` from the dev venv

Push after the commit. (No CI yet — the workflow lands in Step 2. This push just makes the
package visible on `main` so Step 2's first CI run has something to install.)

**Commit + push**:
```bash
git add pyproject.toml .python-version src/kiekkokeskus/__init__.py tests/__init__.py tests/test_package.py
git commit -m "chore(01): scaffold python package"
git push origin main
```

### Step 3: GitHub Actions CI (`chore(01): add CI workflow`)

**Files**: `.github/workflows/ci.yml`

Content exactly as in Technical Specification (with the `permissions: contents: read` block).

**Commit + push**:
```bash
git add .github/workflows/ci.yml
git commit -m "chore(01): add CI workflow"
git push origin main
gh run watch           # or: gh run list --limit 1
gh workflow view ci    # confirms the pushed workflow matches what was committed
```

**Validation** (on the pushed commit, read from GitHub):
- [ ] CI run on this commit is green
- [ ] Setup-python step logs show Python 3.13.x
- [ ] Run summary shows `Permissions: contents: read` (no write perms, no OIDC role)
- [ ] Workflow has no `AWS_*` env and no `secrets.*` references:
      `grep -E 'AWS_|secrets\.' .github/workflows/ci.yml` returns nothing

### Step 4: README (replacing stub) and examples placeholder (`docs(01): README with disclaimer`)

**Files**: `README.md` (overwrite), `tests/fixtures/README.md`, `examples/README.md`

- `README.md` content:
  ```markdown
  # Kiekkokeskus

  Two static NHL stat pages on [jurigregg.com](https://jurigregg.com):
  [`/bolts`](https://jurigregg.com/bolts) follows the Tampa Bay Lightning, and
  [`/leijonat`](https://jurigregg.com/leijonat) follows every Finnish player in the NHL.

  ## How it works

  A Lambda runs once a day at 10:00 ET, fetches the NHL's public (undocumented) API, archives the
  raw responses, and writes JSON into the site's S3 bucket. The pages read only that JSON — the
  browser never talks to the NHL. See [`docs/PLANNING.md`](docs/PLANNING.md) for the full picture
  and [`docs/DECISIONS.md`](docs/DECISIONS.md) for the architectural choices.

  ## Local development

  ```bash
  python3.13 -m venv .venv && source .venv/bin/activate
  pip install -e '.[dev]'
  ruff check . && ruff format --check . && pytest --cov=kiekkokeskus
  ```

  ## Repo map

  - [`docs/`](docs/) — planning, decisions (ADRs), task tracker, testing standards
  - [`initials/`](initials/) — feature specs (`init-nn-{slug}.md`)
  - [`prps/`](prps/) — implementation plans (`prp-nn-{slug}.md`)
  - [`src/kiekkokeskus/`](src/kiekkokeskus/) — the daily collector (Python 3.13, Lambda arm64)
  - [`tests/`](tests/) — pytest; `tests/fixtures/` holds real archived NHL payloads

  ## Disclaimer

  > Kiekkokeskus is a personal, non-commercial project. It is not affiliated with, endorsed
  > by, or sponsored by the National Hockey League, the Tampa Bay Lightning, or any NHL team.
  > Team and league names are trademarks of their respective owners. Data comes from publicly
  > accessible NHL endpoints.
  ```

- `tests/fixtures/README.md` content:
  ```markdown
  # Fixtures

  Real archived NHL payloads live here. **Never hand-write JSON.** Capture with
  `scripts/fetch_fixture.py` (added by init-03). Naming and rules: see
  [`../../docs/TESTING.md`](../../docs/TESTING.md) → "Fixtures".

  ## Provenance

  | file | source URL | fetched at (UTC) | HTTP status | variant of | ADR |
  |---|---|---|---|---|---|
  ```

- `examples/README.md` content:
  ```markdown
  # Examples

  Code patterns to follow when writing new modules. Populated once real modules exist. First
  candidates (from init-03): a pure parser plus its fixture-driven test.
  ```

**Validation** (locally first, then on the pushed CI run):
- [ ] `grep -F "not affiliated with, endorsed" README.md` returns the disclaimer line
- [ ] `grep -F "ruff format --check" README.md` returns the quickstart command
- [ ] `ruff check .` and `ruff format --check .` still green
- [ ] `pytest` still green

**Commit + push**:
```bash
git add README.md tests/fixtures/README.md examples/README.md
git commit -m "docs(01): README with disclaimer"
git push origin main
gh run watch
```
- [ ] CI run on this commit is green

### Step 5: ADR-031, TASK.md complete, CLAUDE.md (`docs(01): ADR-031 tooling, complete TASK, update CLAUDE`)

**Files**: `docs/DECISIONS.md` (append), `docs/TASK.md` (edit), `CLAUDE.md` (edit)

- `docs/DECISIONS.md`: append after ADR-030, before the "Template for New Decisions" block:
  ```markdown
  ---

  ## ADR-031: Python tooling is hatchling + ruff + pytest, pinned to 3.13

  **Date**: 2026-10-02
  **Status**: Accepted

  ### Decision
  - **Build**: hatchling, `src/` layout, editable installs.
  - **Lint + format**: ruff, one tool for both. Rules `E`, `F`, `W`, `I`, `UP`, `B`, `SIM`;
    `line-length = 100`; `target-version = "py313"`.
  - **Tests**: pytest + pytest-cov, with `fail_under = 80` on `src/kiekkokeskus/`.
  - **Pin**: `.python-version` holds `3.13`, matching the Lambda runtime.
  - **CI**: GitHub Actions runs `ruff check`, `ruff format --check`, and `pytest`. It never holds
    AWS credentials.

  ### Alternatives Considered
  | Option | Pros | Cons | Verdict |
  |---|---|---|---|
  | setuptools | ubiquitous | heavier config for no gain in a tiny stdlib package | Rejected |
  | black + flake8 + isort | mature, familiar | three tools where ruff does the job | Rejected |

  ### References
  initials/init-01-repo-scaffold.md, prps/prp-01-repo-scaffold.md
  ```

- `docs/TASK.md` edits (final completion of init-01; the In Progress flip happened in Step 1):
  - Move `init-01-repo-scaffold` from **In Progress** to **Recently Completed** with outcome:
    "scaffold green locally and in CI; ADR-031 added".
  - Update `*Last updated:*` line to `2026-10-02 (init-01 complete)`.

- `CLAUDE.md` Quick Commands → under the `# Test` block, append two lines before the next section:
  ```
  ruff check .                             # lint
  ruff format --check .                    # formatting (use `ruff format .` to fix)
  ```

**Validation** (locally first, then on the pushed CI run):
- [ ] `grep -F "ADR-031" docs/DECISIONS.md` finds the heading
- [ ] `wc -l docs/DECISIONS.md` < 500
- [ ] `grep -F "init-01-repo-scaffold" docs/TASK.md` is only in Recently Completed, not Up Next
- [ ] `grep -F "ruff check ." CLAUDE.md` finds the new line in Quick Commands
- [ ] `ruff check . && ruff format --check . && pytest --cov=kiekkokeskus` all green

**Commit + push**:
```bash
git add docs/DECISIONS.md docs/TASK.md CLAUDE.md
git commit -m "docs(01): ADR-031 tooling, update TASK and CLAUDE"
git push origin main
gh run watch
```
- [ ] CI run on this commit is green
- [ ] All five commits visible on `main` (`git log --oneline -7`)

---

## Testing Requirements

| Layer | Tests | Notes |
|---|---|---|
| 1 Parse | `tests/test_package.py` — import + `__version__` (placeholder until init-03) | no fixtures yet |
| 2–6 | n/a — builders, handler, CDK, pages, deploy all land in later specs | — |
| 7 Manual | run the quickstart from a clean clone; confirm CI is green | — |

Coverage ≥ 80% is trivial: `__init__.py` has one statement.

---

## Error Handling and Edge Cases

| Case | Handling | Where tested |
|---|---|---|
| Fresh clone with no Python 3.13 | Step 0 installs via `brew install python@3.13`, no system link | manual quickstart |
| Runtime dep sneaks in | `dependencies = []` enforced by Step 2 zero-dep check in `/tmp/kk-bare` | Step 2 validation |
| CI token has more than read | `permissions: contents: read` at workflow top; no `AWS_*`/`secrets.*` | Step 3 validation |
| CI red on push | Fix locally, push as a **new** commit (never amend, per Git Safety Protocol) | — |

---

## Cost Impact

None. No AWS resources created or changed. GitHub Actions free-tier minutes only.

---

## Rollback Plan

1. **Code**: `git revert` the five commits in reverse order and push. Since Step 3's workflow is
   reverted alongside Step 2's package, CI won't be left trying to install a non-existent package.
2. **Data**: n/a — no S3 writes.
3. **Local**: delete `.venv/`, `*.egg-info/`, `.pytest_cache/`, `.coverage` (already in
   `.gitignore`).
4. **Verify**: `git log --oneline -8` shows the reverts and `main` is back to docs-only.

---

## Open Questions — none

---

## Confidence Scores

| Dimension | Score | Notes |
|---|---|---|
| Clarity | 9 | Spec is explicit; small judgment calls settled in-line. |
| Feasibility | 8 | Python 3.13 absent on this MacBook; Step 0 handles it. No AWS/NHL/CDK moving parts. |
| Completeness | 9 | Every success criterion maps to a validation; every P0+P1 is in a step. |
| Payload certainty | 10 | No NHL payload work. |
| **Average** | **9.0** | **Ready** |
