# Agent Constitution and Governance Rules (AGENTS.md)

**Version:** 1.4.0 (RFC 2119 Compliant)
**Repository:** Traianus / TridenGuard Substrate

---

## 1. Core Domain & Hardware Invariants

### Deterministic Spatial Substrate
- State continuity **MUST** be maintained over the simplicial complex `S_n = (V_n, E_n, K_n)`.
- Vector representation **MUST** remain decoupled from state decisions.
- Execution **MUST** comply with local edge hardware limits (≤ 8 GB RAM).

### Audit & Domain Logic Invariants
- Agents **MUST** consult `docs/archive/root_clutter/TRAIANUS_AUDIT.md` before applying refactorings to `traianus/app.py`.
- Calibrations in `auto_calibrate_critical_threshold()` **MUST** exclude self-projection (`i = j`) to prevent variance inflation (Correction C1).

### Network Zero-Trust
- Code proposals **MUST NOT** contain external network primitives (`fetch`, `axios`, `urllib`, `requests`, `httpx`, `socket`, `subprocess`, `curl`, `wget`, `aiohttp`, `importlib`, `os.system`, `os.popen`).
  - Scope note: this ban applies to the `Implementation_Block` of mutation proposals. Local repository tooling (e.g. `tools/check_impact.py`, which shells out to `git grep`) is not subject to it.
- Uvicorn/FastAPI endpoints **MUST** bind exclusively to `127.0.0.1`.
- Wildcard CORS policies (`allow_origins=["*"]`) combined with credentials **MUST NOT** be introduced.

### Immutable Persistence (Append-Only)
- Destructive statements (`UPDATE`, `DELETE`) on node history **MUST NOT** be used. State revisions **MUST** be recorded via increasing sequence numbers (`seq`).

---

## 2. System Invariants & Execution Boundaries

- **No Direct OS Authority:** Agents **MUST NOT** assume direct host OS execution authority. Intended actions **MUST** be emitted as structured proposal objects.
- **Literal Grounding Guarantee:** The `Topological_Grounding` quote **MUST** exist exactly (character by character) in the target file.
- **Single-Step Iteration:** Agents **MUST NOT** attempt multi-command chaining or autonomous un-gatekept execution loops.

---

## 3. Complete Agent Matrix & Governance Layer

| Role | Plane / Phase | Operational Scope (SRP) | Strict Invariants (RFC 2119) | Permission Limits (`opencode.jsonc`) |
|---|---|---|---|---|
| `@macro-architect` | Planning | System topology, domain boundaries, API contracts. | MUST NOT edit code or tests. MUST NOT run bash. | `edit: deny` / `bash: deny` |
| `@micro-architect` | Planning | Atomic TDD task decomposition and sequencing. | MUST NOT edit code or tests. MUST NOT run bash. | `edit: deny` / `bash: deny` |
| `@plan-architect` | Planning | Analyzes project, evaluates audits, generates atomic Action Plans. | MUST NOT edit code or tests. MUST NOT run bash. | `edit: deny` / `bash: deny` |
| `@orchestrator` | Governance | Lifecycle phase control and approval gate. | MUST NOT modify files directly. MUST operate step-by-step. | `edit: deny` / `bash: ask` |
| `@dispatcher` | Orchestration | Task assignment and routing to executor agents. | MUST NOT make technical or documentation changes. | `edit: deny` / `bash: deny` |
| `@github-agent` | Git Operations | Issues, `fix/*` branches, PRs and labels via `gh` CLI. | MUST NOT edit code in `traianus/` nor tests. MUST link PRs to Issues. | `edit: deny` / `bash: ask` (`gh issue *`, `gh pr *`) |
| `@spectral-mathematician` | Algebra / Geometry | Verification of S^{d-1} projections, float drift and simplices. | MUST NOT edit source or tests directly. MUST validate via MCP `spectral-math-engine`. | `edit: deny` / `bash: deny` |
| `@test-engineer` | Code (RED) | Write failing unit/integration tests. | MUST write strictly within `tests/`. MUST NOT edit source in `traianus/`. | `edit: allow (tests/*)` |
| `@antigravity-compiler` | Code (GREEN) | Implement code to make active tests pass. | MUST write under `traianus/` and `tools/` under the 5 Radicals. MUST NOT touch `tests/`. | `edit: allow (traianus/*, tools/*)` |
| `@fixer` | Code (Refactor/Bug) | Refactoring patches and bug fixes. | MUST apply strict patches in `traianus/` and `tools/`. MUST NOT alter test expectations. | `edit: allow (traianus/*, tools/*)` |
| `@doc-architect` / `@doc-writer` / `@doc-fixer` | Documentation | Normative `SPEC-*.md`, guides, doc-drift fixes. | MUST edit strictly within `docs/`. MUST NOT modify source or tests. | `edit: allow (docs/*)` |
| `@logographer` | Traceability | Immutable milestone records and closures. | MUST record every milestone in `docs/LOGOGRAPHY.md`. MUST NOT edit code, tests or specs. | `edit: allow (docs/LOGOGRAPHY.md)` |

---

## 4. 1:1 Execution Mirror Layer

| Code Plane | Documentation Plane |
|---|---|
| `@test-engineer` (RED) | `@doc-architect` (Specs) |
| `@antigravity-compiler` (GREEN) | `@doc-writer` (Manuals) |
| `@fixer` (Patches) | `@doc-fixer` (Doc-Drift) |

### A. Code Execution Plane
- **`@test-engineer` (RED):** **MUST** write failing unit or integration tests strictly in `tests/`. **MUST NOT** edit source files in `traianus/`.
- **`@antigravity-compiler` (GREEN):** **MUST** implement source code strictly inside `traianus/` (and `tools/` schemas/MCP) under the 5 Code Radicals to make active tests pass. **MUST NOT** modify test files in `tests/`.
- **`@fixer` (REFACTOR / BUG):** **MUST** apply patch-level corrections and refactorings to `traianus/` and `tools/`. **MUST NOT** alter test expectations to bypass failures.

### B. Logographic Documentation Plane
- **`@doc-architect`:** **MUST** design and update normative specs (`SPEC-*.md`).
- **`@doc-writer`:** **MUST** draft architectural guides inside `docs/`.
- **`@doc-fixer`:** **MUST** resolve doc-drift, broken references, and typos inside `docs/`.

---

## 5. Logographic Documentation Rules

1. **One Node, One Document:** Every directory under `docs/` **MUST** contain exactly one primary markdown document defining that domain node.
2. **Sub-Branch Isolation:** Component sub-documentation **MUST** be placed in isolated sub-folders matching the taxonomy.

---

## 6. Audit & Historical Traceability

- **`@logographer`:** **MUST** record every formal phase completion and milestone in `docs/LOGOGRAPHY.md`. **MUST NOT** edit source code, tests, or system specs.

---

## 7. Mandatory Proposal Schema (Pydantic / 5 Radicals)

All agent mutation proposals **MUST** conform strictly to the Pydantic schema in
`traianus/security/schemas/proposals.py` (`AgentMutationProposal`) with `strict: true`, and
**MUST** be emitted through the structured outputs contract
`build_response_format(AgentMutationProposal)` (normative SEC-M-14..SEC-M-18,
parsed via `traianus/security/schemas/parser.py`):

1. `Intent_Class`: strict classification (`FIX`, `REFACTOR`, `TEST`, `DOC`, `SPEC`).
2. `Target_File`: target path relative to repository root.
3. `Topological_Grounding`: exact UTF-8 quote present in target file.
4. `Implementation_Block`: exact text or code block to insert/replace.
5. `Safety_Abort`: high-level safety status (`NONE`, `BOUNDARY_VIOLATION`,
   `SYNTAX_ERROR`, `UNAUTHORIZED_SCOPE`).
