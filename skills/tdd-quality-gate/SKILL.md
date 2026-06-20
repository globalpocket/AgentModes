---
name: tdd-quality-gate
description: Workflow-specific Skill for the `/tdd-quality-gate` entrypoint; defines only TDD quality-gate phase guidance for workflow-orchestrator.
modeSlugs:
  - workflow-orchestrator
---

# TDD Quality Gate Workflow Skill

Use only after the user explicitly invokes `/tdd-quality-gate`.

## Contract

- This Skill owns the fixed TDD quality-gate phase definitions only.
- Load this Skill at workflow entry for `/tdd-quality-gate`.
- Do not load GitHub Issue workflow instructions from here.
- Execute one phase at a time through `workflow-orchestrator` → `epoch-orchestrator` → atomic workers.
- Preserve one visible TODO for the current phase only.
- Handoffs from workers must be `STATE_DELTA_V1` and about eight lines or fewer.

## Phase outline

1. Rehydrate durable state from `RUN_STATE_V1` or initialize the workflow ledger.
2. Identify the current invariant and allowed files.
3. Delegate current phase to `epoch-orchestrator`.
4. Run exact command workers for requested checks.
5. Classify results with judge workers.
6. Commit `STATE_DELTA_V1` through `state-ledger-writer`.
7. At phase boundary, consider `context-compactor`.
