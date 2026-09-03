---
name: boundary-validator
description: Use when generating or validating code proposals under the 5 Radicals contract (Intent_Class, Target_File, Implementation_Block, Topological_Grounding, Safety_Abort), or when checking a proposal against the boundary-validator MCP Zero-Trust gates.
---

# BoundaryValidator 5 Radicals

Every change proposal must contain exactly:
1. `Intent_Class`: [FIX | REFACTOR | TEST | DOC | SPEC | AUDIT]
2. `Target_File`: relative path within repository root.
3. `Topological_Grounding`: exact UTF-8 quote present literally in the target file.
4. `Implementation_Block`: exact text or code block to insert/replace.
5. `Safety_Abort`: [NONE | BOUNDARY_VIOLATION | SYNTAX_ERROR | UNAUTHORIZED_SCOPE]

## Deterministic gates (validate_proposal)
1. Safety Gate: Safety_Abort != "NONE" -> BLOCKED_BY_SAFETY_GATE
2. Zero-Trust Gate: forbidden network token (fetch(, axios, urllib.request, import requests, httpx, socket, urllib3, subprocess, curl, wget, aiohttp, importlib, os.system, os.popen, requests., http.client, webbrowser, telnet, nc , ftp, xmlrpc) -> ABORTED_VIOLATES_ZERO_TRUST
3. Grounding Gate: non-exact quote in target_file (REFACTOR/FIX/AUDIT) -> ABORTED_GROUNDING_FAILED

Only if the three gates pass: VALIDATED / EXECUTE_SAFE with and_gate_ok: True.
Golden rule: neurons propose, rules dispose.
