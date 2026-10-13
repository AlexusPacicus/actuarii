---
name: boundary-validator
description: Use when generating or validating code proposals under the proposal schema (Intent_Class, Target_File, Implementation_Block, Topological_Grounding, Rationale, Safety_Abort), or when checking a proposal against the boundary-validator MCP Zero-Trust gates.
---

# BoundaryValidator proposal schema

Every change proposal must contain exactly:
1. `Intent_Class`: [FIX | REFACTOR | TEST | DOC | SPEC | AUDIT]
2. `Target_File`: relative path within repository root.
3. `Topological_Grounding`: exact UTF-8 quote present literally in the target file.
4. `Implementation_Block`: exact text or code block to insert/replace.
5. `Rationale`: why the change is made, in a sentence a person can read (1 to 1000 characters, not only
   whitespace). It is recorded with the decision; nothing checks that it is true.
6. `Safety_Abort`: [NONE | BOUNDARY_VIOLATION | SYNTAX_ERROR | UNAUTHORIZED_SCOPE]

Call `validate_proposal` with the proposal as an object and the same file as `target_file`.

## The receipt binds the exact change

The write gate allows a write on a governed path only with a recent `EXECUTE_SAFE` receipt for that
exact text; nothing is normalised. Build the proposal from the tool call you are about to make:

* `Edit`: `Topological_Grounding` = `old_string`, `Implementation_Block` = `new_string`.
* `MultiEdit`: one proposal per edit, the same way.
* `Write`: `Implementation_Block` = the whole `content`; `Topological_Grounding` = a quote of the file
  if it exists (empty if it is new). Prefer `Edit` for large files: a `Write` carries the file twice.
* `NotebookEdit`: `Implementation_Block` = `new_source`.

## Deterministic gates (validate_proposal), in order
1. A NUL anywhere -> ABORTED_VIOLATES_ZERO_TRUST
2. Not the strict schema (missing or extra field, unknown enum, duplicate key, a Rationale that is empty,
   only whitespace or over 1000 characters) -> INVALID_JSON
3. Safety_Abort != "NONE" -> BLOCKED_BY_SAFETY_GATE
4. `target_file` is not the file `Target_File` names -> ABORTED_TARGET_MISMATCH
5. Outside the repository, or a quote not present byte by byte in an existing file (any intent;
   FIX, REFACTOR and AUDIT also fail on a file that does not exist) -> ABORTED_GROUNDING_FAILED
6. For a `.py` target: no possible result parses -> BLOCKED_BY_SAFETY_GATE (SYNTAX_ERROR); a result
   introduces a network, process or code-loading primitive the file does not have (imports such as
   subprocess or socket, os.system and the other os process functions, eval, exec, compile,
   __import__) -> ABORTED_VIOLATES_ZERO_TRUST, with a `reason`

Only if every gate passes: VALIDATED / EXECUTE_SAFE with and_gate_ok: True, and a receipt, written
together with the audit row of the decision (and its Rationale) in one transaction. If they cannot be
written, the decision is QUARANTINED / ABORTED_NOT_RECORDED, with a `reason` and no receipt. The write
gate checks the primitives again on the exact result of the write, against the file as it is then.
Golden rule: neurons propose, rules dispose.
