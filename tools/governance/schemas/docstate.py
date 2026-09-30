from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class DocState(BaseModel):
    """
    Pure Pydantic schema for linear workflow state tracking.
    """

    model_config = ConfigDict(extra="forbid")

    issue_id: str = Field(
        ...,
        description="GitHub Issue ID (e.g. '#1').",
    )
    finding_id: str = Field(
        ...,
        description="Audit finding ID from AUDIT.md (e.g. 'M1').",
    )
    normative_spec: str = Field(
        ...,
        description="Relative path to target normative specification (e.g. 'docs/specifications/security_normative.md').",
    )
    math_proof_status: Literal["PENDING", "VERIFIED", "REJECTED"] = Field(
        default="PENDING",
        description="Spectral Math MCP verification status.",
    )
    tdd_phase: Literal["RED", "GREEN", "REFACTOR"] = Field(
        ...,
        description="Current TDD execution phase.",
    )
    proposal_json: dict = Field(
        default_factory=dict,
        description="Current 5 Radicals proposal payload.",
    )
    mcp_verdict: Literal["EXECUTE_SAFE", "QUARANTINED"] = Field(
        ...,
        description="BoundaryValidator MCP verdict.",
    )
    pr_url: str = Field(
        default="",
        description="URL of created GitHub Pull Request.",
    )
    log_entry_id: str = Field(
        default="",
        description="Logbook entry ID/checksum in docs/LOGOGRAPHY.md.",
    )