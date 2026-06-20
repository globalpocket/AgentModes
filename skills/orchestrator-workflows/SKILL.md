---
name: orchestrator-workflows
description: Compatibility shim for older references; delegates workflow-specific phase authority to `tdd-quality-gate` and `github-issue-main-task` Skills.
modeSlugs:
  - workflow-orchestrator
---

# Orchestrator Workflows Compatibility Shim

This Skill is retained only for backward-compatible discovery by older prompts or local user configurations.

## Current authority

- `/tdd-quality-gate` phase guidance lives in `skills/tdd-quality-gate/SKILL.md`.
- `/github-issue-main-task` phase guidance lives in `skills/github-issue-main-task/SKILL.md`.
- This shim is not the sole runtime source of truth for either workflow.
- Do not duplicate full phase lists here.
- Workflow Orchestrator should load the workflow-specific Skill selected by the explicit Slash Command.

## Compatibility behavior

- If this shim is loaded for `/tdd-quality-gate`, immediately load `tdd-quality-gate` as the next Skill action.
- If this shim is loaded for `/github-issue-main-task`, immediately load `github-issue-main-task` as the next Skill action.
- Do not create `TASK_PACKET_V1` assignments from this shim.
- Never set `TASK_PACKET_V1.assigned_mode` to `workflow`, `tdd-quality-gate`, or `github-issue-main-task`.
