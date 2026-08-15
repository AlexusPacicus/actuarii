# AGENTS.md — Agent Constitution & Operational Directives (v1.5.0)

**Scope:** Repository-wide (`traianus/`, `tests/`, `tools/`)  
**Standard:** RFC 2119 (`MUST` / `MUST NOT`)

---

## 1. Execution Quality & Conciseness

1.1 The agent **MUST** be concise and **MUST NOT** include dead code, superfluous comments, explanatory over-justifications, or modify files outside the direct scope of the task.

1.2 The agent **MUST NOT** leave temporary test scripts, single-use auxiliary files, or data dumps (`.json`, `.log`) in the repository tree.

1.3 The agent **MUST NOT** silence errors with empty `try-except` blocks, unconditional generic catches, or null returns that mask failures.

1.4 The agent MUST follow a TDD workflow (write and verify failing tests first) and MUST run the test suite (`pytest tests/`) to verify passing status before declaring any task completed.

1.5 The agent **MUST NOT** add external dependencies in `pyproject.toml` without explicit approval (v1.0.0 release freeze: the Nix `flake.nix` devshell is out of scope — reproducibility is anchored in pinned `pyproject.toml` + green CI).

---

## 2. Security & Network Zero-Trust

2.1 Code proposals and mutations **MUST NOT** introduce external network primitives (`fetch`, `axios`, `urllib`, `requests`, `httpx`, `socket`, `subprocess`, `curl`, `wget`, `aiohttp`, `importlib`, `os.system`, `os.popen`).

> Scope note: this ban applies to the `Implementation_Block` of mutation proposals. Local repository tooling (e.g. `tools/audit/check_impact.py`, which shells out to `git grep`) is not subject to it.

2.2 Endpoints **MUST** bind exclusively to `127.0.0.1`. Wildcard CORS policies (`allow_origins=["*"]`) combined with credentials **MUST NOT** be introduced.

2.3 The `/ingesta` endpoint **MUST** receive text as raw `text/plain` in the HTTP body, discard JSON wrappers, and enforce `X-Idempotency-Key`.

2.4 Ingress verification **MUST** execute at the byte level: reject null bytes (`\x00`) and strict UTF-8 decoding failures (`errors="strict"`) with HTTP 400.

2.5 The agent **MUST NOT** execute inline Python (`python3 -c`, `python3 -m`). Python execution is restricted to committed scripts under `tools/` or `traianus/`. Any Python script not previously committed requires explicit user approval before execution. This rule is enforced by the `opencode.jsonc` permission matrix (deny `python3 -c *`, deny `python3 -m *`).

---

## 3. Substrate Domain & Mathematical Invariants (384D)

3.1 The agent **MUST** treat `traianus/` strictly as a deterministic state engine operating over 384D float32 L2-normalized vectors ($\|\mathbf{v}\|_2 = 1.0$), spectral projection signatures, and SQLite transitions, within the ≤ 8 GB RAM hardware envelope.

3.2 The agent **MUST NOT** introduce application domain concepts ("ideas", "thoughts", "hyperfocus") into `traianus/` source or tests. These belong exclusively to the client (RefApp-01).

3.3 The agent **MUST** tag the active seed as `epoch_provenance = 'PROSTHETIC_NSM_V1'`. Cross-epoch comparisons **MUST NOT** be performed without re-projection.

3.4 Spectral projections in $C1$ **MUST** exclude self-projection ($i \neq j$) during variance calculation to prevent variance inflation.

3.5 State consolidation **MUST** require the simultaneous satisfaction of both keys in `traianus/core.py`:
$$\text{Consolidated} \iff (\sigma^2 \ge \theta_{\text{dyn}}) \land (\text{EthicalKey} == \text{True})$$

3.6 Agents **MUST** consult `docs/audit/AUDIT.md` before applying refactorings to `traianus/app.py`.

---

## 4. Persistence & Immutability

4.1 The agent **MUST NOT** execute SQL `UPDATE` or `DELETE` statements on `geodesic_axes` or node history. All updates are append-only, recorded via increasing sequence numbers (`seq`).

4.2 Lifecycle states **MUST** be restricted to `pending_approval`, `incubating`, `consolidated`, and the append-only error-log state `telemetry_error` (persisted by the spectral processor and read by `/telemetry`). The `archived` state **MUST NOT** be used or defined in schemas or DDLs. The SQLite `CHECK` constraint mirrors this set.

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

## 6. Governance & Role Taxonomy

6.1 Traianus is governed by a **single executing agent**; there are no live subagents. The former role taxonomy (planning, orchestration, code RED/GREEN, docs, github, traceability) is retained **conceptually** for documentation and process traceability, and the detailed role definitions are archived in git history.

6.2 Enforcement is centralized, not per-role:
- `opencode.jsonc` global permission matrix (git read-only allowlist; `rm *`, webfetch, websearch deny; mutations `ask`).
- The boundary-validator MCP (Zero-Trust gate, SEC-M-01..12) gating mutation proposals.
- The security test suite (`tests/security/`, incl. SEC-M-13 config perimeter).

6.3 Domain boundaries from the taxonomy remain normative for the single agent: edits to `tests/` vs `traianus/` vs `docs/` follow the same separation the roles once enforced (tests are not altered to mask failures; source is not edited to chase the test).

6.4 **Logographic Rules:** every directory under `docs/` **MUST** contain exactly one primary markdown document defining that domain node; component sub-documentation **MUST** be placed in isolated sub-folders matching the taxonomy.
