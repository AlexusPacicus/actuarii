---
name: tdd-cycle
description: Use when implementing or fixing code test-first, one Red-Green-Refactor phase at a time, with a deterministic gate per phase and the full suite before a task is declared done.
---

# TDD cycle (red -> green -> refactor)

The cycle runs in discrete phases. **Phase-at-a-time gating:** do NOT advance to the next phase
until the current phase passes its gate.

## Phases and gates

1. **Red**: write the test that demonstrates the missing behaviour or the failure.
   - Gate: the new test FAILS for the intended reason (`pytest <path> -q` shows that failure). If
     it passes, or fails for another reason, the test is vacuous: do not proceed.
2. **Green**: implement the minimal change that makes the test pass.
   - Gate: the targeted test PASSES (`pytest <path> -q`). Do not refactor until green.
3. **Refactor**: clean up without breaking green.
   - Gate: the full suite is still green (`pytest tests/ -q`).
4. **Verify**: if the repository has CI, confirm that it covers the new or changed tests and
   dependencies.
   - Gate: the CI configuration matches the repository structure; missing or stale CI is a
     blocking defect.

## Rules

- **One phase at a time:** red must be red before writing the fix; green must pass before
  refactoring.
- **Governed files pass the boundary-validator:** before editing a governed path, emit a
  proposal (`Intent_Class` `TEST` for tests, `FIX` or `REFACTOR` for code, grounded in the target
  file, with a `Rationale` that says why the change is made) and call `validate_proposal` with the
  file as `target_file`.
- **Tests run through their own entry point** (`pytest`), never through inline Python.
- **Do not edit tests to mask a failing feature, nor source to chase a broken test.**
- **A test that cannot fail catches nothing:** for each test, know what it would catch and why it
  was red.
