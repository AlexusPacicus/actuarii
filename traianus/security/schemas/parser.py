"""Strict proposal parsing pipeline (Structured Outputs contract).

Implements the ordered parsing pipeline (SEC-M-16..SEC-M-18):
  1. pure ``json.loads``
  2. fenced/embedded extraction + ``json.loads``
  3. aggressive extraction + ``json.loads``
  4. extraction + stdlib repair (trailing commas, unbalanced braces)

Pure stdlib: no external JSON repair dependency. ``parse_proposal`` validates
the parsed payload against ``AgentMutationProposal``; repaired-but-incomplete
payloads raise ``JSONParsingError`` (SEC-M-17) and Pydantic ``ValidationError``
is logged at DEBUG with ``exc_info=True`` (SEC-M-18).
"""
import json
import logging
import re

from traianus.security.schemas.proposals import AgentMutationProposal

logger = logging.getLogger("traianus.security.schemas.parser")


class JSONParsingError(ValueError):
    """Raised when repaired JSON is incomplete or malformed."""


def _extract_json(raw: str, aggressive: bool = False) -> str | None:
    """Extracts the first balanced {...} block (or the fenced payload)."""
    stripped = raw.strip()
    fence = re.search(r"```(?:json)?\s*\n(.*?)```", stripped, re.S)
    if fence:
        return fence.group(1).strip()

    start = stripped.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(stripped)):
        ch = stripped[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return stripped[start : i + 1]
    if aggressive and depth > 0:
        return stripped[start:]
    return None


def _repair_lite(text: str) -> str:
    """Minimal stdlib repair: trailing commas + unbalanced closing braces."""
    repaired = re.sub(r",(\s*[}\]])", r"\1", text)
    depth = 0
    in_string = False
    escape = False
    for ch in repaired:
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
    return repaired + "}" * max(0, depth)


def parse_proposal_json(raw: str) -> tuple[dict, bool]:
    """Parses raw text into a proposal dict following the SEC-M-16 pipeline.

    Returns ``(payload, used_repair)`` where ``used_repair`` is True only when
    the JSON was not natively valid and required stdlib repair.
    """
    try:
        return json.loads(raw.strip()), False
    except (json.JSONDecodeError, TypeError):
        pass

    candidate = _extract_json(raw)
    if candidate is not None:
        try:
            return json.loads(candidate), False
        except (json.JSONDecodeError, TypeError):
            pass

        candidate = _extract_json(raw, aggressive=True) or candidate
        try:
            return json.loads(candidate), False
        except (json.JSONDecodeError, TypeError):
            pass

        try:
            return json.loads(_repair_lite(candidate)), True
        except (json.JSONDecodeError, TypeError):
            pass

    try:
        return json.loads(_repair_lite(raw)), True
    except (json.JSONDecodeError, TypeError):
        pass

    raise JSONParsingError("Unparseable proposal payload")


def parse_proposal(raw: str) -> AgentMutationProposal:
    """Parses and strictly validates a proposal (SEC-M-17, SEC-M-18).

    Repaired-but-incomplete JSON raises ``JSONParsingError``; a natively valid
    payload that violates the schema raises Pydantic ``ValidationError``.
    """
    payload, used_repair = parse_proposal_json(raw)
    try:
        return AgentMutationProposal.model_validate(payload)
    except Exception as exc:  # noqa: BLE001 - both ValidationError and friends
        if used_repair:
            raise JSONParsingError("Repaired JSON is incomplete or malformed") from exc
        logger.debug(
            "Proposal validation failed: %s", exc, exc_info=True
        )
        raise
