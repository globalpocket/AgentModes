#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - exercised on minimal Python installs.
    yaml = None


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "README.md",
    "workflow.yaml",
    "schemas/workflow.schema.yaml",
    "schemas/role.schema.yaml",
    "schemas/invocation.schema.yaml",
    "schemas/result.schema.yaml",
    "schemas/permissions.schema.yaml",
    "schemas/quality-gate.schema.yaml",
    "core/orchestrator.yaml",
    "core/reviewer.yaml",
    "core/reporter.yaml",
    "prompts/core.orchestrator.md",
    "prompts/core.reviewer.md",
    "prompts/core.reporter.md",
    "packs/README.md",
    "packs/development/README.md",
    "runtime-policies/brownie/loop-policy.yaml",
    "runtime-policies/brownie/phase-policy.yaml",
    "runtime-policies/brownie/context-policy.yaml",
    "runtime-policies/brownie/retry-policy.yaml",
    "runtime-policies/brownie/git-policy.yaml",
    "runtime-policies/brownie/model-routing-policy.yaml",
    "legacy/zoocode/README.md",
]

ROLE_FILES = [
    "core/orchestrator.yaml",
    "core/reviewer.yaml",
    "core/reporter.yaml",
]

PROMPT_FILES = [
    "prompts/core.orchestrator.md",
    "prompts/core.reviewer.md",
    "prompts/core.reporter.md",
]

REQUIRED_ROLE_FIELDS = {
    "id",
    "version",
    "kind",
    "scope",
    "invocation_mode",
    "permissions",
    "required_inputs",
    "required_outputs",
    "status_values",
    "behavior_objective",
    "prohibited_actions",
    "quality_gates",
    "output_schema",
}

FORBIDDEN_V2_MARKERS = [
    "ZooCode",
    "Zoo Code",
    "ZooCodeCustom",
    "RooCode",
    "Roo Code",
    "Boomerang",
    "new_task",
    "switch_mode",
    "attempt_completion",
    "handoff back to Orchestrator",
]


def fail(message: str) -> None:
    print(f"validate-v2: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_yaml(rel: str) -> dict:
    path = ROOT / rel
    if yaml is None:
        if rel == "workflow.yaml":
            return load_minimal_workflow_yaml(path, rel)
        return load_minimal_role_yaml(path, rel)
    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        fail(f"{rel}: invalid YAML: {exc}")
    if not isinstance(data, dict):
        fail(f"{rel}: expected YAML mapping")
    return data


def parse_scalar(value: str) -> object:
    value = value.strip()
    if value == "true":
        return True
    if value == "false":
        return False
    try:
        return int(value)
    except ValueError:
        return value.strip('"')


def load_minimal_role_yaml(path: Path, rel: str) -> dict:
    text = path.read_text()
    data: dict[str, object] = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line or line.startswith(" ") or line.startswith("-"):
            i += 1
            continue
        if ":" not in line:
            i += 1
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value:
            data[key] = value.strip('"')
            i += 1
            continue
        if key in {"permissions", "output_schema"}:
            child: dict[str, object] = {}
            i += 1
            while i < len(lines):
                child_line = lines[i]
                if child_line and not child_line.startswith(" "):
                    break
                if child_line.startswith("  ") and not child_line.startswith("    ") and ":" in child_line:
                    child_key, child_value = child_line.split(":", 1)
                    parsed_value = parse_scalar(child_value)
                    if parsed_value == "":
                        parsed_value = {}
                    child[child_key.strip()] = parsed_value
                i += 1
            data[key] = child
            continue
        data[key] = []
        i += 1
    if not data:
        fail(f"{rel}: expected YAML mapping")
    return data


def load_minimal_workflow_yaml(path: Path, rel: str) -> dict:
    text = path.read_text()
    data: dict[str, object] = {}
    modes: list[dict[str, object]] = []
    current_mode: dict[str, object] | None = None
    current_permissions: dict[str, object] | None = None
    current_rules: list[str] | None = None

    for line in text.splitlines():
        if not line or line.lstrip().startswith("#"):
            continue
        if not line.startswith(" ") and ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if key == "modes":
                data["modes"] = modes
            elif value:
                data[key] = parse_scalar(value)
            continue
        if line.startswith("  - "):
            current_mode = {}
            current_permissions = None
            current_rules = None
            modes.append(current_mode)
            rest = line[4:].strip()
            if rest and ":" in rest:
                key, value = rest.split(":", 1)
                current_mode[key.strip()] = parse_scalar(value)
            continue
        if current_mode is None:
            continue
        if line.startswith("    ") and not line.startswith("      ") and ":" in line:
            key, value = line.strip().split(":", 1)
            key = key.strip()
            value = value.strip()
            if key == "permissions":
                current_permissions = {}
                current_mode[key] = current_permissions
                current_rules = None
            elif key == "completion_rules":
                current_rules = []
                current_mode[key] = current_rules
                current_permissions = None
            else:
                current_mode[key] = parse_scalar(value)
                current_permissions = None
                current_rules = None
            continue
        if current_permissions is not None and line.startswith("      ") and ":" in line:
            key, value = line.strip().split(":", 1)
            current_permissions[key.strip()] = parse_scalar(value)
            continue
        if current_rules is not None and line.startswith("      - "):
            current_rules.append(line.strip()[2:].strip())

    if "modes" not in data:
        data["modes"] = modes
    if not data:
        fail(f"{rel}: expected YAML mapping")
    return data


def check_required_files() -> None:
    missing = [rel for rel in REQUIRED_FILES if not (ROOT / rel).exists()]
    if missing:
        fail(f"missing required files: {missing}")


def check_roles() -> None:
    seen_ids: set[str] = set()
    for rel in ROLE_FILES:
        data = load_yaml(rel)
        missing = sorted(REQUIRED_ROLE_FIELDS - set(data))
        if missing:
            fail(f"{rel}: missing required fields {missing}")
        if data["kind"] != "role":
            fail(f"{rel}: kind must be role")
        if data["id"] in seen_ids:
            fail(f"{rel}: duplicate role id {data['id']}")
        seen_ids.add(data["id"])
        permissions = data["permissions"]
        if not isinstance(permissions, dict):
            fail(f"{rel}: permissions must be a mapping")
        if permissions.get("dispatch") is not False:
            fail(f"{rel}: permissions.dispatch must be false")
        if permissions.get("phase_write") is not False:
            fail(f"{rel}: permissions.phase_write must be false")
        if "single_pass" not in str(data["invocation_mode"]):
            fail(f"{rel}: invocation_mode must be single-pass")
        result_fields = set(data["output_schema"])
        for field in ["status", "summary", "changed_files", "verification", "risks", "blockers", "next_recommendation", "confidence"]:
            if field not in result_fields:
                fail(f"{rel}: output_schema missing shared result field {field}")


def check_framework_workflow() -> None:
    data = load_yaml("workflow.yaml")
    if data.get("schema_version") != 1:
        fail("workflow.yaml: schema_version must be 1 for Brownie workspace framework loading")
    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        fail("workflow.yaml: name must be a non-empty string")
    modes = data.get("modes")
    if not isinstance(modes, list) or not modes:
        fail("workflow.yaml: modes must be a non-empty list")

    core_role_ids = {load_yaml(rel)["id"] for rel in ROLE_FILES}
    seen_ids: set[str] = set()
    for index, mode in enumerate(modes):
        if not isinstance(mode, dict):
            fail(f"workflow.yaml: modes[{index}] must be a mapping")
        for field in ["mode_id", "display_name", "prompt_file", "permissions"]:
            if field not in mode:
                fail(f"workflow.yaml: modes[{index}] missing {field}")
        mode_id = mode["mode_id"]
        if not isinstance(mode_id, str) or not mode_id.strip():
            fail(f"workflow.yaml: modes[{index}].mode_id must be a non-empty string")
        if mode_id in seen_ids:
            fail(f"workflow.yaml: duplicate mode_id {mode_id}")
        seen_ids.add(mode_id)
        display_name = mode["display_name"]
        if not isinstance(display_name, str) or not display_name.strip():
            fail(f"workflow.yaml: {mode_id}: display_name must be a non-empty string")

        prompt_file = mode["prompt_file"]
        if not isinstance(prompt_file, str) or not prompt_file.strip():
            fail(f"workflow.yaml: {mode_id}: prompt_file must be a non-empty string")
        prompt_path = Path(prompt_file)
        if prompt_path.is_absolute() or ".." in prompt_path.parts:
            fail(f"workflow.yaml: {mode_id}: prompt_file must stay inside the framework directory")
        if prompt_path.suffix != ".md":
            fail(f"workflow.yaml: {mode_id}: prompt_file must point to Markdown")
        full_prompt_path = ROOT / prompt_path
        if not full_prompt_path.is_file():
            fail(f"workflow.yaml: {mode_id}: prompt_file does not exist: {prompt_file}")
        prompt_text = full_prompt_path.read_text(errors="ignore")
        if not prompt_text.strip():
            fail(f"workflow.yaml: {mode_id}: prompt file must not be empty")
        if mode_id not in prompt_text:
            fail(f"workflow.yaml: {mode_id}: prompt file should identify the mode id")

        permissions = mode["permissions"]
        if not isinstance(permissions, dict):
            fail(f"workflow.yaml: {mode_id}: permissions must be a mapping")
        if permissions.get("read") is not True:
            fail(f"workflow.yaml: {mode_id}: permissions.read must be true")
        for denied_key in ["edit", "command", "git", "network", "mcp", "phase_write", "dispatch"]:
            if permissions.get(denied_key) is not False:
                fail(f"workflow.yaml: {mode_id}: permissions.{denied_key} must be false in Core")

    default_mode_id = data.get("default_mode_id")
    if default_mode_id not in seen_ids:
        fail("workflow.yaml: default_mode_id must reference a declared mode")
    missing_core_ids = sorted(core_role_ids - seen_ids)
    if missing_core_ids:
        fail(f"workflow.yaml: missing Core roles {missing_core_ids}")


def check_prompts() -> None:
    for rel in PROMPT_FILES:
        text = (ROOT / rel).read_text(errors="ignore")
        if not text.strip():
            fail(f"{rel}: prompt must not be empty")


def check_v2_forbidden_markers() -> None:
    checked_roots = ["schemas", "core", "prompts", "packs", "runtime-policies"]
    for root in checked_roots:
        path = ROOT / root
        files = [path] if path.is_file() else list(path.rglob("*"))
        for file_path in files:
            if not file_path.is_file():
                continue
            rel = file_path.relative_to(ROOT).as_posix()
            text = file_path.read_text(errors="ignore")
            for marker in FORBIDDEN_V2_MARKERS:
                if marker in text:
                    fail(f"{rel}: forbidden legacy marker {marker!r}")


def check_legacy_isolated() -> None:
    legacy = ROOT / "legacy" / "zoocode"
    if not legacy.exists():
        fail("legacy/zoocode does not exist")
    for legacy_name in ["modes", "rules", "skills", "commands", "all-agents.yaml"]:
        if not (legacy / legacy_name).exists():
            fail(f"legacy/zoocode missing {legacy_name}")
    for root_name in ["modes", "rules", "skills", "commands", "all-agents.yaml"]:
        if (ROOT / root_name).exists():
            fail(f"legacy asset still exists at root: {root_name}")


def check_member_only_packs_are_not_in_core() -> None:
    development_pack = ROOT / "packs" / "development"
    if not development_pack.exists():
        fail("packs/development extension point does not exist")
    leaked_yaml = sorted(path.relative_to(ROOT).as_posix() for path in development_pack.glob("*.yaml"))
    if leaked_yaml:
        fail(f"member-only development pack role YAML must not be in Core: {leaked_yaml}")


def main() -> None:
    check_required_files()
    check_framework_workflow()
    check_prompts()
    check_roles()
    check_v2_forbidden_markers()
    check_legacy_isolated()
    check_member_only_packs_are_not_in_core()
    print("validate-v2: ok")


if __name__ == "__main__":
    main()
