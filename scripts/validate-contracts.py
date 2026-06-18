#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import os
import re
import shutil
import sys


def ensure_yaml():
    try:
        import yaml  # type: ignore

        return yaml
    except ModuleNotFoundError:
        if os.environ.get("AGENTMODES_UV_PYYAML") == "1":
            raise SystemExit("ERROR: PyYAML is required")
        uv = shutil.which("uv")
        if uv is None:
            raise SystemExit("ERROR: PyYAML is required and uv was not found")
        env = os.environ.copy()
        env["AGENTMODES_UV_PYYAML"] = "1"
        os.execvpe(uv, [uv, "run", "--with", "PyYAML", "python", *sys.argv], env)


yaml = ensure_yaml()

ROOT = Path(__file__).resolve().parents[1]
RULES_DIR = ROOT / "rules"
ALL_AGENTS = ROOT / "all-agents.yaml"


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def load_yaml(path: Path) -> dict:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        fail(f"YAML parse failed: {path}: {e}")
    if not isinstance(data, dict) or not isinstance(data.get("customModes"), list):
        fail(f"{path}: expected top-level mapping with customModes list")
    return data


def load_rule_modes() -> dict[str, dict]:
    modes: dict[str, dict] = {}
    for path in sorted(RULES_DIR.glob("*.yaml")):
        data = load_yaml(path)
        for mode in data["customModes"]:
            if not isinstance(mode, dict):
                fail(f"{path}: customModes entry must be mapping")
            slug = mode.get("slug")
            if not isinstance(slug, str) or not slug:
                fail(f"{path}: invalid slug")
            if slug in modes:
                fail(f"duplicate slug across rules: {slug}")
            mode["__path"] = str(path.relative_to(ROOT))
            modes[slug] = mode
    return modes


def load_all_agents_modes() -> dict[str, dict]:
    data = load_yaml(ALL_AGENTS)
    modes: dict[str, dict] = {}
    for mode in data["customModes"]:
        slug = mode.get("slug") if isinstance(mode, dict) else None
        if not isinstance(slug, str) or not slug:
            fail("all-agents.yaml: invalid slug")
        if slug in modes:
            fail(f"all-agents.yaml: duplicate slug {slug}")
        modes[slug] = mode
    return modes


def instructions(mode: dict) -> str:
    text = mode.get("customInstructions")
    if not isinstance(text, str):
        fail(f"{mode.get('slug', '<unknown>')}: customInstructions must be string")
    return text


def normalized_mode(mode: dict) -> dict:
    return {key: value for key, value in mode.items() if not key.startswith("__")}


def group_contains(value, target: str) -> bool:
    if isinstance(value, str):
        return value == target
    if isinstance(value, list):
        return any(group_contains(item, target) for item in value)
    if isinstance(value, dict):
        return any(group_contains(item, target) for item in value.values())
    return False


def metadata_text(mode: dict) -> str:
    parts = []
    for key in ("roleDefinition", "whenToUse", "description"):
        value = mode.get(key)
        if isinstance(value, str):
            parts.append(value)
    return "\n".join(parts)


def full_mode_text(mode: dict) -> str:
    return metadata_text(mode) + "\n" + instructions(mode)


def require_contains(slug: str, text: str, needle: str) -> None:
    if needle not in text:
        fail(f"{slug}: missing required contract text: {needle}")


def require_regex(slug: str, text: str, pattern: str, reason: str) -> None:
    if re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL) is None:
        fail(f"{slug}: missing {reason}")


def forbid_regex(slug: str, text: str, pattern: str, reason: str) -> None:
    if re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL):
        fail(f"{slug}: forbidden {reason}")


def validate_tester(modes: dict[str, dict]) -> None:
    text = instructions(modes["tester"])
    require_contains("tester", text, "Tester Artifact Materialization Authority exception")
    require_contains("tester", text, "execute_command` is an artifact materialization authority")
    require_contains("tester", text, "Artifact Status: not written / not verified")
    require_regex("tester", text, r"allowed_actions[^\n]+execute_command", "execute_command allowed_actions authority rule")
    require_regex("tester", text, r"artifact_path[^\n]+canonical[^\n]+artifacts/", "canonical artifacts path rule")
    require_regex("tester", text, r"tee|redirection", "tee or redirection artifact write rule")
    require_regex("tester", text, r"pipefail|exit status", "pipefail or exit-status preservation rule")
    require_regex("tester", text, r"exactly once|without rerun", "single execution rule")


def validate_orchestrator(modes: dict[str, dict]) -> None:
    text = instructions(modes["orchestrator"])
    require_contains("orchestrator", text, "Tester Artifact Materialization Authority exception")
    require_contains("orchestrator", text, "Tester artifact authority")
    require_regex(
        "orchestrator",
        text,
        r"Tester artifact authority:.*?assigned_mode=tester.*?allowed_actions=\[execute_command\].*?do not classify `?artifact_permission_conflict`?",
        "Scenario A tester exception example",
    )
    require_contains("orchestrator", text, "doc-evidence-reader first, then analyzer, then librarian")
    require_contains("orchestrator", text, "Do not send standalone documentation presence inspection to Documenter")
    if "README or docs presence checks go to doc-evidence-reader, librarian, analyzer, or documenter" in text:
        fail("orchestrator: forbidden Documenter in standalone README/docs presence routing")


def task_packet_modes(modes: dict[str, dict]) -> dict[str, dict]:
    return {
        slug: mode
        for slug, mode in modes.items()
        if "**TASK_PACKET_V1 Reception Contract**" in instructions(mode)
    }


def validate_scoped_todo_compatibility(modes: dict[str, dict]) -> None:
    for slug, mode in task_packet_modes(modes).items():
        if slug == "orchestrator":
            continue
        text = instructions(mode)
        require_contains(slug, text, "**Zoo/Roo Hard Completion Gate Compatibility**")
        require_contains(slug, text, "exactly one scoped item")
        require_contains(slug, text, "Never call `attempt_completion` while any visible todo is Pending or In Progress")
        require_contains(slug, text, "Call `attempt_completion` exactly once")
        require_contains(slug, text, "do not call `update_todo_list` again")
        require_regex(slug, text, r"Never use `\[-\]`", "no in-progress todo marker rule")

    orch_text = instructions(modes["orchestrator"])
    require_contains("orchestrator", orch_text, "**Scoped TODO Projection Protocol**")
    require_contains("orchestrator", orch_text, "hard Zoo/Roo runtime completion gate")
    require_contains("orchestrator", orch_text, "exactly one pending item")
    require_regex(
        "orchestrator",
        orch_text,
        r"Do not store the full parent workflow plan in the visible todo list",
        "parent workflow plan visible todo prohibition",
    )


def validate_librarian(modes: dict[str, dict]) -> None:
    mode = modes["librarian"]
    groups = mode.get("groups")
    if groups != ["read"]:
        fail(f"librarian: groups must be ['read'], got {groups!r}")
    if group_contains(groups, "command"):
        fail("librarian: command group is forbidden")
    if group_contains(groups, "edit"):
        fail("librarian: edit group is forbidden")

    text = instructions(mode)
    require_contains("librarian", text, "**Librarian TASK_PACKET Preflight**")
    require_contains("librarian", text, "Reject when `artifact_handoff.required` is true")
    require_contains("librarian", text, "Reject when `allowed_actions` includes `execute_command`")
    require_regex("librarian", text, r"falls outside `files\.read_scope`", "scope conflict rejection")
    require_regex("librarian", text, r"max_lines.*less than.*required_sections", "max_lines required_sections validation")
    require_contains("librarian", text, "Do not call `execute_command`.")
    require_regex("librarian", text, r"Do not create directories or files|Do not use shell redirection", "filesystem mutation prohibition")
    require_contains("librarian", text, "**Evidence and Count Integrity**")
    require_contains("librarian", text, "Do not infer a source file's responsibility from its filename alone.")
    require_contains("librarian", text, "A search for `#[test]` alone is not a complete Rust test inventory")
    require_contains("librarian", text, "Every reported file count must equal the number of files actually listed in the same result.")


def validate_orchestrator_packet_preflight(modes: dict[str, dict]) -> None:
    text = instructions(modes["orchestrator"])
    require_contains("orchestrator", text, "**TASK_PACKET Preflight Gate**")
    require_contains("orchestrator", text, "Librarian packets must always use `artifact_handoff.required: false`.")
    require_contains("orchestrator", text, "Librarian packets must not include `execute_command` in `allowed_actions`.")
    require_contains("orchestrator", text, "Scope coverage check")
    require_regex("orchestrator", text, r"max_lines.*greater than or equal to.*required_sections", "max_lines >= required_sections count rule")
    require_regex("orchestrator", text, r"understand a file's structure or responsibility.*authorize reading", "semantic source read evidence rule")
    require_contains("orchestrator", text, "Librarian packet conflict")


def validate_artifact_wording(modes: dict[str, dict]) -> None:
    old = "When `artifact_handoff.paths` is provided, store or reference logs"
    new = "Read-only modes must not create, prepare, touch, redirect output to, or populate those paths"
    for slug, mode in task_packet_modes(modes).items():
        text = instructions(mode)
        if old in text:
            fail(f"{slug}: old ambiguous artifact wording remains")
        if new in text:
            continue
        require_regex(
            slug,
            text,
            r"artifact_handoff\.required.*?read-only.*?Do not create files|artifact_handoff\.paths.*?reference provided artifacts only by path",
            "read-only artifact path non-write condition",
        )


def validate_user_response_composer(modes: dict[str, dict]) -> None:
    mode = modes["user-response-composer"]
    if mode.get("groups") != []:
        fail("user-response-composer: groups must be []")
    text = instructions(mode)
    require_contains("user-response-composer", text, "COMPOSER_BLOCKED: inspection_required")
    require_contains("user-response-composer", text, "Recommended Next Mode: orchestrator")
    require_contains("user-response-composer", text, "Do not inspect, self-dispatch, or invent facts")
    forbid_regex("user-response-composer", text, r"Inspect it yourself|perform the inspection|read/search|run the specified command|use list/search/read", "direct inspection instruction")


def validate_ask(modes: dict[str, dict]) -> None:
    text = instructions(modes["ask"])
    require_contains("ask", text, "Recommended Next Mode")
    require_contains("ask", text, "to Orchestrator")
    require_contains("ask", text, "do not perform the transition")
    require_contains("ask", text, "self-dispatch")
    forbid_regex("ask", text, r"route to the smallest responsible mode", "self-dispatch routing wording")


def validate_documenter(modes: dict[str, dict]) -> None:
    text = instructions(modes["documenter"])
    require_contains("documenter", text, "Failure Summary: DOC_FACTS_V1 missing or insufficient")
    require_contains("documenter", text, "Recommended Next Mode: doc-evidence-reader")
    require_contains("documenter", text, "read only the existing assigned Markdown targets")
    require_contains("documenter", text, "Do not perform standalone presence checks")
    require_contains("documenter", text, "Do not discover documentation destinations")


def validate_mode_metadata(modes: dict[str, dict]) -> None:
    gpt = modes["gpt-oss-needs-analyzer"]
    gpt_description = gpt.get("description")
    if gpt_description != "GPT-OSS分析とOrchestrator向けbrief作成":
        fail("gpt-oss-needs-analyzer: description must match advisory brief contract")
    if "起動" in gpt_description:
        fail("gpt-oss-needs-analyzer: description must not imply Orchestrator launch")
    if gpt.get("groups") != []:
        fail("gpt-oss-needs-analyzer: groups must be []")

    gpt_text = full_mode_text(gpt)
    require_contains("gpt-oss-needs-analyzer", gpt_text, "Recommended Next Mode: orchestrator")
    require_regex(
        "gpt-oss-needs-analyzer",
        gpt.get("roleDefinition", "") + "\n" + instructions(gpt),
        r"without dispatching|No runtime dispatch|do not .*dispatch",
        "explicit no-dispatch contract",
    )
    require_regex(
        "gpt-oss-needs-analyzer",
        instructions(gpt),
        r"Do not .*invoke .*Orchestrator|advisory handoff only",
        "no Orchestrator invocation contract",
    )
    forbid_regex(
        "gpt-oss-needs-analyzer",
        metadata_text(gpt),
        r"Orchestrator起動|dispatch Orchestrator|invoke Orchestrator|call Orchestrator",
        "direct Orchestrator launch metadata",
    )

    ask = modes["ask"]
    if group_contains(ask.get("groups", []), "edit"):
        fail("ask: edit permission is forbidden")
    ask_role = ask.get("roleDefinition")
    if not isinstance(ask_role, str):
        fail("ask: roleDefinition must be string")
    if "read-only" not in ask_role.lower():
        fail("ask: roleDefinition must include read-only")
    if "unless explicitly requested" in ask_role.lower():
        fail("ask: roleDefinition must not include unless explicitly requested")
    ask_text = instructions(ask)
    require_contains("ask", ask_text, "Read-only technical consultation mode. Do not modify files.")
    require_contains("ask", ask_text, "Recommended Next Mode")
    require_regex(
        "ask",
        ask_text,
        r"do not perform the transition|do not transition modes directly",
        "direct transition prohibition",
    )
    require_regex(
        "ask",
        ask_text,
        r"self-dispatch|call `new_task`|switch modes yourself",
        "self-dispatch prohibition",
    )
    forbid_regex(
        "ask",
        ask_role + "\n" + ask_text,
        r"without modifying files unless explicitly requested|Do not modify files unless|unless explicitly requested",
        "edit-on-request wording",
    )


def validate_no_tool_modes(modes: dict[str, dict]) -> None:
    forbidden = re.compile(
        r"Inspect it yourself|Before asking, perform|read/search both|use list/search/read|run the specified command|"
        r"perform the inspection|call `new_task`|call new_task|switch modes yourself",
        flags=re.IGNORECASE,
    )
    metadata_forbidden = re.compile(
        r"Orchestrator起動|dispatch Orchestrator|invoke Orchestrator|call Orchestrator|"
        r"read files directly|run commands directly|inspect workspace directly|workspace inspection authority",
        flags=re.IGNORECASE,
    )
    for slug, mode in modes.items():
        if mode.get("groups") != []:
            continue
        meta = metadata_text(mode)
        if slug == "orchestrator":
            # Orchestrator may explicitly delegate but must not inspect directly.
            text = instructions(mode)
            if re.search(r"inspect workspace (state )?directly|workspace inspection authority", meta, flags=re.IGNORECASE):
                fail(f"{slug}: no-tool metadata promises direct workspace inspection")
            require_contains(slug, text, "This mode does not inspect workspace state directly")
            require_contains(slug, text, "delegate to the least-privilege inspection-capable mode")
            continue
        if metadata_forbidden.search(meta):
            fail(f"{slug}: no-tool metadata contains direct tool, inspection, or dispatch wording")
        text = instructions(mode)
        if forbidden.search(text):
            fail(f"{slug}: no-tool mode contains direct inspection or self-dispatch wording")
        require_regex(slug, text, r"no-tool|no workspace inspection authority|cannot inspect workspace", "no-tool workspace inspection boundary")
        require_regex(slug, text, r"Recommended Next Mode|Orchestrator|ORCHESTRATOR_BRIEF_V1", "Orchestrator handoff or recommendation")
        require_regex(slug, text, r"Do not ask the user|must never ask the user", "no user questions for workspace facts")


def validate_sync(rule_modes: dict[str, dict], all_modes: dict[str, dict]) -> None:
    if len(rule_modes) != len(all_modes):
        fail(f"mode count mismatch: rules={len(rule_modes)} all-agents={len(all_modes)}")
    if set(rule_modes) != set(all_modes):
        missing = sorted(set(rule_modes) ^ set(all_modes))
        fail(f"slug mismatch between rules and all-agents: {missing}")
    for slug, rule_mode in rule_modes.items():
        expected = normalized_mode(rule_mode)
        actual = normalized_mode(all_modes[slug])

        if expected != actual:
            differing_keys = sorted(
                key
                for key in set(expected) | set(actual)
                if expected.get(key) != actual.get(key)
            )
            fail(
                f"all-agents.yaml not synchronized for {slug}: "
                f"{', '.join(differing_keys)}"
            )


def validate_scenarios(modes: dict[str, dict]) -> None:
    tester_text = instructions(modes["tester"])
    orchestrator_text = instructions(modes["orchestrator"])
    for text, slug in ((tester_text, "tester"), (orchestrator_text, "orchestrator")):
        require_contains(slug, text, "cargo test 2>&1 | tee artifacts/test-results/test.txt" if slug == "orchestrator" else "execute_command` is an artifact materialization authority")
    composer_text = instructions(modes["user-response-composer"])
    require_contains("user-response-composer", composer_text, "COMPOSER_BLOCKED: inspection_required")
    ask_text = instructions(modes["ask"])
    require_regex("ask", ask_text, r"Recommended Next Mode.*?Orchestrator", "Scenario C Ask recommendation")
    doc_text = instructions(modes["orchestrator"])
    require_regex("orchestrator", doc_text, r"doc-evidence-reader first, then analyzer, then librarian", "Scenario D documentation presence routing")


def main() -> None:
    rule_modes = load_rule_modes()
    all_modes = load_all_agents_modes()
    for slug in [
        "tester",
        "orchestrator",
        "user-response-composer",
        "ask",
        "documenter",
        "gpt-oss-needs-analyzer",
    ]:
        if slug not in rule_modes:
            fail(f"missing required mode: {slug}")

    validate_tester(rule_modes)
    validate_orchestrator(rule_modes)
    validate_scoped_todo_compatibility(rule_modes)
    validate_librarian(rule_modes)
    validate_orchestrator_packet_preflight(rule_modes)
    validate_artifact_wording(rule_modes)
    validate_user_response_composer(rule_modes)
    validate_ask(rule_modes)
    validate_documenter(rule_modes)
    validate_no_tool_modes(rule_modes)
    validate_sync(rule_modes, all_modes)
    validate_mode_metadata(rule_modes)
    validate_scenarios(rule_modes)

    print("contract validation ok")
    print(f"customModes count = {len(rule_modes)}")
    print("no-tool modes = " + ", ".join(sorted(slug for slug, mode in rule_modes.items() if mode.get("groups") == [])))


if __name__ == "__main__":
    main()
