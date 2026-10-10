# Generate PRP

Generate a Project Requirement Plan (PRP) from an init spec.

## Arguments
- `$ARGUMENTS`: the init spec path, e.g. `initials/init-04-bolts-json.md`

## Instructions

You are generating a PRP for **Kiekkokeskus**.

### Step 1: Validate the Input

1. `$ARGUMENTS` must match `initials/init-nn-{slug}.md`, with a two-digit `nn` (ADR-029). If it
   doesn't, stop and report.
2. The output path is `prps/prp-nn-{slug}.md`, with the same `nn` and slug. If that file already
   exists, stop and ask before overwriting.
3. The spec's **Open Questions** must be empty. If not, stop and list them.

### Step 2: Gather Context

Read:
1. `CLAUDE.md`: conventions and the hard rules (especially Rule 1, ownership)
2. `docs/PLANNING.md`: architecture, data contract, phases
3. `docs/DECISIONS.md`: architecture, hosting, tooling, and UI ADRs
4. `docs/DECISIONS-DATA.md`: **required if the spec touches any parser, builder, or fixture**
5. `docs/TESTING.md`: layers and the gotcha matrix
6. `docs/TASK.md`: status, and whether dependencies are complete

ADRs are binding. If the spec conflicts with one, stop and report the conflict. Don't resolve it
yourself.

### Step 3: Read the Spec

Note every output field and its source, every ADR referenced, the fixtures required, the
**Verify in PRP** items, and the Ownership Check.

### Step 4: Resolve Unverified Facts

For each **Verify in PRP** item, and any payload assumption you notice that isn't backed by an
ADR:
1. Fetch the real endpoint (no auth needed) into a scratch location **outside the repo**. Fixtures
   get committed during execution, not here.
2. Record what you found in the PRP's Verification table.
3. If reality differs from the spec, say so in the report. A change in meaning goes back to
   Claude.ai.

Never fill a gap from community docs or memory alone.

### Step 5: Research the Codebase

1. Find the existing modules, fixtures, and tests this builds on.
2. Check `examples/` for patterns.
3. List exact files to create or modify. Code files stay under 500 lines; docs are exempt (ADR-034).

### Step 6: Write the PRP

Use `prps/template/prp-template.md` and fill every section. Specifically:
- **Output Schema**: the exact JSON, with units and nullability. State whether `schemaVersion`
  changes.
- **Step 0** captures fixtures with `scripts/fetch_fixture.py`.
- Every step is one commit, `{type}(nn): …`, with a concrete validation.
- **Testing Requirements** map to TESTING.md layers and name the gotcha-matrix rows covered.
- **Infra changes** state the expected `cdk diff`, touching only `kiekkokeskus-*`.
- **Rollback** includes data (S3 versions or re-run from raw), not just code.

### Step 7: Score Confidence

Score Clarity, Feasibility, Completeness, and Payload certainty from 1 to 10. If the average is
below 7, or any score is below 5, list the concerns and what would resolve them, and do not mark
the PRP Ready.

### Step 8: Report

1. The PRP path created
2. Confidence scores
3. Verification results, especially any surprises
4. Open questions or ADR conflicts
5. Suggested new ADRs, with the target file (DECISIONS.md or DECISIONS-DATA.md)

## Quality Checklist

- [ ] Output path is `prps/prp-nn-{slug}.md`, matching the init
- [ ] Every output field has a source, units, and nullability
- [ ] Every unverified fact was fetched or is listed as Step 0
- [ ] Every relevant gotcha-matrix row has a named test
- [ ] Nothing writes outside the four owned prefixes, and no non-`kiekkokeskus-*` resources change
- [ ] No ADR contradicted
- [ ] Rollback covers code and data
