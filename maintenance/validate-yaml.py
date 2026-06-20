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

        ruby = shutil.which("ruby")
        if ruby is not None:
            import json
            import subprocess

            class RubyYaml:
                @staticmethod
                def safe_load(text):
                    proc = subprocess.run(
                        [ruby, "-r", "yaml", "-r", "json", "-e", "puts JSON.generate(YAML.safe_load(STDIN.read, permitted_classes: [Symbol], aliases: true))"],
                        input=text,
                        text=True,
                        capture_output=True,
                    )
                    if proc.returncode != 0:
                        raise RuntimeError(proc.stderr.strip())
                    return json.loads(proc.stdout)

                @staticmethod
                def dump(data, **kwargs):
                    proc = subprocess.run(
                        [ruby, "-r", "yaml", "-r", "json", "-e", "obj = JSON.parse(STDIN.read); puts obj.to_yaml(line_width: -1)"],
                        input=json.dumps(data, ensure_ascii=False),
                        text=True,
                        capture_output=True,
                    )
                    if proc.returncode != 0:
                        raise RuntimeError(proc.stderr.strip())
                    return proc.stdout

            return RubyYaml
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
FILES = sorted(RULES_DIR.glob("*.yaml")) + [ALL_AGENTS]

REQUIRED_MODE_KEYS = [
    "slug",
    "name",
    "roleDefinition",
    "groups",
    "customInstructions",
]

BROKEN_PATTERNS = [
    (re.compile(r"customModes:[ \t]+-"), "customModes list starts on same line"),
    (re.compile(r"customInstructions:[ \t]*\|-[ \t]+\S"), "customInstructions content starts on same line"),
    (re.compile(r"source:[ \t]*project[ \t]+customModes:"), "source and customModes concatenated"),
    (re.compile(r"-[ \t]+slug:[ \t]*['\"]?architect['\"]?[ \t]+name:"), "mode fields collapsed onto one line"),
]


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def validate_text_patterns(path: Path, text: str) -> None:
    for pattern, reason in BROKEN_PATTERNS:
        if pattern.search(text):
            fail(f"{path}: broken pattern detected: {reason}")


def validate_file(path: Path, require_unique_slugs: bool = False):
    text = path.read_text(encoding="utf-8")
    validate_text_patterns(path, text)

    try:
        data = yaml.safe_load(text)
    except Exception as e:  # noqa: BLE001
        fail(f"YAML parse failed: {path}: {e}")

    if not isinstance(data, dict):
        fail(f"{path}: top-level YAML must be mapping")

    if "customModes" not in data:
        fail(f"{path}: missing customModes")

    if not isinstance(data["customModes"], list):
        fail(f"{path}: customModes must be list")

    seen_slugs: set[str] = set()

    for index, mode in enumerate(data["customModes"]):
        if not isinstance(mode, dict):
            fail(f"{path}: customModes[{index}] must be mapping")

        for key in REQUIRED_MODE_KEYS:
            if key not in mode:
                fail(f"{path}: customModes[{index}] missing {key}")

        slug = mode.get("slug")
        if not isinstance(slug, str) or not slug.strip():
            fail(f"{path}: customModes[{index}] invalid slug")

        if require_unique_slugs:
            if slug in seen_slugs:
                fail(f"{path}: duplicate slug {slug}")
            seen_slugs.add(slug)

        if "source" in mode:
            fail(f"{path}: {slug}: source must be top-level only")

        if not isinstance(mode["groups"], list):
            fail(f"{path}: {slug}: groups must be list")

        if not isinstance(mode["customInstructions"], str):
            fail(f"{path}: {slug}: customInstructions must be string")

    return data


def main() -> None:
    data_by_path = {
        path: validate_file(path, require_unique_slugs=(path == ALL_AGENTS))
        for path in FILES
    }
    rule_mode_count = sum(len(data_by_path[path]["customModes"]) for path in sorted(RULES_DIR.glob("*.yaml")))
    all_agents_count = len(data_by_path[ALL_AGENTS]["customModes"])
    if all_agents_count != rule_mode_count:
        fail(f"all-agents.yaml: customModes count {all_agents_count} does not match rules count {rule_mode_count}")

    print("yaml validation ok")
    print(f"all-agents.yaml customModes count = {all_agents_count}")


if __name__ == "__main__":
    main()
