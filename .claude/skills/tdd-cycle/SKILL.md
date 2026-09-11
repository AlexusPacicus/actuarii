---
name: tdd-cycle
description: Use when implementing or fixing code in Traianus following the Red-Green-Refactor TDD cycle, one phase at a time, with phase-at-a-time gating, regression via pytest, and the C1 audit harness.
---

# TDD cycle (red -> green -> refactor)

The cycle is executed in discrete phases. **Phase-at-a-time gating:** do NOT
advance to the next phase until the current phase passes its gate. Each gate is
deterministic and MUST be satisfied before the next phase begins.

## Phases and gates

1. **Red** — write (or simulate) the test that demonstrates the failure.
   - Gate: the new test FAILS for the intended reason (`pytest <path> -q` shows
     the target failure). If it passes, the test is vacuous — do not proceed.
2. **Green** — implement the minimal change that makes the test pass.
   - Gate: the targeted test PASSES (`pytest <path> -q`). Do not refactor until green.
3. **Refactor** — clean up without breaking green.
   - Gate: the full suite is still green (`pytest tests/ -q`) after refactoring.
4. **Verify** — confirm `.github/workflows/ci.yml` covers any new/modified test
   paths and dependencies (AGENTS.md §1.6).
   - Gate: CI config matches the repository structure; missing/stale CI is a blocking defect.

## Rules

- **One phase at a time:** never pre-empt the executor gate. Red must be red
  before writing fix code; green must pass before refactoring.
- **Code mutations pass the boundary-validator:** any implementation change is
  emitted as a 5 Radicals proposal (`Intent_Class` ∈ FIX/REFACTOR/TEST) and gated
  by `validate_proposal` (Safety, Zero-Trust Capability, Grounding) per AGENTS §5.
- Empirical validation: `pytest tests/ -q` and `python3 tools/audit/audit_harness.py`
  (C1 GUARD) for the full-suite gate.
- C1 invariant: exclude the self-projection (i=j, value 1.0) when calibrating
  `auto_calibrate_critical_threshold()`.
- Consult `AUDIT.md` before refactoring `traianus/app.py`.
- Do not edit tests to mask a failing feature, nor source to chase a broken test
  (AGENTS §6.3 domain separation).
