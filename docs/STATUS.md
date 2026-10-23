# Actuarii — status

What a new session needs to know, and nothing more. It is updated when each session closes, together with the entry
of `docs/DEVLOG.md`. The criteria of v0.1, the signal, the gate of 24 November and v0.2 are in `docs/ROADMAP.md`; the
decisions, with their reasons, are in `docs/DECISIONS.md`. The PLAN, which held the reasoning up to 14 October, and
the DEVLOG entries before 18 October left the tree; they are in the history at `64292e1` (ADR-033).

The repository's documents are written in English from 2026-10-18 on (ADR-032); older documents are reviewed one by
one, and stay translated, are condensed or leave the tree (ADR-033). The conversation with the author may be in
Spanish.

Updated: 2026-10-23, afternoon.

## v0.1

* **What it is:** work records for coding agents. The README's sentence: "Work records for coding agents. Every
  action leaves a record that it happened, and why. Built for settings where traceability comes first."
* **What it is not:** a security boundary against an adversarial agent. That is v0.2, with its own environment
  (`ISOLATED_ENVIRONMENT.md`, in the history at `dcfd3b5`, ADR-041). AGENTS.md §9 declares what v0.1 does not cover.
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
    commit; installed in this repository, with its first real record in `57dbc72`;
  * Claude Code's automatic memory, turned off in this repository (D5, ADR-010), with its test; the installer does
    not touch it in targets;
  * A20, A31 and A34;
  * AGENTS.md v2.3.0;
  * every governed path with its `denyWrite` entry, no exemptions, checked with a probe;
  * the ROADMAP, with D1–D7 decided;
  * the history rewritten without the personal information and with the *noreply* address, in a new GitHub
    repository (V8);
  * the README (V6) in `main`, with the limits in eight problems (the other half of V5, `8119cb0`), the installation
    with the block and the 223 s, and the real case;
  * the limits by problem (ADR-026), and the text for HN and Reddit on Tuesday 27 with the gate on 24 November
    (ADR-027);
  * the "Resumen" table of `docs/adversarial-audit/CASES.md`, from problem to cases and limits of §9 (V5, `a8458c1`):
    the 35 cases and the 28 limits, each once;
  * `INSTALL.md` as one block pasted from the repository's top level, with nothing to edit (ADR-028), and
    amendment §4e;
  * **the macOS measurement (V4), passed with 223 s:** attempt 5 of `docs/design/CLEAN_ROOM.md` §5, with its
    deviations noted and milestone 1 checked by §4c;
  * **the target named before any write (ADR-029, `c979cea`);**
  * **the real case (ADR-030):** the two defects of the classifier of `noticias` v3, fixed with v0.1 as published
    (`0ef8fb5` and `69d1c36` in AI-Papers-Engine, both with `Actuarii-Record: matches`), the record checked by §4c
    and red and green run; its branch on GitHub and its audit trail in the evidence folder;
  * **the denial of pytest run through the interpreter names `pytest` (ADR-031, `3e3e50f`):** rule R7 of the Bash
    hook and a line in the announcement, checked with `verify_red_green.py` and live;
  * **the two decisions of 2026-10-19 on what was found in the inventory (ADR-038), in the tree:** the three
    passages of `PLAN.md` about the author's professional plans are out, and so is the line of the DEVLOG that names
    a third party, with the two that repeated the name;
  * **the renaming batch of ADR-035:** the files that stay have English names (`DECISIONS.md`, `STATUS.md`,
    `CLEAN_ROOM.md`, `COST.md`, `ISOLATED_ENVIRONMENT.md` and the three memory files), the live documents and the CI
    step cite them, and the records keep the names of their day, with a dated note at the head of the register and of
    the DEVLOG;
  * **the selection of the register (ADR-035):** 22 entries stay and 17 leave, with the author, entry by entry; the
    head names the commit where those that left remain. The register is in English: its head and the 16 entries
    that were in Spanish, translated without other edits;
  * **`CASES.md` condensed (ADR-033):** 200 lines in English, from 722 in Spanish. The "Summary" table translated
    whole, each case in two or three lines, and one reference to the full record in the history;
  * **`CLEAN_ROOM.md` condensed (ADR-033):** 301 lines in English, from 609 in Spanish, with the numbering of its
    sections kept, so the CI step, the README and the ROADMAP still cite it as they did;
  * **`COST.md` in English (ADR-033):** §1 to §5 translated nearly whole, with a dated note that step 1 of the v0.2
    design was done on 2026-10-14 and not measured again, and §6 reduced to a note;
  * **`ISOLATED_ENVIRONMENT.md` condensed (ADR-033):** 298 lines in English, from 350 in Spanish, with its numbering
    kept, a dated note that ADR-034 puts the person in the loop and signed records first, and Triarii named once;
    out of the tree since 2026-10-23 (ADR-041), in the history at `dcfd3b5`;
  * **`SANDBOX.md` condensed (ADR-033):** 203 lines in English, from 243 in Spanish, with its numbering kept and dated
    notes on what changed since: the exemption of `.claude/**` and `.mcp.json` (`b8b912a`), the bare `"Bash"` of
    ADR-022 and who recommends the user-level setting;
  * **the records (ADR-033):** the DEVLOG trimmed to its entries in English, from 2026-10-18 (evening); the PLAN, the
    two audit guidelines, `PROCESO.md`, `PRIOR_ART.md`, `ARRANQUE_PUERTAS.md`, `RECIBO_CONTENIDO.md` and sixteen
    contracts out of the tree, all in the history at `64292e1`; the contract of ADR-031 kept as an example, as
    `docs/design/PYTEST_NAMED.contract.json`, and linked from the README;
  * **V7 (`bde6a7a`, `0c5a315`):** the description of `pyproject.toml` is the README's sentence; the old name of the
    proposal's fields, "by construction" and the numbered phases of the old plan are out of `tools/` and `tests/`,
    each kept out by a test;
  * **the rewrite of ADR-038 (ADR-039):** the history of `main` without the three lines of ADR-038 and what the V8
    check found, run by the author and checked before the push; the new repository, with CI green; the citations of
    the rewritten hashes redone in the tree, 97 of 46 hashes.

  Suite green (3708). The detail, with its commits, is in the DEVLOG.
* Pending, in this order (each criterion, with its cut-off, in the ROADMAP):
  1. **The research of v0.2, at the ROADMAP (ADR-033):** the review of every other document is done. The plan
     (author, 2026-10-20), with findings in the DEVLOG entry of the day and decisions in the register:
     * R0, which answers from outside would change the plan of v0.2: done, in ROADMAP §3 (ADR-040);
     * R1, whether Claude Code can show the reason before the write and report for certain whether the person
       approved: done from the documentation (DEVLOG, 2026-10-20, midday). It shows the reason, but no hook learns
       the person's answer, and three paths approve without the person; Claude recommends that the validator take the
       approval itself, through a channel out of the agent's reach. The live probe of two modes, after the 25th;
     * R2, which existing format covers signed records: done from the documentation (DEVLOG, 2026-10-20, midday).
       Agent Receipts fits the receipt of each write; git's SSH signing with a hardware key fits the commit, and its
       touch could be the approval; Sigstore and SCITT come later. V9 should say how Actuarii differs from Agent
       Receipts;
     * after the 25th, in the window: R3, whether approving and signing can be one act; R4, how it fits decision 3 of
       `ISOLATED_ENVIRONMENT.md` §10; R5, what existing sandboxes already cover (its §7).

     The web only through the integrated browser, with the author's approval of each site; nothing is probed or
     installed in Actuarii.
  2. **The full reading of the README (V6):** done on 2026-10-20 (DEVLOG). Each of its 24 named tests exists, is in
     the file it links and passes; "What comes next" points to ROADMAP §3, and "How it differs" names Agent Receipts.
  3. **Nothing published contradicts the kit (V7):** done on 2026-10-20 (DEVLOG), in two contracts. Still to do: the
     text for HN and Reddit (V9), which asks the question of ADR-034.
  4. **The rewrite of ADR-038:** done (DEVLOG, 2026-10-23), but for the author's steps: push the commit of the
     citations; check that an old hash answers 404 in the new repository; once that commit is green there, delete the
     old repository, before the 25th; and remove `origin` from the two older local clones that point to the same URL.
     The dead citation `54c7f8c` waits for the author: a small contract to the implementer.
* Minor, undated (the DEVLOG of 2026-10-16, in the history): `**` without `re.DOTALL` in `project_config`; the
  Python traceback of an installer `git` call that takes more than 300 s; the installer copies the kit (Apache-2.0)
  without the license text.

## Calendar to the 27th

| When | What |
|---|---|
| Wednesday 14 to Sunday 18 | Done: the perimeter, the installer and its record in git, the measurement (223 s), the limits, the README, the real case, ADR-016 to ADR-032 |
| Monday 19 to Thursday 22 | The review of each document (ADR-033), with the V8 check and v0.2 at the ROADMAP; a full reading of the README |
| Friday 23 and Saturday 24 | The rewrite of ADR-038 once V8 is done, V7 on the translated tree, and the text for HN and Reddit |
| Sunday 25 | The repository opens |
| Tuesday 27 | The text on HN and Reddit, at about 14:00 Madrid time |

## Decisions in force

Since the selection of 2026-10-19 (ADR-035), `docs/DECISIONS.md` keeps the 22 that stayed and only grows; those that
left are in the history at `c2cd12f`, and this list still counts them. In force today: ADR-001
to ADR-041, except ADR-012 and ADR-023, superseded by ADR-022 and ADR-024; the first point of ADR-032 is superseded
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
| 040 | What would change the plan of v0.2, written before the opening |
| 041 | The design of v0.2 leaves the tree |

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
* **The history was rewritten on 2026-10-14, and again for ADR-038** (run on 2026-10-21, pushed on 2026-10-23):
  earlier hashes no longer exist, and the citations in the tree were redone each time. The GitHub repository is the
  new one of ADR-039, with CI green; the old one, renamed, is deleted by the author once the commit of the citations
  is green there.
* **Python:** committed scripts only, through the shim; `pytest` by its own entry point.
* **The DEVLOG,** when each session closes, with the date of the clock and not that of the conversation.
* **A decision of the author** is appended to `docs/DECISIONS.md` with the next number and listed above. The DEVLOG
  cites it by number, without copying it. An old entry is not changed: if it is revised, the new one says which one
  it supersedes, and the old one leaves the list. Translating it (ADR-032) does not change what it decided.
* **Until the 25th** (Claude's recommendation, 2026-10-14), every task answers one question: does it bring the
  installer or the README closer? If not, it is noted in the DEVLOG entry of the day and waits. The only new document
  before the launch is the README.
* **Ideas that leave the path** are noted in the DEVLOG entry of the day, under "Ideas", and wait; from the 25th, as
  issues of the repository.
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
