from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class IntentClass(str, Enum):
    FIX = "FIX"
    REFACTOR = "REFACTOR"
    TEST = "TEST"
    DOC = "DOC"
    SPEC = "SPEC"


class SafetyAbort(str, Enum):
    NONE = "NONE"
    BOUNDARY_VIOLATION = "BOUNDARY_VIOLATION"
    SYNTAX_ERROR = "SYNTAX_ERROR"
    UNAUTHORIZED_SCOPE = "UNAUTHORIZED_SCOPE"


class AgentMutationProposal(BaseModel):
    """
    Structured Output Schema for Agent Mutation Proposals (5 Radicals).
    Enforces strict JSON schema validation at the LLM inference layer.
    """

    model_config = ConfigDict(extra="forbid")

    Intent_Class: IntentClass = Field(
        ...,
        description="Strict intent classification for the proposed change.",
    )
    Target_File: str = Field(
        ...,
        description="Relative target file path contained strictly within REPO_ROOT.",
    )
    Topological_Grounding: str = Field(
        ...,
        description="Exact UTF-8 quote present literally in the target file.",
    )
    Implementation_Block: str = Field(
        ...,
        description="Exact text or code block to insert/replace at the grounding anchor.",
    )
    Safety_Abort: SafetyAbort = Field(
        ...,
        description="High-level safety status flag emitted by the proposing agent.",
    )


def build_response_format(
    response_model: type[BaseModel], *, strict: bool = True, name: str | None = None
) -> dict:
    """
    Builds the OpenAI-compatible structured output response format contract.

    SEC-M-14: emits `{"type": "json_schema", "json_schema": {"name": ...,
    "schema": response_model.model_json_schema(), "strict": <strict>}}`.
    SEC-M-15: strict mode guarantees `additionalProperties: false` and a
    `required` list covering every property (enforced by the model schema).
    """
    schema = response_model.model_json_schema()
    if strict:
        schema.setdefault("additionalProperties", False)
        schema["required"] = list(schema.get("properties", {}).keys())
    return {
        "type": "json_schema",
        "json_schema": {
            "name": name or response_model.__name__,
            "schema": schema,
            "strict": strict,
        },
    }