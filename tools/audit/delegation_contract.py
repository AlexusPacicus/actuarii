"""Delegations and reports as strict JSON documents, validated in code before a subagent launches.

The executing agent hands a subagent a DelegationContract instead of a free-text prompt; the subagent
answers with a DelegationReport. "Strict" has the meaning it has in `build_response_format`
(traianus/security/schemas/proposals.py): every object forbids extra keys, every property is required,
no field has a default, and types are not coerced.

    python3 tools/audit/delegation_contract.py contract [--emit-context] < contract.json
    python3 tools/audit/delegation_contract.py report < report.json
    python3 tools/audit/delegation_contract.py schema contract|report

Exit 0: valid. `contract` prints `contract OK task_id=<id>` and, with --emit-context, the ready-to-run
`context_pack.py` command for the contract's context. Exit 1: invalid; stdout stays empty and stderr
lists every error as `<loc>: <message>` (`$` is the document itself). Exit 2: unreadable stdin or usage.
Duplicate keys and the constants NaN/Infinity are invalid: an ambiguous contract is an invalid one.
The context is checked by its model and by `context_pack.parse_spec`, so the two never disagree.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.audit.context_pack import SpecError, parse_spec

Gate = Literal["pytest_full", "pytest_model", "ruff_ci", "mypy", "validate_proposal", "tsc"]


def _duplicates(what: str, keys: list[str]) -> None:
    repeated = sorted({key for key in keys if keys.count(key) > 1})
    if repeated:
        raise ValueError(f"duplicate {what}: {', '.join(repeated)}")


def _branch(value: str) -> str:
    if ".." in value or value.endswith(("/", ".lock")):
        raise ValueError("a branch has no '..', no trailing '/' and no '.lock' suffix")
    return value


def _relative_path(value: str) -> str:
    if not value or value.startswith("/") or "\\" in value or ".." in value or re.search(r"[?\[\]{}]|\*{3}", value):
        raise ValueError("a path is relative, has no '..' or backslash and only the wildcards * and **")
    return value


def _subject(value: str) -> str:
    if len(value.split("\n", 1)[0]) > 100:
        raise ValueError("the first line is at most 100 characters")
    return value


TaskId = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")]
NonEmpty = Annotated[str, Field(min_length=1)]
RelativePath = Annotated[str, AfterValidator(_relative_path)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class Clause(_Strict):
    clause: str


class Heading(_Strict):
    heading: str


class Symbol(_Strict):
    symbol: str


class Paragraph(_Strict):
    paragraph: str


class Match(_Strict):
    match: str


class Lines(_Strict):
    lines: str


Selector = Clause | Heading | Symbol | Paragraph | Match | Lines


class ContextSource(_Strict):
    path: str
    select: Annotated[list[Selector], Field(min_length=1)]


class ContextSpec(_Strict):
    task: NonEmpty
    sources: Annotated[list[ContextSource], Field(min_length=1)]

    @model_validator(mode="after")
    def _context_pack_accepts_it(self) -> ContextSpec:
        try:
            parse_spec(self.model_dump_json())
        except SpecError as exc:
            raise ValueError(str(exc)) from exc
        return self


class Behaviour(_Strict):
    id: Annotated[str, Field(pattern=r"^B[0-9]{1,2}$")]
    statement: str


class ContractTest(_Strict):
    id: Annotated[str, Field(pattern=r"^T[0-9]{1,2}$")]
    must_catch: str
    expectation: Literal["red", "guard", "manual"]
    reason: str


class DelegationContract(_Strict):
    schema_version: Literal["delegation/1"]
    task_id: TaskId
    title: Annotated[str, Field(min_length=1, max_length=120)]
    branch: Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9._/-]{2,100}$"), AfterValidator(_branch)]
    base_commit: Annotated[str, Field(pattern=r"^[0-9a-f]{7,40}$")]
    attribution: Annotated[str, Field(pattern=r"^Co-Authored-By: .+ <.+@.+>$")] | None
    scope: Literal["engine", "tools", "client"]
    context: ContextSpec
    problem: NonEmpty
    decisions: list[str]
    behaviours: Annotated[list[Behaviour], Field(min_length=1)]
    tests: Annotated[list[ContractTest], Field(min_length=1)]
    files_may_touch: Annotated[list[RelativePath], Field(min_length=1)]
    files_must_not_touch: list[RelativePath]
    gates: Annotated[list[Gate], Field(min_length=1)]
    commit_message: Annotated[str, Field(min_length=1), AfterValidator(_subject)]
    report_schema: Literal["delegation-report/1"]

    @field_validator("behaviours", "tests")
    @classmethod
    def _unique_ids(cls, items: list[Any]) -> list[Any]:
        _duplicates("ids", [item.id for item in items])
        return items

    @field_validator("gates")
    @classmethod
    def _unique_gates(cls, gates: list[str]) -> list[str]:
        _duplicates("gates", gates)
        return gates

    @field_validator("tests")
    @classmethod
    def _manual_tests_are_the_client_tests(cls, tests: list[ContractTest], info: ValidationInfo) -> list[ContractTest]:
        scope = info.data.get("scope")
        manual = [test.expectation == "manual" for test in tests]
        if scope == "client" and not all(manual):
            raise ValueError("every test of a client contract is manual")
        if scope is not None and scope != "client" and any(manual):
            raise ValueError("the expectation manual is valid only when the scope is client")
        return tests

    @field_validator("files_may_touch")
    @classmethod
    def _a_client_touches_only_the_frontend_source(cls, paths: list[str], info: ValidationInfo) -> list[str]:
        outside = [path for path in paths if not path.startswith("frontend/src/")]
        if info.data.get("scope") == "client" and outside:
            raise ValueError(f"a client contract touches only frontend/src/, not {', '.join(outside)}")
        return paths

    @field_validator("gates")
    @classmethod
    def _tsc_is_the_client_gate(cls, gates: list[str], info: ValidationInfo) -> list[str]:
        scope = info.data.get("scope")
        if scope == "client" and gates != ["tsc"]:
            raise ValueError("a client contract has exactly the gate tsc")
        if scope is not None and scope != "client" and "tsc" in gates:
            raise ValueError("the gate tsc is valid only when the scope is client")
        return gates

    @model_validator(mode="after")
    def _disjoint_file_lists(self) -> DelegationContract:
        shared = sorted(set(self.files_may_touch) & set(self.files_must_not_touch))
        if shared:
            raise ValueError(f"listed in both files_may_touch and files_must_not_touch: {', '.join(shared)}")
        return self


class ReportedTest(_Strict):
    id: Annotated[str, Field(pattern=r"^(T|X)[0-9]{1,2}$")]
    red_reason: str
    catches: str


class GateResult(_Strict):
    gate: Gate
    status: Literal["pass", "fail", "not_run"]
    detail: str


class DelegationReport(_Strict):
    schema_version: Literal["delegation-report/1"]
    task_id: TaskId
    commit: Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
    tests: list[ReportedTest]
    gates: Annotated[list[GateResult], Field(min_length=1)]
    choices: list[str]
    ranges_read_beyond_context: list[str]
    not_done: list[str]


MODELS: dict[str, type[BaseModel]] = {"contract": DelegationContract, "report": DelegationReport}


class Invalid(Exception):
    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    _duplicates("key", [key for key, _ in pairs])
    return dict(pairs)


def _no_constant(name: str) -> Any:
    raise ValueError(f"the constant {name} is not allowed")


def parse(raw: str, model: type[BaseModel]) -> Any:
    try:
        data = json.loads(raw, object_pairs_hook=_no_duplicate_keys, parse_constant=_no_constant)
    except ValueError as exc:
        raise Invalid([f"$: invalid JSON: {exc}"]) from exc
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise Invalid(
            [f"{'.'.join(map(str, e['loc'])) or '$'}: {e['msg']}" for e in exc.errors(include_url=False)]
        ) from exc


def response_format(model: type[BaseModel]) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {"name": model.__name__, "schema": model.model_json_schema(), "strict": True},
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    contract = commands.add_parser("contract", help="validate a DelegationContract read from stdin")
    contract.add_argument("--emit-context", action="store_true", help="also print the context_pack command")
    commands.add_parser("report", help="validate a DelegationReport read from stdin")
    schema = commands.add_parser("schema", help="print the strict response format of a model")
    schema.add_argument("model", choices=sorted(MODELS))
    args = parser.parse_args(argv)
    if args.command == "schema":
        sys.stdout.write(json.dumps(response_format(MODELS[args.model]), sort_keys=True) + "\n")
        return 0
    try:
        raw = sys.stdin.read()
    except (OSError, UnicodeDecodeError) as exc:
        sys.stderr.write(f"stdin is not readable: {exc}\n")
        return 2
    try:
        document = parse(raw, MODELS[args.command])
    except Invalid as exc:
        sys.stderr.write("".join(f"{error}\n" for error in exc.errors))
        return 1
    lines = [f"{args.command} OK task_id={document.task_id}"]
    if args.command == "contract" and args.emit_context:
        lines += ["python3 tools/audit/context_pack.py <<'EOF'", document.context.model_dump_json(), "EOF"]
    sys.stdout.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
