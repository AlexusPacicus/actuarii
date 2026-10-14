import os
import sys
import json
import hashlib
import uuid
import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) in sys.path:
    import tools
else:
    sys.path.insert(0, str(REPO_ROOT))
    try:
        import tools
    finally:
        sys.path.remove(str(REPO_ROOT))

import logging

from pydantic import ValidationError

from tools.boundary_validator import hook_gate
from tools.boundary_validator.primitives import NotPython, introduced
from tools.boundary_validator.schemas.proposals import AgentMutationProposal, build_response_format

logger = logging.getLogger("tools.boundary_validator.validator")

AUDIT_LOG_DDL = """
CREATE TABLE IF NOT EXISTS audit_log (
    case_id TEXT PRIMARY KEY,
    timestamp TEXT DEFAULT (datetime('now')),
    intent_class TEXT,
    target_file TEXT,
    decision TEXT NOT NULL,
    safety_abort TEXT,
    rationale TEXT
)
"""

# What can stop a record from being written: the database, its directory, or a text it cannot hold.
RECORD_ERRORS = (sqlite3.Error, OSError, UnicodeError)


def _audit_failure(error: Exception) -> None:
    # The kind of error and no path; stdout is the JSON-RPC channel.
    sys.stderr.write(f"[boundary-validator] audit trail not written ({type(error).__name__})\n")
    sys.stderr.flush()


@contextmanager
def _audit_transaction():
    """One SQLite transaction on the audit database, committed whole or rolled back whole.

    The audit_log of a database created before the rationale column existed gets the column here, keeping its rows.
    """
    db_path = hook_gate._db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        with conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(AUDIT_LOG_DDL)
            if "rationale" not in [column[1] for column in conn.execute("PRAGMA table_info(audit_log)")]:
                conn.execute("ALTER TABLE audit_log ADD COLUMN rationale TEXT")
            yield conn


def _insert_audit(conn: sqlite3.Connection, case_id: str, decision: str, intent_class: str,
                  target_file: str, safety_abort: str, rationale: str | None) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO audit_log "
        "(case_id, intent_class, target_file, decision, safety_abort, rationale) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (case_id, intent_class, target_file, decision, safety_abort, rationale),
    )


def _persist_audit(case_id: str, decision: str, intent_class: str = "",
                   target_file: str = "", safety_abort: str = "", rationale: str | None = None) -> None:
    try:
        with _audit_transaction() as conn:
            _insert_audit(conn, case_id, decision, intent_class, target_file, safety_abort, rationale)
    except RECORD_ERRORS as error:
        _audit_failure(error)


RECEIPTS_DDL = """
CREATE TABLE IF NOT EXISTS receipts (
    case_id TEXT PRIMARY KEY,
    timestamp TEXT DEFAULT (datetime('now')),
    target_file TEXT NOT NULL,
    grounding_sha256 TEXT NOT NULL,
    block_sha256 TEXT NOT NULL
)
"""


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _insert_receipt(conn: sqlite3.Connection, case_id: str, target_file: str,
                    grounding_sha256: str, block_sha256: str) -> None:
    conn.execute(RECEIPTS_DDL)
    conn.execute(
        "INSERT OR IGNORE INTO receipts "
        "(case_id, target_file, grounding_sha256, block_sha256) VALUES (?, ?, ?, ?)",
        (case_id, target_file, grounding_sha256, block_sha256),
    )


def _persist_receipt(case_id: str, target_file: str, grounding_sha256: str, block_sha256: str) -> None:
    try:
        with _audit_transaction() as conn:
            _insert_receipt(conn, case_id, target_file, grounding_sha256, block_sha256)
    except RECORD_ERRORS as error:
        _audit_failure(error)


def _record_execute_safe(case_id: str, intent_class: str, target_file: str, safety_abort: str,
                         rationale: str, grounding_sha256: str, block_sha256: str) -> dict:
    """The EXECUTE_SAFE decision, issued only when its audit row and its receipt are written in one transaction."""
    try:
        with _audit_transaction() as conn:
            _insert_audit(conn, case_id, "EXECUTE_SAFE", intent_class, target_file, safety_abort, rationale)
            _insert_receipt(conn, case_id, target_file, grounding_sha256, block_sha256)
    except RECORD_ERRORS as error:
        _audit_failure(error)
        return {"status": "QUARANTINED", "final_decision": "ABORTED_NOT_RECORDED", "case_id": case_id,
                "reason": "the audit trail could not be written, so no receipt was issued"}
    return {"status": "VALIDATED", "final_decision": "EXECUTE_SAFE", "case_id": case_id, "and_gate_ok": True}


def _grounding_failure() -> dict:
    # Silent Denial: no reason (no path leakage)
    return {"status": "QUARANTINED", "final_decision": "ABORTED_GROUNDING_FAILED",
            "case_id": str(uuid.uuid4())}


def _finalize(decision: dict, intent: str = "", target_file: str = "",
              safety_abort: str = "", rationale: str | None = None) -> dict:
    case_id = decision.get("case_id", str(uuid.uuid4()))
    _persist_audit(case_id, decision.get("final_decision", ""), intent,
                   target_file, safety_abort, rationale)
    return decision


def _no_duplicate_keys(pairs: list) -> dict:
    keys = [key for key, _ in pairs]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate key")
    return dict(pairs)


def _no_constant(name: str):
    raise ValueError(f"the constant {name} is not allowed")


def _resolve_in_root(path: str) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = REPO_ROOT / candidate
    return candidate.resolve()


def _same_file(first: str, second: str) -> bool:
    if not first or not second:
        return False
    a, b = _resolve_in_root(first), _resolve_in_root(second)
    if a == b:
        return True
    return a.exists() and b.exists() and os.path.samefile(a, b)


def _primitive_refusal(case_id: str, resolved: Path, grounding: str, block: str) -> dict | None:
    """The refusal for a Python target whose possible results do not parse or introduce a primitive, else None.

    The write gate decides on the exact result; this is the early warning, so that no receipt is issued for a
    change the gate will refuse. The results are the file with the first occurrence of the quote replaced by the
    block, and the block alone (a Write). The reason never carries a path.
    """
    current = None
    if resolved.exists():
        try:
            current = resolved.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            return {"status": "QUARANTINED", "final_decision": "BLOCKED_BY_SAFETY_GATE", "case_id": case_id,
                    "reason": "the current file is not valid UTF-8, so no result of the change can be computed"}
    results = [block]
    if current is not None and grounding:
        results.append(current.replace(grounding, block, 1))
    parsed = False
    new: set[str] = set()
    for result in results:
        try:
            new.update(introduced(current, result))
        except NotPython:
            continue
        parsed = True
    if not parsed:
        return {"status": "QUARANTINED", "final_decision": "BLOCKED_BY_SAFETY_GATE", "case_id": case_id,
                "reason": "the result of the change does not parse as Python"}
    if new:
        return {"status": "QUARANTINED", "final_decision": "ABORTED_VIOLATES_ZERO_TRUST", "case_id": case_id,
                "reason": "the change introduces: " + ", ".join(sorted(new))}
    return None


def validate_proposal(proposal_json_str: str, target_file_path: str = "") -> dict:
    # Memory sanitization BEFORE processing (SEC-M-09): raw NUL.
    if "\x00" in proposal_json_str or "\x00" in target_file_path:
        return _finalize({"status": "QUARANTINED", "final_decision": "ABORTED_VIOLATES_ZERO_TRUST",
                         "case_id": str(uuid.uuid4())})
    try:
        proposal = json.loads(proposal_json_str, object_pairs_hook=_no_duplicate_keys,
                              parse_constant=_no_constant)
    except (ValueError, RecursionError) as e:
        return _finalize({"status": "QUARANTINED", "final_decision": "INVALID_JSON",
                          "reason": str(e)})

    if not isinstance(proposal, dict):
        return _finalize({"status": "QUARANTINED", "final_decision": "INVALID_JSON",
                          "case_id": str(uuid.uuid4())})

    rationale = None
    try:
        # Post-parse sanitization (SEC-M-09): JSON-escaped NUL \u0000, invisible in the raw string.
        if any("\x00" in str(proposal.get(k, "")) for k in proposal):
            return _finalize({"status": "QUARANTINED", "final_decision": "ABORTED_VIOLATES_ZERO_TRUST",
                              "case_id": str(uuid.uuid4())})

        grounding = proposal.get("Topological_Grounding", "")

        # Strict 5-Radicals conformance (SEC-M-14..18): every radical is
        # required; unknown enums and extra fields fail closed.
        try:
            model = AgentMutationProposal.model_validate(proposal)
        except ValidationError as exc:
            logger.debug("Proposal schema violation", exc_info=exc)
            # A MISSING Safety_Abort is malformed input (INVALID_JSON);
            # only an invalid enum value means the neuron raised a flag.
            if any(err["loc"] == ("Safety_Abort",) and err["type"] != "missing"
                   for err in exc.errors()):
                return _finalize({"status": "QUARANTINED", "final_decision": "BLOCKED_BY_SAFETY_GATE",
                                  "case_id": str(uuid.uuid4())})
            return _finalize({"status": "QUARANTINED", "final_decision": "INVALID_JSON",
                              "case_id": str(uuid.uuid4())})

        intent = model.Intent_Class.value
        safety_abort = model.Safety_Abort.value
        rationale = model.Rationale

        if safety_abort != "NONE":
            return _finalize({"status": "QUARANTINED", "final_decision": "BLOCKED_BY_SAFETY_GATE",
                              "case_id": str(uuid.uuid4())}, intent, target_file_path, safety_abort, rationale)

        # A receipt binds one file: the call's target_file MUST be the file the
        # proposal names.
        if not _same_file(model.Target_File, target_file_path):
            return _finalize({"status": "QUARANTINED", "final_decision": "ABORTED_TARGET_MISMATCH",
                              "case_id": str(uuid.uuid4())}, intent, target_file_path, safety_abort, rationale)

        # Dual Boundary: canonicalization + physical containment within the repo.
        resolved = _resolve_in_root(target_file_path)
        if not resolved.is_relative_to(REPO_ROOT):
            return _finalize(_grounding_failure(), intent, target_file_path, safety_abort, rationale)

        # SEC-M-07 (no fail-open): a file that exists MUST be cited literally,
        # whatever the intent; a file that does not exist cannot be cited, so
        # only the mutating intents (REFACTOR/FIX/AUDIT) fail on it.
        if resolved.exists():
            # BINARY UTF-8 subsequence matching over read_bytes(); an empty
            # file admits only the empty quote.
            quote_bytes = grounding.encode("utf-8")
            file_bytes = resolved.read_bytes()
            if file_bytes:
                grounded = bool(grounding) and quote_bytes in file_bytes
            else:
                grounded = not grounding
            if not grounded:
                return _finalize(_grounding_failure(), intent, target_file_path, safety_abort, rationale)
        elif intent in ["REFACTOR", "FIX", "AUDIT"]:
            return _finalize(_grounding_failure(), intent, target_file_path, safety_abort, rationale)

        # A receipt binds what the proposal says: the hashes come before the decision, so text that cannot
        # be hashed is never an EXECUTE_SAFE.
        case_id = str(uuid.uuid4())
        grounding_sha256 = _sha256(model.Topological_Grounding)
        block_sha256 = _sha256(model.Implementation_Block)
        if resolved.name.lower().endswith(".py"):
            refusal = _primitive_refusal(case_id, resolved, model.Topological_Grounding,
                                         model.Implementation_Block)
            if refusal is not None:
                abort = "SYNTAX_ERROR" if refusal["final_decision"] == "BLOCKED_BY_SAFETY_GATE" else safety_abort
                return _finalize(refusal, intent, target_file_path, abort, rationale)
        return _record_execute_safe(case_id, intent, target_file_path, safety_abort, rationale,
                                    grounding_sha256, block_sha256)
    except Exception:
        # Total function: the validator NEVER raises exceptions (fail-closed).
        return _finalize(_grounding_failure(), rationale=rationale)


# ---------------------------------------------------------------------------
# MCP Server (Model Context Protocol) over stdio (line-delimited JSON-RPC 2.0).
# MCP stdio transport: one JSON-RPC message per line.
# Diagnostic logs go to stderr to avoid corrupting the stdout channel.
# Stdlib only (sys, json, uuid, pathlib); no external dependencies.
# ---------------------------------------------------------------------------

SERVER_NAME = "boundary-validator"
SERVER_VERSION = "1.2.0"
PROTOCOL_VERSION = "2024-11-05"

def _input_schema() -> dict:
    # The strict proposal schema, with its enum definitions hoisted to the
    # document root so that their "#/$defs/..." references resolve.
    proposal = build_response_format(AgentMutationProposal)["json_schema"]["schema"]
    definitions = proposal.pop("$defs")
    return {
        "type": "object",
        "properties": {
            "proposal": proposal,
            "target_file": {
                "type": "string",
                "description": "The file the receipt is for; it MUST be the same file as the proposal's Target_File.",
            },
        },
        "required": ["proposal", "target_file"],
        "$defs": definitions,
    }


TOOL_DEFINITION = {
    "name": "validate_proposal",
    "description": (
        "BoundaryValidator Zero-Trust Gate: evaluates a neuro-symbolic proposal "
        "(the proposal schema, with the Rationale that says why the change is made) and returns "
        "the deterministic gate decision "
        "(EXECUTE_SAFE | ABORTED_GROUNDING_FAILED | ABORTED_VIOLATES_ZERO_TRUST | "
        "BLOCKED_BY_SAFETY_GATE | INVALID_JSON | ABORTED_TARGET_MISMATCH | ABORTED_NOT_RECORDED)."
    ),
    "inputSchema": _input_schema(),
}


def _rpc_result(request_id, result):
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _rpc_error(request_id, code, message):
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle_request(req: dict):
    """Processes a JSON-RPC message (MCP over stdio) and returns the response.

    Plan rule: respond ONLY if `req["id"]` is not None (notifications
    receive no response). Supported methods: initialize, ping, tools/list,
    tools/call. Standard JSON-RPC errors: -32601 method not found,
    -32602 invalid params, -32603 internal error.
    """
    request_id = req.get("id")
    if request_id is None:
        return None

    method = req.get("method")

    if method == "initialize":
        params = req.get("params") or {}
        client_info = params.get("clientInfo", {})
        return _rpc_result(request_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            "instructions": (
                "The validate_proposal tool is the BoundaryValidator Zero-Trust Gate: "
                "neurons propose, rules dispose."
            ),
            "_client": client_info,
        })

    if method == "ping":
        return _rpc_result(request_id, {})

    if method == "tools/list":
        return _rpc_result(request_id, {"tools": [TOOL_DEFINITION]})

    if method == "tools/call":
        params = req.get("params") or {}
        name = params.get("name")
        if name != "validate_proposal":
            return _rpc_error(request_id, -32602, f"Unknown tool: {name!r}")
        arguments = params.get("arguments") or {}
        proposal = arguments.get("proposal")
        target_file = arguments.get("target_file")
        if not isinstance(proposal, dict):
            return _rpc_error(request_id, -32602, "arguments.proposal must be an object")
        if not isinstance(target_file, str) or not target_file:
            return _rpc_error(request_id, -32602, "arguments.target_file must be a non-empty string")
        try:
            decision = validate_proposal(json.dumps(proposal), target_file)
        except Exception as e:  # the gate is total; this is the last line of defence
            return _rpc_error(request_id, -32603, f"Internal error: {e}")
        return _rpc_result(request_id, {
            "content": [{"type": "text", "text": json.dumps(decision, indent=2)}],
            "isError": False,
        })

    return _rpc_error(request_id, -32601, f"Method not found: {method}")


def main():
    """Main MCP stdio server loop: one JSON-RPC message per line."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as e:
            sys.stderr.write(f"[boundary-validator] invalid JSON-RPC: {e}\n")
            sys.stderr.flush()
            continue
        if not isinstance(request, dict):
            sys.stderr.write("[boundary-validator] invalid JSON-RPC: not an object\n")
            sys.stderr.flush()
            continue
        response = handle_request(request)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    if len(sys.argv) > 2:
        print(json.dumps(validate_proposal(sys.argv[1], sys.argv[2]), indent=2))
    else:
        main()
