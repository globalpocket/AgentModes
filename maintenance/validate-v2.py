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
    "schemas/role.schema.yaml",
    "schemas/invocation.schema.yaml",
    "schemas/result.schema.yaml",
    "schemas/permissions.schema.yaml",
    "schemas/quality-gate.schema.yaml",
    "core/orchestrator.yaml",
    "core/reviewer.yaml",
    "core/reporter.yaml",
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
        return load_minimal_role_yaml(path, rel)
    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        fail(f"{rel}: invalid YAML: {exc}")
    if not isinstance(data, dict):
        fail(f"{rel}: expected YAML mapping")
    return data


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
                    parsed_value: object = child_value.strip().strip('"')
                    if parsed_value == "true":
                        parsed_value = True
                    elif parsed_value == "false":
                        parsed_value = False
                    elif parsed_value == "":
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


def check_v2_forbidden_markers() -> None:
    checked_roots = ["schemas", "core", "packs", "runtime-policies"]
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
    check_roles()
    check_v2_forbidden_markers()
    check_legacy_isolated()
    check_member_only_packs_are_not_in_core()
    print("validate-v2: ok")


if __name__ == "__main__":
    main()
