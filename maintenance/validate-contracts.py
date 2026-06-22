#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
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
    import json
    return json.loads(proc.stdout)


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
        "MATERIALIZATION_STALLED_V1",
    ]:
        require(mode, needle)


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
    ]:
        if needle not in raw_contract:
            fail(f"raw-input-materialization contract missing: {needle}")
    for needle in [
        "Keep `new_task.message` small enough",
        "single `raw-input-materializer` subtask",
        "RAW_INPUT_PAYLOAD_V1",
        "Do not paste raw user prompts",
        "artifact paths, line ranges, hashes, issue IDs, and exact commands",
        "remaining context can carry the task evidence",
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
    validate_readme()
    print("contract validation ok")
    print(f"customModes count = {len(modes)}")


if __name__ == "__main__":
    main()
