# Actuarii — roadmap

Drafted by Claude on 2026-10-14, for the author to correct before it was committed (author, 2026-10-14). It serves
two purposes: to cut the scope before 25 October, and to make the review of 24 November against something written
in advance. The author accepted Claude's proposals in V2–V9 and in §3–§5 on 2026-10-14 (D7); §6 lists the decisions
that were open then.

The reasons for each decision are in `docs/PLAN.md`, and the work of each day in `docs/STATUS.md`, which also says
where each criterion stands. Since it was committed, a change of criterion is decided by the author and added, with
its reason, to `docs/DECISIONS.md`. On 24 November this document is only touched to record the result.

Translated from Spanish on 2026-10-18 (ADR-032).

## 1. Three dates

| When | What |
|---|---|
| Sunday 25 October | v0.1 is published, ready or not (author, 2026-10-06): the repository opens |
| Tuesday 27 October | The text for HN and Reddit, at about 14:00 Madrid time (ADR-027) |
| 27 October to 24 November | The signal window (§3) |
| Tuesday 24 November | The gate: the signal is looked at and the start of v0.2 is decided (§4) |

## 2. v0.1

**What it is:** "Work records for coding agents. Every action leaves a record that it happened, and why. Built for
settings where traceability comes first." **What it is not:** a boundary against an adversarial agent; that is
v0.2.

A criterion that is not met on the 25th does not move the date. Each one says how it is checked, when it is cut and
what happens if it is not met.

**V1. The suite, green.**
* Check: `pytest` exits 0 on macOS, and the Linux CI is green, on the commit that is published.
* If not met: the last green commit of `main` is published.

**V2. One-command installation.**
* What: `tools/install.py` leaves the target like this repository:
  * the validator with the reason, and the permission perimeter of AGENTS 7.1;
  * `includeGitInstructions: false`, without which `build --lock` does not set the lock;
  * a `denyWrite` entry for each governed path;
  * the `pre-commit` and `commit-msg` hooks (V3);
  * `pydantic` checked in the interpreter the server will start with, with permission before installing it;
  * it only asks which paths to govern and whether to commit, and it has a mode without questions.

  `INSTALL.md` is rewritten, with the environment outside the repository.
* Check: the installer's tests and steps 1 to 4 of the clean-room test in the CI.
* Cut-off: Friday 16, evening.
* If not met: the first contract carries what the kit needs to work in the target (perimeter,
  `includeGitInstructions`, `denyWrite` and `pydantic`); the second, the questions and `commit-msg`. What does not
  make it stays as a manual step in `INSTALL.md`, and the README says so.

**V3. The record in git.**
* What: a `commit-msg` hook appends to the message of each commit, as trailers, the reasons of the receipts of its
  governed files, and says whether the content of the commit matches what those writes left (D1). It only records;
  it does not block (author, 2026-10-14).
* Check: one test commits a governed file written with a receipt and finds its reason in the message; another
  commits a file changed without a receipt and finds that the message says so.
* Cut-off: Friday 16, with the second installer contract.
* If not met: the README's sentence loses "that it happened" and says what remains: the reason of each governed
  write, in the local database.

**V4. Installing in less than 5 minutes.**
* What: the clean-room test of `docs/design/CLEAN_ROOM.md`, on macOS, with the new installer and its amendment
  committed before measuring. The last measurement gave 612.8 s (2026-10-12).
* Check: milestone 2 comes in less than 300 s (the rule of its §4).
* Cut-off: Sunday 18. The author does it.
* If not met: the README gives the figure, and the author decides with the time of each step (the rule of its §4).

**V5. The limits, complete.**
* What: the limits by problem, each with its reason (ADR-026): four of governance, in v0.1, and four of security,
  which go to v0.2.
  * The "Summary" table of `docs/adversarial-audit/CASES.md` goes from problem to cases, with what was fixed and its
    commit.
  * The limits section of the README gives the eight problems, each with its reason, an example and what changes in
    v0.2, without the ids of the cases.
* Check: each case of `CASES.md`, A01 to A35, and each limit of AGENTS §9 belongs to one problem.
* Cut-off: Monday 19.
* If not met: the README links `CASES.md` and §9 as they are.

**V6. The README in English.**
* What, in this order:
  * the sentence and its first limit (D3);
  * the problem (D6) and which channel decides who;
  * the limits (V5);
  * the installation;
  * the cost per governed write, with its figure (a median of 1875 ms, `docs/design/COST.md`);
  * what falls to the person (`merge`, `switch`, deleting);
  * v0.2 in one sentence;
  * a real case: the two defects of the classifier of `noticias` v3, with their commits (ADR-030).
* Check: everything the README says the kit enforces names the test that checks it; if it has none, it is removed.
* Cut-off: Thursday 22.
* If not met: it is cut in this order: first the real case (a link to the DEVLOG stays), then the table of
  channels. The sentence, the limits and the installation are not cut.

**V7. Nothing published contradicts the kit.**
* What: no document of the published tree describes as current what no longer is. A record describes its own day:
  where it describes something that has since changed, it says so in a dated note that names what replaced it
  (ADR-032). Known on 2026-10-18:
  * the exemption of `.claude/**` in `docs/design/SANDBOX.md` §6;
  * "Blind by construction" in `examples/traianus/skills/instrument-audit/SKILL.md` (the folder stays, ADR-036;
    corrected on 2026-10-19);
  * "5 Radicals" in `docs/` and `examples/`;
  * the description of `pyproject.toml`, which predates the sentence of ADR-009.
* Check: a reading of the translated tree, and a `grep` of those phrases that finds them only next to their note.
* Cut-off: Friday 23.
* If not met: it is published, with an issue opened in the repository itself for each document.

**V8. Before the repository opens.**
* What:
  * the personal information the author listed, out of the tree and out of the history of `main` (D2). It was in
    `docs/PLAN.md`, `docs/DEVLOG.md` and `docs/adversarial-audit/PAUTAS.md` from `de8cabf`, and in
    `.claude/memory/autor.md`; the list of terms is not kept in the repository;
  * on `origin`, only `main`.
* Check: `git log -p main` does not contain the terms the author sets, and `git ls-remote --heads origin` lists only
  `main`.
* Cut-off: Saturday 24.
* If not met: it is the only criterion that delays the opening, because what is published cannot be taken back. The
  author decides.

**V9. The text for HN and Reddit.**
* What: a short technical text in English, with each site's self-promotion rules read first. It goes out on
  Tuesday 27 at about 14:00 Madrid time, 9:00 in New York (ADR-027).
* Cut-off: Saturday 24.
* If not met: the repository opens on the 25th and the text goes out in the first week of the window.

**V10. The published tree in English (ADR-032, ADR-035).**
* What: every document of the tree in English, edited for a reader from outside, in this order: what the README
  links; `DECISIONS.md`; the other records. Every file that stays has an English name (ADR-035). The git history
  stays as it is.
* Check: no document of the tree is in Spanish, except the agent's reasons quoted as they were given, and no file name
  is.
* Cut-off: Saturday 24.
* If not met: what is not translated leaves the tree; the history keeps it in Spanish.

**Out of v0.1 (decided):**
* A19, A32, option (c) with A33, and A35 go to v0.2, declared in §9. A21, A23, A24, A25 and A28 stay declared
  without a fix (author, 2026-10-14).
* Nothing of Traianus, no governance improvement that does not answer a real failure, and no new function except the
  record in git (author, 2026-10-06 and 2026-10-14).
* The plain names of the fields, the plugin, a single command with its own screen (ADR-028) and the cost
  optimisation go to v0.2.

## 3. The signal window

**The commitment (author, 2026-10-07):** within the four weeks after publication, success if at least 5 outside
people install it or open an issue, or if one working conversation starts. If it does not come, it is reviewed with
data, without reframing. The four weeks are counted from the text for HN and Reddit, on Tuesday 27 October
(ADR-027).

**How it is counted:**
* People are counted, not actions: someone who installs it and also opens an issue counts once.
* **Outside:** not the author, nor someone close to the author who was asked to try it.
* **Installs it:** there is something to show: they say so in an issue, a comment or a message, or they have a public
  repository with `.actuarii.json`. Clones, visits and GitHub stars are not installations; they are noted as
  context.
* **Opens an issue:** an issue or a pull request from an account that is not the author's and is not spam.
* **Working conversation:** an exchange about paid work or a collaboration that names Actuarii, with an answer from
  both sides. One is enough.
* **Where it is noted:** GitHub keeps only 14 days of traffic. Each Sunday (1, 8, 15 and 22 November), and on
  Tuesday 24 at the close, a line in the DEVLOG says what counts, linked when it is public, with the traffic as
  context. Of a private conversation, only its existence is noted, without names: the DEVLOG is public.
* **Until when:** what arrives up to Tuesday 24 November at 23:59, Madrid time (ADR-027).

## 4. The gate of 24 November

The count of §3 is looked at, with its evidence, and nothing else.

* **If it is met:** v0.2 starts (§5). Phase 4, Traianus as agent memory, also needs its own usefulness criterion
  (`docs/PLAN.md`).
* **If it is not met:**
  * neither v0.2 nor phase 4 starts;
  * the DEVLOG records what came, with the figures, and why the author thinks the rest did not;
  * whatever comes next is a new plan, with its own signal written in advance, not a continuation of this one;
  * four people out of five do not count as a signal.

## 5. v0.2

**What it is:** first, a person in the loop and signed records (author, 2026-10-19, ADR-034). Then the isolated
environment of `docs/design/ISOLATED_ENVIRONMENT.md`: the whole agent inside, and the gates and a write broker
outside. Its motivation is the one v0.1 set aside: that using agents safely needs a middleware (author,
2026-10-13). It starts only if the gate is passed.

**Criteria:**
* A person in the loop: the person sees the agent's reason next to the change and approves or refuses each receipt,
  and the approval or the refusal goes into the record (ADR-034).
* Signed records: the record is signed out of the agent's reach, someone other than the author can check it, and a
  forged one is detected (ADR-034).
* The guarantees E1–E9 (`ISOLATED_ENVIRONMENT.md` §3).
* The battery of its §8: each case of the two audits that applies, and the "Internet" cases, comes out as expected,
  in Claude Code and in OpenCode.
* The cost: the median time added per governed write, below 1 s, with the method of `docs/design/COST.md` (in v0.1,
  1875 ms).
* The installation: from zero in less than 300 s, with the method of `docs/design/CLEAN_ROOM.md`.
* Plain names for the proposal's fields (author, 2026-10-14).
* The rule of each measurement, committed before measuring.

**Order:** first the person in the loop and the signed records, each with its research and its decisions taken
before any code (ADR-034); then the phases v0.2-a to v0.2-e of `ISOLATED_ENVIRONMENT.md` §9, with the decisions of
its §10 taken before the prototype.

**Date and scope:** the date is set on 24 November, with the rule of v0.1: it does not move; the scope is cut. Of
the PLAN's "Ideas for v0.2", only what a criterion here needs goes in.

## 6. Decisions that were open

Each one carries Claude's recommendation and, once taken, the author's decision. All were taken and went to
`docs/DECISIONS.md`: D1 is ADR-016; D2, ADR-020; D3 and D6, ADR-018; D4, ADR-019; D5, ADR-010; and D7, ADR-017.

* **D1. The record registers the write, not only the request.**
  * The problem: the audit trail keeps hashes, not the text. A `commit-msg` hook could only pair receipts and commit
    by file and by time, and receipts of writes that were never made, or were undone, would come in. That is what
    another agent's review criticised.
  * **Decided (author, 2026-10-14):** the record compares the content of the commit with what the writes with a
    receipt left, and says so in the trailer ("matches" or "changed outside the channel"). The computation goes
    inside the gate that already runs before each write, with no new process; a `PostToolUse` hook, which would add
    about 250 ms per write (`COST.md` §4), is ruled out.
  * Consequence for the contract: the gate no longer opens the database only to read. **Decided (author,
    2026-10-14):** if it cannot store the expected result, it denies the write, as the validator does without a
    record.
* **D2. The history.**
  * Removing the personal information from the history changes the hash of almost every commit since 6 October. The
    DEVLOG, the contracts and the Traianus case of the README cite hashes. (That case was replaced by the one in
    `noticias` v3 on 2026-10-18, ADR-030.)
  * **Decided (author, 2026-10-14):** the personal information goes, from the history too; the author keeps the
    list.
  * Before Friday 16, when the README starts. With the commit map of `git filter-repo` the citations are redone,
    and every cited hash is checked to exist. GitHub can keep serving old commits by their hash: the rewritten
    history goes to a new repository and the old one is deleted.
* **D3. The README's first limit (A30).** **Decided (author, 2026-10-14):** it goes right below the sentence. Only
  what goes through the governed channel leaves a record; what `Bash` does, and what goes to paths that are not
  governed, does not.
* **D4. Reporting A33 and A34 to Anthropic before publishing.**
  * **Decided (author, 2026-10-14):** they are not reported. A34 is documented behaviour, and Claude Code already
    has its switch (`omitClaudeMd`, since 2.1.271). A33 follows from its documented design: the sandbox covers
    `Bash`, and the file tools go through their permission prompts.
  * The README describes them exactly, with the version, as limits of the kit and not as faults of Claude Code.
  * To be reconsidered if a test shows Claude Code writing without asking where it says it asks.
* **D5. Claude Code's ordinary memory in Actuarii.**
  * Without option (c), the `Write` tool still reaches `~/.claude/projects/…/memory/`.
  * `.claude/memory/MEMORY.md` still said that option (c) denied it (fixed in `0116031`).
  * Claude Code tells the agent to write its memory there; the only thing stopping it is a line of `CLAUDE.md`, that
    is, an instruction and not a rule.
  * Claude Code's documentation (code.claude.com/docs/en/memory, read on 2026-10-14) gives two project settings:
    `autoMemoryEnabled: false` turns the automatic memory off, and `autoMemoryDirectory` moves it to another
    directory, with an absolute path or one that starts with `~/`.
  * Checked on 2026-10-14: Actuarii's ordinary memory has been empty since 5 October. Of 31 subagent transcripts,
    none received the instruction of the automatic memory, and 6 received the index of `.claude/memory/` through
    `CLAUDE.md`. The blind reviewer receives neither (`omitClaudeMd`), though it has never run in Actuarii.
  * **Decided (author, 2026-10-14):** `autoMemoryEnabled: false` in the whole project, not only for blind reviews,
    which are already covered. It goes in a small contract, after the installer, with its test and the fix of the
    false line of `.claude/memory/MEMORY.md`. The memory under code is published on the 25th, and memories are
    written knowing that.
* **D6. The README's frame.**
  * The von Neumann paragraph of the PLAN is written in a security key.
  * **Decided (author, 2026-10-14):** the frame explains why the rules live outside the model, and names security
    against an adversarial agent as what v0.2 brings, not v0.1.
* **D7. Claude's proposals in V2–V9 and in §3–§5.** **Accepted (author, 2026-10-14).**
