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
OUT = ROOT / "all-agents.yaml"

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


class LiteralDumper(yaml.SafeDumper):
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow=flow, indentless=False)


def represent_str(dumper, data: str):
    style = "|" if "\n" in data else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


LiteralDumper.add_representer(str, represent_str)


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def load_yaml(path: Path):
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        fail(f"YAML parse failed: {path}: {e}")


def validate_text_patterns(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for pattern, reason in BROKEN_PATTERNS:
        if pattern.search(text):
            fail(f"{path}: broken pattern detected: {reason}")


def validate_data(path: Path, data) -> None:
    if not isinstance(data, dict):
        fail(f"{path}: top-level YAML must be mapping")

    modes = data.get("customModes")
    if not isinstance(modes, list):
        fail(f"{path}: customModes must be list")

    local_slugs: set[str] = set()

    for index, mode in enumerate(modes):
        if not isinstance(mode, dict):
            fail(f"{path}: customModes[{index}] must be mapping")

        for key in REQUIRED_MODE_KEYS:
            if key not in mode:
                fail(f"{path}: customModes[{index}] missing {key}")

        slug = mode["slug"]
        if not isinstance(slug, str) or not slug.strip():
            fail(f"{path}: customModes[{index}] invalid slug")

        if slug in local_slugs:
            fail(f"{path}: duplicate slug {slug}")

        if "source" in mode:
            fail(f"{path}: {slug}: source must be top-level only")

        if not isinstance(mode["groups"], list):
            fail(f"{path}: {slug}: groups must be list")

        if not isinstance(mode["customInstructions"], str):
            fail(f"{path}: {slug}: customInstructions must be string")

        local_slugs.add(slug)


def load_rule_modes(path: Path) -> list[dict]:
    validate_text_patterns(path)
    data = load_yaml(path)
    validate_data(path, data)
    return data["customModes"]


def validate_generated(expected_count: int) -> None:
    validate_text_patterns(OUT)
    generated = load_yaml(OUT)
    validate_data(OUT, generated)
    if len(generated["customModes"]) != expected_count:
        fail("all-agents.yaml: customModes count mismatch")


def main() -> None:
    merged: dict[str, object] = {"customModes": []}
    seen_slugs: set[str] = set()

    for path in sorted(RULES_DIR.glob("*.yaml")):
        for mode in load_rule_modes(path):
            slug = mode["slug"]
            if slug in seen_slugs:
                fail(f"duplicate slug across rules: {slug}")
            seen_slugs.add(slug)
            merged["customModes"].append(mode)

    merged["source"] = "project"

    OUT.write_text(
        yaml.dump(
            merged,
            Dumper=LiteralDumper,
            allow_unicode=True,
            sort_keys=False,
            width=4096,
            default_flow_style=False,
        ),
        encoding="utf-8",
    )

    validate_generated(len(merged["customModes"]))
    head = OUT.read_text(encoding="utf-8").splitlines()[:10]
    print("all-agents.yaml head:")
    for line in head:
        print(line)
    print(f"generated {OUT.relative_to(ROOT)} with {len(merged['customModes'])} modes")


if __name__ == "__main__":
    main()
