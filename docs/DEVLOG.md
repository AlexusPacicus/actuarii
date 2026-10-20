# Actuarii — DEVLOG

One entry per session, the newest at the top: what was done (with its commits), what was decided and why, what went
wrong and what was learnt. What the design documents already tell is linked, not repeated. It is written when each
session closes (the author's decision, 2026-10-07).

**Selection (2026-10-20, ADR-033):** the entries before 2026-10-18 (evening), in Spanish, left this file. They are in
the history: this file at `caa9541`. Those of 5 and 6 October among them were rebuilt on the 7th from `git log` and
the PLAN.

**Note (2026-10-19, ADR-035):** files were renamed into English. `docs/DECISIONES.md` is now `docs/DECISIONS.md`;
`docs/ESTADO.md`, `docs/STATUS.md`; `docs/design/PRUEBA_EN_LIMPIO.md`, `docs/design/CLEAN_ROOM.md`;
`docs/design/COSTE.md`, `docs/design/COST.md`; `docs/design/ENTORNO_PROPIO.md`,
`docs/design/ISOLATED_ENVIRONMENT.md`; and the memory files `autor.md`, `preguntar-ante-ambiguedad.md` and
`pocas-peticiones-al-autor.md`, `author.md`, `ask-when-ambiguous.md` and `few-requests-to-the-author.md`. The
entries keep the names of their day.

## 2026-10-20 (morning, the records)

The records ADR-033 proposed to take out of the tree are selected with the author: every document of `docs/` but the
ROADMAP is now reviewed.

**Done**
* **The DEVLOG,** trimmed to its entries in English, from 2026-10-18 (evening): 396 lines kept of 1868. Its head is
  translated, and says that the earlier entries are in the history at `caa9541`. It stays because the ROADMAP (§3,
  §4), the status and the memory rely on it as the live log. The head says "one entry per session", which is what the
  log has become; the original said "per day".
* **Out of the tree, in the history at `caa9541`:** the PLAN, the two audit guidelines, `PROCESO.md`, `PRIOR_ART.md`,
  `ARRANQUE_PUERTAS.md`, `RECIBO_CONTENIDO.md` and sixteen contracts. `docs/process/` and `docs/prior-art/` are gone.
* **One contract kept as an example:** that of ADR-031, renamed `docs/design/PYTEST_NAMED.contract.json` with its
  content unchanged, its commit message in Spanish as it was given. The README links it where it tells that fix.
* **What cited them, brought up to date:**
  * the ROADMAP: where the reasons for each decision are, phase 4's criterion and the ideas for v0.2 point to the
    history;
  * the status: its head, the two rules on ideas that wait, which now go in the DEVLOG entry of the day and, from the
    25th, in issues, and the list of pending work;
  * the register's head: a note that the PLAN, the old DEVLOG entries and the contracts and designs its entries cite
    are in the history;
  * the memory, each file with its receipt: `MEMORY.md` points to the ROADMAP for phase 4, and the two feedback
    memories say that the DEVLOG entries they cite are in the history.
* **Left on purpose:** the docstring of `tests/security/test_validator_target_and_grounding.py`, which names
  `PROCESO.md` §3.2 as the source of its day; and a path in `tests/security/test_hook_case_identity.py`, which does
  not need the file to exist.
* **Found for V7:** four test docstrings still say "5 Radicals", and one of them is in Spanish; it is noted in the
  status as a contract for the implementer.

**Decided (author)**
* **The DEVLOG is trimmed; the PLAN, the six records and the contracts but one leave the tree;** the contract of
  ADR-031 stays as an example.

**Next**
* **`ROADMAP.md`,** where the author stops to work on v0.2 (ADR-033).
* **The V8 check,** with the author's list of terms, and then the rewrite of ADR-038.

## 2026-10-20 (morning, the README's line on Spanish)

**Done**
* **The README's line on the language** says what is true today: the documents it links are in English; the
  development log, some other records and most commit messages before 18 October are in Spanish.

**Decided (author)**
* **The wording that is exact today,** to be replaced when the review of ADR-033 ends by the one ADR-032 foresees:
  the tree in English, and the history keeping the earlier records and commit messages in Spanish.

## 2026-10-20 (morning, SANDBOX.md condensed)

`docs/design/SANDBOX.md` is condensed into English (ADR-033): 203 lines, from 243 in Spanish. With it, every document
of `docs/` that the README links is in English.

**Done**
* **What stays, with its numbering:** §1 to §3 nearly whole, the test plan (§7) and its results (§8), with the finding
  of S8; §4, §5 and §9 shorter; §6 with the configuration as it was proposed and applied (`546730b`). The README
  (§8), the docstrings of three tests (§6, §9) and ROADMAP V7 (§6) still cite it as they did, so no contract was
  needed. The internal labels of the fixes (F1, F4c, F5) leave.
* **Dated notes for what changed since (V7):**
  * §6: the exemption of `.claude/**` and `.mcp.json` from `denyWrite` ended on 2026-10-14 (`92df87a`); this is the
    item V7 named;
  * §8: the bare `"Bash"` in `ask` that S5 mentions was removed by ADR-022 on 2026-10-15;
  * §5: the user-level `allowUnsandboxedCommands: false` is recommended by `INSTALL.md`, not by the README, and the
    installer warns when it is missing.
* **Checked:** every section another document cites exists; the 22 rows of S1 to S9 are there; the figures of §8 are
  the same, apart from the label "F4c, v0.2" and the dates of the note; no Spanish is left; no prose line passes 120
  characters.

**Decided (author)**
* **`SANDBOX.md` is condensed,** with its numbering kept.

**Next**
* **The README's line on Spanish** (line 14) says the design records are in Spanish, which is no longer true of those
  it links. Claude proposes the new wording to the author.
* **The review of each document (ADR-033),** with the V8 check: the records that do not stay, and `ROADMAP.md`, where
  the author stops to work on v0.2.

## 2026-10-20 (morning, ISOLATED_ENVIRONMENT.md condensed)

`docs/design/ISOLATED_ENVIRONMENT.md` is condensed into English (ADR-033): 298 lines, from 350 in Spanish. Claude had
estimated about 140; the tables of §3, §4.1, §4.9, §5 and §8 are whole.

**Done**
* **What stays, with its numbering:** §2, §3 (E1–E9), §6 and §8 nearly whole; the rest in a few lines each, with the
  diagram; §10 as open decisions, one line each. The README (§6), the ROADMAP (§3, §9, §10) and ADR-034 (decision 3
  of §10) still cite it as they did.
* **What V7 asked of it:**
  * a dated note at the head and in §9: ADR-034 puts a person in the loop and signed records before these phases;
  * the proposal is called by its current name, not "5 Radicals" (ADR-011);
  * the line that said the README's von Neumann frame came from Triarii leaves: the README no longer has it.
* **Triarii,** named once, in §4.9, as the starting point of the internet environment. Its origin, its license and
  decision 9 of the draft, on relicensing its code, leave the tree; the history keeps them.
* **Checked:** the diagram's arrows and box edges line up; every section another document cites exists; no Spanish is
  left, nor "5 Radicals", "von Neumann" or the hackathon; no prose line passes 120 characters.

**Decided (author)**
* **`ISOLATED_ENVIRONMENT.md` is condensed,** with its numbering kept.
* **Triarii is named in one sentence,** without its origin or decision 9; the author chose the option offered for a
  public project.

**Next**
* **The review of each document (ADR-033),** with the V8 check: `SANDBOX.md` remains of what the README links.

## 2026-10-19 (night, COST.md in English)

`docs/design/COST.md` is in English (ADR-033): 122 lines, from 141.

**Done**
* **§1 to §5 translated nearly whole,** with their numbering: the rule written before measuring, the results and the
  design for v0.2 are what the README's 1875 ms rests on. The README cites §5, the ROADMAP §4 and the design of the
  own environment §5, as before. The local path of the transcripts and their session ids leave.
* **A dated note in §5:** step 1 of the design, the validator in `permissions.allow`, was done on 2026-10-14
  (`f5517ae`, ADR-012, kept by ADR-022), for the permission prompts and not for the cost, which has not been measured
  again. Steps 2 and 3 are not done, as `.claude/settings.json` shows. Claude had first said 2026-10-15 (ADR-022);
  `git log -S` gave the right date before the note was written.
* **§6, the comparison with governance by instruction,** is a short note: proposed and not run, and the README claims
  nothing about saving tokens.
* **Checked:** the figures of §1 to §5 are the same as before, apart from the ids of the transcripts that left and the
  dates, ADRs and commits of the two notes; no Spanish is left; no prose line passes 120 characters.
* **The README** no longer says "in Spanish" next to `COST.md`.

**Decided (author)**
* **`COST.md`:** §1 to §5 translated nearly whole, and §6 reduced to a note.

**Next**
* **The review of each document (ADR-033),** with the V8 check: `ISOLATED_ENVIRONMENT.md` and `SANDBOX.md` remain of
  what the README links.

## 2026-10-19 (night, CLEAN_ROOM.md condensed)

`docs/design/CLEAN_ROOM.md` is condensed into English (ADR-033): 301 lines, from 609 in Spanish.

**Done**
* **What stays:**
  * §1 to §4 nearly whole: they are the rule written before measuring;
  * each amendment, §4b to §4f, with its date, its reason and what it changes; §4f more fully, as the plan written
    before the README's real case;
  * §5 by attempt: the tables of attempt 3 (612.8 s) and of the V4 measurement (223 s), the two real cases, and the CI
    and the three rehearsals in a paragraph each, with what they found and what was fixed.

  Receipt ids, hash prefixes and the paths of the machine leave; the head names `0c5f669`, where the full record is.
* **The numbering of the sections is kept:** the CI step and its test ("section 4"), the README (§4f, §5), the
  ROADMAP, COST (§4b) and the status still cite it as they did. The README now says "its record is in §5", since the
  full one is in the history.
* **Quotes given in Spanish** (the text of §4f, the agent's words, the person's interventions) are translated only.
* **One note added:** finding 1 of attempt 5 proposed naming the target before any write; the text says it was done
  in ADR-029 (`119d569`), as V7 asks of what has changed since.
* **Checked:** every section another document cites exists; every commit cited comes from the old text, except
  `0c5f669` and `119d569`; no Spanish is left; no prose line passes 120 characters.

**Decided (author)**
* **`CLEAN_ROOM.md` is condensed,** with its numbering kept, and the quotes given in Spanish are translated only
  (Claude had recommended keeping the original next to the translation).

**Next**
* **The review of each document (ADR-033),** with the V8 check.

## 2026-10-19 (night, CASES.md condensed)

`docs/adversarial-audit/CASES.md` is condensed into English (ADR-033): 200 lines, from 722 in Spanish.

**Done**
* **What stays:**
  * a short head, with the two rounds and the guidelines approved before each;
  * the "Summary" table, translated whole, with the names of the README's eight problems;
  * each case in two or three lines: what was tried, what happened and how it stands.

  The guarantees (G), the batches of fixes in the case lines (F) and the classifications proposed at the time (C)
  leave: they depend on the audit guidelines, which leave the tree.
* **The full record,** in Spanish, is in the history: the head names `f322818`, which the rewrite of ADR-038 changes
  and the commit that redoes the citations covers.
* **Checked:**
  * each of the 35 cases has one entry and is in the summary;
  * each of the 28 limits of AGENTS §9 is in the summary once;
  * every commit the new text cites comes from the old one, except the reference `f322818`;
  * no prose line passes 120 characters.
* **The README** no longer says "(in Spanish)" next to `CASES.md`; **ROADMAP V5** names the table "Summary".

**Decided (author)**
* **`CASES.md` is condensed,** and it reaches the full record through one reference in its head, not a link per case:
  anchors to Spanish headings inside a commit would all break with the rewrite.

**Next**
* **The review of each document (ADR-033),** with the V8 check.

## 2026-10-19 (evening, the register in English)

The register is translated: its head and the 16 entries that stay and were in Spanish, without other edits (ADR-032,
ADR-035).

**Done**
* **The words:** the titles are those of the status table, and the vocabulary is that of ADR-032 on and of the
  ROADMAP (record, receipt, gate, audit trail, reason, clean-room test, own environment). Paths keep the names of
  their day; the headings of the PLAN, still in Spanish, are quoted as they are, as ADR-034 does; the decimal comma
  becomes a point (612.8 s).
* **The head** gains one line: translated from Spanish on 2026-10-19, up to ADR-031, and translating an entry does
  not change what it decided.
* **Checked that only the language changed:**
  * the code spans, the ids of decisions, cases, criteria and sections, the dates and the figures are the same
    before and after, except for the decimal point and the line of the head;
  * the bullets and numbered items are the same, 104;
  * each of the 22 entries has its five fields, and no line passes 120 characters.

  One slip was found and undone: backticks around `noticias` in the title of ADR-030, which the original does not
  have.

**Next**
* **The review of each document (ADR-033),** with the V8 check.

## 2026-10-19 (late afternoon, the selection)

The register is selected (ADR-035): 22 entries stay and 17 leave, decided with the author entry by entry.

**Done**
* **The criterion:** an entry stays if it explains something a reader from outside sees in the kit or in its public
  calendar, and no document that stays already tells it. It leaves if it is the organisation of the work, or a detail
  that the code, the tests, the README or the ROADMAP already tell.
* **Stay:** 001, 005, 007, 008, 009, 010, 011, 014, 016, 019, 021, 022, 026, 027, 028, 030, 032, 033, 034, 035, 036
  and 037.
* **Leave:** 002, 003, 004, 006, 012, 013, 015, 017, 018, 020, 023, 024, 025, 029, 031, 038 and 039. They remain in
  the history at `04107e0`, which the head of the register names, and the status still lists them among the
  decisions in force.
* **Where it was close:**
  * 014 stays: whoever adopts the kit sees the jargon of the schema in every proposal, and the entry says it changes
    in v0.2;
  * 019 stays: it is the dated answer to whether A33 and A34 were reported to Anthropic;
  * 027 stays: it moves the gate that ADR-005 dates on 22 November to the 24th;
  * 030 stays: it shows that the README's real case was chosen and planned before it was done;
  * 037 stays: it closes the third condition of ADR-036;
  * 038 and 039 leave, like 020: they deal with personal information, and the rewrite runs before the repository
    opens.
* **A hash to redo:** `04107e0` changes with the rewrite of ADR-038; the commit that redoes the citations covers it.

**Decided (author)**
* **The selection,** entry by entry: the 12 entries to discuss, Claude's first pass of ADR-035 confirmed, and ADR-037
  to ADR-039, written after that pass.

**Next**
* **The translation of the register:** its head and its 16 entries still in Spanish, unedited otherwise.

## 2026-10-19 (afternoon, the renaming)

The renaming batch of ADR-035 is done: the files that stay have English names, and the live documents cite them.

**Done**
* **The inventory, before any edit:** outside the records, only the name of the CI step and
  `tests/unit/test_ci_workflow.py`, which pins it, cited an old name in code or tests.
  `test_config_perimeter.py` checks that every file `CLAUDE.md` imports exists, so `CLAUDE.md`, `opencode.jsonc`
  and the rename of the status go in one commit.
* **The CI step, through the implementer:** the contract (`0a43847`) is the first with the `.contract.json` suffix;
  the commit, `e4536e1`, carries `Actuarii-Record: matches`. The executing agent validated the report, ran
  `verify_red_green.py` (T1 red at base and green at the end, T2 guard, the full suite green), checked by hand that
  the diff, two lines, touches only the contract's files, and advanced `main` by fast-forward.
* **Renamed:**
  * `DECISIONS.md`, `STATUS.md`, `CLEAN_ROOM.md`, `COST.md` and `ISOLATED_ENVIRONMENT.md`, with `git mv`;
  * the three memory files, written under their new names with a receipt each, with their `name:` and their links;
    the author deleted the old ones.
* **The links:**
  * the README, the status, the ROADMAP, `CASES.md`, and the cross-references of `COST.md` and
    `ISOLATED_ENVIRONMENT.md`;
  * `CLAUDE.md`, `opencode.jsonc` and `MEMORY.md`, with a receipt each;
  * a dated note at the head of the register and of this DEVLOG that says which name replaced which.
* **Left as they are, on purpose:**
  * the records: the entries of the register, the DEVLOG, the PLAN and the contracts;
  * a case told in `CASES.md`, whose receipts were for the path of their day;
  * ROADMAP V8, which says where a text was.

  No contract was renamed: ADR-035 renames only the contracts the review keeps as examples.

Suite green (3705). Disk: 5.1 GiB free.

**Decided (author)**
* **The records keep the names of their day,** with a dated note at the head of the register and of the DEVLOG.
  It applies the rule of ADR-032 to the file names, so it has no entry of its own.

**Next**
* **The review of each document (ADR-033),** with the selection of the register and the V8 check.

## 2026-10-19 (afternoon)

What the inventory of 2026-10-18 left to the author is decided (ADR-038): the author's professional plans leave the
tree, and a line that names a third party leaves the tree and, by a rewrite still to be run, the history of `main`.

**Done**
* **Checked before editing:**
  * the three passages of `PLAN.md` are the only ones about the author's professional plans;
  * across every ref, the third party is named in exactly three distinct lines, all on `main` and none in a commit
    message: the line of the 2026-10-18 entry (afternoon, the real case), and the two that pointed to it, in the
    2026-10-18 entry (evening) and in pending item 2 of the status.
* **Out of the tree:** the three passages and the three lines. What they leave behind is adjusted: the usefulness
  criterion of `PLAN.md` counts three conditions, the list of the real case ends with a full stop, and the evening
  entry says "the decisions above". Pending item 2 of the status, now empty, is removed and the list renumbered.
* **ADR-038,** and the status.
* **The procedure of the rewrite, prepared and not run,** outside the repository: a backup copy, a fresh clone,
  `git filter-repo --replace-text` with rules that match the three lines without writing the name, the checks before
  any push, the citations of rewritten hashes (ten in the tree today) and the two options for GitHub. It waits for
  the author's confirmation.
* **Done from a session opened in Actuarii,** with the announcement read: the session in Traianus could not run
  Actuarii's git hooks, because Traianus's Python shim came first on its `PATH`.

Suite green (3705). Disk: 5.1 GiB free.

**Decided (author)**
* **ADR-038.**
* **ADR-039:** the rewritten `main` goes to a new repository, as on 2026-10-14.
* **The V8 check goes with the review of each document, and the rewrite waits for it,** so that it runs once.

**Next**
* **The review of each document (ADR-033),** with the V8 check.
* **Then the rewrite,** with the figures of the procedure measured again; the commit that redoes the citations, with
  each cited hash checked; and the push to the new repository.

## 2026-10-19 (midday)

The review of ADR-033 is planned: file names go into English and the register is selected, not condensed (ADR-035);
`examples/traianus/` stays, with a section in the README (ADR-036).

**Done**
* **The plan of the review, in the conversation:** the inventory of the tree (about 6,200 lines in Spanish in 16
  documents, and 17 contracts), what cites each document, the target tree, the rules for condensing and the order.
  It is not written into the repository: the only new document before the launch is the README.
* **Found while making the inventory:**
  * `examples/traianus/` is used: three tests load it. The status said that nothing used it;
  * the CI job's name cites `PRUEBA_EN_LIMPIO.md` §4, and `tests/unit/test_ci_workflow.py` pins it;
  * `CLAUDE.md` and `opencode.jsonc` load `docs/ESTADO.md`.
* **ADR-035 and ADR-036;** the README's "Where it comes from"; "Blind by construction" corrected in the example's
  review procedure; ROADMAP V7 and V10; the status.

**Decided (author)**
* **ADR-035:** English file names, renamed in one batch at the start of the review; the register keeps the
  decisions a reader needs, unedited, selected entry by entry.
* **ADR-036:** `examples/traianus/` stays, under four conditions.
* **ADR-037:** the README links Traianus, which closes the third condition of ADR-036.

**Next**
* **The renaming batch of ADR-035,** from a session opened in Actuarii, with the contract for the CI job and its
  test.
* **The selection of the register,** entry by entry.

## 2026-10-19 (morning)

A person in the loop stays out of v0.1 and opens v0.2, with signed records (ADR-034).

**Done**
* **The author's question:** whether a person in the loop should go into v0.1. Claude advised against it; the four
  reasons are in the context of ADR-034.
* **ADR-034;** the "In v0.2" lines of problems 2 and 7 and "What comes next" in the README; ROADMAP §5; the status.
* **Done from a session opened in Traianus:** Actuarii's session announcement was not read, and only files outside
  `governed_paths` changed.

**Decided (author)**
* **ADR-034:** neither a person in the loop nor signed records go into v0.1; both open v0.2, before the own
  environment, and the text for HN and Reddit asks about them.

**Next**
* **The review of each document (ADR-033),** as planned for this week.
* **V9:** the text for HN and Reddit carries the question of ADR-034.

## 2026-10-18 (night)

The published tree is shortened, document by document (ADR-033). The CI passed on the pushes of the day.

**Done**
* **The CI of Linux, green** on the pushes of the day, R7 included (author). V1 holds on `main`.
* **Claude's assessment, at the author's request.**
  * In favour: the kit is honest about what it guarantees and is well built, and the real case is its best evidence.
  * Against:
    * a narrow value proposition for the audience it names, which will ask who approved a change and whether the
      record can be forged;
    * a cost per write that pushes work to ungoverned paths (A30);
    * a dependence on one vendor;
    * a process layer heavier than the product;
    * no outside demand yet.
  * Recommended: a much shorter tree, a pitch centred on the record and the verified delegation, and a person in
    the loop and signed records before the own environment in v0.2.
* **ADR-033,** and the status updated with the review of each document and the questions for v0.2.

**Decided (author)**
* **ADR-033:** the tree is shortened. Each document stays, is condensed or leaves the tree, in a review with the
  author. At the ROADMAP, the author stops to work on v0.2 and research it.

**Next**
* **The review of each document,** from Monday, starting from the proposal in ADR-033.

## 2026-10-18 (evening)

The first entry in English. The published tree goes into English (ADR-032); the status, the memory and the roadmap
are translated.

**Done**
* **The inventory of what gets published:**
  * the kit, its tests and the reference documents (README, INSTALL, AGENTS, agents and skills) were already in
    English;
  * `docs/` (about 6,400 lines) and the memory were in Spanish, and so are the messages of the 329 commits.
* **Found while making the inventory, and left to the author** (status, pending item 2):
  * three lines of `PLAN.md` about the author's professional plans;
  * `examples/traianus/`, which nothing uses and which still says "Blind by construction".

  The tree and the history are both published: taking something out of the tree does not take it out of the
  history.
* **ADR-032.**
* **Translated, edited for a reader from outside:**
  * `ESTADO.md`, brought up to date at the same time;
  * the four memory files, each with its receipt; `pocas-peticiones-al-autor.md` now says that ADR-022 removed the
    bare `"Bash"` it describes;
  * `ROADMAP.md`, with V7 rewritten and a new V10 for the translation. Dated notes mark what changed since: option
    (c) in `MEMORY.md`, fixed in `0116031`; the Traianus case, replaced by ADR-030.
* **The README** no longer marks the ROADMAP as Spanish.

**Decided (author)**
* **ADR-032:** the published tree in English, by priority, with what is not translated by the 25th leaving the tree;
  the history stays as it is; the repository's documents are written in English from now on.

**Next**
* **The author:** review the translated `ROADMAP.md` as the sample of tone and edits, and the decisions above.
  On closing, the author said that "we will be able to shorten"; what and how is to be agreed before translating
  more, and is not recorded as a decision.
* **Translation, priority 1:** `CASES.md`, `PRUEBA_EN_LIMPIO.md`, `COSTE.md`, `ENTORNO_PROPIO.md`, `SANDBOX.md`.
  Then `DECISIONES.md`, then the rest. When it is done, the README's line about Spanish says that the history keeps
  the original commit messages.
