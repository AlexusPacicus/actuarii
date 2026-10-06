# AGENTS.md — Agent constitution (v2.0.0)

**Scope:** the whole repository.
**Standard:** RFC 2119 (`MUST` / `MUST NOT`).

This file states the rules for every coding agent working here. Rules marked **[enforced]** are
enforced in code by Actuarii: an agent that breaks them is stopped, whatever it was told. The
others are conventions that the agent follows and the reviewer checks. Section 9 lists what the
enforcement does not cover.

---

## 1. Sources of truth

1.1 `.actuarii.json` at the repository root is the source of the enforced rules: the governed
paths, the receipt window, where Python may run, the contract registry and the blind review. The
agent **MUST NOT** assume a rule this file describes applies to a path; the configuration
decides. **[enforced]** Without the file, a built-in minimum applies. With an invalid file, every
`Edit` and `Write` inside the repository is denied except for `.actuarii.json` itself.

1.2 At the start of every session the hook `tools/hooks/announce_governance.py` puts the active
rules and their source into the agent's context. The agent **MUST** read that announcement
before its first edit.

1.3 `.actuarii.json` and the configured contract registry are always governed, whatever the
configuration lists. **[enforced]** Every change to the rules leaves a receipt in the audit
trail.

## 2. Governed writes

2.1 Before an `Edit` or `Write` on a governed path, the agent **MUST** call the boundary-validator
MCP tool `validate_proposal` with a proposal and with the exact file as its separate `target_file`
argument. **[enforced]** The hook `tools/hooks/require_boundary_validation.py` denies the edit
unless the audit trail holds an `EXECUTE_SAFE` for that file within the configured window. The
denial names the rule, its source and the call that resolves it.

2.2 A proposal **MUST** conform to the strict 5 Radicals schema
(`tools/boundary_validator/schemas/proposals.py`): `Intent_Class` (`FIX`, `REFACTOR`, `TEST`,
`DOC`, `SPEC`, `AUDIT`), `Target_File`, `Topological_Grounding`, `Implementation_Block` and
`Safety_Abort`. **[enforced]**

2.3 For `FIX`, `REFACTOR` and `AUDIT`, the `Topological_Grounding` **MUST** be a quote present
character by character in the target file. **[enforced]**

2.4 An `Implementation_Block` **MUST NOT** contain network or process primitives (`fetch`,
`axios`, `urllib`, `requests`, `httpx`, `aiohttp`, `http.client`, `socket`, `curl`, `wget`,
`subprocess`, `os.system`, `os.popen`, `importlib` and the rest of the validator's matrix).
**[enforced]** Repository tooling that must start a process does it in one designated module
(`tools/audit/run_process.py`), which tests import.

2.5 A `Safety_Abort` other than `NONE` blocks the proposal. The agent **MUST** set it when it
sees that the change crosses a boundary it should not cross. **[enforced]**

## 3. Contract context

3.1 Before editing a path registered in the contract registry, the agent **MUST** have the
sections the registry requires served by `tools/audit/context_pack.py`, from the contract file as
it is now and within the registry window. **[enforced]** The hook
`tools/hooks/require_contract_context.py` denies the edit otherwise, and its denial prints the
command that serves the missing sections.

3.2 A receipt proves that the sections were served, not that they were read or that the code
conforms. Conformance to a contract is verified by tests.

## 4. Python

4.1 Python runs only as a script committed in `HEAD`, under the kit directory (`tools/`) or a
`python_script_dirs` entry. **[enforced]** The shim `tools/bin/python3` (also `python` and
`python3.11`) decides by argv alone, and the hook `tools/hooks/deny_python_escapes.py` denies the
`Bash` commands that reach an interpreter around it.

4.2 The agent **MUST NOT** run inline Python (`python3 -c`, `python3 -m`, stdin). **[enforced]**
Test runners and servers are called by their own entry points (`pytest`, not `python3 -m
pytest`).

4.3 A script that is not committed yet needs the user's explicit approval before it runs.

## 5. Blind review

5.1 A review that must not see what the author wants to be true is run by the read-only subagent
`.claude/agents/blind-reviewer.md` over a package built by `tools/audit/build_review_package.py`
from the `review` configuration. **[enforced]** While the review lock is set, the hook
`tools/hooks/confine_review_reads.py` denies every `Read`, `Grep` and `Glob` outside the package.

5.2 The reviewer changes no file and returns a verdict. The executing agent records it and
clears the lock (`build_review_package.py unlock`).

## 6. Delegation

6.1 One agent executes at a time. The executing agent writes contracts and reviews diffs; it
delegates code and tests to the subagent `.claude/agents/implementer.md`.

6.2 A delegation is a strict JSON `DelegationContract`, and the answer a `DelegationReport`
(`tools/audit/delegation_contract.py`). Both **MUST** be validated in code before they are used:
`delegation_contract.py contract` before the launch and `delegation_contract.py report` before
the report is accepted.

6.3 The implementer works on the one branch the contract names, touches only the files it lists,
writes the tests first, passes every gate the contract names, never pushes and stops at a commit.
The review of the diff, the merge and the records stay with the executing agent.

6.4 When a contract changes a schema or a shared format, it **MUST** list every test that builds
that format, so that the implementer does not stop on a file it may not touch.

## 7. Permission perimeter

7.1 `.claude/settings.json` (Claude Code) and `opencode.jsonc` (OpenCode) **MUST** stay identical
in perimeter: read-only git commands and the scripts under `tools/` allowed; `rm`, inline Python,
web fetch and web search denied; every other `Bash` call and every mutation asked. **[enforced by tests]**

7.2 Both harnesses load the same instructions: `CLAUDE.md` imports and the OpenCode
`instructions` list name the same files. **[enforced by tests]**

## 8. Engineering conventions

8.1 Test first (`tdd-cycle` skill): a test that fails for the stated reason, then the minimal
change, then the full suite green before a task is declared done.

8.2 Tests are not changed to hide a failure, and source is not changed to chase a broken test.

8.3 No dead code, no superfluous comments, no files outside the task's scope. No temporary
scripts, logs or data dumps left in the tree.

8.4 No silenced errors: no empty `except`, no unconditional generic catch, no null return that
hides a failure. A gate that cannot verify denies; it never fails open.

8.5 No new dependency without the user's explicit approval.

8.6 Each version that will run, and its comparison rule, is committed before any result exists.

## 9. Declared limits

The enforcement above does not cover:

* **Writes through `Bash`.** The hooks gate `Edit` and `Write`; a file written by a shell command
  is not gated.
* **Self-issued receipts.** The agent obtains its own `EXECUTE_SAFE`. A receipt proves that a
  well-formed, grounded proposal without forbidden primitives was recorded before the edit, not
  that a human approved it.
* **The content of an edit.** A receipt binds a target file, not what is written to it.
* **Forged logs.** The audit trail and the `context_pack` log are local files. A line written
  through `Bash` forges a receipt, and a receipt names neither agent nor session.
* **Edited scripts.** The shim binds the identity of a committed script, not its content: a
  committed script edited in the working tree still runs.
* **Clever shell.** `deny_python_escapes.py` is a text-level heuristic, not a shell parser:
  `eval`, assembled interpreter paths, login shells that rebuild `PATH` and quoting nested more
  than one level pass it.
* **No session gate.** Without `CLAUDE_ENV_FILE` the shim is not put on the `PATH`; the session
  hook says so on stderr.
* **The session announcement** informs; it cannot block anything.
* **Python 3.9.** The hooks are written to import under a Python 3.9 system interpreter, which is
  checked statically, not by running one.
