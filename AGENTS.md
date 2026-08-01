# 🏛️ Agent Constitution and Governance Rules (`AGENTS.md`)

> **Purpose:** Define operational boundaries, architectural invariants, and inviolable rules for OpenCode agents (`@plan-architect`, `@orchestrator`, `@fixer`, `@antigravity-compiler`, `@logographer`) within the **Traianus** / **TridenGuard** repository.

---

## 📐 1. Domain and Architectural Principles
* **Traianus (Deterministic Spatial Substrate):**
  - Maintains state continuity over a simplicial complex $S_n = (V_n, E_n, K_n)$.
  - Decouples vector representation from state decisions.
  - **Strict Hardware Constraint:** Local or offline execution on edge ($\le 8\text{ GB}$ RAM).
* **TridenGuard (Neuro-Symbolic Firewall):**
  - Zero-Trust evaluation via deterministic rules (*Policy Gate*, *Zero-Trust Gate*, *Grounding Gate*).
  - Golden rule: *"Neurons propose, rules dispose"*.

---

## 🛡️ 2. Operational Invariants and Inviolable Rules

1. **Audit Synchronization:** Always consult `TRAIANUS_AUDIT.md` before applying refactorizations to `traianus/app.py`.
2. **Variance Threshold Correction (C1):** When calibrating `auto_calibrate_critical_threshold()` in `traianus/app.py`, the self-projection of the vector onto itself ($i = j$, value $1.0$) **must always be excluded** to avoid artificially inflating the variance.
3. **Zero-Trust and Network Security:**
   - Block any code fragment attempting external network requests (`fetch()`, `axios`, `urllib.request`, `requests`).
   - Restrict Uvicorn/FastAPI server to `127.0.0.1` and remove wildcard CORS policy (`allow_origins=["*"]`) combined with credentials.
4. **Literal Grounding Guarantee:** When refactoring or repairing code (`REFACTOR`, `FIX`), the citation assigned in `Topological_Grounding` must exist exactly (character by character) in the Traianus source file.
5. **Immutable Persistence (*Append-Only*):** The use of destructive statements (`UPDATE`, `DELETE`) on node history is prohibited; state modifications are recorded by inserting new revisions with increasing sequence (`seq`).

---

## 🤖 3. Sub-Agent Roles and Flows

* **`@fixer`:** Specialist in syntactic patches, FastAPI endpoint fixes, and audit finding resolution.
* **`@antigravity-compiler`:** Neuro-symbolic compiler generating structured code proposals under the **5 Code Radicals** (`Intent_Class`, `Runtime_Contract`, `Implementation_Block`, `Topological_Grounding`, `Safety_Abort`).
* **`@logographer`:** Documentation architect responsible for updating `docs/LOGOGRAPHY.md` and preventing spec-code drift (*Doc-Drift*).
* **`@plan-architect`:** Chief Architect who analyzes the project, evaluates audits, and generates atomic Action Plans with TDD criteria; `edit: deny`, `bash: deny` (never touches code). Canonical source: `docs/architecture/opencode_architecture.md` §4.
* **`@orchestrator`:** Conductor who assigns phases to executors, controls the TDD Red-Green-Refactor cycle (one phase at a time), and consolidates reports; `edit: deny`, `bash: ask`.

---

## 💻 4. Response Format
* **Conciseness and Atomic Patches:** Generate clean, concise diffs directly applicable to the repository.
* **Empirical Validation:** Every modification must be verifiable by running `pytest` in `tests/` or the audit harness in `tools/audit_harness.py`.