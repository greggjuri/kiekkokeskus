# Init Template - Feature Specification

Copy to `initials/init-nn-{slug}.md`. Use the reserved number from `docs/TASK.md`, or the next free
one for an unplanned spec, and bump it in TASK.md (ADR-029). Written in Claude.ai.

---

## init-nn: {Feature Name}

**Created**: {YYYY-MM-DD}
**Phase**: {1 Foundation / 2 Data / 3 Pages / 4 History / Future}
**Depends On**: {init-nn, … or "None"}
**ADRs**: {every ADR this spec relies on or touches, e.g. ADR-012, 015, 030}

---

## Problem Statement

{What this solves, in 1–3 sentences.}

## Goal

{What is true when this is done. One commit-sized outcome; if it needs two PRPs, it's two specs.}

## Requirements

### Must Have (P0)
1. {Requirement}

### Should Have (P1)
1. {Requirement}

### Nice to Have (P2)
1. {Requirement}

## Output / Data Contract

*Builder and collector specs: required. Page specs: list the fields consumed. Delete otherwise.*

| Field | Source endpoint + JSON path | Units / type | Nullable | Notes |
|---|---|---|---|---|
| `{field}` | `{api-web…/club-stats/TBL/{season}/2 → skaters[].points}` | int | no | |
| `{pointPctg}` | `{standings/{date} → standings[].pointPctg}` | fraction 0–1 | yes (0 GP, ADR-015) | |

- **schemaVersion change?** {no / yes, with the reason. Pages updated in the same PRP.}
- **S3 keys written**: {all under `data/kiekkokeskus/…`}

## Fixtures and Gotchas

*Which real payloads to capture, and which TESTING.md gotcha-matrix rows this spec must satisfy.*

| Fixture to capture | Why | Gotcha rows (ADR) |
|---|---|---|
| `{endpoint-slug}__{date}.json.gz` | {what it contains that matters} | {015, 017} |

## UI (page specs only)

- **Strings**: every user-visible string, in both languages

  | Key | EN | FI |
  |---|---|---|
  | `{table.points}` | {Points} | {Pisteet} |

- **Defaults**: {sort column + direction, position filter, language fallback}
- **URL params**: {`?pos=`, `?sort=`, `?dir=`, `?lang=`}
- **Mobile**: {pinned column, horizontal scroll, what's hidden}
- **Empty / stale / error states**: {what each looks like}

## Ownership Check

- **AWS resources created or changed**: {only `kiekkokeskus-*`, or "none"}
- **S3 prefixes written**: {must be within `bolts/`, `leijonat/`, `kiekkokeskus/`,
  `data/kiekkokeskus/`}
- **Touches anything owned by the main site?** {must be "no". If yes, stop: that needs an ADR first.}

## Success Criteria

- [ ] {Testable criterion: a test, a smoke check, or a visible result}

## Out of Scope

- {Explicitly excluded}

## Verify in PRP

*Facts this spec assumes but nobody has seen in a real payload. The PRP must fetch and confirm
each one before building on it, and record the result as an ADR in DECISIONS-DATA.md.*

- [ ] {e.g. hits/blocks come from `stats/rest/en/skater/realtime`}

## Open Questions

*Must be empty before `/generate-prp`.*

## Notes

---

## What Makes a Good Spec Here

- Says WHAT and WHERE THE DATA COMES FROM, not how to code it.
- Every field has a source and units. "Points" isn't a spec; `skaters[].points`, int, is.
- Every assumption about the NHL is either backed by an ADR or listed under Verify in PRP.
- Out of Scope is filled in. That's where scope creep gets stopped.

**Next**: in Claude Code, `/generate-prp initials/init-nn-{slug}.md` → `prps/prp-nn-{slug}.md`.
