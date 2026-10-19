# Actuarii

**Work records for coding agents. Every action leaves a record that it happened, and why. Built for settings
where traceability comes first.**

**The first limit.** Only what goes through the governed channel leaves a record, and that channel is, above
all, the writes to the paths you chose to govern. What the agent does through `Bash`, and what it writes to
paths you did not govern, leaves none. An agent can move its work there, and we have seen one do it
([below](#limits)).

Actuarii v0.1 is not a security boundary against an adversarial agent. That is what v0.2 is for.

It works with [Claude Code](https://claude.com/claude-code) on macOS and Linux. The design records and the
development log are in Spanish; this README, the installation guide and the agent rules are in English.

## Why the rules live outside the model

A coding agent reads instructions and data through the same channel, its context, and it cannot reliably tell
them apart. A file it opens, a test output or a web page can change what it does next. A record that the agent
keeps, or a rule that the agent is asked to follow, is only as good as the agent's reading of its context at
that moment.

Actuarii does not try to keep the agent from being convinced. It takes the decision away from it. The agent
proposes a change and gives its reason; code outside the model checks the proposal and records the decision;
the write goes through only if a receipt for that exact change exists. Whatever convinced the agent, the record
says what was written and why the agent said it was writing it. The reason is recorded, not verified: nothing
checks that it is true.

### What a record looks like

Every commit that changes a governed file carries its record at the end of the message:

```
Actuarii-Record: matches: src/app.py
Actuarii-Rationale: Why the change was made, as the agent gave it in its proposal.
Actuarii-Record: changed outside the channel: AGENTS.md
```

`matches` means that the writes the gate allowed lead from the file at `HEAD` to what the commit holds, and the
`Actuarii-Rationale` lines are the reasons the agent gave for them. `changed outside the channel` means that
something else changed the file: you, an editor, a tool the gate does not see. The full trail (every proposal,
decision, refusal and reason) stays in a local database under `.data/`, which git ignores; the trailers are what
travels with the repository. This repository is developed under its own rules: since `ba6a120`, every commit
that changes a governed file carries its record.

### Which channel decides who

| What the agent does | Who decides | Record |
|---|---|---|
| `Edit`, `Write`, `MultiEdit`, `NotebookEdit` on a governed path | Code: the write gate, with a receipt for that exact change | The proposal, its reason and, except for `NotebookEdit`, what the write left |
| A change to the rules (`.actuarii.json`) | Code: the same gate; the file is always governed | The same |
| `Edit` or `Write` on any other path of the repository | You, through Claude Code's permission mode | None |
| `Bash` | The operating system's sandbox: no write to a governed path, no network. Outside a closed list of read-only commands, your permission mode decides each command | None |
| Running Python | Code: a shim that runs only scripts committed in `HEAD` | None |
| `git commit` | Code: the `pre-commit` hook refuses a governed path that differs from the disk; the `commit-msg` hook writes the record | Trailers in the message |
| `git merge`, `switch`, `restore`, `push`; deleting or renaming a governed file | You: the sandbox keeps them from the agent | None |
| File tools outside the repository (`.git/hooks`, your home directory) | You, through Claude Code's permission prompt | None |
| The integrated browser, your Chrome, connectors, tools that act on the host | The model, with your approval of each site or action | None |
| Reading your credentials (`~/.ssh`, `~/.aws`) | No one | None |

The rows where the model or no one decides are declared limits, not oversights.

### What the kit enforces, and the test that checks it

1. A write to a governed path without a receipt is denied, and the denial names the rule, the file it comes
   from and the call that resolves it.
   [`test_hook_gate.py`](tests/security/test_hook_gate.py):
   `test_a_path_the_configuration_governs_is_denied_without_a_receipt`,
   `test_a_denial_names_the_path_the_rule_the_source_the_window_and_the_call`.
2. A receipt covers one exact change: one byte of difference is another change.
   [`test_content_receipt.py`](tests/security/test_content_receipt.py):
   `test_an_edit_with_other_content_than_the_receipt_is_denied_down_to_one_byte`.
3. Every proposal carries its reason, which is recorded with the decision, also when the proposal is refused.
   No receipt is issued without its record.
   [`test_rationale.py`](tests/security/test_rationale.py):
   `test_a_proposal_without_a_rationale_is_a_schema_violation_and_leaves_no_receipt`,
   `test_a_refusal_after_the_schema_records_the_rationale`,
   `test_an_execute_safe_is_not_issued_when_the_audit_database_cannot_be_written`.
4. The gate records what each write leaves before it allows it, and denies the write when it cannot.
   [`test_gate_record.py`](tests/security/test_gate_record.py):
   `test_a_write_is_denied_when_the_audit_database_can_be_read_but_not_written`.
5. Each commit says, for each governed file, whether the recorded writes lead to what it holds.
   [`test_commit_record.py`](tests/security/test_commit_record.py):
   `test_a_governed_file_written_through_the_gate_is_committed_with_its_record_and_its_rationale`,
   `test_a_governed_file_changed_without_the_gate_is_committed_as_changed_outside_the_channel`.
6. A commit cannot store in a governed path anything other than the file on disk.
   [`test_commit_integrity.py`](tests/security/test_commit_integrity.py):
   `test_a_forged_blob_written_with_hash_object_and_staged_with_update_index_is_refused`,
   `test_a_real_commit_with_an_older_blob_staged_is_refused_and_accepted_once_the_index_matches_the_disk`.
7. The rules are governed too: `.actuarii.json` always needs a receipt, and an invalid one denies every write
   inside the repository, its own fix included until it has a receipt.
   [`test_project_config.py`](tests/security/test_project_config.py):
   `test_the_configuration_itself_is_always_governed`;
   [`test_hook_gate.py`](tests/security/test_hook_gate.py):
   `test_an_invalid_configuration_denies_everything_inside_the_root_with_the_error`,
   `test_the_configuration_file_stays_subject_to_a_receipt_when_it_is_invalid`.
8. A governed Python write cannot introduce a process, network or code-loading primitive the file did not
   have. [`test_gate_primitives.py`](tests/security/test_gate_primitives.py):
   `test_an_edit_with_a_receipt_whose_result_introduces_a_primitive_is_denied`.
9. Python runs only scripts committed in `HEAD`, from the directories the configuration allows.
   [`test_python_gate.py`](tests/security/test_python_gate.py):
   `test_denies_argv_that_is_not_a_committed_script`,
   `test_an_uncommitted_script_in_a_permitted_directory_is_still_denied`.
10. `Bash` runs in the operating system's sandbox, which keeps it from the governed paths and the network. The
    operating system enforces it; the tests pin the settings, here and in what the installer writes, and the
    behaviour was probed by hand ([`SANDBOX.md`](docs/design/SANDBOX.md) §8).
    [`test_sandbox_settings.py`](tests/security/test_sandbox_settings.py):
    `test_the_committed_sandbox_values_are_strict`,
    `test_every_governed_path_of_the_committed_configuration_has_its_deny_write_entry`;
    [`test_installer.py`](tests/unit/test_installer.py):
    `test_the_sandbox_values_of_the_installer_are_the_ones_the_settings_test_pins`.
11. The kit's permission rules allow no `Bash` command outside a closed list of read-only commands, the kit's
    own scripts and `pytest`, and they deny `rm`, inline Python and the network tools.
    [`test_config_perimeter.py`](tests/security/test_config_perimeter.py):
    `test_security_SEC_M_13_allow_list_is_closed`,
    `test_security_SEC_M_13_required_denies_persist`.
12. The installer never overwrites: with any conflict it lists them all and writes nothing.
    [`test_installer.py`](tests/unit/test_installer.py):
    `test_a_conflict_exits_one_names_it_and_leaves_the_target_untouched`,
    `test_every_conflict_is_listed_at_once`.

## Limits

An adversarial audit of the kit recorded 35 cases. Each one is in
[`CASES.md`](docs/adversarial-audit/CASES.md) (in Spanish), and every limit that remains is declared in
[`AGENTS.md` §9](AGENTS.md#9-declared-limits). They come down to eight problems:

* **Governance (problems 1 to 4).** The record can be incomplete without anyone trying. These are the limits of
  v0.1.
* **Security (problems 5 to 8).** An agent that looks for a way out finds one. That is what v0.2 is for, if it
  comes ([below](#what-comes-next)).

### Governance: the record can be incomplete without anyone trying

1. **The record covers only its channel.** It is made when a file tool writes a governed path, not on the disk.
   None of these leaves a record:
   * `Bash`;
   * the paths you did not govern;
   * the integrated browser and the connectors.

   A commit made with `--no-verify` gets no record, and one carried over by a rebase keeps its trailers
   without a new check.

   *Example:* in a test on a real repository, the agent was asked to write tests for a module whose directory
   was governed. It wrote them in `tests/unit/`, which was not, and said it did so to avoid asking for a receipt
   ([`PRUEBA_EN_LIMPIO.md`](docs/design/PRUEBA_EN_LIMPIO.md) §5). It broke no rule.

   *In v0.2:* every write to a governed path from inside the environment, `Bash` included, goes through one
   broker, and deleting or renaming a governed file gets a governed channel. The paths you do not govern stay
   outside.
2. **No person approves the receipts or their reasons.** There is no human in the loop. The agent issues its own
   receipt and writes its own reason. The validator checks the form of the proposal and its quote of the file,
   not that the reason is true. The red phase of a delegated test and the delegation itself work the same way:
   the agent that executes checks itself.

   *Example:* in the installation measured on macOS, the agent got its receipt and wrote two seconds later.
   Claude Code asked the person to approve the write and showed its content. The reason went only to the
   validator, and no one read it.

   *In v0.2, first:* a person sees the agent's reason next to the change and approves or refuses each receipt,
   and the approval goes into the record. Later, the broker writes exactly what it validated, and a delegated
   implementer can write only the files its contract lists.
3. **The kit trusts the way you set it up.** Some of what the person sets up changes what the kit does:
   * a governed path that is a symbolic link is governed by its target;
   * with git's `core.fileMode` off, the commit check can refuse a valid commit;
   * without Claude Code's session environment file, the Python shim is not on the `PATH`.

   The session announcement reports the configuration and does not check it.

   *Example:* whenever the sandbox is on, the announcement says that `Bash` cannot write the governed paths. It
   does not check that each one has its `denyWrite` entry.

   *In v0.2:* the announcement becomes a report generated from the environment's real configuration.
4. **When the validator goes down, work stops.** Without the validator's server there are no receipts, and every
   governed write is denied. The kit fails closed, but a malformed request can stop the server until the session
   restarts.

   *Example:* a tool call whose `arguments` is a list instead of an object ends the server.

   *In v0.2:* the broker rejects a malformed request and keeps running.

### Security: an agent that looks for a way out finds one

5. **The gates start in an environment the agent can reach.** The hooks, the validator and the commit hooks run
   outside the sandbox, with the `python3`, the `PATH` and the settings of the session. The file tools can write
   `.git/hooks` and `.git/config`, which the sandbox keeps from `Bash`, and only Claude Code's permission prompt
   stands in the way. The boundary is borrowed from Claude Code: these are limits of the kit, not faults of
   Claude Code.

   *Example:* with a virtual environment inside the repository, a `sitecustomize.py` planted in its
   `site-packages` ran at every call of a gate, outside the sandbox. That is why the install guide keeps the
   environment outside the repository.

   *In v0.2:* the gates and the broker run outside the environment, installed outside the repository, and load
   nothing the agent can reach. Nothing inside can write `.git`.
6. **The checks are text, not a boundary.** The list of forbidden Python primitives, the shell check that keeps
   Python behind the shim and the list of read-only commands are checks on text, and each has known ways around
   it. The boundary for what runs is the operating system's sandbox.

   *Example:* `pytest` runs every test file it collects, committed or not, with its own interpreter and outside
   the shim.

   *In v0.2:* the environment's permissions replace these checks as the boundary.
7. **Outside the audit database, records can be written.** The sandbox protects the database file, not the rest
   of `.data/`: the context log, the blind review's lock and the database's journal files. The commit trailers
   are text: anyone can write them, and nothing signs them.

   *Example:* removing the review lock from `Bash` ends a blind review.

   *In v0.2, first:* the records are signed out of the agent's reach, so that someone else can check them and a
   forged one is detected. Later, the audit trail and the lock live outside the environment, and a blind review
   runs in an environment that sees only its package.
8. **The session has what you have.** The kit runs with your permissions: nothing stops `Bash` or `Read` from
   reading your credentials.

   *Example:* in this repository's audit, `Bash` could open `~/.ssh` and `~/.config/gh` from inside the sandbox.

   *In v0.2:* your home directory does not exist inside the environment. The network reaches only what the
   configuration allows, through a proxy outside it.

v0.2 does not solve prompt injection either. The agent still reads content it cannot trust; what changes is that
it can no longer act outside its environment ([`ENTORNO_PROPIO.md`](docs/design/ENTORNO_PROPIO.md) §6).

## Install

You need `git`, Claude Code and Python 3.11, as `python3.11`. Open a terminal at the top level of your repository
and paste this block as it is. Nothing in it needs editing:

```bash
REPO=$(git rev-parse --show-toplevel) &&
ACTUARII=$(dirname "$REPO")/actuarii &&
git clone https://github.com/AlexusPacicus/actuarii.git "$ACTUARII" &&
python3.11 -m venv ~/.venvs/actuarii &&
source ~/.venvs/actuarii/bin/activate &&
python3 "$ACTUARII/tools/install.py" "$REPO" &&
cd "$REPO"
```

The block does three things and stops at the first that fails:

1. it clones Actuarii next to your repository, never inside it;
2. it creates the session's Python environment outside the repository, in `~/.venvs/actuarii`, and activates
   it;
3. it runs the installer.

The installer asks at most three questions:

* which other paths to govern. This question starts by naming the repository the kit goes into. If that is not
  the one you meant, stop with Ctrl-C: nothing has been written yet;
* whether to install the kit's one dependency, `pydantic`, when the environment lacks it;
* whether to commit what it installed.

Then start Claude Code in the same terminal, with `claude`. [`INSTALL.md`](INSTALL.md) has the details, the mode
without questions and what each file does.

**How long it takes.** Measured once on macOS, by the author, who knows the kit: **223 s**, about four minutes,
from a fresh clone of a real repository to the first governed write. That includes reading the guide and
installing `pydantic` from scratch. The agent's part, from the prompt to the write, took 19 s. The earlier
procedure, in several steps, took 612.8 s ([`PRUEBA_EN_LIMPIO.md`](docs/design/PRUEBA_EN_LIMPIO.md) §5).

## What it costs

Each governed write adds a median of **1875 ms**: the round trip to the validator (1378 ms) and two hooks of
about 250 ms each, which are almost all Python start-up. The validator itself answers in 4 ms; most of the
round trip is the harness. A proposal is about 1.06 times the size of the edit it covers. Measured on 7 October
2026 over 15 writes ([`COSTE.md`](docs/design/COSTE.md), in Spanish); the kit has changed since and has not been
measured again. v0.1 is not optimised; the design for v0.2 is in `COSTE.md` §5.

## What falls to you

The only governed channel is writing content through the file tools. Everything else on a governed path
falls to you, because the sandbox blocks it and no receipt can allow it:

* `git merge`, `switch`, `restore` and a `checkout` of a path, when they rewrite governed files;
* deleting, renaming or changing the mode of a governed file;
* `git push`;
* the permission prompts of Claude Code, as your permission mode decides: for `Bash` commands outside the
  read-only list, and for the file tools outside the repository.

When `main` has not moved since a branch left it, the agent can fast-forward `main` to the branch without
rewriting the tree.

## What comes next

If v0.1 shows a signal, set in advance in [`ROADMAP.md`](docs/ROADMAP.md), v0.2 starts with the two
questions a team that needs traceability asks first: who approved this change, and can the record be forged. A
person sees the agent's reason next to each change and approves or refuses its receipt, and the records are signed
out of the agent's reach, so that someone else can check them. Then v0.2 runs the whole agent inside an isolated
environment of its own, with the gates and a write broker outside it, so that the boundary no longer depends on one
vendor's hooks and is designed to hold against an adversarial agent
([`ENTORNO_PROPIO.md`](docs/design/ENTORNO_PROPIO.md)).

## A real case

This is one piece of real work in another project, done with v0.1 as published. The case was planned before it was
done ([`PRUEBA_EN_LIMPIO.md`](docs/design/PRUEBA_EN_LIMPIO.md) §4f); the full record is in §5.

[AI Papers Engine](https://github.com/AlexusPacicus/AI-Papers-Engine) has a lexical classifier of papers by method
family, and it had two defects:
* the key `gan` matched inside `organization`;
* a text with `diffusion transformer` tied between two families and came out as `other`.

On 18 October the kit was installed on a fresh clone with the block above, governing `explorations/v3/**`. Claude
Code (Sonnet 5.5) got one task: fix both, tests first. It took 8½ minutes, and this is what happened:

* **The agent wrote the tests first.** The validator refused its first proposal, which imported `importlib`; the
  agent rewrote the import.
* **The gate denied one `Edit` that had no receipt of its own.** The agent asked for one and went on.
* **The agent could not run the tests.** The kit denies `python3 -m pytest`, and the denial, Claude Code's generic
  message, did not say that `pytest` itself is allowed. The agent tried three times and then stopped, and the person
  told it to use `pytest`. This is a gap in the kit, and this case found it. Counting that, the person stepped in
  four times.
* **Two commits, each with its record.**
  [`0ef8fb5`](https://github.com/AlexusPacicus/AI-Papers-Engine/commit/0ef8fb5) holds the tests: run against the old
  classifier, the two that check the defects fail for the stated reasons, and the control passes.
  [`69d1c36`](https://github.com/AlexusPacicus/AI-Papers-Engine/commit/69d1c36) holds the fix, and all three tests
  pass. Its message ends with:

  ```
  Actuarii-Record: matches: explorations/v3/scripts/classify_method_family.py
  Actuarii-Rationale: Corrige dos defectos: las claves se buscan con límites de palabra (gan ya no cuenta dentro de organization) y una clave contenida en otra más larga de otra familia no suma (diffusion dentro de diffusion transformer), lo que evita el empate.
  Actuarii-Rationale: Importa re, necesario para buscar las claves con límites de palabra.
  ```

* **Checked afterwards against the audit trail:** three governed writes, each with a receipt issued before it for
  that exact content, and no governed change without a write.

The reasons are the agent's own, in the language of the task. Nothing checked them, and no person approved them
(problem 2 above).

**The gap, closed through the same channel.** The kit's Bash hook now denies `python3 -m pytest` itself, before
Claude Code's rule, and names the call that works: `pytest`, with the same arguments. The session announcement says
how tests run, too. The fix followed the same steps:
* a decision of the author;
* a contract for the implementer, which wrote the tests first;
* a check in code that the new tests failed before the change and pass after it;
* a commit whose record says `matches` for each of its four files
  ([`f42cd45`](https://github.com/AlexusPacicus/actuarii/commit/f42cd45)).

## Where it comes from

Actuarii was not designed first and used later. It grew as the governance of
[Traianus](https://github.com/AlexusPacicus/Traianus), a research project run by one person with coding agents, and
was extracted from it, with its history, on 5 October 2026. [`examples/traianus/`](examples/traianus/) is that
project's configuration in Actuarii's format, with the agents and the review procedure it used. It is the only real
configuration that uses the contract registry and the blind review, and the tests load it. Traianus itself does not
run Actuarii: it still runs the gates as they were before the extraction.

## License

Apache-2.0. See [`LICENSE`](LICENSE).
