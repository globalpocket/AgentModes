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
- Preserve one visible TODO for the current phase only when TODOs are needed.
- Format visible TODOs as a multi-line Zoo/Roo TODO body with actual newline characters between the heading and checklist items; do not serialize the TODO as a single escaped string and do not include literal `\n` escape sequences.
- Use `VISIBLE_TODO_V1` (`docs/contracts/visible-todo-v1.md`) for visible TODO handoffs, keeping `title` and `items` structured until the final Zoo/Roo rendering boundary.

## Phase outline

1. Rehydrate or initialize durable state.
2. Use `issue-reader` to fetch the issue body and relationship metadata.
3. Use `gpt-oss-needs-analyzer` only for pure analysis of fetched issue facts when needed.
4. Update `USER_NEEDS_V1` and `RUN_STATE_V1` through ledger writers.
5. If implementation is required, load `tdd-quality-gate` and continue by epoch.
6. Mutate GitHub state only through the dedicated mutation worker for the current atomic action.

## Machine-readable phase contract

```yaml
phase_contract:
  workflow: github-issue-main-task
  phase_execution: one_phase_at_a_time
  default_supervisor: workflow-orchestrator
  supervisor_handoff_chain:
    - workflow-orchestrator
    - epoch-orchestrator
    - state-ledger-writer
    - workflow-orchestrator
  worker_class_handoff: atomic-workers
  mutation_gate:
    required_fields: [repository, issue_or_pr_id, action, idempotency_key, payload_summary]
    allowed_mutation_workers: [issue-comment-writer, sub-issue-creator, issue-closer]
    blocker_if_missing: BLOCKED_DELTA_V1
  phases:
    - id: rehydrate_state
      allowed_workers: [state-ledger-reader, ledger-consistency-checker]
      required_artifacts: [RUN_STATE_V1, initialization_decision]
      exit_delta: STATE_DELTA_V1.rehydrated_state
    - id: fetch_issue
      allowed_workers: [issue-reader, github-relationship-checker]
      required_artifacts: [issue_body_artifact, relationship_metadata]
      exit_delta: STATE_DELTA_V1.issue_facts
    - id: analyze_needs
      allowed_workers: [gpt-oss-needs-analyzer]
      required_artifacts: [fetched_issue_facts]
      exit_delta: USER_NEEDS_V1.update_request
    - id: update_ledgers
      allowed_workers: [intake-ledger-writer, state-ledger-writer]
      required_artifacts: [USER_NEEDS_V1, RUN_STATE_V1_delta]
      exit_delta: SESSION_START_V1_or_RUN_STATE_V1.updated
    - id: implementation_epoch
      allowed_workers: [workflow-orchestrator, epoch-orchestrator]
      required_artifacts: [tdd_quality_gate_phase_contract]
      exit_delta: STATE_DELTA_V1.implementation_result
    - id: mutate_github
      allowed_workers: [issue-comment-writer, sub-issue-creator, issue-closer]
      required_artifacts: [repository, issue_or_pr_id, action, action_contract, idempotency_key, payload_summary]
      exit_delta: STATE_DELTA_V1.github_mutation_result
```
