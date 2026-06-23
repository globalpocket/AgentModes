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
- Format visible TODOs with actual newline characters between the heading and checklist items; do not include literal `\n` escape sequences.
- Handoffs from workers must be `STATE_DELTA_V1` and about eight lines or fewer.

## Phase outline

1. Rehydrate durable state from `RUN_STATE_V1` or initialize the workflow ledger.
2. Identify the current invariant and allowed files.
3. Delegate current phase to `epoch-orchestrator`.
4. Run exact command workers for requested checks.
5. Classify results with judge workers.
6. Commit `STATE_DELTA_V1` through `state-ledger-writer`.
7. At phase boundary, consider `context-compactor`.

## Machine-readable phase contract

```yaml
phase_contract:
  workflow: tdd-quality-gate
  phase_execution: one_phase_at_a_time
  default_supervisor: workflow-orchestrator
  supervisor_handoff_chain:
    - workflow-orchestrator
    - epoch-orchestrator
    - state-ledger-writer
    - workflow-orchestrator
  worker_class_handoff: atomic-workers
  phases:
    - id: rehydrate_state
      allowed_workers: [state-ledger-reader, ledger-consistency-checker]
      required_artifacts: [RUN_STATE_V1, initialization_decision]
      exit_delta: STATE_DELTA_V1.rehydrated_state
    - id: identify_invariant
      allowed_workers: [tree-indexer, source-excerpt-reader, scope-checker]
      required_artifacts: [current_invariant, allowed_files]
      exit_delta: STATE_DELTA_V1.phase_scope
    - id: delegate_epoch
      allowed_workers: [epoch-orchestrator]
      required_artifacts: [TASK_PACKET_V1]
      exit_delta: STATE_DELTA_V1.epoch_result
    - id: run_checks
      allowed_workers: [exact-command-runner, test-runner, coverage-runner, format-lint-runner, build-runner]
      required_artifacts: [exact_commands, command_result_artifacts]
      exit_delta: STATE_DELTA_V1.command_results
    - id: classify_results
      allowed_workers: [test-result-classifier, coverage-checker, compiler-diagnostic-classifier, contract-checker]
      required_artifacts: [command_result_artifact_paths]
      exit_delta: STATE_DELTA_V1.quality_gate_decision
    - id: commit_state
      allowed_workers: [state-ledger-writer]
      required_artifacts: [validated_STATE_DELTA_V1]
      exit_delta: RUN_STATE_V1.updated
    - id: phase_boundary_compaction
      allowed_workers: [context-compactor]
      required_artifacts: [RUN_STATE_V1, artifact_index]
      exit_delta: STATE_DELTA_V1.compaction_result
```
