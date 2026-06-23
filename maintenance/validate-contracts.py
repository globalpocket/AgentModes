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
        "expected current-hop map",
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
            "next_action: {type: new_task, tool: new_task, mode: orchestrator}",
            "Recommended Next Mode: orchestrator only",
            "completion_unwind.return_to_mode: user-response-composer",
            "allowed_next_modes: [orchestrator]",
            "terminal forbidden modes/classes",
        ],
        "state-ledger-writer": [
            "handoff_status: requires_parent_dispatch",
            "workflow_complete: false",
            "next_action: {type: new_task, tool: new_task, mode: orchestrator}",
            "Return Recommended Next Mode: orchestrator",
            "do not replace the original `return_to_mode`",
            "allowed_next_modes: [orchestrator]",
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

def validate_readme() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    for needle in [
        "raw入力をartifactへ保存し、`RAW_INPUT_REF_V1`で次モードへ渡すだけ",
        "`TASK_PACKET_V1` is sparse and compact",
        "common control-plane/slash/todo/routing/post-condense boilerplate is installed as Zoo/Roo Global Rules from `rules/`",
    ]:
        if needle not in text:
            fail(f"README missing: {needle}")


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
    validate_externalized_boilerplate(modes)
    validate_no_large_body_regressions(modes)
    validate_visible_todo_formatting_contract()
    validate_readme()
    print("contract validation ok")
    print(f"customModes count = {len(modes)}")


if __name__ == "__main__":
    main()
