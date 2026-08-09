import sys
import json
import uuid
import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from traianus.storage import DB_PATH
from traianus.security.schemas.parser import JSONParsingError, parse_proposal_json


def _persist_audit(case_id: str, decision: str, intent_class: str = "",
                   target_file: str = "", safety_abort: str = "") -> None:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS audit_log ("
                "case_id TEXT PRIMARY KEY, timestamp TEXT DEFAULT (datetime('now')),"
                "intent_class TEXT, target_file TEXT, decision TEXT NOT NULL,"
                "safety_abort TEXT)"
            )
            conn.execute(
                "INSERT OR IGNORE INTO audit_log "
                "(case_id, intent_class, target_file, decision, safety_abort) "
                "VALUES (?, ?, ?, ?, ?)",
                (case_id, intent_class, target_file, decision, safety_abort),
            )
    except sqlite3.Error:
        pass  # Fail-open on logging: never block the gate due to audit failure


def _grounding_failure() -> dict:
    # Silent Denial: no reason (no path leakage)
    return {"status": "QUARANTINED", "final_decision": "ABORTED_GROUNDING_FAILED",
            "case_id": str(uuid.uuid4())}


def _finalize(decision: dict, intent: str = "", target_file: str = "",
              safety_abort: str = "") -> dict:
    case_id = decision.get("case_id", str(uuid.uuid4()))
    _persist_audit(case_id, decision.get("final_decision", ""), intent,
                   target_file, safety_abort)
    return decision


def validate_proposal(proposal_json_str: str, target_file_path: str = "") -> dict:
    # Memory sanitization BEFORE processing (SEC-M-09): raw NUL.
    if "\x00" in proposal_json_str or "\x00" in target_file_path:
        return _finalize({"status": "QUARANTINED", "final_decision": "ABORTED_VIOLATES_ZERO_TRUST",
                         "case_id": str(uuid.uuid4())})
    try:
        proposal, _used_repair = parse_proposal_json(proposal_json_str)
    except JSONParsingError as e:
        return _finalize({"status": "QUARANTINED", "final_decision": "INVALID_JSON",
                          "reason": str(e)})

    try:
        # Post-parse sanitization (SEC-M-09): JSON-escaped NUL \u0000, invisible in the raw string.
        if any("\x00" in str(proposal.get(k, "")) for k in proposal):
            return _finalize({"status": "QUARANTINED", "final_decision": "ABORTED_VIOLATES_ZERO_TRUST",
                              "case_id": str(uuid.uuid4())})

        safety_abort = proposal.get("Safety_Abort", "NONE")
        block = proposal.get("Implementation_Block", "")
        intent = proposal.get("Intent_Class", "NONE")
        grounding = proposal.get("Topological_Grounding", "")

        if safety_abort != "NONE":
            return _finalize({"status": "QUARANTINED", "final_decision": "BLOCKED_BY_SAFETY_GATE",
                              "case_id": str(uuid.uuid4())}, intent, target_file_path, safety_abort)

        forbidden = [
            "fetch(", "axios", "urllib.request", "import requests", "httpx",
            "socket", "urllib3", "subprocess", "curl", "wget", "aiohttp",
            "importlib", "os.system", "os.popen", "requests.", "http.client",
            "webbrowser", "telnet", "nc ", "ftp", "xmlrpc",
        ]
        if any(token in block for token in forbidden):
            return _finalize({"status": "QUARANTINED", "final_decision": "ABORTED_VIOLATES_ZERO_TRUST",
                              "case_id": str(uuid.uuid4())}, intent, target_file_path, safety_abort)

        # SEC-M-07 (no fail-open): REFACTOR/FIX/AUDIT are mutating intents, so
        # literal grounding against a target file is MANDATORY. Omitting
        # `target_file_path` is a grounding failure, not a pass.
        if intent in ["REFACTOR", "FIX", "AUDIT"]:
            if not target_file_path:
                return _finalize(_grounding_failure(), intent, target_file_path, safety_abort)
            # Dual Boundary: canonicalization + physical containment within the repo.
            resolved = Path(target_file_path).expanduser().resolve(strict=True)
            if not resolved.is_relative_to(REPO_ROOT):
                return _finalize(_grounding_failure(), intent, target_file_path, safety_abort)
            # BINARY UTF-8 subsequence matching over read_bytes().
            quote_bytes = grounding.encode("utf-8")
            file_bytes = resolved.read_bytes()
            if not grounding or quote_bytes not in file_bytes:
                return _finalize(_grounding_failure(), intent, target_file_path, safety_abort)

        return _finalize({"status": "VALIDATED", "final_decision": "EXECUTE_SAFE",
                          "case_id": str(uuid.uuid4()), "and_gate_ok": True},
                         intent, target_file_path, safety_abort)
    except Exception:
        # Total function: the validator NEVER raises exceptions (fail-closed).
        return _finalize(_grounding_failure())


# ---------------------------------------------------------------------------
# MCP Server (Model Context Protocol) over stdio (line-delimited JSON-RPC 2.0).
# MCP stdio transport: one JSON-RPC message per line.
# Diagnostic logs go to stderr to avoid corrupting the stdout channel.
# Stdlib only (sys, json, uuid, pathlib); no external dependencies.
# ---------------------------------------------------------------------------

SERVER_NAME = "tridenguard-validator"
SERVER_VERSION = "1.2.0"
PROTOCOL_VERSION = "2024-11-05"

TOOL_DEFINITION = {
    "name": "validate_proposal",
    "description": (
        "TridenGuard Zero-Trust Gate: evaluates a neuro-symbolic proposal "
        "(5 Radicals) and returns the deterministic gate decision "
        "(EXECUTE_SAFE | ABORTED_GROUNDING_FAILED | ABORTED_VIOLATES_ZERO_TRUST | "
        "BLOCKED_BY_SAFETY_GATE | INVALID_JSON)."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "proposal": {
                "type": "string",
                "description": "Serialized JSON proposal with keys Intent_Class, Implementation_Block, Topological_Grounding, Safety_Abort.",
            },
            "target_file": {
                "type": "string",
                "description": "Source file path for literal grounding verification (required for REFACTOR/FIX/AUDIT).",
            },
        },
        "required": ["proposal"],
    },
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
                "The validate_proposal tool is the TridenGuard Zero-Trust Gate: "
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
        proposal = arguments.get("proposal", "")
        target_file = arguments.get("target_file", "")
        if not isinstance(proposal, str):
            return _rpc_error(request_id, -32602, "arguments.proposal must be a string")
        try:
            decision = validate_proposal(proposal, target_file)
        except Exception as e:  # e.g. missing file in the grounding check
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
            sys.stderr.write(f"[tridenguard-validator] invalid JSON-RPC: {e}\n")
            sys.stderr.flush()
            continue
        if not isinstance(request, dict):
            sys.stderr.write("[tridenguard-validator] invalid JSON-RPC: not an object\n")
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
