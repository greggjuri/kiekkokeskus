# init-01: Repo Scaffold

**Created**: 2026-10-02
**Phase**: 1 Foundation
**Depends On**: None
**ADRs**: ADR-002 (disclaimer), ADR-025 (AWS profile, mentioned only), ADR-029 (naming); adds ADR-031

---

## Problem Statement

The repo holds only docs. There's no Python package, no test runner, no linter, and no CI, so
init-02 and init-03 have nothing to build on and nothing to enforce the house rules.

## Goal

A fresh clone on the MacBook goes from `git clone` to green `ruff` + `pytest` with three commands,
and the same checks run in GitHub Actions on every push. The README states what the project is and
carries the not-affiliated disclaimer.

## Requirements

### Must Have (P0)
1. **`pyproject.toml`**, built with **hatchling** in a `src/` layout:
   - project name `kiekkokeskus`, `requires-python = ">=3.13,<3.14"`
   - **no runtime dependencies** (`dependencies = []`), per PLANNING Key Constraint 3
   - optional `dev` extra: `pytest`, `pytest-cov`, `ruff`, `boto3`. boto3 is dev-only because
     Lambda provides it.
   - `[tool.pytest.ini_options]`: `testpaths = ["tests"]`, `addopts = "--strict-markers"`
   - `[tool.coverage.run]` source `kiekkokeskus`; `[tool.coverage.report]` `fail_under = 80`,
     `show_missing = true`
2. **ruff** as both linter and formatter, configured in `pyproject.toml`:
   - `target-version = "py313"`, `line-length = 100`, `src = ["src", "tests"]`
   - lint rules: `E`, `F`, `W`, `I` (isort), `UP` (pyupgrade), `B` (bugbear), `SIM`
   - `ruff format` with defaults
3. **`.python-version`** containing `3.13`, so pyenv picks it up automatically.
4. **Package skeleton**: `src/kiekkokeskus/__init__.py` with `__version__ = "0.1.0"` and nothing
   else.
5. **One real test**, `tests/test_package.py`: the package imports and `__version__` is a string.
   It keeps CI meaningful until init-03 adds real tests.
6. **`tests/fixtures/README.md`**: an empty provenance table (`file | source URL | fetched at (UTC) |
   HTTP status | variant of | ADR`), with a short note pointing at TESTING.md "Fixtures". No
   fixtures yet.
7. **CI**, `.github/workflows/ci.yml`:
   - triggers on push to any branch and on pull requests
   - `ubuntu-latest`, `actions/setup-python` reading `.python-version`, pip cache
   - steps: `pip install -e '.[dev]'` → `ruff check .` → `ruff format --check .` →
     `pytest --cov=kiekkokeskus`
   - **no AWS credentials and no deploy step, ever, in this workflow.** Infra and page test jobs
     get added by init-02 and init-06.
8. **`README.md`** (replacing the GitHub stub), with these sections:
   - one-paragraph what-it-is, with `/bolts` and `/leijonat` links
   - how it works in 3–4 lines: daily Lambda → S3 JSON → static pages, with a link to
     `docs/PLANNING.md`
   - local dev quickstart (the three commands below)
   - repo map: `docs/`, `initials/`, `prps/`, `src/`, `tests/`
   - **Disclaimer**, verbatim:
     > Kiekkokeskus is a personal, non-commercial project. It is not affiliated with, endorsed
     > by, or sponsored by the National Hockey League, the Tampa Bay Lightning, or any NHL team.
     > Team and league names are trademarks of their respective owners. Data comes from publicly
     > accessible NHL endpoints.

### Should Have (P1)
1. **`examples/README.md`**, a short note that `examples/` will hold code patterns once real modules
   exist (first candidates: a parser plus its fixture test, from init-03).
2. **CLAUDE.md Quick Commands** get the lint commands added: `ruff check .`, `ruff format .`.

### Nice to Have (P2)
1. A CI status badge in the README.

## Local Dev Quickstart (must work exactly as written)

```bash
python3.13 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
ruff check . && ruff format --check . && pytest --cov=kiekkokeskus
```

## Ownership Check

- **AWS resources created or changed**: none
- **S3 prefixes written**: none
- **Touches anything owned by the main site?** No

## ADR to Add (ADR-031, in `docs/DECISIONS.md`)

**ADR-031: Python tooling is hatchling + ruff + pytest, pinned to 3.13.** Use hatchling for builds
(`src/` layout, editable installs) and ruff as the sole linter and formatter, with the settings
above. pytest and pytest-cov run with an 80% coverage floor on `src/kiekkokeskus/`. `.python-version`
pins 3.13 to match the Lambda runtime. CI runs lint, format-check, and tests on every push and
never holds AWS credentials. Alternatives considered: setuptools (heavier config for no gain
here), and black + flake8 + isort (three tools where one does the job).

## TASK.md Updates

- Phase 0 "create repo" → Recently Completed.
- `init-01-repo-scaffold` → In Progress at start, Recently Completed at the end, with a one-line
  outcome.
- Remove the README note from Up Next.

## Success Criteria

- [ ] On the MacBook, the three quickstart commands run clean from a fresh clone
- [ ] `ruff check .` and `ruff format --check .` pass on the whole repo
- [ ] `pytest --cov=kiekkokeskus` passes, with coverage ≥ 80% (trivially, for now)
- [ ] The GitHub Actions CI run is green on the push
- [ ] The README contains the disclaimer verbatim
- [ ] `pip install -e .` without `[dev]` installs **zero** third-party packages
- [ ] ADR-031 is in DECISIONS.md, and TASK.md is updated
- [ ] No file over 500 lines

## Out of Scope

- `infra/` and anything CDK (init-02)
- `scripts/` (deploy, fetch_fixture, smoke, lifecycle) (init-02 / init-03)
- `site/` and any JS tooling (init-06)
- Real fixtures and NHL calls (init-03)
- pre-commit hooks, type checking (mypy/pyright), and Dependabot, which can be revisited later as
  their own specs if wanted

## Verify in PRP

- [ ] Python 3.13 is installed on the MacBook (`python3.13 --version`) via pyenv or Homebrew. If
      not, the PRP's Step 0 says how to install it. It does not change the pin.

## Open Questions

(none)

## Notes

- Keep the commit sequence small: (1) pyproject, `.python-version`, package, and test; (2) CI;
  (3) README and examples; (4) ADR-031, TASK.md, and CLAUDE.md.
- `.gitignore` already exists from the initial commit. Don't rewrite it; append to it only if
  something new needs ignoring.
