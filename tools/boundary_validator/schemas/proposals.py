from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, field_validator


class IntentClass(str, Enum):
    FIX = "FIX"
    REFACTOR = "REFACTOR"
    TEST = "TEST"
    DOC = "DOC"
    SPEC = "SPEC"
    # AUDIT participates in the mutating-intent grounding gate (validator
    # SEC-M-07, MCP tool docs); the schema lagged behind its own consumers.
    AUDIT = "AUDIT"


class SafetyAbort(str, Enum):
    NONE = "NONE"
    BOUNDARY_VIOLATION = "BOUNDARY_VIOLATION"
    SYNTAX_ERROR = "SYNTAX_ERROR"
    UNAUTHORIZED_SCOPE = "UNAUTHORIZED_SCOPE"


class AgentMutationProposal(BaseModel):
    """
    Structured Output Schema for Agent Mutation Proposals: the intent, the file, the quote that grounds the
    change, the change itself, the safety flag and the Rationale that says why the change is made.
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
    Rationale: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description=(
            "Why the change is made, in words the person who reads the record understands: 1 to 1000 "
            "characters, not only whitespace. It is recorded with the decision; nothing checks that it is true."
        ),
    )

    @field_validator("Rationale")
    @classmethod
    def rationale_has_a_visible_character(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Rationale must contain at least one character that is not whitespace")
        return value


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