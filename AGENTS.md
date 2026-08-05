# AGENTS.md — Agent Constitution & Operational Directives (v1.5.0)

**Scope:** Repository-wide (`traianus/`, `tests/`, `tools/`)  
**Standard:** RFC 2119 (`MUST` / `MUST NOT`)

---

## 1. Execution Quality & Conciseness

1.1 The agent **MUST** be concise and **MUST NOT** include dead code, superfluous comments, explanatory over-justifications, or modify files outside the direct scope of the task.

1.2 The agent **MUST NOT** leave temporary test scripts, single-use auxiliary files, or data dumps (`.json`, `.log`) in the repository tree.

1.3 The agent **MUST NOT** silence errors with empty `try-except` blocks, unconditional generic catches, or null returns that mask failures.

1.4 The agent **MUST** run the test suite (`pytest tests/`) and verify its passing status before declaring any task completed.

1.5 The agent **MUST NOT** add external dependencies in `pyproject.toml` or `flake.nix` without explicit approval.

---

## 2. Security & Network Zero-Trust

2.1 Code proposals and mutations **MUST NOT** introduce external network primitives (`fetch`, `axios`, `urllib`, `requests`, `httpx`, `socket`, `subprocess`, `curl`, `wget`, `aiohttp`, `importlib`, `os.system`, `os.popen`).

> Scope note: this ban applies to the `Implementation_Block` of mutation proposals. Local repository tooling (e.g. `tools/check_impact.py`, which shells out to `git grep`) is not subject to it.

2.2 Endpoints **MUST** bind exclusively to `127.0.0.1`. Wildcard CORS policies (`allow_origins=["*"]`) combined with credentials **MUST NOT** be introduced.

2.3 The `/ingesta` endpoint **MUST** receive text as raw `text/plain` in the HTTP body, discard JSON wrappers, and enforce `X-Idempotency-Key`.

2.4 Ingress verification **MUST** execute at the byte level: reject null bytes (`\x00`) and strict UTF-8 decoding failures (`errors="strict"`) with HTTP 400.

---

## 3. Substrate Domain & Mathematical Invariants (384D)

3.1 The agent **MUST** treat `traianus/` strictly as a deterministic state engine operating over 384D float32 L2-normalized vectors ($\|\mathbf{v}\|_2 = 1.0$), spectral projection signatures, and SQLite transitions, within the ≤ 8 GB RAM hardware envelope.

3.2 The agent **MUST NOT** introduce application domain concepts ("ideas", "thoughts", "hyperfocus") into `traianus/` source or tests. These belong exclusively to the client (RefApp-01).

3.3 The agent **MUST** tag the active seed as `epoch_provenance = 'PROSTHETIC_NSM_V1'`. Cross-epoch comparisons **MUST NOT** be performed without re-projection.

3.4 Spectral projections in $C1$ **MUST** exclude self-projection ($i \neq j$) during variance calculation to prevent variance inflation.

3.5 State consolidation **MUST** require the simultaneous satisfaction of both keys in `traianus/core.py`:
$$\text{Consolidated} \iff (\sigma^2 \ge \theta_{\text{dyn}}) \land (\text{EthicalKey} == \text{True})$$

3.6 Agents **MUST** consult `docs/exploring/root_clutter/TRAIANUS_AUDIT.md` before applying refactorings to `traianus/app.py`.

---

## 4. Persistence & Immutability

4.1 The agent **MUST NOT** execute SQL `UPDATE` or `DELETE` statements on `geodesic_axes` or node history. All updates are append-only, recorded via increasing sequence numbers (`seq`).

4.2 Lifecycle states **MUST** be restricted to `pending_approval`, `incubating`, and `consolidated`. The `archived` state **MUST NOT** be used or defined in schemas or DDLs.

4.3 Local adjacency $E_n$ ($\epsilon = 0.8$, L2) **MUST** remain a purely observational metric in `/relations` and **MUST NOT** alter lifecycle states.

---

## 5. Structured Mutation Proposals (Pydantic / 5 Radicals)

5.1 Mutation proposals **MUST** conform strictly to the Pydantic schema in `traianus/security/schemas/proposals.py` (`AgentMutationProposal`) with `strict: true`, and **MUST** be emitted through the structured outputs contract `build_response_format(AgentMutationProposal)` (normative SEC-M-14..SEC-M-18, parsed via `traianus/security/schemas/parser.py`):

1. `Intent_Class`: strict classification (`FIX`, `REFACTOR`, `TEST`, `DOC`, `SPEC`).
2. `Target_File`: target path relative to repository root.
3. `Topological_Grounding`: exact UTF-8 quote present in target file.
4. `Implementation_Block`: exact text or code block to insert/replace.
5. `Safety_Abort`: high-level safety status (`NONE`, `BOUNDARY_VIOLATION`, `SYNTAX_ERROR`, `UNAUTHORIZED_SCOPE`).

5.2 **No Direct OS Authority:** Agents **MUST NOT** assume direct host OS execution authority. Intended actions **MUST** be emitted as structured proposal objects.

5.3 **Literal Grounding Guarantee:** The `Topological_Grounding` quote **MUST** exist exactly (character by character) in the target file.

5.4 **Single-Step Iteration:** Agents **MUST NOT** attempt multi-command chaining or autonomous un-gatekept execution loops.

---

## 6. Governance & Agent Matrix

6.1 The full role definitions live in `.opencode/agents/*.md`. The SRP matrix is enforced through `opencode.jsonc` edit permissions:

| Role | Plane / Phase | Operational Scope (SRP) | Permission Limits (`opencode.jsonc`) |
|---|---|---|---|
| `@macro-architect` | Planning | System topology, domain boundaries, API contracts. | `edit: deny` / `bash: deny` |
| `@micro-architect` | Planning | Atomic TDD task decomposition and sequencing. | `edit: deny` / `bash: deny` |
| `@plan-architect` | Planning | Analyzes project, evaluates audits, generates atomic Action Plans. | `edit: deny` / `bash: deny` |
| `@orchestrator` | Governance | Lifecycle phase control and approval gate. | `edit: deny` / `bash: ask` |
| `@dispatcher` | Orchestration | Task assignment and routing to executor agents. | `edit: deny` / `bash: deny` |
| `@github-agent` | Git Operations | Issues, `fix/*` branches, PRs and labels via `gh` CLI. | `edit: deny` / `bash: ask` (`gh issue *`, `gh pr *`) |
| `@spectral-mathematician` | Algebra / Geometry | Verification of S^{d-1} projections, float drift and simplices. | `edit: deny` / `bash: deny` |
| `@test-engineer` | Code (RED) | Write failing unit/integration tests. MUST write strictly within `tests/`. MUST NOT edit source in `traianus/`. | `edit: allow (tests/*)` |
| `@antigravity-compiler` | Code (GREEN) | Implement code to make active tests pass. MUST write under `traianus/` and `tools/` under the 5 Radicals. MUST NOT touch `tests/`. | `edit: allow (traianus/*, tools/*)` |
| `@fixer` | Code (Refactor/Bug) | Refactoring patches and bug fixes. MUST apply strict patches in `traianus/` and `tools/`. MUST NOT alter test expectations. | `edit: allow (traianus/*, tools/*)` |
| `@doc-architect` / `@doc-writer` / `@doc-fixer` | Documentation | Normative `SPEC-*.md`, guides, doc-drift fixes. MUST edit strictly within `docs/`. MUST NOT modify source or tests. | `edit: allow (docs/*)` |
| `@logographer` | Traceability | Immutable milestone records and closures. MUST record every milestone in `docs/LOGOGRAPHY.md`. MUST NOT edit code, tests or specs. | `edit: allow (docs/LOGOGRAPHY.md)` |

6.2 **1:1 Execution Mirror:** `@test-engineer` (RED) ↔ `@doc-architect` (Specs); `@antigravity-compiler` (GREEN) ↔ `@doc-writer` (Manuals); `@fixer` (Patches) ↔ `@doc-fixer` (Doc-Drift).

6.3 **Logographic Rules:** every directory under `docs/` **MUST** contain exactly one primary markdown document defining that domain node; component sub-documentation **MUST** be placed in isolated sub-folders matching the taxonomy.
