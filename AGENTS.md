# AGENTS.md — Agent constitution (v2.1.0)

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
rules and their source into the agent's context, and says whether the `Bash` sandbox is on and the
commit integrity hook installed. The agent **MUST** read that announcement before its first edit.

1.3 `.actuarii.json` and the configured contract registry are always governed, whatever the
configuration lists. **[enforced]** Every change to the rules leaves a receipt in the audit
trail.

## 2. Governed writes

2.1 Before an `Edit`, `MultiEdit`, `Write` or `NotebookEdit` on a governed path, the agent **MUST**
call the boundary-validator MCP tool `validate_proposal` with a proposal for that exact change and
with the exact file as its separate `target_file` argument. **[enforced]** The hook
`tools/hooks/require_boundary_validation.py` denies the write unless the audit trail holds an
`EXECUTE_SAFE` receipt for it within the configured window: for an `Edit`, the receipt's
`Topological_Grounding` is the `old_string` and its `Implementation_Block` the `new_string`; a
`MultiEdit` needs one such receipt per edit; for a `Write` the `Implementation_Block` is the whole
`content`, and for a `NotebookEdit` the `new_source`. Nothing is normalised: one character of
difference is another change. A tool the gate does not know that names a governed path needs a
receipt for that file. The denial names the rule, its source and the call that resolves it.

2.2 A proposal **MUST** conform to the strict proposal schema
(`tools/boundary_validator/schemas/proposals.py`): `Intent_Class` (`FIX`, `REFACTOR`, `TEST`,
`DOC`, `SPEC`, `AUDIT`), `Target_File`, `Topological_Grounding`, `Implementation_Block`,
`Rationale` (1 to 1000 characters that say why the change is made, in words the person who reads
the audit trail understands; it is recorded with the decision and nothing checks that it is true)
and `Safety_Abort`, sent as an object, with `target_file` naming the same file as `Target_File`.
**[enforced]**

2.3 When the target file exists, the `Topological_Grounding` **MUST** be a quote present byte by
byte in it, whatever the intent; an empty file admits only the empty quote. For a file that does
not exist yet, `FIX`, `REFACTOR` and `AUDIT` are refused. **[enforced]**

2.4 A write to a governed Python file (`.py`) **MUST NOT** introduce a network, process or
code-loading primitive: an import of `subprocess`, `socket`, `urllib`, `http`, `importlib`,
`ctypes`, `multiprocessing`, `asyncio` or another module listed in
`tools/boundary_validator/primitives.py`; an `os` process function (`os.system`, `os.popen`,
`os.exec*`, `os.spawn*`, `os.fork`), or `from os import *`; or a reference to `eval`, `exec`,
`compile` or `__import__`. **[enforced]** The write gate parses the exact result of the write with
`ast` and denies a primitive the file did not already have, or a result that does not parse; the
validator refuses the receipt early on the same grounds. Other files get no such check. Repository
tooling and tests that must start a process do it in one designated module
(`tools/audit/run_process.py`).

2.5 A `Safety_Abort` other than `NONE` blocks the proposal. The agent **MUST** set it when it
sees that the change crosses a boundary it should not cross. **[enforced]**

2.6 A commit **MUST NOT** store in a governed path anything other than the file on disk.
**[enforced]** The git hook `tools/git/pre-commit`, which the person installs as
`.git/hooks/pre-commit`, refuses a commit in which a staged governed path differs from the disk
(content or mode), or in which any staged path is spelled otherwise than the disk spells it. A
governed file is committed whole.

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
`delegation_contract.py contract` before the launch, and `delegation_contract.py report` and
`tools/audit/verify_red_green.py` before the report is accepted. **[enforced]** The report names the
pytest node ids and the expectation of every test; the verifier runs them, in temporary worktrees,
at the base commit with the final test files and at the final commit, and then the whole suite at
the final commit: a red test must not pass at base, a guard must, and everything must pass at the
end. The proof is the run, not the report.

6.3 The implementer works on the one branch the contract names, touches only the files it lists,
writes the tests first, passes every gate the contract names, never pushes and stops at a commit.
The review of the diff, the merge and the records stay with the executing agent.

6.4 When a contract changes a schema or a shared format, it **MUST** list every test that builds
that format, so that the implementer does not stop on a file it may not touch.

6.5 A contract that changes a hook **MUST** order its edits so that each one leaves the hook
working: a hook is read again on every call, so a half-made hook is the one in force. A new
module and its import come before the code that uses them.

## 7. Permission perimeter

7.1 `.claude/settings.json` (Claude Code) and `opencode.jsonc` (OpenCode) **MUST** stay identical
in permission rules: read-only git commands, the scripts under `tools/`, `pytest`, a closed list of
read-only commands (`ls`, `cat`, `head`, `tail`, `wc`, `grep`, `df`, `echo`, `sed -n`, `sort`,
`uniq`, `diff`) and the validator's own tool, `validate_proposal`, which writes only the audit
trail, allowed; `rm`, inline Python, web fetch and web search denied; every other `Bash` call
asked. **[enforced by tests]** What an allowed command writes through a redirection is not asked;
inside the sandbox it never reaches a governed path (7.3). `Edit` and `Write` ask or not according
to the permission mode the person chooses; on a governed path they need their receipt in any mode
(2.1). The `Bash` sandbox of 7.3 exists only in Claude Code.

7.2 Both harnesses load the same instructions: `CLAUDE.md` imports and the OpenCode
`instructions` list name the same files. **[enforced by tests]**

7.3 In Claude Code, `Bash` commands and every process they start run inside the operating
system's sandbox (`sandbox` in `.claude/settings.json`): no network except through the sandbox
proxy, whose allowlist is empty; no write, move or deletion in the governed paths or in the
validator's audit database; no retry outside the sandbox; no session without it; and every
command not allowed is still asked. **[enforced]** by the operating system; its settings are
pinned by tests, and every governed path **MUST** have its `denyWrite` entry.

7.4 Git commands that write governed paths in the working tree (`switch`, `merge`, `restore`, a
`checkout` of a path) fail inside the sandbox. The person runs them.

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

* **`Bash` without the sandbox.** Under OpenCode, on native Windows, or with the sandbox off (the
  session announcement says which), writes through `Bash` pass none of the gates and `Bash`
  reaches the network. A `.claude/settings.local.json` present before the session starts can turn
  the sandbox or the hooks off; during the session it cannot be written. An
  `allowUnsandboxedCommands: false` in the user's own `~/.claude/settings.json` holds against it.
* **OpenCode's skills.** `.opencode/` is not governed: an agent writes its skills without a receipt,
  from `Bash` too. A changed copy turns the test that keeps both tools' skills identical red, and the
  Claude Code copy, which is governed, cannot follow it without a receipt.
* **Self-issued receipts.** The agent obtains its own `EXECUTE_SAFE`. A receipt proves that a
  well-formed, grounded proposal for that exact change was recorded before the write, not that a
  human approved it.
* **What a receipt does not bind.** `replace_all` of an `Edit` decides how many times the approved
  change applies; a `NotebookEdit` binds only its `new_source`; a tool the gate does not know gets
  a receipt per file, with any content.
* **Primitives are a deny list.** The check of 2.4 stops a direct primitive in Python. Python has
  other ways (`getattr` on strings, `sys.modules`, `pickle`, native extensions), and other files
  are not checked. It warns the honest agent; the boundary for what runs is the sandbox (7.3).
* **Forged logs.** The `context_pack` log and the review lock live in `.data/` and are written
  from `Bash`: a line written there forges a context receipt, and removing the lock ends a blind
  review. The validator's audit database is out of `Bash`'s reach while the sandbox is on. A
  receipt names neither agent nor session.
* **Commits around the hook.** `git commit --no-verify` and git's internal commands (`commit-tree`,
  `update-ref`) skip the hook, and `git merge` does not run it; the person approves each of those
  commands. The hook works only where the person installed it (the session announcement says
  whether it is), and with `core.fileMode` off its mode check can refuse a valid commit.
* **Test runners.** `pytest` runs the test files it collects, committed or not, with its own
  interpreter, outside the shim; so do `uv run` and `pipx run`. With the sandbox on they reach
  neither the network nor the governed paths.
* **Red for the stated reason.** The verifier of 6.2 proves that a red test does not pass at the
  base commit, not that it fails for the reason the report gives; a test with several node ids is
  red when they do not all pass at base. The base commit keeps its own `conftest.py` and support
  files: only the test files are brought from the final commit.
* **Edited scripts.** The shim binds the identity of a committed script, not its content: a
  committed script edited in the working tree still runs.
* **Clever shell.** `deny_python_escapes.py` is a text-level heuristic, not a shell parser:
  `eval`, assembled interpreter paths, login shells that rebuild `PATH` and quoting nested more
  than one level pass it, and a quoted argument can read as an assignment. With the sandbox on, a
  way around it reaches neither the network nor the governed paths.
* **Read-only commands that are not.** Some commands of the allow list of 7.1 write or start a
  program through their own options, without a prompt: `sort -o` and `sort --compress-program`,
  `uniq` with an output file, and `sed -n` with its `w` command and, in GNU `sed`, its `e` command,
  which runs a shell command. With the sandbox on, they reach neither the network nor the governed
  paths.
* **No session gate.** Without `CLAUDE_ENV_FILE` the shim is not put on the `PATH`; the session
  hook says so on stderr.
* **The session announcement** informs; it cannot block anything.
* **Python 3.9.** The hooks and the commit check are written to import under a Python 3.9 system
  interpreter. The hook commands are run by the tests under the system `/usr/bin/python3` where
  one exists, on the payloads the tests carry; the rest is checked statically.
