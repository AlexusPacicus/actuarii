"""Contract-context hook (tools/hooks/require_contract_context.py).

Edit and Write on a path registered in the contract registry are denied unless every contract
section its rules require was served by tools/audit/context_pack.py within the window, from the
contract file as it is now. The registry is the file `contract_registry` names in .actuarii.json,
or none. The hook is driven through `main` and its pure functions on a synthetic root with an
injected clock; only the import-failure tests spawn it.
"""

import ast
import io
import json
import re
import shlex
import sys
import time
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.security.test_hook_case_identity import CaseBlindFs
from tools import project_config
from tools.audit import context_pack, run_process

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "tools" / "hooks" / "require_contract_context.py"
SETTINGS = REPO_ROOT / ".claude" / "settings.json"
BOUNDARY_HOOK = ["python3", "$CLAUDE_PROJECT_DIR/tools/hooks/require_boundary_validation.py"]
CONTRACT_HOOK = ["python3", "$CLAUDE_PROJECT_DIR/tools/hooks/require_contract_context.py"]

STAMP = "%Y-%m-%dT%H:%M:%SZ"
NOW = 1_800_000_000.0
WINDOW = 14400
CONTRACT = "frontend/audits/contracts.md"
NOTES_FILE = "docs/notes.md"
REGISTRY_REL = "contracts/registry.json"
CONTRACT_TEXT = (
    "# Contracts\n\n"
    "Engine path (one text at a time)\n  binary32 in, binary64 stored\n\n"
    "## 0. Data layer\nbits\n\n"
    "## 1. K6\ncolour\n"
)
NOTES_TEXT = "# Notes\nbody\n"
SHAS = {path: sha256(text.encode("utf-8")).hexdigest()
        for path, text in ((CONTRACT, CONTRACT_TEXT), (NOTES_FILE, NOTES_TEXT))}
ENGINE = (CONTRACT, "paragraph", "Engine path")
DATA = (CONTRACT, "heading", "0. Data layer")
K6 = (CONTRACT, "heading", "1. K6")
NOTES = (NOTES_FILE, "heading", "Notes")


def rule(name, paths, *requires):
    return {"name": name, "paths": paths,
            "requires": [dict(zip(("path", "kind", "value"), item)) for item in requires]}


REGISTRY = {"window_seconds": WINDOW, "rules": [
    rule("vector", ["src/vec.py", "src/store/**"], ENGINE),
    rule("k6", ["exp/k6_*.py"], DATA, K6),
    rule("wide", ["exp/**"], DATA, ENGINE),
    rule("aux", ["aux/**"], DATA, NOTES, K6),
]}


@pytest.fixture(scope="module")
def hook():
    from tools.hooks import require_contract_context

    return require_contract_context


@pytest.fixture
def env(tmp_path):
    root = tmp_path.resolve() / "repo"
    files = {CONTRACT: CONTRACT_TEXT, NOTES_FILE: NOTES_TEXT,
             REGISTRY_REL: json.dumps(REGISTRY)}
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    outside = root.parent / "outside.py"
    outside.write_text("", encoding="utf-8")
    return SimpleNamespace(root=root, outside=outside, contract=root / CONTRACT,
                           log=root / ".data" / "context_pack.log",
                           registry=root / REGISTRY_REL)


def stamp(seconds):
    return time.strftime(STAMP, time.gmtime(seconds))


def receipt(requirement, age=0, **fields):
    path, kind, value = requirement
    entry = {"ts": stamp(NOW - age), "task": "t", "path": path, "kind": kind, "value": value,
             "file_sha256": SHAS[path], "status": "served"}
    return {**entry, **fields}


def write_log(env, *lines):
    env.log.parent.mkdir(exist_ok=True)
    env.log.write_bytes(b"".join(
        (line if isinstance(line, bytes) else json.dumps(line).encode("utf-8")) + b"\n"
        for line in lines))


def run(hook, env, target, tool="Edit", now=NOW):
    payload = json.dumps({"tool_name": tool, "tool_input": {"file_path": str(target)}})
    return hook.main(payload, env.root, env.log, env.registry, now)


COMMAND = re.compile(r"^python3 tools/audit/context_pack\.py <<'EOF'\n(.+)\nEOF$", re.MULTILINE)


def command_text(err):
    found = COMMAND.search(err)
    assert found, f"no ready-to-run context_pack command in {err!r}"
    return found[1]


def missing(err):
    return [(source["path"], kind, value) for source in json.loads(command_text(err))["sources"]
            for selector in source["select"] for kind, value in selector.items()]


# T1: what the hook does not gate


@pytest.mark.parametrize("tool", ["Read", "Grep", "Glob", "Bash", "NotebookEdit"])
def test_tools_other_than_edit_and_write_pass(hook, env, tool):
    assert run(hook, env, "src/vec.py", tool) == 0
    assert not env.log.exists()


@pytest.mark.parametrize("target", ["plain.py", "src/other.py", ""])
def test_unregistered_and_empty_targets_pass_without_a_log(hook, env, target):
    assert run(hook, env, target) == 0
    assert not env.log.exists()


def test_a_payload_without_a_file_path_passes(hook, env):
    payload = json.dumps({"tool_name": "Write", "tool_input": {}})
    assert hook.main(payload, env.root, env.log, env.registry, NOW) == 0


@pytest.mark.parametrize("form", ["absolute", "parent", "symlink"])
def test_targets_resolving_outside_the_root_pass(hook, env, form):
    (env.root / "escape.py").symlink_to(env.outside)
    target = {"absolute": env.outside, "parent": "../outside.py",
              "symlink": env.root / "escape.py"}[form]
    assert run(hook, env, target) == 0
    assert not env.log.exists()


# T2, T3, T4: what counts as a receipt


@pytest.mark.parametrize("target, rules, required", [
    ("src/vec.py", ["vector"], [ENGINE]),
    ("src/store/deep/x.py", ["vector"], [ENGINE]),
    ("exp/k6_a.py", ["k6", "wide"], [DATA, K6, ENGINE]),
])
def test_without_a_log_the_denial_names_every_requirement(hook, env, capsys, target, rules, required):
    assert run(hook, env, target) == 2
    err = capsys.readouterr().err
    assert target in err
    assert all(name in err for name in rules)
    assert all(value in err for _path, _kind, value in required)
    assert missing(err) == required
    assert not env.log.exists()


@pytest.mark.parametrize("target, served, absent", [
    ("src/vec.py", [ENGINE], []),
    ("exp/other.py", [DATA, ENGINE], []),
    ("exp/other.py", [DATA], [ENGINE]),
    ("exp/k6_a.py", [DATA, K6, ENGINE], []),
    ("exp/k6_a.py", [DATA, K6], [ENGINE]),
    ("exp/k6_a.py", [ENGINE, DATA], [K6]),
    ("exp/k6_a.py", [K6, ENGINE], [DATA]),
])
def test_every_requirement_of_every_matching_rule_must_be_served(
        hook, env, capsys, target, served, absent):
    write_log(env, *(receipt(item) for item in served))
    code, err = run(hook, env, target), capsys.readouterr().err
    if absent:
        assert code == 2
        assert missing(err) == absent
    else:
        assert code == 0
        assert err == ""


RECEIPTS = [
    ("fresh", receipt(ENGINE), True),
    ("exactly at the window", receipt(ENGINE, age=WINDOW), True),
    ("older than the window", receipt(ENGINE, age=WINDOW + 1), False),
    ("from the future", receipt(ENGINE, age=-1), False),
    ("contract edited since", receipt(ENGINE, file_sha256="0" * 64), False),
    ("status error", receipt(ENGINE, status="error"), False),
    ("another value", receipt((CONTRACT, "paragraph", "Other")), False),
    ("another kind", receipt(ENGINE, kind="heading"), False),
    ("another path", receipt(ENGINE, path="frontend/audits/other.md"), False),
]


@pytest.mark.parametrize("entry, granted",
                         [pytest.param(entry, granted, id=name) for name, entry, granted in RECEIPTS])
def test_only_a_fresh_matching_receipt_counts(hook, env, capsys, entry, granted):
    write_log(env, entry)
    code = run(hook, env, "src/vec.py")
    assert (code == 0) is granted
    if not granted:
        assert missing(capsys.readouterr().err) == [ENGINE]


# T5: matching


@pytest.mark.parametrize("pattern, rel, expected", [
    ("traianus/storage/**", "traianus/storage/_storage.py", True),
    ("traianus/storage/**", "traianus/storage/deep/nested.py", True),
    ("traianus/storage/**", "traianus/storage_x.py", False),
    ("traianus/storage/**", "traianus/app.py", False),
    ("traianus/app.py", "traianus/app.py", True),
    ("traianus/app.py", "traianus/appXpy", False),
    ("traianus/app.py", "traianus/app.pyc", False),
    ("tools/experiments/k6_*.py", "tools/experiments/k6_colour_predictability.py", True),
    ("tools/experiments/k6_*.py", "tools/experiments/sub/k6_x.py", False),
    ("tools/experiments/k6_*.py", "tools/experiments/k6_a/b.py", False),
    ("tools/experiments/k6_*.py", "tools/experiments/k6_x.txt", False),
    ("a/*/c.py", "a/b/c.py", True),
    ("a/*/c.py", "a/b/d/c.py", False),
    ("a/**/c.py", "a/b/d/c.py", True),
    ("a/**/c.py", "a/c.py", True),
    ("*", "a.py", True),
    ("*", "a/b.py", False),
    ("**", "a/b.py", True),
])
def test_glob_star_stays_in_a_segment_and_double_star_crosses(hook, pattern, rel, expected):
    assert project_config.path_matches(pattern, rel) is expected
    assert hook.matching_rules({"rules": [rule("r", [pattern], ENGINE)]}, rel) == (
        [rule("r", [pattern], ENGINE)] if expected else [])


@pytest.mark.parametrize("form", ["relative", "absolute", "dotdot", "relative-dotdot",
                                  "file-symlink", "dir-symlink"])
def test_every_spelling_of_a_registered_target_is_denied(hook, env, capsys, form):
    (env.root / "src").mkdir()
    (env.root / "src" / "vec.py").write_text("", encoding="utf-8")
    (env.root / "alias.py").symlink_to(env.root / "src" / "vec.py")
    (env.root / "lnk").symlink_to(env.root / "src", target_is_directory=True)
    target = {
        "relative": "src/vec.py",
        "absolute": env.root / "src" / "vec.py",
        "dotdot": env.root / "src" / ".." / "src" / "vec.py",
        "relative-dotdot": "src/../src/vec.py",
        "file-symlink": env.root / "alias.py",
        "dir-symlink": env.root / "lnk" / "vec.py",
    }[form]
    assert run(hook, env, target) == 2
    err = capsys.readouterr().err
    assert "src/vec.py" in err
    assert missing(err) == [ENGINE]


def test_a_symlink_spelled_like_a_registered_path_is_matched_by_what_it_resolves_to(hook, env):
    (env.root / "src" / "store").mkdir(parents=True)
    (env.root / "plain.py").write_text("", encoding="utf-8")
    (env.root / "src" / "store" / "link.py").symlink_to(env.root / "plain.py")
    assert run(hook, env, env.root / "src" / "store" / "link.py") == 0


# T6: fail closed


@pytest.mark.parametrize("raw", [
    "{not json", "", "[]", '"Edit"', "[" * 100000,
    json.dumps({"tool_name": "Edit", "tool_input": "src/vec.py"}),
    json.dumps({"tool_name": "Edit", "tool_input": {"file_path": 5}}),
], ids=["bad-json", "empty", "array", "string", "deeply-nested", "tool-input-string",
        "file-path-number"])
def test_malformed_input_blocks(hook, env, raw):
    assert hook.main(raw, env.root, env.log, env.registry, NOW) == 2


BROKEN_REGISTRIES = {
    "missing file": None,
    "not json": "{not json",
    "not an object": "[]",
    "no window": json.dumps({"rules": []}),
    "window is text": json.dumps({"window_seconds": "4h", "rules": []}),
    "window is a bool": json.dumps({"window_seconds": True, "rules": []}),
    "rules is not a list": json.dumps({"window_seconds": WINDOW, "rules": {}}),
    "paths is not a list": json.dumps({"window_seconds": WINDOW,
                                       "rules": [rule("r", "src/vec.py", ENGINE)]}),
    "requirement without a value": json.dumps({"window_seconds": WINDOW, "rules": [
        {"name": "r", "paths": ["src/vec.py"],
         "requires": [{"path": CONTRACT, "kind": "paragraph"}]}]}),
}
BROKEN = pytest.mark.parametrize("text", BROKEN_REGISTRIES.values(), ids=list(BROKEN_REGISTRIES))


def break_registry(env, text):
    if text is None:
        env.registry.unlink()
    else:
        env.registry.write_text(text, encoding="utf-8")


@BROKEN
@pytest.mark.parametrize("target", ["src/vec.py", "plain.py"])
def test_an_unusable_registry_denies_every_edit_inside_the_root(hook, env, capsys, text, target):
    break_registry(env, text)
    assert run(hook, env, target) == 2
    assert env.registry.name in capsys.readouterr().err


@BROKEN
def test_an_unusable_registry_can_still_be_repaired(hook, env, text):
    break_registry(env, text)
    assert run(hook, env, env.registry) == 0
    assert run(hook, env, env.outside) == 0


def test_a_log_that_cannot_be_read_denies(hook, env, capsys):
    env.log.mkdir(parents=True)
    assert run(hook, env, "src/vec.py") == 2
    assert "context_pack.log" in capsys.readouterr().err


def test_a_missing_contract_file_denies(hook, env, capsys):
    write_log(env, receipt(ENGINE))
    env.contract.unlink()
    assert run(hook, env, "src/vec.py") == 2
    assert CONTRACT in capsys.readouterr().err


MALFORMED_LINES = [
    b"not json", b"[1, 2]", b'{"status": "served"}', b"\xff\xfe", b"[" * 100000,
    json.dumps(receipt(ENGINE, ts=5)).encode(),
    json.dumps(receipt(ENGINE, ts="yesterday")).encode(),
    json.dumps(receipt(ENGINE, path=["x"])).encode(),
    json.dumps(receipt(ENGINE, file_sha256=None)).encode(),
]


def test_malformed_log_lines_grant_nothing(hook, env):
    write_log(env, *MALFORMED_LINES)
    assert run(hook, env, "src/vec.py") == 2


def test_malformed_log_lines_are_skipped_and_do_not_hide_a_valid_receipt(hook, env):
    write_log(env, *MALFORMED_LINES[:3], receipt(ENGINE), *MALFORMED_LINES[3:])
    assert run(hook, env, "src/vec.py") == 0


# T7: the message, the tool and the receipt agree


def serve_what_the_denial_asks(hook, env, target, monkeypatch, capsys):
    assert run(hook, env, target, now=time.time()) == 2
    monkeypatch.setattr(sys, "stdin", io.StringIO(command_text(capsys.readouterr().err)))
    assert context_pack.main(["--root", str(env.root)]) == 0
    capsys.readouterr()


def test_the_command_in_the_denial_serves_exactly_what_the_hook_requires(
        hook, env, monkeypatch, capsys):
    assert run(hook, env, "aux/x.py") == 2
    spec = json.loads(command_text(capsys.readouterr().err))
    assert spec["sources"] == [
        {"path": CONTRACT, "select": [{"heading": "0. Data layer"}, {"heading": "1. K6"}]},
        {"path": NOTES_FILE, "select": [{"heading": "Notes"}]},
    ]
    serve_what_the_denial_asks(hook, env, "aux/x.py", monkeypatch, capsys)
    assert run(hook, env, "aux/x.py", now=time.time()) == 0


def test_a_contract_edited_after_serving_must_be_served_again(hook, env, monkeypatch, capsys):
    serve_what_the_denial_asks(hook, env, "aux/x.py", monkeypatch, capsys)
    assert run(hook, env, "aux/x.py", now=time.time()) == 0
    env.contract.write_text(CONTRACT_TEXT + "\nAmended.\n", encoding="utf-8")
    assert run(hook, env, "aux/x.py", now=time.time()) == 2
    assert missing(capsys.readouterr().err) == [DATA, K6]
    serve_what_the_denial_asks(hook, env, "aux/x.py", monkeypatch, capsys)
    assert run(hook, env, "aux/x.py", now=time.time()) == 0


# T8: the registry comes from the configuration, on every call

FOREIGN = re.compile(r"AGENTS|SS\d|(?i:traianus)")


def configured(config_file, registry=REGISTRY_REL):
    config_file({
        "schema": "actuarii-config/1", "governed_paths": ["AGENTS.md"], "python_script_dirs": [],
        "contract_registry": registry, "review": None, "receipt_window_seconds": 900,
    })


def run_configured(hook, env, target, tool="Edit", now=NOW, **primitives):
    payload = json.dumps({"tool_name": tool, "tool_input": {"file_path": str(target)}})
    return hook.main(payload, env.root, env.log, now=now, **primitives)


def test_the_registry_is_the_file_the_configuration_names(hook, env, config_file, capsys):
    configured(config_file)
    assert run_configured(hook, env, "src/vec.py") == 2
    assert missing(capsys.readouterr().err) == [ENGINE]
    write_log(env, receipt(ENGINE))
    assert run_configured(hook, env, "src/vec.py") == 0


def test_a_registry_elsewhere_in_the_root_is_the_one_that_is_read(hook, env, config_file):
    other = env.root / "elsewhere" / "r.json"
    other.parent.mkdir()
    other.write_text(json.dumps({"window_seconds": WINDOW, "rules": [rule("only", ["plain.py"], ENGINE)]}),
                     encoding="utf-8")
    configured(config_file, "elsewhere/r.json")
    assert run_configured(hook, env, "plain.py") == 2
    assert run_configured(hook, env, "src/vec.py") == 0


@pytest.mark.parametrize("target", ["src/vec.py", "exp/k6_a.py", "plain.py", REGISTRY_REL])
def test_with_a_null_registry_every_edit_passes_without_a_log(hook, env, config_file, target):
    configured(config_file, None)
    assert run_configured(hook, env, target) == 0
    assert not env.log.exists()


def test_without_a_configuration_file_there_is_no_registry(hook, env, config_file):
    assert run_configured(hook, env, "src/vec.py") == 0


def test_the_configuration_is_read_on_every_call(hook, env, config_file):
    configured(config_file, None)
    assert run_configured(hook, env, "src/vec.py") == 0
    configured(config_file)
    assert run_configured(hook, env, "src/vec.py") == 2
    configured(config_file, None)
    assert run_configured(hook, env, "src/vec.py") == 0


def test_an_explicit_registry_path_is_used_instead_of_the_configuration(hook, env, config_file):
    configured(config_file, None)
    assert run(hook, env, "src/vec.py") == 2


@pytest.mark.parametrize("target", ["src/vec.py", "plain.py", REGISTRY_REL])
def test_an_invalid_configuration_denies_every_edit_inside_the_root(hook, env, config_file, capsys, target):
    config_file("{")
    assert run_configured(hook, env, target) == 2
    err = capsys.readouterr().err
    assert ".actuarii.json" in err
    assert "not valid JSON" in err


def test_an_invalid_configuration_can_still_be_repaired_and_outside_the_root_passes(hook, env, config_file):
    config_file("{")
    assert run_configured(hook, env, ".actuarii.json") == 0
    (env.root / ".actuarii.json").write_text("{", encoding="utf-8")
    assert run_configured(hook, env, env.root / ".actuarii.json") == 0
    assert run_configured(hook, env, env.outside) == 0
    assert run_configured(hook, env, "../outside.py") == 0


def test_an_invalid_configuration_can_be_repaired_through_a_case_variant_of_its_name(hook, repo, config_file):
    config_file("{")
    (repo.root / ".actuarii.json").write_text("{", encoding="utf-8")
    assert run_configured(hook, repo, ".ACTUARII.JSON", **BLIND) == 0
    assert run_configured(hook, repo, "PLAIN.PY", **BLIND) == 2


@BROKEN
@pytest.mark.parametrize("target", ["src/vec.py", "plain.py"])
def test_an_unusable_configured_registry_denies_every_edit_and_names_its_source(
        hook, env, config_file, capsys, text, target):
    configured(config_file)
    break_registry(env, text)
    assert run_configured(hook, env, target) == 2
    err = capsys.readouterr().err
    assert REGISTRY_REL in err
    assert "contract_registry" in err
    assert ".actuarii.json" in err


@BROKEN
def test_an_unusable_configured_registry_can_still_be_repaired(hook, env, config_file, text):
    configured(config_file)
    break_registry(env, text)
    assert run_configured(hook, env, env.registry) == 0
    assert run_configured(hook, env, env.outside) == 0


def test_the_denial_for_missing_context_names_the_registry_and_where_it_comes_from(
        hook, env, config_file, capsys):
    configured(config_file)
    assert run_configured(hook, env, "src/vec.py") == 2
    err = capsys.readouterr().err
    assert REGISTRY_REL in err
    assert "contract_registry" in err
    assert ".actuarii.json" in err
    assert missing(err) == [ENGINE]


SCENARIOS = ["missing-context", "unusable-registry", "invalid-configuration", "missing-contract",
             "unreadable-log", "malformed-input"]


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_the_denials_are_free_of_foreign_citations(hook, env, config_file, capsys, scenario):
    configured(config_file)
    if scenario == "unusable-registry":
        break_registry(env, "{not json")
    elif scenario == "invalid-configuration":
        config_file("{")
    elif scenario == "missing-contract":
        write_log(env, receipt(ENGINE))
        env.contract.unlink()
    elif scenario == "unreadable-log":
        env.log.mkdir(parents=True)
    if scenario == "malformed-input":
        code = hook.main("[]", env.root, env.log, now=NOW)
    else:
        code = run_configured(hook, env, "src/vec.py")
    err = capsys.readouterr().err
    assert code == 2
    assert err
    assert not FOREIGN.search(err), err


# T8b: one copy of the matcher, and an import that cannot exit 1


def test_the_hook_carries_no_copy_of_the_matcher_nor_a_fixed_registry():
    names = set()
    for node in hook_tree().body:
        if isinstance(node, ast.FunctionDef):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names |= {target.id for target in node.targets if isinstance(target, ast.Name)}
    assert not names & {"path_matches", "WILDCARDS", "GLOB_REGEX", "REGISTRY_PATH"}


def test_the_matcher_of_the_hook_is_the_one_of_the_project_configuration(hook):
    assert hook.path_matches is project_config.path_matches


def spawn_hook(tmp_path, config_source):
    """The hook, copied into a throwaway repository whose project configuration module is `config_source`
    (None: absent), run with an isolated interpreter on an Edit of a path inside it."""
    root = tmp_path / "kit"
    (root / "tools" / "hooks").mkdir(parents=True)
    (root / "tools" / "__init__.py").write_text("", encoding="utf-8")
    copy = root / "tools" / "hooks" / HOOK.name
    copy.write_text(HOOK.read_text(encoding="utf-8"), encoding="utf-8")
    if config_source is not None:
        (root / "tools" / "project_config.py").write_text(config_source, encoding="utf-8")
    payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": str(root / "x.py")}})
    return run_process.run([sys.executable, "-I", str(copy)], stdin=payload)


def test_a_working_project_configuration_lets_the_spawned_hook_allow(tmp_path):
    done = spawn_hook(tmp_path, (REPO_ROOT / "tools" / "project_config.py").read_text(encoding="utf-8"))
    assert (done.returncode, done.stderr) == (0, "")


@pytest.mark.parametrize("source, cause", [
    pytest.param(None, "project_config", id="absent"),
    pytest.param("raise RuntimeError('boom')\n", "boom", id="raises"),
    pytest.param("def broken(:\n", "SyntaxError", id="syntax-error"),
    pytest.param("CONFIG_NAME = 1\n", "cannot import name", id="incomplete"),
])
def test_a_project_configuration_that_cannot_be_imported_denies_with_exit_2(tmp_path, source, cause):
    done = spawn_hook(tmp_path, source)
    assert done.returncode == 2
    assert done.stdout == ""
    assert done.stderr.startswith("[require_contract_context] fail-closed:")
    assert cause in done.stderr


# T8c: the relocated registry of Traianus is an example, unchanged

EXAMPLE = REPO_ROOT / "examples" / "traianus" / "contract_registry.json"
EXAMPLE_SHA256 = "c4ee65c6dd021b23e0dab8f74c5af5b8f87235166c55791798cbe4eb7f2fbb4a"


def test_the_example_registry_is_byte_for_byte_the_one_that_was_moved(hook):
    assert sha256(EXAMPLE.read_bytes()).hexdigest() == EXAMPLE_SHA256


def test_the_example_registry_loads_and_has_rules(hook):
    assert hook.load_registry(EXAMPLE)["rules"]


def test_no_registry_remains_under_the_hooks_directory():
    assert not (REPO_ROOT / "tools" / "hooks" / "contract_registry.json").exists()


# T9: startup surface


def hook_tree():
    return ast.parse(HOOK.read_text(encoding="utf-8"), feature_version=(3, 9))


def test_hook_imports_only_the_standard_library_and_the_project_configuration():
    names = set()
    for node in ast.walk(hook_tree()):
        if isinstance(node, ast.Import):
            names |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            names.add("." * node.level + (node.module or ""))
    foreign = {name for name in names if name.split(".")[0] not in sys.stdlib_module_names}
    assert foreign == {"tools.project_config"}, foreign


def test_hook_postpones_annotations_and_parses_as_python_39():
    """An import failure exits 1, which the harness reads as a broken hook, not a denial."""
    assert any(isinstance(node, ast.ImportFrom) and node.module == "__future__"
               and any(alias.name == "annotations" for alias in node.names)
               for node in hook_tree().body)


# T10: registration

PERMISSIONS = {
    "defaultMode": "default",
    "allow": [
        "Bash(python3 tools/*)", "Bash(python3 tools/*.py)", "Bash(python3 tools/mcp/*)",
        "Bash(python3 tools/audit/*)", "Bash(python3 tools/experiments/*)",
        "Bash(python3 tools/hooks/*)", "Bash(python3 tools/boundary_validator/validator.py)",
        "Bash(git status)", "Bash(git status *)", "Bash(git diff)", "Bash(git diff *)",
        "Bash(git log *)", "Bash(git show *)", "Bash(git rev-parse *)", "Bash(git grep *)",
        "Bash(git blame *)", "Bash(git ls-files *)",
    ],
    "deny": ["WebFetch", "WebSearch", "Bash(rm *)", "Bash(python3 -c *)", "Bash(python3 -m *)"],
    "ask": [
        "Bash", "Bash(git add *)", "Bash(git checkout -b *)", "Bash(git commit *)",
        "Bash(git checkout *)", "Bash(git branch *)", "Bash(git stash *)", "Bash(git tag *)",
        "Bash(git remote *)", "Bash(git fetch *)", "Bash(git pull *)", "Bash(git push *)",
        "Bash(git config *)", "Bash(git merge *)", "Bash(git rebase *)", "Bash(git reset *)",
        "Bash(git clean *)", "Bash(git submodule *)", "Bash(git rm *)", "Bash(git worktree *)",
        "Bash(gh issue *)", "Bash(gh pr *)",
    ],
}


def settings():
    return json.loads(SETTINGS.read_text(encoding="utf-8"))


def test_hook_follows_the_boundary_hook_under_edit_write():
    [entry] = [item for item in settings()["hooks"]["PreToolUse"] if item["matcher"] == "Edit|Write"]
    assert [shlex.split(item["command"]) for item in entry["hooks"]] == [BOUNDARY_HOOK, CONTRACT_HOOK]


def test_registration_changes_nothing_else_in_settings():
    """Pinned at the commit that added the hook; a deliberate perimeter change updates it
    (the python gate wiring, 54c7f8c, is the second such change)."""
    current = settings()
    assert current["permissions"] == PERMISSIONS
    parsed = [
        {**group, "hooks": [{**hook, "command": shlex.split(hook["command"])} for hook in group["hooks"]]}
        for group in current["hooks"]["PreToolUse"][1:]
    ]
    assert parsed == [
        {"matcher": "Read|Grep|Glob", "hooks": [
            {"type": "command", "command": ["python3", "$CLAUDE_PROJECT_DIR/tools/hooks/confine_review_reads.py"]}]},
        {"matcher": "Bash", "hooks": [
            {"type": "command", "command": ["python3", "$CLAUDE_PROJECT_DIR/tools/hooks/deny_python_escapes.py"]}]},
    ]
    assert current["enableAllProjectMcpServers"] is True
    assert set(current) == {"permissions", "hooks", "enableAllProjectMcpServers"}
    assert set(current["hooks"]) == {"PreToolUse", "SessionStart"}


# T11: the target is what the filesystem says it is, not how it is spelled

FS = CaseBlindFs()
BLIND = {"samefile": FS.samefile, "scandir": FS.scandir}
REFUSAL = "denied by the test"
VARIANTS = [
    ("src/vec.py", "SRC/VEC.PY"),
    ("src/store/deep/x.py", "Src/STORE/Deep/X.py"),
    ("src/store/new.py", "SRC/STORE/new.py"),
    ("exp/k6_a.py", "EXP/K6_A.PY"),
    ("exp/other.py", "Exp/Other.py"),
    ("aux/x.py", "AUX/X.PY"),
]
EXISTING_BROKEN = {name: text for name, text in BROKEN_REGISTRIES.items() if text is not None}


def refuse(*_args):
    raise PermissionError(REFUSAL)


def run_as(hook, env, target, tool="Edit", **primitives):
    payload = json.dumps({"tool_name": tool, "tool_input": {"file_path": str(target)}})
    return hook.main(payload, env.root, env.log, env.registry, NOW, **primitives)


@pytest.fixture
def repo(env):
    for name in ("src/vec.py", "src/store/deep/x.py", "exp/k6_a.py", "exp/other.py", "aux/x.py", "plain.py"):
        path = env.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
    return env


def spellings(repo, variant):
    return {"relative": variant, "absolute": repo.root / variant,
            "root-prefix": Path(str(repo.root).upper()) / variant}


@pytest.mark.parametrize("form", ["relative", "absolute", "root-prefix"])
@pytest.mark.parametrize("exact, variant", VARIANTS)
def test_a_registered_path_in_other_case_is_denied_like_its_exact_spelling(
        hook, repo, capsys, exact, variant, form):
    assert run_as(hook, repo, exact, **BLIND) == 2
    reference = capsys.readouterr().err
    assert missing(reference)
    assert run_as(hook, repo, spellings(repo, variant)[form], **BLIND) == 2
    assert capsys.readouterr().err == reference


@pytest.mark.parametrize("variant", ["PLAIN.PY", "SRC/Other.py", "Docs/Notes.md", "EXP2/x.py"])
def test_an_unregistered_path_in_other_case_passes(hook, repo, variant):
    assert run_as(hook, repo, variant, **BLIND) == 0
    assert not repo.log.exists()


@pytest.mark.parametrize("exact, variant", VARIANTS)
def test_a_receipt_covers_a_registered_path_in_other_case(hook, repo, exact, variant):
    write_log(repo, receipt(ENGINE), receipt(DATA), receipt(K6), receipt(NOTES))
    assert run_as(hook, repo, exact, **BLIND) == 0
    assert run_as(hook, repo, variant, **BLIND) == 0


@pytest.mark.parametrize("text", EXISTING_BROKEN.values(), ids=list(EXISTING_BROKEN))
def test_an_unusable_registry_can_be_repaired_through_a_case_variant_of_its_path(hook, repo, text):
    break_registry(repo, text)
    assert run_as(hook, repo, "CONTRACTS/REGISTRY.JSON", **BLIND) == 0
    assert run_as(hook, repo, "CONTRACTS/OTHER.PY", **BLIND) == 2


def test_a_directory_that_cannot_be_listed_inside_the_root_denies(hook, repo, capsys):
    assert run_as(hook, repo, "SRC/VEC.PY", samefile=FS.samefile, scandir=refuse) == 2
    err = capsys.readouterr().err
    assert "SRC/VEC.PY" in err
    assert REFUSAL in err


def test_a_path_the_filesystem_refuses_outside_the_root_passes(hook, repo):
    def samefile(first, second):
        if not Path(first).is_relative_to(repo.root):
            raise PermissionError(REFUSAL)
        return FS.samefile(first, second)

    assert run_as(hook, repo, repo.outside, samefile=samefile, scandir=FS.scandir) == 0


def test_a_path_that_cannot_be_resolved_denies_with_the_path_and_the_cause(hook, repo, capsys):
    assert run_as(hook, repo, "src/vec\x00.py", **BLIND) == 2
    err = capsys.readouterr().err
    assert "cannot resolve" in err
    assert "null" in err


def test_a_symlink_loop_denies(hook, repo, capsys):
    (repo.root / "loop").symlink_to(repo.root / "loop")
    assert run_as(hook, repo, "loop/x.py", **BLIND) == 2
    assert "cannot resolve" in capsys.readouterr().err


def test_a_home_relative_path_is_expanded_before_it_is_decided(hook, repo, capsys, monkeypatch):
    monkeypatch.setenv("HOME", str(repo.root / "src"))
    assert run_as(hook, repo, "~/vec.py", **BLIND) == 2
    assert missing(capsys.readouterr().err) == [ENGINE]


def test_an_unreadable_root_denies_instead_of_reading_every_path_as_outside(hook, repo, capsys):
    assert run_as(hook, repo, repo.outside, samefile=refuse, scandir=FS.scandir) == 2
    assert REFUSAL in capsys.readouterr().err


@pytest.mark.parametrize("form", ["relative", "absolute", "root-prefix"])
def test_on_a_case_insensitive_filesystem_a_real_variant_is_denied(hook, repo, capsys, form):
    if not (repo.root / "SRC").exists():
        pytest.skip("the filesystem under tmp_path is case-sensitive: a variant names no file here")
    assert run_as(hook, repo, spellings(repo, "SRC/VEC.PY")[form]) == 2
    assert missing(capsys.readouterr().err) == [ENGINE]
