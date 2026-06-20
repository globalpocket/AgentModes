---
name: github-issue-main-task
description: Workflow-specific Skill for the `/github-issue-main-task` entrypoint; defines GitHub Issue intake and routing phases for workflow-orchestrator.
modeSlugs:
  - workflow-orchestrator
---

# GitHub Issue Main Task Workflow Skill

Use only after the user explicitly invokes `/github-issue-main-task`.

## Contract

- This Skill owns GitHub Issue workflow phases only.
- Load this Skill first for `/github-issue-main-task`.
- Do not load TDD workflow instructions until the implementation phase is reached.
- Issue URLs are read by `issue-reader`; GPT-OSS modes must not infer issue contents from a URL.
- GitHub read and mutation workers are separate: `issue-reader`, `issue-comment-writer`, `sub-issue-creator`, and `issue-closer`.

## Phase outline

1. Rehydrate or initialize durable state.
2. Use `issue-reader` to fetch the issue body and relationship metadata.
3. Use `gpt-oss-needs-analyzer` only for pure analysis of fetched issue facts when needed.
4. Update `USER_NEEDS_V1` and `RUN_STATE_V1` through ledger writers.
5. If implementation is required, load `tdd-quality-gate` and continue by epoch.
6. Mutate GitHub state only through the dedicated mutation worker for the current atomic action.
