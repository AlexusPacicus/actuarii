# Actuarii — DEVLOG

One entry per session, the newest at the top: what was done (with its commits), what was decided and why, what went
wrong and what was learnt. What the design documents already tell is linked, not repeated. It is written when each
session closes (the author's decision, 2026-10-07).

**Selection (2026-10-20, ADR-033):** the entries before 2026-10-18 (evening), in Spanish, left this file. They are in
the history: this file at `64292e1`. Those of 5 and 6 October among them were rebuilt on the 7th from `git log` and
the PLAN.

**Note (2026-10-19, ADR-035):** files were renamed into English. `docs/DECISIONES.md` is now `docs/DECISIONS.md`;
`docs/ESTADO.md`, `docs/STATUS.md`; `docs/design/PRUEBA_EN_LIMPIO.md`, `docs/design/CLEAN_ROOM.md`;
`docs/design/COSTE.md`, `docs/design/COST.md`; `docs/design/ENTORNO_PROPIO.md`,
`docs/design/ISOLATED_ENVIRONMENT.md`; and the memory files `autor.md`, `preguntar-ante-ambiguedad.md` and
`pocas-peticiones-al-autor.md`, `author.md`, `ask-when-ambiguous.md` and `few-requests-to-the-author.md`. The
entries keep the names of their day.

**Note (2026-10-23, ADR-038):** the history of `main` was rewritten from 2026-08-02 on. The hashes the entries cite
are those of the new history, each replaced from the rewrite's commit map.

## 2026-10-23 (the rewrite of ADR-038)

The history of `main` is rewritten, with the three lines of ADR-038 and what the V8 check found, and the rewritten
`main` is in a new repository (ADR-039). This entry also covers the sessions of 21 and 22 October, which wrote none.

**Done**
* **The figures of the procedure, measured again** on the last commit of the old `main`: 358 commits, 356 of which
  change hash, from 2026-08-02 on; the 46 merges kept; 2 commit messages rewritten; the three lines of ADR-038 and the
  paths with the folder's name, in versions of 6 files, all in `docs/`; no governed file changed; the final tree
  identical. The citations to redo grew from ten to 46 hashes in 11 files, because the rewrite now starts on
  2026-08-02 and the condensed documents cite "the history, at commit X".
* **Three findings of the measurement:**
  * no citation is in a governed path, so the commit that redoes them needs no receipt;
  * 12 hexadecimal words in the tree are not commits of this repository and stay as they are: the two GitHub Actions
    SHAs, six commits of `noticias` and AI-Papers-Engine, and four pieces of test data;
  * one citation was already dead: `54c7f8c`, in a docstring of `tests/security/test_contract_context_hook.py`, is in
    neither this history nor the copy of 2026-10-14. It is probably `4af76a9` (2026-09-24, "wire the python gate").
    The file is governed, so it goes apart.
* **The rewrite, run by the author** in their own terminal, outside the session: steps 0 to 5 on 2026-10-21, the
  checks on 22 and 23 October, the push on the 23rd. A full mirror as backup; a fresh clone of `main` alone, without
  tags; `git filter-repo` with rules generated from two private files, so that neither the name nor the term was typed
  in a session or written in the repository.
* **The checks before the push,** all as expected: 358 commits; the name and the term found 0 times in the tree, the
  messages and the diffs; the final tree identical to the old one; the commits whose tree changes, only in `docs/`; the
  two subjects rewritten (`e62110b`, `b60733d`). Checked by Claude, reading only: the first two commits keep their
  hash, the 45 `Actuarii-Record` trailers are still in the messages, and the 7 commits that messages cite are in the
  new `main`.
* **ADR-039:** the old repository renamed, and a new private one with the same name that received only `main`; its CI
  green (author). The working copy is a fresh clone of it, with `.data/` copied over and both git hooks installed with
  mode 755.
* **The citations redone:** each of the 46 hashes cited in the 11 files, replaced by its new hash at the same length:
  97 occurrences, each checked against the commit map. No old hash is left, and every hash cited in the tree is a
  commit of this history, but the 12 words and `54c7f8c` above.

Suite green (3708). Disk: 4.7 GiB free.

**What went wrong**
* **The comparison with the old history brought its tags.** Its `git fetch` from the backup had no `--no-tags`, and git
  fetched the backup's 9 tags, which point to old commits, one with the term in its name. A push of `main` would not
  have taken them, but the clone could still reach the old history. The author deleted them, expired the reflog and
  pruned before the push; the clone kept only `refs/heads/main`. The procedure now says `--no-tags`.
* **The git hooks lose their mode in a copy:** git stores them as `100644`, and without a `chmod` git ignores them, so
  no commit of the new clone would be checked or get its record. Found before the clone, and the procedure now sets
  755.

**Decided (author)**
* **This entry goes in the commit of the citations** (2026-10-22), so that `main` would not move between the measurement
  and the rewrite.

**Next**
* **The author:** pushes this commit; checks that an old hash answers 404 in the new repository; once this commit is
  green there, deletes the old repository, before the 25th; and removes `origin` from the two older local clones that
  still point to the same URL, since a push from them would upload the old history.
* **The dead citation `54c7f8c`:** a small contract to the implementer, if the author decides it.
* **V9,** the text for HN and Reddit, with the question of ADR-034.

## 2026-10-20 (late afternoon, V7)

V7 is done: nothing published says something the kit no longer does. The sweep found nothing new in `docs/`, beyond
the three notes added when each document was condensed; all of what it found was in governed files, so it went to
the implementer in two contracts.

**Done**
* **The first contract (`bde6a7a`):**
  * the description of `pyproject.toml` is now the README's sentence, and `test_packaging.py` pins it;
  * the old name of the proposal's fields is gone from `tools/` and `tests/`: a comment of the validator, docstrings
    in four test modules and a constant, now `FIELDS`;
  * the docstring of `test_review_confinement.py` said that the reviewer's blindness holds by construction, which
    contradicts the README's problem 7; it now says that the confinement is enforced by code and that what the
    harness gives the reviewer before any read is a declared limit;
  * two docstrings in Spanish, translated (`test_security.py` and `tests/security/__init__.py`);
  * two new tests keep them out: the old name, from every file of `tools/` and `tests/` but the test that guards it;
    "by construction", from their module docstrings.
* **The second contract (`0c5a315`):** three module docstrings named numbered phases of the old plan. One said that
  the validator did not yet implement what its tests assert, which it has done for weeks; the one of
  `tools/audit/check_impact.py` was in Spanish, and the installer copies that file into every target. A new test
  keeps numbered phases out of the module docstrings.
* **The check of each contract:** the report validated, `verify_red_green.py` run by Claude (each red test fails at
  the base and passes at the end, each guard passes at both, and the full suite passes at the end), and the diff
  reviewed by hand: it touches only the files of the contract, each with `Actuarii-Record: matches`.
* **Left out on purpose:** a docstring that cites `PROCESO.md`, its source of the day; the file name
  `test_tridenguard_dual_boundary.py`, old but not wrong; and a string in Spanish in `test_db_isolation.py`, which is
  test data.
* **The two contracts stay out of the tree,** as the sixteen that left with ADR-033; their commits carry what they
  decided.

**Ideas** (after the 25th; both are new functions, and ADR-004 keeps them out before the launch)
* **Red for the stated reason** (AGENTS.md §9): the verifier proves only that a red test does not pass at the base.
  The report could carry the signature of the expected failure, an exception type or a piece of the assertion
  message, and the verifier would look for it in pytest's output at the base.
* **The verifier compares the diff with the contract** (A28): `git diff --name-only` from the base to the final
  commit, checked against `files_may_touch` and `files_must_not_touch`. Today the executing agent checks it by hand.

Both answer the README's problem 2: the agent that executes checks itself.

**Next**
* **V9,** the text for HN and Reddit, with the question of ADR-034.

## 2026-10-20 (afternoon, the README read in full)

V6's full reading of the README is done, with the author, section by section.

**Done**
* **V6's check:** each of the 24 tests the README names exists, is in the file it links, and passes (89 cases with
  their parameters). Each claim of what the kit enforces names its test.
* **The sections:** all of them stand as they are, but for two additions the author decided:
  * "What comes next" says that the order of v0.2 is not fixed, that the answers that would change it are written in
    ROADMAP §3, and asks readers to say so in an issue;
  * a new section, "How it differs", names Agent Receipts (R2): it signs a receipt for every tool call after it runs,
    with a key held outside the agent; Actuarii decides before the write, records the reason, and says at each commit
    whether the governed files match. It promises no format for v0.2, since R3 is not decided.
* **Left for the rewrite:** the hashes the README cites (`57dbc72`, `3e3e50f`) change with it; the commit that redoes
  the citations covers them.

**Decided (author)**
* **The two additions** above.

**Next**
* **V7,** nothing published contradicts the kit, on the shortened tree; then V9, the text for HN and Reddit.

## 2026-10-20 (afternoon, the V8 check)

The first half of V8 is checked: the history of `main` against the personal terms the author set. The list is not
written here or anywhere in the repository.

**Done**
* **The method:** six terms, each searched as a whole word and without regard to case, in the tree of `main`, in its
  commit messages, in every diff of its history, merges included, and in the working tree. Whole words, because some
  of the terms are also pieces of ordinary English words.
* **The result:**
  * three terms appear nowhere;
  * two appear only in their ordinary technical sense: false positives;
  * one is real in two places: two commit messages of 2026-08-02, inherited from Traianus (`e62110b` and `b60733d`),
    which name the author's professional plans; and paths in documents that left the tree, which carry the name of a
    folder of the author's machine. Neither is in the tree of `main`.
* **An uncommitted DEVLOG entry,** written today, named the same term; it now speaks of NLnet's calls without it.

**Decided (author)**
* **The history is rewritten, not dropped:** the repository opens with its history, so that the records it cites stay
  checkable. A single commit with no history was weighed and set aside: it would remove the evidence the README,
  `CASES.md` and the condensed documents point to.
* **The rewrite of ADR-038 takes, as it foresaw, what the check found:** the two commit messages and the paths with the
  folder's name, matched as a whole word. It now starts on 2026-08-02, so almost every hash changes, and the commit
  that redoes the citations grows; Claude measures the procedure's figures again before it runs.

* **The second half of V8, run by the author:** `git ls-remote --heads origin` lists only `main`, at `3a8e865`, the
  last push.

**Next**
* **The rewrite:** Claude measures the figures of the procedure again; the author runs it.

## 2026-10-20 (midday, NLnet's calls)

The author brought a page of NLnet's open calls and asked whether one fits Actuarii. Read on 2026-10-20 through the
integrated browser, with the author's approval of the site: on nlnet.nl, the CodeSupply call with its guide for
applicants, eligibility, FAQ and consortium; the Restack call and its FAQ; the proposal form; and NLnet's policy on
generative AI (v1.1, 2026-01-26). Nothing was submitted.

**Findings** (documented, on the pages named)
* **Restack** leaves out AI-related projects unless they already have more than a million active users.
* **CodeSupply** funds open metadata on software packages, their origin and licensing among them: 5,000 to 50,000 €
  for a first grant and 60,000 € at most per person, from a budget of 400,000 € expected to be allocated by early 2027.
  A call every two months; the review takes three to five months from the deadline; payment by milestones, only for
  work done after the selection. The paid staff of the four members of the consortium (AboutCode, the Edsger
  Institute, NLnet and the Universidad Rey Juan Carlos) cannot apply.
* **The proposal** is written in the applicant's own words, and any use of generative AI in it is declared with the
  log of its prompts. The form says NLnet is not interested in AI-generated projects or proposals.
* **NLnet's policy on generative AI,** in force since 2025-12-08, asks every funded project to mark generated code per
  commit, with the model and its version, how it was used and its prompts or a summary of them, and suggests a tool
  that fills this in at the commit. Outcomes purely generated by AI are not paid.

**What it implies (Claude's reading, inferred, not a decision)**
* The calls fit Actuarii poorly: Restack excludes it, and CodeSupply would pay only the human part of the work.
* The policy describes a need that Actuarii covers in part. Today it records the reason of each write and whether the
  commit matches what was recorded; it does not name the model or the session (AGENTS.md §9), does not keep the
  prompts, and covers only the governed paths.

**Ideas**
* **NLnet's grantees as an audience** (Claude's proposal, noted at the author's request): every project NLnet funds
  must disclose its generated code per commit, and NLnet announced 47 new grants on 2026-10-15. They are people with
  a need Actuarii serves, which matters for the signal of 24 November more than a grant does. It waits until after
  the 25th.
* **An architectural specification of the kit** (the author): strict, covering its aspects from the data on; the kit
  has none today. Claude's suggestion: requirements with stable identifiers, each pinned by a test, served to the
  agent through the contract registry (AGENTS.md §3). With v0.2.

## 2026-10-20 (midday, R2)

R2 of the research of v0.2: which existing format covers signed records, so that v0.2 emits one instead of inventing
it (ADR-034). Read on 2026-10-20 through the integrated browser, with the author's approval of each site: the
repository and the specification of Agent Receipts (github.com/agent-receipts/obsigna, agentreceipts.ai, its receipt
schema), the in-toto Attestation Framework (spec v1.2), SLSA Provenance v1, the Sigstore overview, gitsign's README,
git-config on SSH signing, and RFC 9943 (SCITT). Nothing was installed or probed.

**Written before reading:** each candidate against five questions: R2.a, what it signs and whether our record fits;
R2.b, who verifies it, and how; R2.c, where the key lives, and whether it can stay out of the agent's reach; R2.d, the
cost of adopting it; R2.e, whether it detects a forged record and a missing one. SCITT was added to the list of
ADR-034; Agent Receipts was looked up first, since the search of 2026-10-06 only named it.

**Findings** (D documented, I inferred)

| Candidate | R2.a fits | R2.b verifies | R2.c key | R2.d cost | R2.e detects |
|---|---|---|---|---|---|
| Agent Receipts 0.5.0 (Obsigna) | Yes, closely: a W3C Verifiable Credential per action, with target, parameters hash, before and after hashes, the human principal and a chain; the reason has no field of its own (D) | Ed25519; how a verifier gets the public key is not specified (D) | An out-of-process daemon holds it, over a Unix socket; HSM or KMS on its trust model (D) | A Python SDK on PyPI, a Go daemon; young: one author, 20 stars (D) | Modification, insertion, deletion and reorder of the chain, formally checked; the end of an open chain only with a terminal receipt; an action never emitted, no (D) |
| in-toto Attestation v1.2 | Yes, as a predicate of our own about an artifact's digest (D) | Through whatever signs the envelope (D) | The signer's (I) | Mature, wide tooling (I) | One attestation; no chain or order (I) |
| SLSA Provenance v1 | No: a predicate for builds (D) | — | — | — | — |
| Sigstore (Fulcio, Rekor) | Blobs and in-toto attestations (D) | Yes, without trusting the author: an identity certificate and an inclusion proof in a public log (D) | No long-lived key: an OIDC login per signing (D), which the agent cannot complete from the sandbox (I) | Network; the public log shows the signer's identity unless an own instance runs (D) | Backdating and forgery (I) |
| gitsign | The commit, trailers included (D) | `gitsign verify` with identity and log; GitHub does not show it as verified (D) | A browser login per signing, or a cache of about ten minutes (D) | A Go binary, network per commit (D) | As Sigstore (I) |
| git SSH signing | The commit, trailers included (D) | A file of allowed signers, in the repository or outside it (D) | A key on disk is within the agent's reach; a hardware key that needs a touch is not (I) | None: git and `ssh-keygen` (D) | The commit; not the receipts outside commits (I) |
| SCITT, RFC 9943 (June 2026) | Signed statements of any content, registered in a transparency service that returns receipts (D) | Through the service's receipts (D) | The issuer's (not read) | A transparency service to run or use (I) | Equivocation, by transparency (D) |

**What it implies (Claude's reading, inferred, not a decision)**
* For each write, Agent Receipts is the closest existing format: the fields of our receipt map onto it, and its daemon
  keeps the key out of the agent's process. Adopting the format does not require its daemon. Risks: version 0.5.0 and
  one author, and its public key distribution is not specified.
* For each commit, git's SSH signing with a hardware key covers the record of the commit with no new dependency, and
  the touch of the key could be the person's approval: approving and signing in one act (R3), at the commit (line C3
  of ROADMAP §3), without a step at each write.
* Sigstore and SCITT add verification by a third party through a transparency log; they cost network and a public
  identity, or a service of one's own. They fit later, to publish evidence, not first.
* For the text of V9: Agent Receipts already signs every tool call of Claude Code, after the fact, through a
  `PostToolUse` hook. Actuarii decides before the write and records the reason; the text should say how they differ.

**Next**
* **R3 to R5, after the 25th,** starting from two candidates: the commit signed with a hardware key as the approval,
  and the receipt of each write in the format of Agent Receipts, signed out of the agent's reach.

## 2026-10-20 (midday, R1)

R1 of the research of v0.2: whether Claude Code can show the agent's reason before the write and report for certain
whether the person approved it. Read on 2026-10-20 through the integrated browser, with the author's approval of each
site: the hooks reference (code.claude.com/docs/en/hooks), the permissions page (…/permissions) and the Agent SDK's
permissions (…/agent-sdk/permissions). Nothing was probed.

**Written before reading:** four questions, each answered "documented yes", "documented no" or "not documented":
R1.a, can a hook put the reason before the person; R1.b, can the kit learn for certain what the person answered,
told apart from an approval by a rule, a mode or the classifier; R1.c, does it hold in each permission mode; R1.d, can
the agent forge the approval or go around it.

**Findings**
* **R1.a, documented yes.** With `ask`, the `permissionDecisionReason` of a `PreToolUse` hook is shown to the person
  in the permission prompt, with a label of where the hook comes from. In auto mode the classifier can deny such a
  call but not approve it silently (hooks, "PreToolUse decision control").
* **R1.b, documented no.** No hook receives the person's answer. `PermissionRequest` runs before the prompt and can
  decide in the person's place; `PermissionDenied` fires only in auto mode, not when the person denies a prompt by
  hand; `PostToolUseFailure` does not fire for a permission denial (hooks, those three sections). Inferred: the kit
  can only deduce that someone allowed the call, from `PostToolUse` on the same call.
* **R1.c, documented for four modes.** `default` and `plan` prompt; auto mode prompts for a hook's `ask`; `dontAsk`
  denies what would prompt. Not documented: what `acceptEdits` and `bypassPermissions` do with a hook's `ask`. An
  `ask` rule in the settings prompts even in `bypassPermissions` (Agent SDK permissions, "How permissions are
  evaluated").
* **R1.d, documented yes, by three paths:** a `PermissionRequest` hook from any settings file or plugin; a mod that
  handles `tool.check`, unless managed settings or a Team or Enterprise login are in place (permissions, "Precedence
  among rules, hooks, and mods"); and the Agent SDK host's `canUseTool` callback. Where the person's answer is kept
  (the transcript?) is not documented; the agent can write outside the repository with permission (A33).

**What it implies (Claude's reading, inferred, not a decision)**
* Claude Code's permission prompt shows the reason but cannot be the approval: the kit never learns who answered, and
  three paths approve without the person.
* A certain approval has to be taken by the kit, out of the agent's reach: (a) a host of its own on the Agent SDK,
  whose `canUseTool` is the answer, close to the own environment; or (b) the validator issues no receipt until the
  person approves through a channel the agent cannot reach, such as a command in the person's terminal, outside the
  session and the sandbox. (b) depends on no hook of Claude Code and is the natural place to sign (R3); it adds a
  step for the person at each write, the friction of C1 and A30.
* Claude recommends (b) as the starting point of R3. To be probed live after the 25th: a hook's `ask` in
  `acceptEdits` and `bypassPermissions`, and where the transcript records the answer.

**Next**
* **R2,** the formats for signed records, by Wednesday 21 at night.

## 2026-10-20 (midday, the research of v0.2 and R0)

The review reaches the ROADMAP, where the author stops to research v0.2 (ADR-033). The research is planned, and its
first piece, R0, is committed.

**Done**
* **The plan of the research,** with a time box that leaves Thursday 22 for the reading of the README:
  * R0, which answers from outside would change the plan of v0.2: today;
  * R1, what Claude Code can show and report about a person's approval, from its documentation, and R2, which
    existing format covers signed records: by Wednesday 21 at night;
  * R3 to R5: after the 25th, in the window.

  Findings go in the DEVLOG entry of the day, with their source, their date and whether they are documented, probed
  or inferred; decisions go in the register; no new document before the 25th.
* **R0, in ROADMAP §3:** six lines, each with what people would say and what it changes in v0.2 (the cost first,
  another tool first, approval at the commit, the environment first, adopting what exists, the distribution first).
  A line changes the plan at two outside people, or one working conversation that sets it as its condition. §5 says
  that only that list can change the order of v0.2.
* **ADR-040,** because the ROADMAP and the status ask that a decision of the author on the ROADMAP go to the register
  with its reason. It points to §3 and does not repeat the list.

**Decided (author)**
* **The plan of the research:** R0 to R2 before the 25th, R3 to R5 after it.
* **R0 in ROADMAP §3,** with the threshold of two outside people (ADR-040).

**Next**
* **R1 and R2,** by Wednesday 21 at night, through the integrated browser with the author's approval of each site.

## 2026-10-20 (morning, the records)

The records ADR-033 proposed to take out of the tree are selected with the author: every document of `docs/` but the
ROADMAP is now reviewed.

**Done**
* **The DEVLOG,** trimmed to its entries in English, from 2026-10-18 (evening): 396 lines kept of 1868. Its head is
  translated, and says that the earlier entries are in the history at `64292e1`. It stays because the ROADMAP (§3,
  §4), the status and the memory rely on it as the live log. The head says "one entry per session", which is what the
  log has become; the original said "per day".
* **Out of the tree, in the history at `64292e1`:** the PLAN, the two audit guidelines, `PROCESO.md`, `PRIOR_ART.md`,
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
  of S8; §4, §5 and §9 shorter; §6 with the configuration as it was proposed and applied (`582cd65`). The README
  (§8), the docstrings of three tests (§6, §9) and ROADMAP V7 (§6) still cite it as they did, so no contract was
  needed. The internal labels of the fixes (F1, F4c, F5) leave.
* **Dated notes for what changed since (V7):**
  * §6: the exemption of `.claude/**` and `.mcp.json` from `denyWrite` ended on 2026-10-14 (`b8b912a`); this is the
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
  (`cdc07f4`, ADR-012, kept by ADR-022), for the permission prompts and not for the cost, which has not been measured
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

  Receipt ids, hash prefixes and the paths of the machine leave; the head names `ac706a1`, where the full record is.
* **The numbering of the sections is kept:** the CI step and its test ("section 4"), the README (§4f, §5), the
  ROADMAP, COST (§4b) and the status still cite it as they did. The README now says "its record is in §5", since the
  full one is in the history.
* **Quotes given in Spanish** (the text of §4f, the agent's words, the person's interventions) are translated only.
* **One note added:** finding 1 of attempt 5 proposed naming the target before any write; the text says it was done
  in ADR-029 (`c979cea`), as V7 asks of what has changed since.
* **Checked:** every section another document cites exists; every commit cited comes from the old text, except
  `ac706a1` and `c979cea`; no Spanish is left; no prose line passes 120 characters.

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
* **The full record,** in Spanish, is in the history: the head names `1fe043d`, which the rewrite of ADR-038 changes
  and the commit that redoes the citations covers.
* **Checked:**
  * each of the 35 cases has one entry and is in the summary;
  * each of the 28 limits of AGENTS §9 is in the summary once;
  * every commit the new text cites comes from the old one, except the reference `1fe043d`;
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
  the history at `c2cd12f`, which the head of the register names, and the status still lists them among the
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
* **A hash to redo:** `c2cd12f` changes with the rewrite of ADR-038; the commit that redoes the citations covers it.

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
* **The CI step, through the implementer:** the contract (`9667dc4`) is the first with the `.contract.json` suffix;
  the commit, `61b3322`, carries `Actuarii-Record: matches`. The executing agent validated the report, ran
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
    (c) in `MEMORY.md`, fixed in `87d9e88`; the Traianus case, replaced by ADR-030.
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
