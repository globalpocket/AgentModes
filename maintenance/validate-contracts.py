#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def load_yaml(path: Path):
    ruby = shutil.which("ruby")
    if ruby is None:
        fail("ruby is required for YAML validation")
    proc = subprocess.run(
        [ruby, "-r", "yaml", "-r", "json", "-e", "puts JSON.generate(YAML.safe_load(STDIN.read, permitted_classes: [Symbol], aliases: true))"],
        input=path.read_text(encoding="utf-8"),
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        fail(f"YAML parse failed for {path}: {proc.stderr.strip()}")
    return json.loads(proc.stdout)



def load_yaml_text(text: str, label: str):
    ruby = shutil.which("ruby")
    if ruby is None:
        fail("ruby is required for YAML validation")
    proc = subprocess.run(
        [ruby, "-r", "yaml", "-r", "json", "-e", "puts JSON.generate(YAML.safe_load(STDIN.read, permitted_classes: [Symbol], aliases: true))"],
        input=text,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        fail(f"YAML parse failed for {label}: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def fenced_yaml_blocks(markdown: str, label: str) -> list[dict]:
    blocks: list[dict] = []
    for index, match in enumerate(re.finditer(r"```yaml\n(.*?)\n```", markdown, flags=re.DOTALL), start=1):
        parsed = load_yaml_text(match.group(1), f"{label} fenced yaml block {index}")
        if not isinstance(parsed, dict):
            fail(f"{label} fenced yaml block {index}: expected mapping")
        blocks.append(parsed)
    return blocks


def find_yaml_mapping(blocks: list[dict], key: str, label: str) -> dict:
    for block in blocks:
        if key in block:
            value = block[key]
            if not isinstance(value, dict):
                fail(f"{label}: {key} must be a mapping")
            return value
    fail(f"{label}: missing fenced yaml mapping {key}")


def require_list(mapping: dict, key: str, expected: list[str], label: str) -> None:
    value = mapping.get(key)
    if not isinstance(value, list):
        fail(f"{label}: {key} must be a list")
    missing = [item for item in expected if item not in value]
    if missing:
        fail(f"{label}: {key} missing {missing}")

def mode_text(mode: dict) -> str:
    return mode.get("customInstructions") or ""


def collect_modes() -> dict[str, dict]:
    modes: dict[str, dict] = {}
    for path in sorted((ROOT / "modes").glob("*.yaml")):
        data = load_yaml(path)
        for mode in data.get("customModes", []):
            slug = mode.get("slug")
            if not slug:
                fail(f"{path}: mode without slug")
            if slug in modes:
                fail(f"duplicate slug: {slug}")
            mode["__path"] = str(path.relative_to(ROOT))
            modes[slug] = mode
    return modes


def require(mode: dict, needle: str) -> None:
    if needle not in mode_text(mode):
        fail(f"{mode['slug']}: missing required text: {needle}")


def validate_raw_input_materializer(modes: dict[str, dict]) -> None:
    mode = modes.get("raw-input-materializer") or fail("missing raw-input-materializer")
    for needle in [
        "Sole responsibility: save raw input verbatim as artifacts and return `RAW_INPUT_REF_V1`.",
        "escape-safe `RAW_INPUT_PAYLOAD_V1` envelope",
        "byte_count, and sha256",
        "Do not analyze, summarize, classify, plan, implement, test, dispatch, or answer the substantive request.",
        "Do not forward, echo, excerpt, or repackage the raw body",
        "Recommended Next Mode: gpt-oss-intake-analyzer",
        "handoff_status: requires_parent_dispatch",
        "workflow_complete: false",
        "next_action: {type: new_task, tool: new_task, mode: gpt-oss-intake-analyzer}",
        "MATERIALIZATION_STALLED_V1",
        "never recommend `code`",
        "raw-input-materializer → gpt-oss-intake-analyzer → intake-ledger-writer → orchestrator",
        "routing_control",
        "allowed_next_modes: [gpt-oss-intake-analyzer]",
        "completion_unwind.return_to_mode: user-response-composer",
        "test-writer",
        "patch-applier",
        "new-file-writer",
        "forbidden_next_mode_classes: [implementation, test, worker]",
        "terminal forbidden modes/classes",
    ]:
        require(mode, needle)
    for forbidden in [
        "before handing off to gpt-oss-intake-analyzer",
        "every other responsibility belongs to the next mode",
    ]:
        if forbidden in (mode.get("roleDefinition", "") + "\n" + mode.get("whenToUse", "")):
            fail(f"raw-input-materializer retains direct handoff wording: {forbidden}")


def validate_external_common_contract() -> None:
    contract_path = ROOT / "docs" / "contracts" / "compact-mode-contract.md"
    global_rule_path = ROOT / "rules" / "00-agentmodes-compact-mode-contract.md"
    text = contract_path.read_text(encoding="utf-8")
    global_text = global_rule_path.read_text(encoding="utf-8")
    if text != global_text:
        fail("rules/00-agentmodes-compact-mode-contract.md must stay byte-for-byte in sync with docs/contracts/compact-mode-contract.md")
    for needle in [
        "replaces repeated fixed prompt boilerplate",
        "Do not call `run_slash_command` autonomously",
        "Do not self-dispatch with `new_task` or `switch_mode` unless the mode is an orchestrator",
        "Orchestrator delegation means creating a child task with Boomerang `new_task(mode, message)`",
        "A `switch_mode` transition can be valid as part of runtime setup",
        "DELEGATION_BLOCKED",
        "Treat post-condense summaries as advisory",
    ]:
        if needle not in text:
            fail(f"compact-mode-contract missing: {needle}")


def validate_task_packet_contract(modes: dict[str, dict]) -> None:
    contract = (ROOT / "docs" / "contracts" / "task-packet-v1.md").read_text(encoding="utf-8")
    raw_contract = (ROOT / "docs" / "contracts" / "raw-input-materialization.md").read_text(encoding="utf-8")
    for needle in [
        "escape-safe `RAW_INPUT_PAYLOAD_V1` envelope carrying the exact raw input body",
        "delimiter string that does not occur anywhere in the raw body",
        "byte count, and sha256",
        "No downstream mode may receive the raw body inline",
        "ZooCodeCustom/runtime pre-LLM materialization",
        "must never recommend or route to `code`",
        "canonical post-materialization chain",
        "routing_control",
        "return_to_mode: user-response-composer",
        "terminal_mode_must_not_be: code",
        "Current-hop allowlist",
        "test-writer",
        "patch-applier",
        "new-file-writer",
        "forbidden_next_mode_classes",
        "terminal_forbidden_modes",
        "terminal_forbidden_mode_classes",
        "handoff_status: requires_parent_dispatch",
        "workflow_complete: false",
        "next_action",
        "tool: new_task",
        "switch_mode` is not the primary intake-chain continuation primitive",
        "expected_allowed_next_modes",
        "expected_allowed_next_modes_slash_workflow",
        "routing_mode_classes",
    ]:
        if needle not in raw_contract:
            fail(f"raw-input-materialization contract missing: {needle}")
    raw_blocks = fenced_yaml_blocks(raw_contract, "raw-input-materialization contract")
    routing_control = find_yaml_mapping(raw_blocks, "routing_control", "raw-input-materialization contract")
    require_list(routing_control, "allowed_next_modes", ["gpt-oss-intake-analyzer"], "routing_control")
    require_list(routing_control, "forbidden_next_modes", ["code", "tester", "test-writer", "refactorer", "patch-applier", "new-file-writer"], "routing_control")
    require_list(routing_control, "forbidden_next_mode_classes", ["implementation", "test", "worker"], "routing_control")
    completion_unwind = routing_control.get("completion_unwind")
    if not isinstance(completion_unwind, dict):
        fail("routing_control: completion_unwind must be a mapping")
    if completion_unwind.get("return_to_mode") != "user-response-composer":
        fail("routing_control: completion_unwind.return_to_mode must be user-response-composer")
    if completion_unwind.get("policy") != "unwind_parent_chain":
        fail("routing_control: completion_unwind.policy must be unwind_parent_chain")
    require_list(completion_unwind, "terminal_forbidden_modes", ["code", "tester", "test-writer", "refactorer", "patch-applier", "new-file-writer"], "completion_unwind")
    require_list(completion_unwind, "terminal_forbidden_mode_classes", ["implementation", "test", "worker"], "completion_unwind")

    expected_allowed = find_yaml_mapping(raw_blocks, "expected_allowed_next_modes", "raw-input-materialization contract")
    expected_hops = {
        "raw-input-materializer": ["gpt-oss-intake-analyzer"],
        "gpt-oss-intake-analyzer": ["intake-ledger-writer"],
        "intake-ledger-writer": ["orchestrator"],
        "state-ledger-writer": ["orchestrator"],
    }
    for slug, expected in expected_hops.items():
        require_list(expected_allowed, slug, expected, "expected_allowed_next_modes")

    expected_slash_allowed = find_yaml_mapping(raw_blocks, "expected_allowed_next_modes_slash_workflow", "raw-input-materialization contract")
    expected_slash_hops = {
        "raw-input-materializer": ["gpt-oss-intake-analyzer"],
        "gpt-oss-intake-analyzer": ["intake-ledger-writer"],
        "intake-ledger-writer": ["workflow-orchestrator"],
        "state-ledger-writer": ["workflow-orchestrator"],
    }
    for slug, expected in expected_slash_hops.items():
        require_list(expected_slash_allowed, slug, expected, "expected_allowed_next_modes_slash_workflow")

    mode_classes = find_yaml_mapping(raw_blocks, "routing_mode_classes", "raw-input-materialization contract")
    expected_classes = {
        "code": "implementation",
        "refactorer": "implementation",
        "tester": "test",
        "test-writer": "test",
        "patch-applier": "worker",
        "new-file-writer": "worker",
    }
    for slug, expected_class in expected_classes.items():
        if mode_classes.get(slug) != expected_class:
            fail(f"routing_mode_classes: {slug} must be {expected_class}")

    for needle in [
        "Keep `new_task.message` small enough",
        "single `raw-input-materializer` subtask",
        "RAW_INPUT_PAYLOAD_V1",
        "Do not paste raw user prompts",
        "artifact paths, line ranges, hashes, issue IDs, and exact commands",
        "remaining context can carry the task evidence",
        "The next step after materialization is intake analysis, not `code`",
        "handoff_status: requires_parent_dispatch",
        "workflow_complete: false",
        "next_action: {type: new_task, tool: new_task, mode: <next-mode>}",
        "preserve `routing_control.completion_unwind`",
        "final completion must unwind to `return_to_mode: user-response-composer`",
        "allowed_next_modes` is current-hop only",
        "concrete forbidden implementation/test/worker slugs/classes",
        "terminal forbidden modes/classes",
        "Expected current-hop map:",
        "Slash workflows:",
        "active parent controller",
        "workflow-orchestrator",
        "Broad edit worker dynamic scope",
        "action_contract.allowed_file_regex",
        "files.allowlist",
        "DELEGATION_BLOCKED",
    ]:
        if needle not in contract:
            fail(f"TASK_PACKET_V1 contract missing: {needle}")
    for slug in ["orchestrator", "workflow-orchestrator"]:
        mode = modes.get(slug) or fail(f"missing {slug}")
        require(mode, "`new_task.message` stays compact")
        require(mode, "materialize context first")
        require(mode, "RAW_INPUT_PAYLOAD_V1")
        require(mode, "only allowed raw-body subtask")
        require(mode, "artifact paths or line ranges")
        if "1200" in mode_text(mode) or "target <=" in mode_text(mode):
            fail(f"{slug}: character-budget checking wording remains")

    cross_mode_needles = {
        "code": [
            "do not accept direct handoff from raw-input-materializer",
            "preserve it in your handoff unchanged",
            "never set yourself as terminal completion target",
        ],
        "intake-ledger-writer": [
            "handoff_status: requires_parent_dispatch",
            "workflow_complete: false",
            "next_action: {type: new_task, tool: new_task, mode: <active-parent-controller>}",
            "active parent controller",
            "workflow-orchestrator",
            "completion_unwind.return_to_mode: user-response-composer",
            "allowed_next_modes: [orchestrator]",
            "allowed_next_modes: [workflow-orchestrator]",
            "terminal forbidden modes/classes",
        ],
        "state-ledger-writer": [
            "handoff_status: requires_parent_dispatch",
            "workflow_complete: false",
            "next_action: {type: new_task, tool: new_task, mode: <active-parent-controller>}",
            "active parent controller",
            "workflow-orchestrator",
            "do not replace the original `return_to_mode`",
            "allowed_next_modes: [orchestrator]",
            "allowed_next_modes: [workflow-orchestrator]",
            "terminal forbidden modes/classes",
        ],
        "orchestrator": [
            "Boomerang `new_task`, setting both required parameters",
            "Do not satisfy delegation by changing your own active mode",
            "A mode switch may be part of the runtime transition",
            "If only `switch_mode` occurred",
            "DELEGATION_BLOCKED",
            "Reject or correct any handoff that jumps from intake/materialization directly to `code`",
            "Preserve `routing_control.completion_unwind`",
            "allowed_next_modes` as current-hop only",
            "terminal forbidden modes/classes",
            "broad edit workers",
            "action_contract.allowed_file_regex",
            "files.allowlist",
        ],
        "workflow-orchestrator": [
            "Boomerang `new_task`, setting both required parameters",
            "Do not satisfy delegation by changing your own active mode",
            "A mode switch may be part of the runtime transition",
            "If only `switch_mode` occurred",
            "DELEGATION_BLOCKED",
            "Reject or correct any handoff that jumps from intake/materialization directly to `code`",
            "Preserve `routing_control.completion_unwind`",
            "allowed_next_modes` as current-hop only",
            "terminal forbidden modes/classes",
            "broad edit workers",
            "action_contract.allowed_file_regex",
            "files.allowlist",
        ],
        "epoch-orchestrator": [
            "Boomerang `new_task`, setting both required parameters",
            "Do not satisfy delegation by changing your own active mode",
            "A mode switch may be part of the runtime transition",
            "If only `switch_mode` occurred",
            "DELEGATION_BLOCKED",
            "target atomic worker slug",
            "compact TASK_PACKET_V1",
            "broad edit workers",
            "action_contract.allowed_file_regex",
            "files.allowlist",
        ],
        "gpt-oss-intake-supervisor": [
            "routing_control.completion_unwind.return_to_mode",
            "runtime repair or re-materialization",
            "Do not synthesize missing routing_control",
        ],
    }
    for slug, needles in cross_mode_needles.items():
        mode = modes.get(slug) or fail(f"missing {slug}")
        for needle in needles:
            require(mode, needle)



def group_names(mode: dict) -> set[str]:
    names: set[str] = set()
    for group in mode.get("groups", []):
        if isinstance(group, str):
            names.add(group)
        elif isinstance(group, list) and group and isinstance(group[0], str):
            names.add(group[0])
    return names


def edit_file_regex(mode: dict) -> str | None:
    for group in mode.get("groups", []):
        if isinstance(group, list) and group and group[0] == "edit":
            for item in group[1:]:
                if isinstance(item, dict) and isinstance(item.get("fileRegex"), str) and item["fileRegex"].strip():
                    return item["fileRegex"]
    return None



def worker_contract(mode: dict) -> dict:
    blocks = fenced_yaml_blocks(mode_text(mode), mode.get("slug", "<unknown>"))
    return find_yaml_mapping(blocks, "worker_contract", mode.get("slug", "<unknown>"))


def validate_least_privilege_contracts(modes: dict[str, dict]) -> None:
    atomic = load_yaml(ROOT / "modes" / "atomic-workers.yaml").get("customModes", [])
    atomic_slugs = {mode.get("slug") for mode in atomic}
    edit_regex_required = {
        "test-patch-writer",
        "manifest-editor",
        "ci-workflow-writer",
        "dependency-editor",
        "artifact-materializer",
    }
    dynamic_scope_edit_allowlist = {"patch-applier", "new-file-writer"}
    command_worker_allowlist = {
        "exact-command-runner",
        "test-runner",
        "coverage-runner",
        "format-lint-runner",
        "build-runner",
        "provider-operator",
        "container-operator",
        "environment-inspector",
    }
    mcp_mutation_workers = {"issue-comment-writer", "sub-issue-creator", "issue-closer"}
    mcp_read_workers = {"issue-reader"}
    expected_required_fields = {
        "read": ["assigned_mode", "goal", "done"],
        "mcp_read": ["assigned_mode", "goal", "action_contract", "done"],
        "edit": ["assigned_mode", "goal", "files", "action_contract", "done"],
        "command": ["assigned_mode", "goal", "commands", "action_contract", "done"],
        "mcp_mutation": ["assigned_mode", "goal", "action_contract", "done"],
    }

    for mode in atomic:
        slug = mode.get("slug")
        text = mode_text(mode)
        groups = group_names(mode)
        contract = worker_contract(mode)
        if contract.get("output_contract") != "STATE_DELTA_V1" or contract.get("blocker_contract") != "BLOCKED_DELTA_V1":
            fail(f"{slug}: worker_contract must declare STATE_DELTA_V1 and BLOCKED_DELTA_V1")
        contract_class = contract.get("class")
        if contract_class in expected_required_fields and contract.get("required_packet_fields") != expected_required_fields[contract_class]:
            fail(f"{slug}: worker_contract.required_packet_fields must match {contract_class} requirements")
        for needle in ["STATE_DELTA_V1", "BLOCKED_DELTA_V1", "TASK_PACKET_V1"]:
            if needle not in text:
                fail(f"{slug}: atomic worker missing base contract text: {needle}")

        if slug in mcp_read_workers:
            if "**Atomic MCP Read Worker Kernel**" not in text:
                fail(f"{slug}: MCP read worker must use MCP read kernel")
            if contract.get("class") != "mcp_read":
                fail(f"{slug}: worker_contract.class must be mcp_read")
            if contract.get("required_action_contract_fields") != ["repository", "object_ref"]:
                fail(f"{slug}: worker_contract.required_action_contract_fields must gate MCP reads")
            for needle in ["repository", "object_ref", "MCP read scope"]:
                if needle not in text:
                    fail(f"{slug}: MCP read worker missing read gate: {needle}")
            continue

        if slug in mcp_mutation_workers:
            if contract.get("class") != "mcp_mutation":
                fail(f"{slug}: worker_contract.class must be mcp_mutation")
            required_action_fields = contract.get("required_action_contract_fields")
            if required_action_fields != ["repository", "issue_or_pr_id", "action", "idempotency_key", "payload_summary"]:
                fail(f"{slug}: worker_contract.required_action_contract_fields must gate GitHub mutations")
            if "**Atomic MCP Mutation Worker Kernel**" not in text:
                fail(f"{slug}: MCP mutation worker must use MCP mutation kernel")
            for needle in ["issue_or_pr_id", "repository", "idempotency key", "payload summary", "never infer it from prose"]:
                if needle not in text:
                    fail(f"{slug}: MCP mutation worker missing issue/PR mutation gate: {needle}")
            continue

        if "command" in groups:
            if contract.get("class") != "command" or contract.get("exact_commands_only") is not True or contract.get("cwd_scope_required") is not True:
                fail(f"{slug}: worker_contract must declare command exactness and cwd scope")
            if slug not in command_worker_allowlist:
                fail(f"{slug}: unexpected command-capable atomic worker")
            if "**Atomic Command Worker Kernel**" not in text:
                fail(f"{slug}: command worker must use command kernel")
            for needle in ["Run only exact commands listed in `commands`", "exit code", "cwd/scope", "Forbidden without explicit `action_contract`"]:
                if needle not in text:
                    fail(f"{slug}: command worker missing exact-command contract: {needle}")
            continue

        if "edit" in groups:
            if contract.get("class") != "edit" or contract.get("target_files_must_be_explicit") is not True:
                fail(f"{slug}: worker_contract must declare edit class and explicit target files")
            if slug not in edit_regex_required | dynamic_scope_edit_allowlist:
                fail(f"{slug}: edit-capable atomic worker must be audited in regex-required set or dynamic-scope allowlist")
            if "**Atomic Edit Worker Kernel**" not in text:
                fail(f"{slug}: edit worker must use edit kernel")
            if slug in edit_regex_required and not edit_file_regex(mode):
                fail(f"{slug}: edit-capable atomic worker requires fileRegex")
            if slug in dynamic_scope_edit_allowlist:
                if contract.get("dynamic_scope_required") is not True or contract.get("dynamic_scope_one_of") != ["action_contract.allowed_file_regex", "files.allowlist"]:
                    fail(f"{slug}: worker_contract must require dynamic edit scope")
                for needle in ["Dynamic scope required", "action_contract.allowed_file_regex", "files.allowlist", "do not rely on broad edit permission alone"]:
                    if needle not in text:
                        fail(f"{slug}: broad edit worker missing dynamic scope guard: {needle}")
            require(mode, "Edit only paths explicitly named in `files`")
            continue

        if contract_class not in expected_required_fields:
            fail(f"{slug}: unknown worker_contract.class {contract_class}")
        if contract.get("class") != "read" or contract.get("required_scope_one_of") != ["files", "source_of_truth", "artifact_handoff"]:
            fail(f"{slug}: worker_contract must declare read class and scope alternatives")
        if "**Atomic Read Worker Kernel**" not in text:
            fail(f"{slug}: read-only atomic worker must use read kernel")
        if "run commands" not in text or "mutate files/state" not in text:
            fail(f"{slug}: read-only worker must forbid commands and mutation")

    missing_command = command_worker_allowlist - atomic_slugs
    if missing_command:
        fail(f"command worker allowlist contains missing slugs: {sorted(missing_command)}")

    dependency_regex = edit_file_regex(modes["dependency-editor"])
    if not dependency_regex or "package\\.json" not in dependency_regex or "Cargo\\.toml" not in dependency_regex or "pyproject\\.toml" not in dependency_regex or "(^|.*/)" not in dependency_regex:
        fail("dependency-editor: fileRegex must cover dependency manifests, including nested monorepo manifests")
    ci_regex = edit_file_regex(modes["ci-workflow-writer"])
    if ci_regex != "(^\\.github/workflows/.*\\.ya?ml$)":
        fail("ci-workflow-writer: fileRegex must be limited to .github/workflows YAML")


def validate_externalized_boilerplate(modes: dict[str, dict]) -> None:
    for slug, mode in modes.items():
        text = mode_text(mode)
        for forbidden in [
            "**External Common Contract**",
            "docs/contracts/compact-mode-contract.md",
            "**Compact Fixed Prompt Contract**",
            "**Control-Plane Serialization Contract**",
            "**Slash Command Invocation Boundary**",
            "**Visible TODO Admission Contract**",
            "**Delegated Routing Boundary**",
            "**Post-Condense Rehydration Contract**",
            "run_slash_command",
            "post-condense",
        ]:
            if forbidden in text:
                fail(f"{slug}: common/global boilerplate remains inline: {forbidden}")


def validate_no_large_body_regressions(modes: dict[str, dict]) -> None:
    for path in [ROOT / "README.md", ROOT / "docs" / "contracts" / "task-packet-v1.md"]:
        text = path.read_text(encoding="utf-8")
        for forbidden_budget in ["1200 characters", "character budget", "character-count", "target <=", "must not exceed 1200"]:
            if forbidden_budget in text.lower():
                fail(f"{path.relative_to(ROOT)}: character-budget checking wording remains: {forbidden_budget}")

    forbidden = [
        "full TASK_PACKET skeleton",
        "Keep keys exactly",
        "Use `[]` or `\"\"` for unknown values",
        "paste full logs",
        "paste full diffs",
        "re-inject the entire raw artifact",
    ]
    for slug, mode in modes.items():
        text = mode_text(mode)
        for needle in forbidden:
            if needle in text:
                fail(f"{slug}: forbidden prompt-bloat wording remains: {needle}")


def validate_visible_todo_formatting_contract() -> None:
    expected = "literal `\\n` escape sequences"
    for rel in [
        "rules/00-agentmodes-compact-mode-contract.md",
        "docs/contracts/compact-mode-contract.md",
        "skills/tdd-quality-gate/SKILL.md",
    ]:
        text = (ROOT / rel).read_text(encoding="utf-8")
        if expected not in text:
            fail(f"{rel}: missing visible TODO literal newline escape guard")

    expected_japanese = "文字列 `\\n` を含めない"
    for rel in ["commands/tdd-quality-gate.md", "commands/github-issue-main-task.md"]:
        text = (ROOT / rel).read_text(encoding="utf-8")
        if expected_japanese not in text:
            fail(f"{rel}: missing visible TODO literal newline escape guard")


def validate_workflow_skill_phase_contracts() -> None:
    expected = {
        "skills/tdd-quality-gate/SKILL.md": [
            "phase_contract:",
            "workflow: tdd-quality-gate",
            "allowed_workers:",
            "required_artifacts:",
            "exit_delta:",
            "supervisor_handoff_chain:",
        ],
        "skills/github-issue-main-task/SKILL.md": [
            "phase_contract:",
            "workflow: github-issue-main-task",
            "allowed_workers:",
            "required_artifacts:",
            "exit_delta:",
            "mutation_gate:",
            "required_fields: [repository, issue_or_pr_id, action, idempotency_key, payload_summary]",
            "blocker_if_missing: BLOCKED_DELTA_V1",
        ],
    }
    for rel, needles in expected.items():
        text = (ROOT / rel).read_text(encoding="utf-8")
        blocks = fenced_yaml_blocks(text, rel)
        phase_contract = find_yaml_mapping(blocks, "phase_contract", rel)
        phases = phase_contract.get("phases")
        if not isinstance(phases, list) or not phases:
            fail(f"{rel}: phase_contract.phases must be a non-empty list")
        supervisor_handoff_chain = phase_contract.get("supervisor_handoff_chain")
        if not isinstance(supervisor_handoff_chain, list) or not supervisor_handoff_chain:
            fail(f"{rel}: phase_contract.supervisor_handoff_chain must be a non-empty list")
        known_slugs = set(collect_modes())
        unknown_handoff = [slug for slug in supervisor_handoff_chain if slug not in known_slugs]
        if "atomic worker" in supervisor_handoff_chain:
            fail(f"{rel}: supervisor_handoff_chain must not contain abstract non-slug item 'atomic worker'")
        if unknown_handoff:
            fail(f"{rel}: supervisor_handoff_chain has unknown mode slugs {unknown_handoff}")
        if phase_contract.get("worker_class_handoff") != "atomic-workers":
            fail(f"{rel}: phase_contract.worker_class_handoff must be atomic-workers")
        mutation_gate = phase_contract.get("mutation_gate")
        if rel.endswith("github-issue-main-task/SKILL.md"):
            if not isinstance(mutation_gate, dict):
                fail(f"{rel}: mutation_gate must be a mapping")
            required_fields = mutation_gate.get("required_fields")
            allowed_mutation_workers = mutation_gate.get("allowed_mutation_workers")
            if not isinstance(required_fields, list) or not required_fields:
                fail(f"{rel}: mutation_gate.required_fields must be non-empty")
            if not isinstance(allowed_mutation_workers, list) or not allowed_mutation_workers:
                fail(f"{rel}: mutation_gate.allowed_mutation_workers must be non-empty")
            unknown_mutation_workers = [worker for worker in allowed_mutation_workers if worker not in known_slugs]
            if unknown_mutation_workers:
                fail(f"{rel}: mutation_gate has unknown allowed_mutation_workers {unknown_mutation_workers}")
        for needle in needles:
            if needle not in text:
                fail(f"{rel}: missing workflow phase contract text: {needle}")
        seen_phase_ids: set[str] = set()
        for phase in phases:
            if not isinstance(phase, dict):
                fail(f"{rel}: every phase must be a mapping")
            for key in ["id", "allowed_workers", "required_artifacts", "exit_delta"]:
                if key not in phase:
                    fail(f"{rel}: phase missing {key}")
            phase_id = phase["id"]
            if not isinstance(phase_id, str) or not phase_id:
                fail(f"{rel}: phase id must be a non-empty string")
            if phase_id in seen_phase_ids:
                fail(f"{rel}: duplicate phase id {phase_id}")
            seen_phase_ids.add(phase_id)
            if not isinstance(phase["allowed_workers"], list) or not phase["allowed_workers"]:
                fail(f"{rel}: phase {phase.get('id')} allowed_workers must be non-empty")
            unknown_workers = [worker for worker in phase["allowed_workers"] if worker not in known_slugs]
            if unknown_workers:
                fail(f"{rel}: phase {phase.get('id')} has unknown allowed_workers {unknown_workers}")
            if not isinstance(phase["required_artifacts"], list) or not phase["required_artifacts"]:
                fail(f"{rel}: phase {phase.get('id')} required_artifacts must be non-empty")
            for artifact in phase["required_artifacts"]:
                if not isinstance(artifact, str) or not re.match(r"^[A-Za-z0-9_.-]+$", artifact):
                    fail(f"{rel}: phase {phase.get('id')} required_artifacts must be machine-readable identifiers")
            if not isinstance(phase["exit_delta"], str) or not re.match(r"^[A-Za-z0-9_.-]+$", phase["exit_delta"]):
                fail(f"{rel}: phase {phase.get('id')} exit_delta must be a machine-readable identifier")
            if rel.endswith("github-issue-main-task/SKILL.md") and phase_id == "mutate_github":
                required_fields = phase_contract["mutation_gate"]["required_fields"]
                missing_artifacts = [field for field in required_fields if field not in phase["required_artifacts"]]
                if missing_artifacts:
                    fail(f"{rel}: mutate_github phase missing mutation gate artifacts {missing_artifacts}")


def validate_readme() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    for needle in [
        "raw入力をartifactへ保存し、`RAW_INPUT_REF_V1`で次モードへ渡すだけ",
        "`TASK_PACKET_V1` is sparse and compact",
        "common control-plane/slash/todo/routing/post-condense boilerplate is installed as Zoo/Roo Global Rules from `rules/`",
        "docs/contracts/gpt-oss-downstream-compatible-output-policy.md",
    ]:
        if needle not in text:
            fail(f"README missing: {needle}")


def load_gpt_oss_policy_coverage() -> tuple[list[str], list[str]]:
    contract_path = ROOT / "docs" / "contracts" / "gpt-oss-downstream-compatible-output-policy.md"
    text = contract_path.read_text(encoding="utf-8")
    for needle in [
        "gpt_oss_downstream_compatible_output_policy",
        "gpt_oss_policy_coverage",
        "gpt_oss_standard_schema_map",
        "Schema field contracts",
        "downstream_must_not_reinfer: true",
    ]:
        if needle not in text:
            fail(f"{contract_path.relative_to(ROOT)} missing: {needle}")

    blocks = fenced_yaml_blocks(text, str(contract_path.relative_to(ROOT)))
    coverage = find_yaml_mapping(blocks, "gpt_oss_policy_coverage", str(contract_path.relative_to(ROOT)))
    producer_slugs = coverage.get("producer_slugs")
    consumer_slugs = coverage.get("consumer_slugs")
    if not isinstance(producer_slugs, list) or not all(isinstance(slug, str) and slug for slug in producer_slugs):
        fail("gpt_oss_policy_coverage.producer_slugs must be a non-empty list of strings")
    if not isinstance(consumer_slugs, list) or not all(isinstance(slug, str) and slug for slug in consumer_slugs):
        fail("gpt_oss_policy_coverage.consumer_slugs must be a non-empty list of strings")
    return producer_slugs, consumer_slugs


def validate_gpt_oss_downstream_policy(modes: dict[str, dict]) -> None:
    producer_slugs, consumer_slugs = load_gpt_oss_policy_coverage()
    for slug in producer_slugs:
        mode = modes.get(slug) or fail(f"missing GPT-OSS producer mode: {slug}")
        for needle in [
            "GPT-OSS Downstream-Compatible Output Policy",
            "docs/contracts/gpt-oss-downstream-compatible-output-policy.md",
            "downstream-consumable schema artifact",
            "downstream_must_not_reinfer: true",
            "downstream_should_escalate_if_fields_missing: true",
            "recommended_next_mode",
            "confidence",
        ]:
            require(mode, needle)

    for slug in consumer_slugs:
        mode = modes.get(slug) or fail(f"missing GPT-OSS consumer mode: {slug}")
        text = mode_text(mode)
        if (
            "GPT-OSS" not in text
            or "do not reinterpret" not in text
            or "docs/contracts/gpt-oss-downstream-compatible-output-policy.md" not in text
        ):
            fail(f"{slug}: missing GPT-OSS explicit-field consumption rule")


def validate_generated_count(expected: int) -> None:
    generated = load_yaml(ROOT / "all-agents.yaml")
    count = len(generated.get("customModes", []))
    if count != expected:
        fail(f"all-agents.yaml customModes count mismatch: expected {expected}, got {count}")


def main() -> None:
    modes = collect_modes()
    validate_generated_count(len(modes))
    validate_external_common_contract()
    validate_raw_input_materializer(modes)
    validate_task_packet_contract(modes)
    validate_least_privilege_contracts(modes)
    validate_externalized_boilerplate(modes)
    validate_no_large_body_regressions(modes)
    validate_visible_todo_formatting_contract()
    validate_workflow_skill_phase_contracts()
    validate_readme()
    validate_gpt_oss_downstream_policy(modes)
    print("contract validation ok")
    print(f"customModes count = {len(modes)}")


if __name__ == "__main__":
    main()
