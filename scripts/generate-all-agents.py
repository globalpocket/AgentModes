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


def validate_no_broken_patterns(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for pattern, reason in BROKEN_PATTERNS:
        if pattern.search(text):
            fail(f"{path}: broken pattern detected: {reason}")


def validate_mode(path: Path, mode, index: int, seen_slugs: set[str] | None = None) -> None:
    if not isinstance(mode, dict):
        fail(f"{path}: customModes[{index}] must be mapping")

    for key in REQUIRED_MODE_KEYS:
        if key not in mode:
            fail(f"{path}: customModes[{index}] missing {key}")

    slug = mode.get("slug")
    if not isinstance(slug, str) or not slug.strip():
        fail(f"{path}: customModes[{index}] invalid slug")

    if seen_slugs is not None:
        if slug in seen_slugs:
            fail(f"duplicate slug: {slug}")
        seen_slugs.add(slug)

    if not isinstance(mode.get("groups"), list):
        fail(f"{path}: {slug}: groups must be list")

    if not isinstance(mode.get("customInstructions"), str):
        fail(f"{path}: {slug}: customInstructions must be string")


def load_rule_modes(path: Path, seen_slugs: set[str]) -> list[dict]:
    validate_no_broken_patterns(path)
    data = load_yaml(path)

    if not isinstance(data, dict):
        fail(f"{path}: top-level YAML must be mapping")

    modes = data.get("customModes")
    if not isinstance(modes, list):
        fail(f"{path}: customModes must be list")

    if len(modes) != 1:
        fail(f"{path}: customModes must contain exactly one mode")

    for index, mode in enumerate(modes):
        validate_mode(path, mode, index, seen_slugs)

    return modes


def validate_generated(expected_count: int) -> None:
    validate_no_broken_patterns(OUT)
    generated = load_yaml(OUT)
    if not isinstance(generated, dict):
        fail("all-agents.yaml: top-level must be mapping")
    modes = generated.get("customModes")
    if not isinstance(modes, list):
        fail("all-agents.yaml: customModes must be list")
    if len(modes) != expected_count:
        fail("all-agents.yaml: customModes count mismatch")
    for index, mode in enumerate(modes):
        validate_mode(OUT, mode, index)


def main() -> None:
    merged: dict[str, object] = {"customModes": []}
    seen_slugs: set[str] = set()

    for path in sorted(RULES_DIR.glob("*.yaml")):
        merged["customModes"].extend(load_rule_modes(path, seen_slugs))

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
    print(f"generated {OUT.relative_to(ROOT)} with {len(merged['customModes'])} modes")


if __name__ == "__main__":
    main()
