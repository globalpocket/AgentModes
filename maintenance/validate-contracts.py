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

ORCHESTRATOR_NO_TOOL_MODES = {
    "orchestrator",
    "workflow-orchestrator",
}

TERMINAL_NO_TOOL_MODES = {
    "user-response-composer",
    "gpt-oss-needs-analyzer",
}


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


def validate_no_tool_classification(modes: dict[str, dict]) -> None:
    actual = {
        slug
        for slug, mode in modes.items()
        if mode.get("groups") == []
    }
    expected = ORCHESTRATOR_NO_TOOL_MODES | TERMINAL_NO_TOOL_MODES

    if actual != expected:
        fail(
            "unclassified no-tool modes: "
            f"actual={sorted(actual)!r} expected={sorted(expected)!r}"
        )


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
    require_contains(
        "orchestrator",
        text,
        "exactly one ownership marker in `context_delta.facts`: "
        "`owning_orchestrator: orchestrator`",
    )
    require_contains(
        "orchestrator",
        text,
        "Other verified factual entries may coexist in "
        "`context_delta.facts`",
    )
    require_contains(
        "orchestrator",
        text,
        "the exactly-one restriction applies only to ownership markers, "
        "not to the total number of facts",
    )
    require_contains(
        "orchestrator",
        text,
        "Do not include `owning_orchestrator: workflow-orchestrator`",
    )

    if (
        "must include exactly one fact in `context_delta.facts`"
        in text
    ):
        fail(
            "orchestrator: ownership wording incorrectly limits the "
            "entire facts collection to one entry"
        )
    require_contains(
        "orchestrator",
        text,
        "Do not route a regular-Orchestrator composition failure "
        "to `workflow-orchestrator`",
    )
    require_contains(
        "orchestrator",
        text,
        "Do not create a wrapper `new_task` targeting `orchestrator`",
    )
    require_contains(
        "orchestrator",
        text,
        "**Workflow Isolation Boundary**",
    )
    require_contains(
        "orchestrator",
        text,
        "Regular Orchestrator must not load `orchestrator-workflows`",
    )
    require_contains("orchestrator", text, "**Explicit First-Step Fidelity**")
    require_contains("orchestrator", text, "**Large Task Admission Control**")
    if "**SoD Workflow**" in text:
        fail("orchestrator: duplicated SoD Workflow phase list remains")
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


def validate_workflow_orchestrator(modes: dict[str, dict]) -> None:
    mode = modes.get("workflow-orchestrator")
    if mode is None:
        fail("workflow-orchestrator: missing required mode")
    if mode.get("groups") != []:
        fail("workflow-orchestrator: groups must be []")
    text = instructions(mode)
    for needle in [
        "**Workflow Invocation Gate**",
        "**Workflow Skill Entry**",
        "Workflow Invocation Required",
        "The `skill` call must be the only tool call in that assistant message.",
        "**Workflow Completion**",
        "**Provider Recovery Coordination**",
        "**Large Task Admission Control**",
        "**Internal Routing Contract**",
        "Do not create a wrapper `new_task` targeting `orchestrator`",
        "Do not call `new_task` targeting `workflow-orchestrator` or `orchestrator`",
        "Code granularity check",
        "Responsibility check",
        "state-rehydrate",
    ]:
        require_contains("workflow-orchestrator", text, needle)
    require_contains(
        "workflow-orchestrator",
        text,
        "exactly one ownership marker in `context_delta.facts`: "
        "`owning_orchestrator: workflow-orchestrator`",
    )
    require_contains(
        "workflow-orchestrator",
        text,
        "Other verified factual entries may coexist in "
        "`context_delta.facts`",
    )
    require_contains(
        "workflow-orchestrator",
        text,
        "the exactly-one restriction applies only to ownership markers, "
        "not to the total number of facts",
    )
    require_contains(
        "workflow-orchestrator",
        text,
        "Do not include `owning_orchestrator: orchestrator`",
    )

    if (
        "must include exactly one fact in `context_delta.facts`"
        in text
    ):
        fail(
            "workflow-orchestrator: ownership wording incorrectly "
            "limits the entire facts collection to one entry"
        )
    require_contains(
        "workflow-orchestrator",
        text,
        "Do not fall back to regular `orchestrator`",
    )
    forbid_regex(
        "workflow-orchestrator",
        text,
        r"## Workflow: tdd-quality-gate|## Workflow: github-issue-main-task|### Phase: red-write",
        "duplicated workflow phase list in mode prompt",
    )


def validate_control_plane_serialization(modes: dict[str, dict]) -> None:
    for slug, mode in modes.items():
        text = instructions(mode)
        if slug in TERMINAL_NO_TOOL_MODES:
            require_contains(slug, text, "**No-Tool Control Boundary**")
            require_contains(slug, text, "This mode must not call any tool.")
            require_regex(
                slug,
                text,
                r"Do not call `skill`.*`run_slash_command`.*`update_todo_list`.*`new_task`.*`switch_mode`.*`attempt_completion`",
                "no-tool control-plane prohibition",
            )
            if "**Control-Plane Serialization Contract**" in text:
                fail(f"{slug}: terminal no-tool mode must not include Control-Plane Serialization Contract")
            continue
        require_contains(slug, text, "**Control-Plane Serialization Contract**")
        require_contains(slug, text, "Emit at most one control-plane tool call in one assistant message.")
        require_contains(slug, text, "A `skill` call must be the only tool call in that message.")
        require_contains(slug, text, "Ordinary workspace tools such as read, search, edit, or command execution must not be emitted in the same message as a control-plane tool.")


def validate_slash_command_boundary(modes: dict[str, dict]) -> None:
    stale_permissive_phrases = [
        "Slash commands may run only when",
        "/init is allowed only when",
        "/analysys is allowed only when",
        "unless the raw user prompt explicitly requested the corresponding command purpose",
        "unless the raw user prompt explicitly runs a slash command",
    ]
    for slug, mode in modes.items():
        text = instructions(mode)
        require_contains(slug, text, "**Slash Command Invocation Boundary**")
        require_contains(slug, text, "Never call `run_slash_command` autonomously.")
        require_contains(slug, text, "Shell commands belong in a Tester or other explicitly command-capable TASK_PACKET.")
        require_contains(slug, text, "Missing or unrelated Slash Commands are not Provider Health Failures.")
        for phrase in stale_permissive_phrases:
            if phrase in text:
                fail(f"{slug}: stale permissive slash-command wording: {phrase}")


def validate_internal_routing(modes: dict[str, dict]) -> None:
    for slug in ("orchestrator", "workflow-orchestrator"):
        text = instructions(modes[slug])
        require_contains(slug, text, "**Internal Routing Contract**")
        require_contains(slug, text, "Delegate specialist work only with `new_task`.")
        require_contains(slug, text, "Never call `switch_mode` for internal work.")
        require_contains(slug, text, "Do not create a wrapper `new_task` targeting `orchestrator`.")
    for slug, mode in modes.items():
        if slug in ORCHESTRATOR_NO_TOOL_MODES:
            continue
        text = instructions(mode)
        require_contains(slug, text, "**Delegated Routing Boundary**")
        require_contains(slug, text, "Never call `new_task`.")
        require_contains(slug, text, "Never call `switch_mode`.")
        require_contains(slug, text, "Never invoke another mode directly.")
        require_contains(slug, text, "Recommended Next Mode")


def validate_visible_todo_admission(modes: dict[str, dict]) -> None:
    for slug, mode in modes.items():
        text = instructions(mode)
        if slug in TERMINAL_NO_TOOL_MODES:
            require_contains(slug, text, "**No-Tool TODO Boundary**")
            require_contains(slug, text, "Do not call `update_todo_list`.")
            if "**Visible TODO Admission Contract**" in text:
                fail(f"{slug}: terminal no-tool mode must not include Visible TODO Admission Contract")
            continue
        require_contains(slug, text, "**Visible TODO Admission Contract**")
        require_contains(slug, text, "The first `update_todo_list` call in a task must contain exactly one item.")
        require_contains(slug, text, "Never place the full project plan, all workflow phases, all user headings, or future-mode work in visible REMINDERS.")
        require_contains(slug, text, "Never encode multiple todos inside one todo body")


def validate_command_group_policy(modes: dict[str, dict]) -> None:
    allowed = {"artifact-manager", "tester", "segregated-devops", "release-manager", "security-auditor"}
    actual = {slug for slug, mode in modes.items() if group_contains(mode.get("groups", []), "command")}
    if actual != allowed:
        fail(f"command group modes must be exactly {sorted(allowed)!r}, got {sorted(actual)!r}")
    if modes["code"].get("groups") != ["read", "edit", "mcp"]:
        fail(f"code: groups must be ['read', 'edit', 'mcp'], got {modes['code'].get('groups')!r}")
    if modes["diagnostic-reporter"].get("groups") != ["read", "mcp"]:
        fail("diagnostic-reporter: groups must be ['read', 'mcp']")


def validate_patch_recovery_skill(modes: dict[str, dict]) -> None:
    path = ROOT / "skills" / "apply-diff-recovery" / "SKILL.md"
    require_file(path)
    data = markdown_frontmatter(path)
    if data.get("name") != "apply-diff-recovery":
        fail("apply-diff-recovery: frontmatter name must be 'apply-diff-recovery'")
    expected_slugs = {"code", "debug", "refactorer", "test-writer"}
    if set(data.get("modeSlugs") or []) != expected_slugs:
        fail("apply-diff-recovery: modeSlugs must be exactly ['code', 'debug', 'refactorer', 'test-writer']")
    skill_text = path.read_text(encoding="utf-8")
    for needle in [
        "`-------` must be on its own line",
        "Retry `apply_diff` at most once",
        "`patch_application_failed`",
        "Do not invent helper methods",
        "read_file",
    ]:
        if needle not in skill_text:
            fail(f"apply-diff-recovery: missing required text: {needle}")
    for slug in ["code", "debug", "refactorer", "test-writer"]:
        text = instructions(modes[slug])
        require_contains(slug, text, "**Patch Application Contract**")
        require_contains(slug, text, "Before the first `apply_diff`, load `apply-diff-recovery`")
        require_contains(slug, text, "Do not call `execute_command`.")


def validate_post_condense_rehydration(modes: dict[str, dict]) -> None:
    for slug, mode in modes.items():
        text = instructions(mode)
        if slug in ORCHESTRATOR_NO_TOOL_MODES:
            require_contains(slug, text, "**Orchestrated Post-Condense Rehydration Contract**")
            require_contains(slug, text, "no direct workspace inspection authority")
            require_contains(slug, text, "[ ] state-rehydrate:")
            require_contains(slug, text, "`update_todo_list` call must be the only control-plane call")
            require_contains(slug, text, "delegate exactly one `state-rehydrate` task with `new_task`")
            require_contains(slug, text, "`new_task` call must be the only control-plane call")
            require_contains(slug, text, "Wait for the rehydration handoff")
            for forbidden in [
                "**Post-Condense Rehydration Contract**",
                "**No-Tool Post-Condense Boundary**",
            ]:
                if forbidden in text:
                    fail(f"{slug}: forbidden post-condense contract text remains: {forbidden}")
            continue
        if slug in TERMINAL_NO_TOOL_MODES:
            require_contains(slug, text, "**No-Tool Post-Condense Boundary**")
            require_contains(slug, text, "cannot rehydrate workspace state directly")
            require_regex(slug, text, r"Do not read, search, execute, inspect", "terminal no-tool inspection prohibition")
            for forbidden in [
                "**Post-Condense Rehydration Contract**",
                "**Orchestrated Post-Condense Rehydration Contract**",
                "Re-establish current truth from current workspace files",
            ]:
                if forbidden in text:
                    fail(f"{slug}: forbidden post-condense contract text remains: {forbidden}")
            if slug == "user-response-composer":
                require_contains(slug, text, "COMPOSER_BLOCKED: inspection_required")
                require_contains(slug, text, "Missing Facts")
                require_contains(slug, text, "Recommended Next Mode: orchestrator")
            if slug == "gpt-oss-needs-analyzer":
                require_contains(slug, text, "blocked_by_permission")
                require_contains(slug, text, "analysis_confidence: unavailable")
                require_contains(slug, text, "ORCHESTRATOR_BRIEF_V1")
                require_contains(slug, text, "Recommended Next Mode: orchestrator")
            continue
        require_contains(slug, text, "**Post-Condense Rehydration Contract**")
        require_contains(slug, text, "Conversation summaries, condensed context, and REMINDERS are advisory coordination state, not workspace evidence.")
        require_contains(slug, text, "Do not reuse stale line numbers")


def validate_terminal_no_tool_stop_conditions(
    modes: dict[str, dict],
) -> None:
    forbidden_phrases = [
        "**Loop Guard and Stop Conditions**",
        "**Output Discipline**",
        "If an `update_todo_list` payload is identical",
        "split it into separate todos",
        "Do not continue monitoring loops with",
        "same failure fingerprint",
        "proceed with a concrete non-todo action",
        "Do not retry a failed `attempt_completion` with the same content",
        "Use concise fixed sections requested by `output_contract`",
    ]

    for slug in TERMINAL_NO_TOOL_MODES:
        text = instructions(modes[slug])

        require_contains(
            slug,
            text,
            "**No-Tool Stop Conditions**",
        )
        require_contains(
            slug,
            text,
            "Do not inspect workspace state, repair todos, invoke tools",
        )

        for phrase in forbidden_phrases:
            if phrase in text:
                fail(
                    f"{slug}: stale operational no-tool wording remains: "
                    f"{phrase}"
                )


def validate_explicit_first_step(modes: dict[str, dict]) -> None:
    text = instructions(modes["orchestrator"])
    require_contains("orchestrator", text, "**Explicit First-Step Fidelity**")
    require_contains("orchestrator", text, "Exact shell commands are routed to Tester, never to Slash Commands.")
    require_contains("orchestrator", text, "Do not substitute a semantically related Skill, Slash Command, or exploratory task for the explicit first step.")


def validate_large_task_admission(modes: dict[str, dict]) -> None:
    for slug in ("orchestrator", "workflow-orchestrator"):
        text = instructions(modes[slug])
        require_contains(slug, text, "**Large Task Admission Control**")
        require_contains(slug, text, "One Code task owns exactly one implementation invariant")
        require_contains(slug, text, "`files.edit_files` for Code must contain no more than three files.")
        require_contains(slug, text, "Code granularity check")
        require_contains(slug, text, "Responsibility check")


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
        require_contains(
            slug,
            text,
            "Terminal local outcomes are `completed`, `failed`, `task_packet_conflict`, `blocked_by_permission`, and `not_found_after_inspection`.",
        )
        require_contains(
            slug,
            text,
            "never label a failed command, unsatisfied `done` condition, or failed required action as `completed`",
        )
        if (
            "Terminal local outcomes are `completed`, `task_packet_conflict`, "
            "`blocked_by_permission`, and `not_found_after_inspection`."
            in text
        ):
            fail(f"{slug}: terminal outcomes do not include failed")
        require_regex(slug, text, r"Never use `\[-\]`", "no in-progress todo marker rule")

    orch_text = instructions(modes["orchestrator"])
    require_contains("orchestrator", orch_text, "**Scoped TODO Projection Protocol**")
    require_contains("orchestrator", orch_text, "hard Zoo/Roo runtime completion gate")
    require_contains("orchestrator", orch_text, "exactly one pending item")
    require_contains("orchestrator", orch_text, "[x] workflow: completed")
    require_contains("orchestrator", orch_text, "[x] workflow: failed")
    require_contains("orchestrator", orch_text, "when no next task remains")
    require_contains("orchestrator", orch_text, "do not create a synthetic pending task")
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
    require_contains(
        "librarian",
        text,
        "The normal three-candidate limit applies only to target discovery.",
    )
    require_contains(
        "librarian",
        text,
        "complete directory, crate, source-file, documentation-file, or test-file inventory",
    )
    forbid_regex(
        "librarian",
        text,
        r"Search, read, and command operations",
        "command operation wording",
    )
    forbid_regex(
        "librarian",
        text,
        r"list/search/read/command exploration",
        "command exploration wording",
    )
    forbid_regex(
        "librarian",
        text,
        r"Reference commands are limited",
        "reference command permission wording",
    )
    require_contains(
        "librarian",
        text,
        "Search and read operations must stay inside the current workspace",
    )
    require_contains(
        "librarian",
        text,
        "use Codebase Index before list/search/read exploration",
    )
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
    require_contains("user-response-composer", text, "**No-Tool Control Boundary**")
    require_contains("user-response-composer", text, "**No-Tool TODO Boundary**")
    require_contains("user-response-composer", text, "**No-Tool Post-Condense Boundary**")
    require_contains("user-response-composer", text, "COMPOSER_BLOCKED: inspection_required")
    require_contains("user-response-composer", text, "Recommended Next Mode: orchestrator")
    require_contains("user-response-composer", text, "Do not inspect, self-dispatch, or invent facts")
    require_contains(
        "user-response-composer",
        text,
        "owning_orchestrator: orchestrator",
    )
    require_contains(
        "user-response-composer",
        text,
        "owning_orchestrator: workflow-orchestrator",
    )
    require_contains(
        "user-response-composer",
        text,
        "owner-aware `Recommended Next Mode`",
    )
    require_contains(
        "user-response-composer",
        text,
        "Never output the literal placeholder `<owning_orchestrator>`",
    )
    require_contains(
        "user-response-composer",
        text,
        "exactly one ownership marker, not exactly one total fact",
    )
    require_contains(
        "user-response-composer",
        text,
        "Other verified factual entries may coexist in "
        "`context_delta.facts`",
    )
    require_contains(
        "user-response-composer",
        text,
        "both valid markers appearing together",
    )
    require_contains(
        "user-response-composer",
        text,
        "any unknown `owning_orchestrator` value",
    )

    stale_ownership_input = (
        "Require exactly one ownership fact in "
        "`context_delta.facts`"
    )
    if stale_ownership_input in text:
        fail(
            "user-response-composer: ambiguous ownership input wording "
            "remains"
        )

    stale_total_fact_wording = (
        "must include exactly one fact in `context_delta.facts`"
    )

    for owner_slug in ("orchestrator", "workflow-orchestrator"):
        owner_text = instructions(modes[owner_slug])
        if stale_total_fact_wording in owner_text:
            fail(
                f"{owner_slug}: stale total-fact ownership wording remains"
            )
    require_contains(
        "user-response-composer",
        text,
        "**No-Tool Stop Conditions**",
    )
    stale_fixed_composer_lines = [
        (
            "return `COMPOSER_BLOCKED: inspection_required` to Orchestrator"
        ),
        (
            "return only: `COMPOSER_BLOCKED: inspection_required`, "
            "`Missing Facts`, and `Recommended Next Mode: orchestrator`"
        ),
    ]

    for phrase in stale_fixed_composer_lines:
        if phrase in text:
            fail(
                "user-response-composer: "
                f"stale fixed Orchestrator return remains: {phrase}"
            )
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
    gpt_instructions = instructions(gpt)
    require_contains("gpt-oss-needs-analyzer", gpt_instructions, "**No-Tool Control Boundary**")
    require_contains("gpt-oss-needs-analyzer", gpt_instructions, "**No-Tool TODO Boundary**")
    require_contains("gpt-oss-needs-analyzer", gpt_instructions, "**No-Tool Post-Condense Boundary**")
    require_contains(
        "gpt-oss-needs-analyzer",
        gpt_instructions,
        "The user question budget is zero.",
    )
    require_contains(
        "gpt-oss-needs-analyzer",
        gpt_instructions,
        "Never ask the user a clarification question",
    )
    require_contains(
        "gpt-oss-needs-analyzer",
        gpt_instructions,
        "Do not call `ask_followup_question`.",
    )
    require_contains(
        "gpt-oss-needs-analyzer",
        gpt_instructions,
        "**No-Tool Stop Conditions**",
    )

    if "Ask only when the raw prompt cannot be understood" in gpt_instructions:
        fail(
            "gpt-oss-needs-analyzer: "
            "stale clarification permission remains"
        )
    require_contains("gpt-oss-needs-analyzer", gpt_instructions, "analysis_confidence: unavailable")
    require_contains("gpt-oss-needs-analyzer", gpt_text, "Recommended Next Mode: orchestrator")
    require_regex(
        "gpt-oss-needs-analyzer",
        gpt.get("roleDefinition", "") + "\n" + gpt_instructions,
        r"without dispatching|No runtime dispatch|do not .*dispatch",
        "explicit no-dispatch contract",
    )
    require_regex(
        "gpt-oss-needs-analyzer",
        gpt_instructions,
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
        r"perform the inspection|switch modes yourself",
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
        if slug in {"orchestrator", "workflow-orchestrator"}:
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


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def require_file(path: Path) -> None:
    if not path.is_file():
        fail(f"required runtime file missing: {relative(path)}")


def markdown_frontmatter(path: Path) -> dict:
    require_file(path)
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        fail(f"{relative(path)} missing YAML frontmatter")
    end = text.find("\n---", 4)
    if end == -1:
        fail(f"{relative(path)} missing closing YAML frontmatter delimiter")
    try:
        data = yaml.safe_load(text[4:end]) or {}
    except Exception as exc:  # noqa: BLE001
        fail(f"{relative(path)} invalid YAML frontmatter: {exc}")
    if not isinstance(data, dict):
        fail(f"{relative(path)} frontmatter must be a mapping")
    return data


def validate_runtime_layout() -> None:
    for forbidden_dir in (ROOT / "scripts", ROOT / "workflows"):
        if forbidden_dir.exists():
            fail(f"top-level runtime-incompatible directory must not exist: {relative(forbidden_dir)}")

    for required in [
        ROOT / "maintenance" / "generate-all-agents.py",
        ROOT / "maintenance" / "validate-yaml.py",
        ROOT / "maintenance" / "validate-contracts.py",
        ROOT / "skills" / "orchestrator-workflows" / "SKILL.md",
        ROOT / "skills" / "provider-health-recovery-flow" / "SKILL.md",
        ROOT / "skills" / "provider-health-recovery" / "SKILL.md",
        ROOT / "commands" / "tdd-quality-gate.md",
        ROOT / "commands" / "github-issue-main-task.md",
    ]:
        require_file(required)


def validate_skill_frontmatter() -> None:
    expected = {
        ROOT / "skills" / "orchestrator-workflows" / "SKILL.md": {
            "name": "orchestrator-workflows",
            "modeSlugs": ["workflow-orchestrator"],
            "description_contains": ["tdd-quality-gate", "github-issue-main-task"],
        },
        ROOT / "skills" / "provider-health-recovery-flow" / "SKILL.md": {
            "name": "provider-health-recovery-flow",
            "modeSlugs": ["orchestrator", "workflow-orchestrator"],
            "description_contains": [],
        },
        ROOT / "skills" / "provider-health-recovery" / "SKILL.md": {
            "name": "provider-health-recovery",
            "modeSlugs": ["segregated-devops"],
            "description_contains": [],
        },
    }
    for path, spec in expected.items():
        data = markdown_frontmatter(path)
        if data.get("name") != spec["name"]:
            fail(f"{relative(path)} frontmatter name must be {spec['name']!r}")
        if sorted(data.get("modeSlugs") or []) != sorted(spec["modeSlugs"]):
            fail(f"{relative(path)} frontmatter modeSlugs must be exactly {spec['modeSlugs']!r}")
        description = str(data.get("description") or "")
        if not description:
            fail(f"{relative(path)} frontmatter description is required")
        for needle in spec["description_contains"]:
            if needle not in description:
                fail(f"{relative(path)} frontmatter description must mention {needle!r}")


def validate_runtime_skill_semantics() -> None:
    workflow_path = ROOT / "skills" / "orchestrator-workflows" / "SKILL.md"
    provider_path = ROOT / "skills" / "provider-health-recovery-flow" / "SKILL.md"

    workflow_text = workflow_path.read_text(encoding="utf-8")
    provider_text = provider_path.read_text(encoding="utf-8")

    required_workflow = [
        "sole runtime source of truth for the phase order of both workflows",
        "Workflow names are procedures, not mode slugs.",
        "Execution Owner: Current Orchestrator.",
        "Procedure: Execute `## Workflow: tdd-quality-gate` in this same Skill",
        "Never set `TASK_PACKET_V1.assigned_mode` to `workflow`",
        "Do not create a wrapper `new_task` targeting `orchestrator`",
        "Backlogization Completed",
        "do not continue from successful sub-issue creation",
        "rerun the `issue-intake-routing` procedure",
        "select the open sub-issue with the lowest Issue number",
        "`issue-intake-routing` when at least one unhandled open sub-issue remains",
    ]
    for needle in required_workflow:
        if needle not in workflow_text:
            fail(f"orchestrator-workflows: missing runtime semantic text: {needle}")

    forbidden_workflow = [
        "Assigned Mode: Workflow",
        "### Phase: tdd-quality-gate\n- Assigned Mode: `orchestrator`",
        "### Phase: return-to-parent-routing-conditional\n"
        "- Assigned Mode: `issue-tracker`\n"
        "- Entry Condition: Active issue is a sub-issue and parent routing is required.",
    ]

    for needle in forbidden_workflow:
        if needle in workflow_text:
            fail(
                "orchestrator-workflows: "
                f"stale or ambiguous workflow text remains: {needle}"
            )

    provider_frontmatter = markdown_frontmatter(provider_path)
    if sorted(provider_frontmatter.get("modeSlugs") or []) != ["orchestrator", "workflow-orchestrator"]:
        fail(
            "provider-health-recovery-flow: modeSlugs must be exactly "
            "['orchestrator', 'workflow-orchestrator']"
        )

    required_provider = [
        "This Skill does not classify provider failures",
        "## Phase 1: provider-recovery",
        "## Phase 2: resume-after-recovery",
        "Provider Health Failure has already been explicitly confirmed",
        "`segregated-devops` subtask must load and follow the `provider-health-recovery` Skill",
        "Orchestrator coordinates this flow but must not load or execute the operational `provider-health-recovery` Skill itself",
        "`provider-health-recovery-flow` is an Orchestrator coordination Skill",
    ]
    for needle in required_provider:
        if needle not in provider_text:
            fail(
                "provider-health-recovery-flow: "
                f"missing runtime semantic text: {needle}"
            )

    forbidden_provider = [
        "provider-failure-classification",
        "Assigned Mode: `recovery-supervisor`",
        "- Required Skill: Load and follow `provider-health-recovery`.",
    ]
    for needle in forbidden_provider:
        if needle in provider_text:
            fail(
                "provider-health-recovery-flow: "
                f"stale classification phase remains: {needle}"
            )


def validate_command_frontmatter() -> None:
    for path in [
        ROOT / "commands" / "tdd-quality-gate.md",
        ROOT / "commands" / "github-issue-main-task.md",
    ]:
        data = markdown_frontmatter(path)
        if not data.get("description"):
            fail(f"{relative(path)} frontmatter description is required")
        if not data.get("argument-hint"):
            fail(f"{relative(path)} frontmatter argument-hint is required")
        if data.get("mode") != "workflow-orchestrator":
            fail(f"{relative(path)} frontmatter mode must be 'workflow-orchestrator'")


def validate_stale_runtime_references() -> None:
    workflows_prefix = "workflows/"
    scripts_prefix = "python scripts/"
    stale_needles = [
        workflows_prefix + "tdd-quality-gate.json",
        workflows_prefix + "github-issue-main-task.json",
        workflows_prefix + "provider-health-recovery.json",
        scripts_prefix + "generate-all-agents.py",
        scripts_prefix + "validate-yaml.py",
        scripts_prefix + "validate-contracts.py",
    ]
    checked_roots = [
        ROOT / "README.md",
        ROOT / "commands",
        ROOT / "skills",
        ROOT / "rules",
        ROOT / "maintenance",
        ROOT / "all-agents.yaml",
    ]
    self_path = Path(__file__).resolve()
    files: list[Path] = []
    for root in checked_roots:
        if root.is_file():
            files.append(root)
        elif root.is_dir():
            files.extend(path for path in root.rglob("*") if path.is_file())
    for path in files:
        if path.resolve() == self_path:
            continue
        if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        if any(part == ".git" for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for needle in stale_needles:
            if needle in text:
                fail(f"stale runtime reference {needle!r} found in {relative(path)}")


def main() -> None:
    rule_modes = load_rule_modes()
    all_modes = load_all_agents_modes()
    for slug in [
        "tester",
        "orchestrator",
        "workflow-orchestrator",
        "user-response-composer",
        "ask",
        "documenter",
        "gpt-oss-needs-analyzer",
    ]:
        if slug not in rule_modes:
            fail(f"missing required mode: {slug}")

    validate_no_tool_classification(rule_modes)
    validate_control_plane_serialization(rule_modes)
    validate_slash_command_boundary(rule_modes)
    validate_visible_todo_admission(rule_modes)
    validate_post_condense_rehydration(rule_modes)
    validate_terminal_no_tool_stop_conditions(rule_modes)
    validate_internal_routing(rule_modes)
    validate_workflow_orchestrator(rule_modes)
    validate_command_group_policy(rule_modes)
    validate_patch_recovery_skill(rule_modes)
    validate_explicit_first_step(rule_modes)
    validate_large_task_admission(rule_modes)
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
    validate_runtime_layout()
    validate_skill_frontmatter()
    validate_runtime_skill_semantics()
    validate_command_frontmatter()
    validate_stale_runtime_references()

    print("contract validation ok")
    print(f"customModes count = {len(rule_modes)}")
    print("no-tool modes = " + ", ".join(sorted(slug for slug, mode in rule_modes.items() if mode.get("groups") == [])))


if __name__ == "__main__":
    main()
