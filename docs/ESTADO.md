# Actuarii — status

What a new session needs to know, and nothing more. It is updated when each session closes, together with the entry
of `docs/DEVLOG.md`. The history and the reasoning behind each decision are in `docs/PLAN.md`, which is read when
needed and not loaded in every session (author, 2026-10-14). The criteria of v0.1, the signal, the gate of 24
November and v0.2 are in `docs/ROADMAP.md`; the decisions are in `docs/DECISIONES.md`.

The repository's documents are written in English from 2026-10-18 on (ADR-032); older documents are reviewed one by
one, and stay translated, are condensed or leave the tree (ADR-033). The conversation with the author may be in
Spanish.

Updated: 2026-10-19, afternoon.

## v0.1

* **What it is:** work records for coding agents. The README's sentence: "Work records for coding agents. Every
  action leaves a record that it happened, and why. Built for settings where traceability comes first."
* **What it is not:** a security boundary against an adversarial agent. That is v0.2, with its own environment
  (`docs/design/ENTORNO_PROPIO.md`). AGENTS.md §9 declares what v0.1 does not cover.
* **Publication:** the repository opens on 25 October, ready or not, and is private until then. The text for HN and
  Reddit goes out on Tuesday 27 at about 14:00 Madrid time (ADR-027).
* **Committed success signal:** within the four weeks after the text, up to Tuesday 24 November, 5 outside people
  who install it or open an issue, or one working conversation. If it does not come, it is reviewed with data,
  without reframing. How it is counted: ROADMAP §3.

## Where we are

* Done and verified:
  * the reason (`Rationale`) in every proposal;
  * the permission perimeter, without the `Bash` wildcard in `ask` and with the wider list (ADR-022), checked with
    the probe;
  * the gate and long texts (ADR-024);
  * the one-command installer (V2): the perimeter, `includeGitInstructions`, the `pydantic` check, the questions
    (what else to govern, `pip` with permission and the commit), `--no-input`, and `INSTALL.md` rewritten;
  * the record in git (V3, ADR-016): the gate records what each write leaves and `commit-msg` compares it with the
    commit; installed in this repository, with its first real record in `ba6a120`;
  * Claude Code's automatic memory, turned off in this repository (D5, ADR-010), with its test; the installer does
    not touch it in targets;
  * A20, A31 and A34;
  * AGENTS.md v2.3.0;
  * every governed path with its `denyWrite` entry, no exemptions, checked with a probe;
  * the ROADMAP, with D1–D7 decided;
  * the history rewritten without the personal information and with the *noreply* address, in a new GitHub
    repository (V8);
  * the README (V6) in `main`, with the limits in eight problems (the other half of V5, `2092f2f`), the installation
    with the block and the 223 s, and the real case;
  * the limits by problem (ADR-026), and the text for HN and Reddit on Tuesday 27 with the gate on 24 November
    (ADR-027);
  * the "Resumen" table of `docs/adversarial-audit/CASES.md`, from problem to cases and limits of §9 (V5, `da3ccd0`):
    the 35 cases and the 28 limits, each once;
  * `INSTALL.md` as one block pasted from the repository's top level, with nothing to edit (ADR-028), and
    amendment §4e;
  * **the macOS measurement (V4), passed with 223 s:** attempt 5 of `docs/design/PRUEBA_EN_LIMPIO.md` §5, with its
    deviations noted and milestone 1 checked by §4c;
  * **the target named before any write (ADR-029, `119d569`);**
  * **the real case (ADR-030):** the two defects of the classifier of `noticias` v3, fixed with v0.1 as published
    (`0ef8fb5` and `69d1c36` in AI-Papers-Engine, both with `Actuarii-Record: matches`), the record checked by §4c
    and red and green run; its branch on GitHub and its audit trail in the evidence folder;
  * **the denial of pytest run through the interpreter names `pytest` (ADR-031, `f42cd45`):** rule R7 of the Bash
    hook and a line in the announcement, checked with `verify_red_green.py` and live;
  * **the two decisions of 2026-10-19 on what was found in the inventory (ADR-038), in the tree:** the three
    passages of `PLAN.md` about the author's professional plans are out, and so is the line of the DEVLOG that names
    a third party, with the two that repeated the name.

  Suite green (3705). The detail, with its commits, is in the DEVLOG.
* Pending, in this order (each criterion, with its cut-off, in the ROADMAP):
  1. **The shortened tree (ADR-033, with ADR-032 and ADR-035):** first the renaming batch of ADR-035, from a
     session opened in Actuarii. Then the author reviews each document with Claude, and each one stays (translated),
     is condensed, or leaves the tree; this register is not condensed but selected, entry by entry (ADR-035).
     ADR-033 carries Claude's proposal as the starting point, not as a decision. `ROADMAP.md` is already translated,
     and is also the sample of tone and edits. When the review reaches it, the author stops to work on v0.2.
     Questions Claude brought for that research:
     * a person in the loop and records that cannot be forged: they open v0.2, before the own environment, and
       neither goes into v0.1 (ADR-034, which lists their questions);
     * an own environment: what do existing sandboxes already cover, and what would set this one apart?
     * the signal window: which answers from outside would change the plan of v0.2, written before the opening.
  2. **A full reading of the README** before Thursday 22 (V6).
  3. **Nothing published contradicts the kit (V7),** on the translated tree, and the text for HN and Reddit (V9),
     which asks the question of ADR-034. The description of `pyproject.toml` still uses the old sentence.
  4. **The V8 check and the rewrite of ADR-038:** `git log -p main` without the personal terms the author sets, whose
     list is not kept in the repository; then one rewrite of the history, which takes out the three lines of ADR-038
     and whatever the check finds. The procedure was prepared on 2026-10-19, outside the repository; on GitHub, the
     rewritten `main` goes to a new repository (ADR-039). Then a new commit redoes the citations of the hashes that
     changed. The check goes with the review of each document (item 1), and the rewrite waits for it, so that it runs
     once (author, 2026-10-19). Before it runs, Claude measures the figures of the procedure again.
* Minor, undated (DEVLOG, 2026-10-16): `**` without `re.DOTALL` in `project_config`; the Python traceback of an
  installer `git` call that takes more than 300 s; the installer copies the kit (Apache-2.0) without the license
  text.

## Calendar to the 27th

| When | What |
|---|---|
| Wednesday 14 to Sunday 18 | Done: the perimeter, the installer and its record in git, the measurement (223 s), the limits, the README, the real case, ADR-016 to ADR-032 |
| Monday 19 to Thursday 22 | The review of each document (ADR-033), with the V8 check and v0.2 at the ROADMAP; a full reading of the README |
| Friday 23 and Saturday 24 | The rewrite of ADR-038 once V8 is done, V7 on the translated tree, and the text for HN and Reddit |
| Sunday 25 | The repository opens |
| Tuesday 27 | The text on HN and Reddit, at about 14:00 Madrid time |

## Decisions in force

They are in `docs/DECISIONES.md`, which only grows, except once, at the selection of ADR-035. In force today: ADR-001
to ADR-039, except ADR-012 and ADR-023, superseded by ADR-022 and ADR-024; the first point of ADR-032 is superseded
by ADR-033, its point on file names by ADR-035, and its point on the history, for one rewrite, by ADR-038.

| ADR | Decision |
|---|---|
| 001 | Name, license and relationship with Traianus |
| 002 | The kit first; Traianus as agent memory, only with a signal |
| 003 | Published on 25 October, ready or not |
| 004 | What is not done before the launch |
| 005 | The success signal |
| 006 | Private repository until the 25th, and a single DEVLOG |
| 007 | Distribution of v0.1: an installer that copies the kit |
| 008 | One-command installation, with the environment outside the repository |
| 009 | v0.1 is work records; security is v0.2 |
| 010 | The agent's memory, under code; Claude Code's automatic memory, off |
| 011 | The reason, mandatory, and no receipt without a record |
| 013 | Which audit fixes go into v0.1 |
| 014 | Plain names for the proposal's fields, in v0.2 |
| 015 | A short status at the start of each session, instead of the PLAN |
| 016 | The record in git |
| 017 | The ROADMAP |
| 018 | The README: its first limit and its frame |
| 019 | A33 and A34 are not reported to Anthropic |
| 020 | The history, without personal information and with the *noreply* address |
| 021 | Decisions go in this register, which only grows |
| 022 | The permission perimeter, without wildcard and with the wider list |
| 024 | Only a name that is too long stops being a path |
| 025 | The record in git and the installer's questions, in two contracts |
| 026 | Limits by problem: governance in v0.1, security in v0.2 |
| 027 | The text for HN and Reddit on Tuesday 27; the gate on Tuesday 24 November |
| 028 | Installation as one pasted block; a command with its own screen in v0.2 |
| 029 | The installer names the target in its first question, before any write |
| 030 | The README's real case, in `noticias` v3: the two defects of the classifier |
| 031 | The denial of `python3 -m pytest` names `pytest` |
| 032 | The published tree is in English; the history stays as it is (its first point, superseded by 033) |
| 033 | The published tree is shortened, document by document |
| 034 | A person in the loop and signed records open v0.2; neither goes into v0.1 |
| 035 | File names in English; the register keeps the decisions a reader needs, unedited |
| 036 | `examples/traianus/` stays, as where the kit comes from |
| 037 | The README links Traianus |
| 038 | The author's professional plans leave the tree; a line that names a third party leaves the tree and the history |
| 039 | The rewrite of ADR-038 goes to a new repository |

## How we work

* **The sandbox is on:** `Bash` does not write the governed paths or reach the network. Git commands that rewrite
  governed paths (`switch`, `merge`, `restore`) and `push` are run by the author with `!`. When `main` has not moved
  since a branch left it, the executing agent advances it without rewriting the tree (`git branch -f main <branch>`
  and `git switch main`).
* **The executing agent writes no code.** Code and tests go to the `implementer` subagent, with `model: "sonnet"`,
  through a JSON contract validated with `delegation_contract.py`. Then the executing agent:
  * validates the report;
  * runs `verify_red_green.py` itself;
  * reviews the diff and checks by hand that it touches only the contract's files;
  * advances `main`.
* **A contract lists every test it affects** (AGENTS 6.4): those that build the format, those that pin the behaviour
  that changes, and those that read the code as text.
* **The validator's MCP server runs the code it started with.** A change to the validator takes effect in the next
  session. The tool schema shown to a resumed session may be an old copy: send the reason anyway.
* **The `commit-msg` hook is installed in this repository:** every commit that changes a governed file carries its
  record (`Actuarii-Record`, `Actuarii-Rationale`). An unexpected `changed outside the channel` is looked at before
  going on.
* **A commit message does not mention `python3 -m pytest`:** R7 denies a `git commit -m` that contains it. When it
  has to be named, use `git commit -F -` with a heredoc whose delimiter is quoted.
* **Commit only when `pytest` exits 0,** checking its exit code. Before a full suite, check the free disk space.
* **No attribution to Claude** in commits or PRs. The commit address is GitHub's *noreply* address.
* **The history was rewritten on 2026-10-14:** earlier hashes no longer exist, and the citations in `docs/` were
  redone. The GitHub repository is the new one, with CI green; the old one was deleted (author, 2026-10-14).
* **Python:** committed scripts only, through the shim; `pytest` by its own entry point.
* **The DEVLOG,** when each session closes, with the date of the clock and not that of the conversation.
* **A decision of the author** is appended to `docs/DECISIONES.md` with the next number and listed above. The DEVLOG
  cites it by number, without copying it. An old entry is not changed: if it is revised, the new one says which one
  it supersedes, and the old one leaves the list. Translating it (ADR-032) does not change what it decided.
* **Until the 25th** (Claude's recommendation, 2026-10-14), every task answers one question: does it bring the
  installer or the README closer? If not, it is noted in the PLAN and waits. The only new document before the launch
  is the README.
* **Ideas that leave the path** are noted in the PLAN and wait.
* **The agent's memory** is the one in `.claude/memory/`, under code, with a receipt per write. It is published on
  the 25th: memories are written knowing that. Claude Code's automatic memory is off (`autoMemoryEnabled: false` in
  `.claude/settings.json`, ADR-010); if a session's context brings its instruction, it is not followed and the cause
  is looked for.
* **In a measurement or a real case,** the executing agent gives the method, never commands; what happened in a
  session is read in its transcript, not on the screen.

## How to start a session

1. Read the session announcement: the sandbox must be on and the integrity hook installed.
2. Read the latest DEVLOG entry.
3. Go on with the first pending item of the list above.
