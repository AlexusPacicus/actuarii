# Actuarii — decisions

The register of the author's decisions. It only grows: an entry is never edited, and revising a decision means
adding another that says which one it supersedes. Those in force are listed in `docs/STATUS.md`. The technical
decisions of a contract stay in the contract. The date of each entry comes from the clock.

ADR-001 to ADR-020 were written on 2026-10-14 and gather the decisions in force that day, taken between 5 and 14
October. Each one carries the date it was taken and where its reasoning is. What came before is not migrated.

Translated from Spanish on 2026-10-19, up to ADR-031 (ADR-032): translating an entry does not change what it decided.

**Note (2026-10-19, ADR-035):** files were renamed into English. `docs/DECISIONES.md` is now `docs/DECISIONS.md`;
`docs/ESTADO.md`, `docs/STATUS.md`; `docs/design/PRUEBA_EN_LIMPIO.md`, `docs/design/CLEAN_ROOM.md`;
`docs/design/COSTE.md`, `docs/design/COST.md`; `docs/design/ENTORNO_PROPIO.md`,
`docs/design/ISOLATED_ENVIRONMENT.md`; and the memory files `autor.md`, `preguntar-ante-ambiguedad.md` and
`pocas-peticiones-al-autor.md`, `author.md`, `ask-when-ambiguous.md` and `few-requests-to-the-author.md`. The
entries keep the names of their day.

**Selection (2026-10-19, ADR-035):** this register keeps the decisions a reader needs, unedited. ADR-002, 003, 004,
006, 012, 013, 015, 017, 018, 020, 023, 024, 025, 029, 031, 038 and 039 left it; they are in the history, in
Spanish up to ADR-031, at commit `04107e0`. The numbers do not change, and the gaps stay. Leaving this file does not
change whether a decision is in force: `docs/STATUS.md` keeps that list. From here on the register only grows again.

**Note (2026-10-20, ADR-033):** the PLAN, the DEVLOG entries before 2026-10-18 (evening), and the contracts and
designs that the entries cite as their source, other than those still in `docs/design/`, left the tree. They are in
the history at `caa9541`.

## ADR-001 — Name, license and relationship with Traianus (2026-10-05, author)

**Context:** the kit was born governing Traianus and is extracted into a repository of its own.
**Decision:** it is called Actuarii, under the Apache-2.0 license, and it keeps its history with `git filter-repo`.
This repository is the canonical one: Traianus keeps a vendored copy, and changes come in here first and are ported
by hand.
**Consequences:** when Traianus lifts the freeze on its `pyproject.toml`, it comes to depend on the package.
**Supersedes:** —
**Source:** `docs/PLAN.md`, "Decisiones tomadas".

## ADR-005 — The success signal (2026-10-07, author)

**Context:** we need to know, with a criterion written in advance, whether the kit interests anyone.
**Decision:** four weeks from publication. Success if at least 5 outside people install it or open an issue, or if a
working conversation starts. If it does not come, it is reviewed with data, without reframing. How it is counted,
and what happens on 22 November, is in the ROADMAP, §3 and §4 (ADR-017).
**Consequences:** without a signal, neither v0.2 nor phase 4 starts.
**Supersedes:** —
**Source:** `docs/PLAN.md`, "Decisiones de la semana 1"; `docs/ROADMAP.md`.

## ADR-007 — Distribution of v0.1: an installer that copies the kit (2026-10-08, author)

**Context:** the shim only runs scripts committed in the repository itself, and the kit governs itself. The
`sandbox` key and the `pre-commit` are written into the project anyway, and a plugin lives outside the repository.
**Decision:** an installer written with Python's standard library, which imports under a system Python 3.9, copies
the kit into the target's `tools/`. If anything conflicts, it stops, says what conflicts and writes nothing. The
plugin is left for v0.2.
**Consequences:** the validator needs `pydantic` in the environment.
**Supersedes:** —
**Source:** `docs/PLAN.md`, "Decisiones de la fase 2".

## ADR-008 — One-command installation, with the environment outside the repository (2026-10-12, author)

**Context:** the measurement on macOS gave 612.8 s, and almost all of that time was the person following the guide.
**Decision:** `tools/install.py` does everything with one command: it checks, installs and writes the configuration.
* It only asks which paths to govern, besides the minimum ones, and whether to commit.
* It checks `pydantic` in the interpreter the server will start with, and asks for permission before installing it.
* It has a mode without questions.

Actuarii's environment lives outside the repository (2026-10-13).
**Consequences:** two contracts for the implementer and a new measurement (ROADMAP, V2 and V4).
**Supersedes:** —
**Source:** `docs/PLAN.md`, "Instalación en una orden" and "Principios de diseño".

## ADR-009 — v0.1 is work records; security is v0.2 (2026-10-13, author)

**Context:** the audit (A19–A35) showed that a boundary built on Claude Code has too many ways out against an
adversarial agent.
**Decision:** v0.1 is work records for coding agents: "Work records for coding agents. Every action leaves a record
that it happened, and why. Built for settings where traceability comes first." Security against an adversarial agent
is not part of this version: it goes to v0.2, with an isolated environment of its own
(`docs/design/ENTORNO_PROPIO.md`).
**Consequences:** AGENTS.md §9 declares what v0.1 does not cover. The earlier goal, showing that a middleware is
needed, becomes the motivation of v0.2.
**Supersedes:** —
**Source:** `docs/PLAN.md`, "Fase 3" and "Ideas para la v0.2"; `docs/DEVLOG.md`, 2026-10-14.

## ADR-010 — The agent's memory, under code; Claude Code's automatic memory, off (2026-10-13, author)

**Context:** without memory, the agent is not valid. Claude Code's automatic memory lives outside the repository,
with no receipt and no versions, and option (c), which was going to deny it, went to v0.2.
**Decision:** the agent's memory is the one in `.claude/memory/`: one receipt per write, and git keeps every version.
On 2026-10-14 it was decided to turn the automatic memory off in the whole project with `autoMemoryEnabled: false`.
It goes in a small contract, after the installer, which also fixes the line of `MEMORY.md` about option (c).
**Consequences:** the memory is published on the 25th, and memories are written knowing that. In the projects where
the kit is installed, the automatic memory is not touched.
**Supersedes:** —
**Source:** `docs/PLAN.md`, "Principios de diseño"; `docs/ROADMAP.md`, D5.

## ADR-011 — The reason, mandatory, and no receipt without a record (2026-10-14, author)

**Context:** for the "why" of the records to be true, it has to be kept with each decision.
**Decision:** `Rationale` is mandatory in every proposal (from 1 to 1000 characters) and is kept with every
decision, refused ones included. If the record cannot be written, there is no receipt. "The proposal schema"
replaces "5 Radicals".
**Consequences:** old audit databases are migrated on first use.
**Supersedes:** —
**Source:** `docs/design/MOTIVO.contrato.json`; `docs/DEVLOG.md`, 2026-10-14.

## ADR-014 — Plain names for the proposal's fields, in v0.2 (2026-10-14, author)

**Context:** the names of the proposal's schema are jargon.
**Decision:** `Topological_Grounding` and `Implementation_Block` take plain names (`old_string`, `new_string` or
`reason`) in v0.2. Before the launch, only the jargon of the descriptions and of the README is cleaned.
**Consequences:** —
**Supersedes:** —
**Source:** `docs/PLAN.md`, "Ideas para la v0.2".

## ADR-016 — The record in git (2026-10-14, author)

**Context:** the audit trail records that a write was requested, not that it was made. It keeps hashes and not the
text, and it lives in a local database that git ignores.
**Decision:**
* A `commit-msg` hook appends to the message of each commit, as trailers, the reasons of the receipts of its
  governed files.
* The trailer says whether the content of the commit matches what the writes with a receipt left. The gate computes
  the expected content before each write, with no new process, and if it cannot store it, it denies the write.
* The hook only records: it does not block the commit. The installer installs it.

**Consequences:** the gate now writes to the database, and the installer's second contract grows. If it does not
arrive in time, the README's sentence loses "that it happened" (ROADMAP, V3).
**Supersedes:** —
**Source:** `docs/DEVLOG.md`, 2026-10-14 (afternoon); `docs/ROADMAP.md`, D1.

## ADR-019 — A33 and A34 are not reported to Anthropic (2026-10-14, author)

**Context:** A33 and A34 concern Claude Code's behaviour.
**Decision:** they are not reported.
* A34 is documented behaviour, with its switch (`omitClaudeMd`).
* A33 follows from the documented design: the sandbox covers `Bash`, and the file tools go through the permission
  prompts.

The README describes them with their version, as limits of the kit and not as faults of Claude Code.
**Consequences:** to be reconsidered if a test shows Claude Code writing without asking where it says it asks.
**Supersedes:** —
**Source:** `docs/ROADMAP.md`, D4.

## ADR-021 — Decisions go in this register, which only grows (2026-10-14, author)

**Context:** decisions lived in six places: the PLAN, the DEVLOG, `ESTADO.md`, the ROADMAP, `ENTORNO_PROPIO.md` and
the contracts. When they were revised, they were edited over.
**Decision:**
* The author's decisions go in `docs/DECISIONES.md`.
* An entry is never edited: revising a decision means adding another that says which one it supersedes.
* Those in force are listed in `docs/ESTADO.md`.
* The technical decisions of a contract stay in the contract.
* The DEVLOG cites decisions by their number. The PLAN stays as history up to the 14th and only receives the ideas
  that wait.

**Consequences:** what came before the 14th is not migrated: ADR-001 to ADR-020 gather what was in force that day.
Making the kit enforce "only append" stays as an idea for v0.2.
**Supersedes:** —
**Source:** this entry.

## ADR-022 — The permission perimeter, without wildcard and with the wider list (2026-10-15, author)

**Context:** the author still saw too many manual permissions. Claude Code evaluates deny, then ask, then allow, and
the bare `"Bash"` at the head of `ask` made every call to `Bash` ask: the list of ADR-012 approved nothing in Claude
Code.
**Decision:**
* Without asking, in Claude Code and in OpenCode: `pytest`; the read-only commands of ADR-012 plus `cut`, `tr`,
  `jq`, `cmp` and `date` (with no argument or with a `+` format); the read-only git commands plus `git merge-base`,
  `git rev-list` and `git for-each-ref`; and `validate_proposal`.
* In Claude Code, no `ask` or `deny` rule covers an `allow`, and what asks for the rest is the `default` mode, not a
  wildcard. OpenCode keeps its `"*": "ask"` first.
* The git and `gh` commands that write still ask. So does `git branch`, and branches are listed with
  `git for-each-ref`.
* What some commands of the list write through their options (`sort`, `uniq`, `sed`, and the `--output` of
  `git diff`, `git log` and `git show`) is declared in §9.
* It goes in a small contract, before the installer's first, which carries this perimeter to the targets.

**Consequences:** AGENTS 7.1 is rewritten, with a test that nothing covers an `allow`. In another permission mode,
the mode decides what no rule names. `implementer.md` asks for one command per call, without variables, `cd` or
loops. It applies from the session after its commit.
**Supersedes:** ADR-012.
**Source:** `docs/design/PERIMETRO_SIN_COMODIN.contrato.json`; `docs/DEVLOG.md`, 2026-10-15.

## ADR-026 — Limits by problem: governance in v0.1, security in v0.2 (2026-10-17, author)

**Context:** V5 asked for one row per case of `docs/adversarial-audit/CASES.md`, from A01 to A35. A list of cases
says what was tested, not why the kit fails. The audit already separated two profiles: A, the honest agent that makes
mistakes, and B, the one that looks for a way out. It is the line of ADR-009 between v0.1 and v0.2.
**Decision:**
* Limits are counted by problem, each with its reason. There are eight.
* Governance: the record is left incomplete without anyone trying (v0.1).
  1. The record covers only its channel: it is made at the call to the tool, not on the disk. A01, A08, A29 and A30.
  2. No person approves the receipts or their reasons: there is no human in the loop. The agent issues its own
     receipt and writes its own reason, and the validator checks the form and the quote, not that the reason is
     true. The red phase and the delegation work the same way: the agent that executes checks itself. A02, A03, A04,
     A12, A15, A16 and A28.
  3. The kit trusts the way the person installs it: symbolic links, `core.fileMode` or the session's `PATH`; the
     announcement reports and does not check. A11, A14, A24 and A26.
  4. When the validator goes down, work stops: without the server there are no receipts, and every governed write is
     denied. A18 and A21.
* Security: an agent that looks for a way out finds one (v0.2).
  5. The gates start in an environment the agent can reach: they run outside the sandbox, with the Python, the `PATH`
     and the settings of the repository. A09, A10, A19, A31, A32 and A33.
  6. The checks are text, not a boundary: lists of what is forbidden and shell heuristics; the boundary is the
     sandbox. A05, A06, A07 and A23.
  7. Outside the audit database, records can be written: `.data/`, the blind review's lock and the trailers. A13, A25
     and A34.
  8. The session has what the person has: the kit runs with the person's permissions. A35.
* A17, A20, A22 and A27 are not limits: they go at the foot of the table, with their commit.
* The "Resumen" table of `CASES.md` goes from problem to cases, with what was fixed and its commit. The limits
  section of the README gives the eight problems, each with its reason, an example and what changes in v0.2, without
  the ids of the cases.
* V5 is checked this way: each case of `CASES.md` and each limit of AGENTS §9 belongs to a problem.
* Putting a person in the loop of the receipts is a new function: it does not go in before the 25th (ADR-004).

**Consequences:** V5 of the ROADMAP changes (ADR-017). AGENTS §9 is not reordered before the macOS measurement (V4),
because the installer copies it.
**Supersedes:** —
**Source:** `docs/DEVLOG.md`, 2026-10-17.

## ADR-027 — The text for HN and Reddit on Tuesday 27; the gate on Tuesday 24 November (2026-10-17, author)

**Context:** 25 October is a Sunday. At the weekend HN and Reddit have less traffic, and the kit's audience reads
from Monday to Friday; this has not been measured, because the sessions do not search the web. ADR-003 sets the 25th
for publication, and ADR-005 counts four weeks from publication.
**Decision:**
* The repository opens on Sunday 25, as ADR-003 says.
* The text for HN and Reddit (V9) goes out on Tuesday 27 at about 14:00 Madrid time, 9:00 in New York: that week
  Europe has already changed its clocks and the United States has not.
* The four weeks of the signal (ADR-005) are counted from the text: what arrives up to Tuesday 24 November at 23:59,
  Madrid time, counts, and the gate moves to that day.
* The two days are not working margin: ADR-004 is still in force.

**Consequences:** §1, §3, §4, §5 and V9 of the ROADMAP change (ADR-017). It is decided before there is any data from
the window, so it is not a reframing.
**Supersedes:** —
**Source:** `docs/DEVLOG.md`, 2026-10-17.

## ADR-028 — Installation as one pasted block; a command with its own screen in v0.2 (2026-10-18, author)

**Context:** in attempt 4 of the clean-room test, as in attempt 2, the example paths of `INSTALL.md` were copied as
they were. The warning that marked them as examples was in prose. Besides, step 1 started in `~/src`, which may not
exist. The author proposed a single command, with a small installation interface.
**Decision:**
* `INSTALL.md` installs with a single block pasted from the repository's top level, with nothing to edit:
  * it takes the repository's path from `git rev-parse`;
  * it clones Actuarii next to it;
  * it creates and activates the environment outside the repository;
  * it runs the installer, whose questions are the interface.

  Each step is joined to the next with `&&`, so the block stops at the first failure. The installer does not change.
* The macOS measurement (V4) is repeated with amendment §4e of `docs/design/PRUEBA_EN_LIMPIO.md`.
* A single command with its own screen, whether a Claude Code plugin or a bootstrap program, is a new function: it
  goes to v0.2 (ADR-004). A `curl … | sh` is not used: it is a bad first impression for a traceability kit.

**Consequences:** the README's installation section uses the same block. The "Out of v0.1" line of the ROADMAP
changes (ADR-017).
**Supersedes:** —
**Source:** `docs/DEVLOG.md`, 2026-10-18.

## ADR-030 — The README's real case, in noticias v3: the two defects of the classifier (2026-10-18, author)

**Context:** V6 asked for the Traianus case, with its commits. A new case in Traianus collides with ADR-004, and the
one of 5 October predates v0.1: it has no reasons and no record in git. `noticias` (AI-Papers-Engine) is public,
under AGPL-3.0, and its `v3-exp` branch has real work unrelated to the kit. The real case of the clean-room test
(2026-10-12) found two defects of the lexical classifier, `explorations/v3/scripts/classify_method_family.py`, and
they are still there:
* the `gan` family is counted inside words such as `organization`, because the keys are searched as substrings;
* a text with `diffusion transformer` always ties between `diffusion` and `diffusion_transformer_or_hybrid`, and
  comes out as `other`.

**Decision:**
* The README's real case is fixing those two defects, tests first, with v0.1 as it is published.
* It is done in a clean clone of `origin/v3-exp`, with `explorations/v3/**` governed.
* The plan is written before doing it (`docs/design/PRUEBA_EN_LIMPIO.md` §4f), and the README tells what happens,
  however it turns out.
* The Traianus case waits until its repository opens.

**Consequences:** V6 of the ROADMAP changes (ADR-017): the case is this one, and it is still the first thing to be
cut. The author's working copy is not used: it has the `.env` and private notes that are not committed.
**Supersedes:** —
**Source:** `docs/DEVLOG.md`, 2026-10-18.

## ADR-032 — The published tree is in English; the history stays as it is (2026-10-18, author)

**Context:** the repository opens on 25 October. The kit, its tests and the reference documents (README, INSTALL,
AGENTS, agents and skills) are in English. `docs/`, about 6,400 lines, and the agent's memory are in Spanish, and so
are the messages of the 329 commits. The author decided that the project cannot be published in Spanish, and that
the documents need edits for a reader from outside.
**Decision:**
* Every document of the published tree is translated into English, and edited for a reader from outside. The work
  goes in this order, so that it can be cut:
  1. what the README links: `CASES.md`, `PRUEBA_EN_LIMPIO.md`, `COSTE.md`, `ENTORNO_PROPIO.md`, `SANDBOX.md` and
     `ROADMAP.md`;
  2. this register, `DECISIONES.md`;
  3. the other records: `DEVLOG.md`, `PLAN.md`, `ESTADO.md`, the audit guidelines, `PROCESO.md`, `PRIOR_ART.md`,
     `ARRANQUE_PUERTAS.md`, `RECIBO_CONTENIDO.md`, the memory and the contracts.
* What is not translated by 25 October leaves the tree; the history keeps it in Spanish.
* The git history is not rewritten. Rewriting it would change every hash, including those the README, the clean-room
  results and the development log cite as evidence. The README says that the project was written in Spanish up to
  v0.1.
* From now on the repository's documents are written in English: the development log, the status, new decisions and
  the memory. The conversation with Claude may stay in Spanish.
* File names stay as they are: tests, the CI, `CLAUDE.md` and `opencode.jsonc` cite them.
* A translated record keeps its dates and what it said then. Where it describes something that has since changed, it
  says so in a dated note that names what replaced it.

**Consequences:** V6 and V7 of the ROADMAP change (ADR-017). Entries of this register written before this one keep
their meaning once translated; what each one decided does not change.
**Supersedes:** —
**Source:** `docs/DEVLOG.md`, 2026-10-18.

## ADR-033 — The published tree is shortened, document by document (2026-10-18, author)

**Context:** ADR-032 translates every document of the tree. They are about 6,400 lines of records written for the
work itself, against a kit of about 30 files. A reader from outside will not read most of them, and translating them
all competes with the launch. The author agreed that the tree should be shortened.
**Decision:**
* The published tree is shortened. The author reviews each document with Claude, and each one either stays
  (translated), is condensed (translated, keeping what a reader from outside needs), or leaves the tree. The history
  keeps every one, in Spanish.
* Claude's proposal is the starting point of that review, not a decision:
  * stays: the README, `INSTALL.md`, `AGENTS.md` and `ROADMAP.md`;
  * condensed: the "Resumen" of `CASES.md` with a link to each case, the results of `PRUEBA_EN_LIMPIO.md`, and
    `COSTE.md`, `ENTORNO_PROPIO.md` and `SANDBOX.md`, reduced to what the README needs;
  * condensed as a register: the decisions of `DECISIONES.md`, one line of decision and one of reason each;
  * out of the tree: the DEVLOG, the PLAN, the audit guidelines, `PROCESO.md`, `PRIOR_ART.md`, the contracts and
    the other designs.
* What the code, the tests, the CI, `CLAUDE.md` or `opencode.jsonc` need stays wherever the review puts it, or the
  review says what changes with it.
* When the review reaches `ROADMAP.md`, the author stops to work on v0.2 and research it; ideas or changes that come
  out of it go to this register.

**Consequences:** the first point of ADR-032 changes: not every document is translated, only those that stay or are
condensed. The rest of ADR-032 holds: English from now on, the history as it is, dated notes in the records that
stay. V10 of the ROADMAP is checked on the shortened tree.
**Supersedes:** ADR-032, in part (its first point).
**Source:** `docs/DEVLOG.md`, 2026-10-18.

## ADR-034 — A person in the loop and signed records open v0.2; neither goes into v0.1 (2026-10-19, author)

**Context:** two of the README's limits are the first questions of a reader from the settings it names, where
traceability comes first. Problem 2: no person approves the receipts or their reasons; the agent issues its own
receipt and writes its own reason. Problem 7: the commit trailers are text, and nothing signs them. That is, who
approved this change, and can the record be forged. Claude's assessment of 2026-10-18 recommended both before the
own environment of v0.2. On 2026-10-19 the author asked whether a person in the loop should go into v0.1. Claude
advised against it, for four reasons:
* ADR-004 admits no new function before the 25th except the record in git, and every task left before the opening
  is on its path;
* done properly, it needs a contract, the implementer, the check of red and green, a live check and a rewrite of
  problem 2 in the README, `CASES.md` and AGENTS §9, with V1 green on the commit that is published;
* half of it weakens the claim. A `PreToolUse` hook can put the reason in Claude Code's permission prompt (the `ask`
  decision, to be confirmed in the documentation), but it does not learn whether the person accepted, and an
  approval written where the agent can reach it is one more record that can be forged (problems 5 and 7). The README
  would gain a limit, not lose one;
* every governed write would wait for the person, on top of the 1875 ms it already costs, and friction moves work
  to the paths that are not governed (A30).

**Decision:**
* A person in the loop does not go into v0.1. ADR-004 holds, and problem 2 stays a declared limit.
* v0.2 starts with two pieces, before the own environment of `docs/design/ENTORNO_PROPIO.md`:
  1. **a person in the loop:** the person sees the agent's reason next to the change and approves or refuses each
     receipt, and the approval or the refusal goes into the record;
  2. **signed records:** the record is signed out of the agent's reach, so that someone other than the author can
     check it and a forged one is detected.

  The phases of the environment (v0.2-a to v0.2-e, `ENTORNO_PROPIO.md` §9) come after them.
* The README says so: the "In v0.2" lines of problems 2 and 7, and "What comes next".
* The text for HN and Reddit (V9) asks it: whether a person approving each receipt with the agent's reason in front
  of them, and records that someone else can verify, would change whether the reader uses the kit, and what they
  would need first. The answers are noted as context for v0.2; they do not change how the signal is counted
  (ROADMAP §3).
* The gate of 24 November does not change: v0.2, these two pieces included, starts only if the signal is met.

**Open for the research of v0.2 (Claude's questions, not decided):**
* whether Claude Code can show the reason before the write and report for certain whether the person approved it:
  the `PermissionRequest` hook and the `ask` decision of `PreToolUse`, in each permission mode;
* whether an existing format covers the signature (Agent Receipts, in-toto, SLSA provenance, signed commits), so
  that Actuarii emits compatible records instead of inventing them (`docs/prior-art/PRIOR_ART.md`, "Lo que la
  búsqueda aporta al diseño", point 2);
* whether approving and signing can be one act: a key the agent cannot use without the person;
* how it fits decision 3 of `ENTORNO_PROPIO.md` §10, which proposes fewer questions inside the environment: the
  approvals of receipts would be the questions that remain.

**Consequences:** ROADMAP §5 changes its order and gains two criteria. The README's three passages change before V7
is checked. `ENTORNO_PROPIO.md` keeps its phases, which now come after these two pieces, and is reviewed under
ADR-033 like the rest.
**Supersedes:** —
**Source:** `docs/DEVLOG.md`, 2026-10-19.

## ADR-035 — File names in English; the register keeps the decisions a reader needs, unedited (2026-10-19, author)

**Context:** ADR-032 kept the file names as they were, because tests, the CI, `CLAUDE.md` and `opencode.jsonc` cite
them, so a translated document would still carry a Spanish name. ADR-033 proposed condensing this register to one
line of decision and one of reason per entry, which would rewrite every entry, while ADR-021 says that an entry is
never edited and that the register only grows. On 2026-10-19, planning the review of ADR-033, the author decided
both.
**Decision:**
* **File names in English.** Every file that stays in the published tree has an English name; a file that leaves the
  tree keeps its old name in the history. The names:
  * `docs/DECISIONES.md` becomes `docs/DECISIONS.md`;
  * `docs/ESTADO.md` becomes `docs/STATUS.md`;
  * `docs/design/PRUEBA_EN_LIMPIO.md` becomes `docs/design/CLEAN_ROOM.md`;
  * `docs/design/COSTE.md` becomes `docs/design/COST.md`;
  * `docs/design/ENTORNO_PROPIO.md` becomes `docs/design/ISOLATED_ENVIRONMENT.md`;
  * `.claude/memory/autor.md`, `preguntar-ante-ambiguedad.md` and `pocas-peticiones-al-autor.md` become
    `author.md`, `ask-when-ambiguous.md` and `few-requests-to-the-author.md`, with their `name:` and their links;
  * a contract kept as an example changes `.contrato.json` to `.contract.json`.
* **In one batch, at the start of the review,** so that each condensed document is written under its final name and
  each link is fixed once. Each part goes through its own channel, from a session opened in Actuarii:
  * `CLAUDE.md`, `opencode.jsonc` and the memory, with a receipt; the author deletes the old memory files;
  * the name of the CI job and `tests/unit/test_ci_workflow.py`, which pins it, through a contract for the
    implementer;
  * the documents and their links, by the executing agent, with a `grep` of the tree before the commit.
* **The register keeps the decisions a reader needs, unedited.** No entry is condensed: each one either stays as it
  is, translated (ADR-032), or leaves this file. Those that leave stay in the history, in Spanish, at the commit
  before the selection, which the head of the register names. The numbers do not change, and the gaps stay. Leaving
  the file does not change whether a decision is in force; the status keeps that list. The selection is made with the
  author, entry by entry, starting from Claude's first pass on the titles, which is not a decision:
  * stay: 001, 005, 007, 008, 009, 010, 011, 016, 021, 022, 028, 032, 033, 034;
  * leave: 004, 006, 015, 017, 020 and 025, and 012 and 023, already superseded;
  * to discuss: 002, 003, 013, 014, 018, 019, 024, 026, 027, 029, 030 and 031.

  This entry and ADR-036 stay. After the selection the register only grows again, as ADR-021 says.

**Consequences:** V10 of the ROADMAP also covers the file names. The history keeps the old names: commit messages,
and the records that leave the tree, cite them. Selecting before translating saves translating the entries that
leave.
**Supersedes:** ADR-032, in part (the file names stay as they are); ADR-021, in part (the register only grows: the
selection removes entries once).
**Source:** `docs/DEVLOG.md`, 2026-10-19.

## ADR-036 — `examples/traianus/` stays, as where the kit comes from (2026-10-19, author)

**Context:** the status recommended removing `examples/traianus/` from the tree, because "nothing uses it, it
describes a private project from inside and it still says 'Blind by construction'". Two of those three claims were
false. Three tests load the folder (`test_project_config.py`, `test_contract_context_hook.py` and
`test_agent_docs.py`), and it is the only real configuration that uses the contract registry, the blind review and
`python_script_dirs`. Traianus is a public repository, and this repository's history starts in it. The author
proposed keeping the folder as an example of where the kit comes from, with a short section in the README, because
it can give confidence.
**Decision:**
* `examples/traianus/` stays in the tree.
* The README gets a short section, "Where it comes from", under four conditions:
  1. it says that Traianus does not run Actuarii: Traianus still runs the gates as they were before the extraction,
     and the example is its configuration in Actuarii's format;
  2. "Blind by construction" is corrected in the example's review procedure, which contradicts problem 7 of the
     README;
  3. Traianus's history has not gone through the cleaning of ADR-020, so whether the README links Traianus or only
     names it is the author's decision, before V7 is checked;
  4. the section goes in the README, the only new document before the launch, and not in a new file of the folder.

**Consequences:** the status corrects its claim. Nothing changes in the tests.
**Supersedes:** —
**Source:** `docs/DEVLOG.md`, 2026-10-19.

## ADR-037 — The README links Traianus (2026-10-19, author)

**Context:** ADR-036 left to the author, as its third condition, whether "Where it comes from" links Traianus or only
names it, because Traianus's history has not gone through the cleaning of ADR-020.
**Decision:** the section links Traianus. Traianus is public, and the link is what lets a reader check where the kit
comes from.
**Consequences:** the README stays as it was committed in `9466452`. The third condition of ADR-036 is closed.
**Supersedes:** —
**Source:** `docs/DEVLOG.md`, 2026-10-19.

## ADR-040 — What would change the plan of v0.2, written before the opening (2026-10-20, author)

**Context:** ADR-033 stops the review at the ROADMAP to research v0.2. One of the questions Claude brought was which
answers from outside would change the plan of v0.2. Written after the answers arrive, it would be a reframing; written
before the opening, it is a commitment, like the signal (ADR-005).
**Decision:** the list of six lines in ROADMAP §3, with its rule. An answer counts for a line only in its own words; a
line changes the plan when two outside people say it independently, or a working conversation sets it as its
condition; the lines that reach it apply in the order of their count. Only that list can change the order of §5.
**Consequences:** §3 and §5 of the ROADMAP change. The answers change neither how the signal is counted nor the gate
(§4). The Sunday lines of the DEVLOG also say which answer counted for which line.
**Supersedes:** —
**Source:** `docs/DEVLOG.md`, 2026-10-20.
