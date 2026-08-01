import sys
import json
import uuid
from pathlib import Path


def validate_proposal(proposal_json_str: str, target_file_path: str = "") -> dict:
    try:
        proposal = json.loads(proposal_json_str)
    except Exception as e:
        return {"status": "QUARANTINED", "decision": "INVALID_JSON", "reason": str(e)}


    safety_abort = proposal.get("Safety_Abort", "NONE")
    block = proposal.get("Implementation_Block", "")
    intent = proposal.get("Intent_Class", "NONE")
    grounding = proposal.get("Topological_Grounding", "")


    if safety_abort != "NONE":
        return {"status": "QUARANTINED", "final_decision": "BLOCKED_BY_SAFETY_GATE", "case_id": str(uuid.uuid4())}


    forbidden = ["fetch(", "axios", "urllib.request", "import requests"]
    if any(token in block for token in forbidden):
        return {"status": "QUARANTINED", "final_decision": "ABORTED_VIOLATES_ZERO_TRUST", "case_id": str(uuid.uuid4())}


    if intent in ["REFACTOR", "FIX", "AUDIT"] and target_file_path:
        file_content = Path(target_file_path).read_text(encoding="utf-8")
        if not grounding or grounding not in file_content:
            return {"status": "QUARANTINED", "final_decision": "ABORTED_GROUNDING_FAILED", "case_id": str(uuid.uuid4())}


    return {"status": "VALIDATED", "final_decision": "EXECUTE_SAFE", "case_id": str(uuid.uuid4()), "and_gate_ok": True}


# ---------------------------------------------------------------------------
# MCP Server (Model Context Protocol) over stdio (line-delimited JSON-RPC 2.0).
# MCP stdio transport: one JSON-RPC message per line.
# Diagnostic logs go to stderr to avoid corrupting the stdout channel.
# Stdlib only (sys, json, uuid, pathlib); no external dependencies.
# ---------------------------------------------------------------------------

SERVER_NAME = "tridenguard-validator"
SERVER_VERSION = "1.1.0"
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
