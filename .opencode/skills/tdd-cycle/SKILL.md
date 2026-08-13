---
name: tdd-cycle
description: Use when implementing or fixing code in Traianus following the Red-Green-Refactor TDD cycle, one phase at a time, with regression via pytest and the C1 audit harness.
---

# TDD cycle (red -> green -> refactor)

1. Red: write (or simulate) the test that demonstrates the failure.
2. Green: implement the minimal change that makes the test pass.
3. Refactor: clean up without breaking the green.

Rules:
- Process one phase at a time; do not advance until the executor reports success.
- Empirical validation: `python3 -m pytest tests/ -q` and `python3 tools/audit/audit_harness.py` (C1 GUARD).
- C1 invariant: exclude the self-projection (i=j, value 1.0) when calibrating `auto_calibrate_critical_threshold()`.
- Consult `AUDIT.md` before refactoring `traianus/app.py`.
