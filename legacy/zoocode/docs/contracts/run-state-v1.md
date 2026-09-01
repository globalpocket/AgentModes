# RUN_STATE_V1 Durable Ledger Contract

`RUN_STATE_V1` is the durable source of truth for Orchestrator continuity. Conversation history, TODOs, and condensed summaries are cache only.

## Required fields

```json
{
  "version": "RUN_STATE_V1",
  "run_id": "rust-runtime-hardening",
  "specification_path": "docs/tasks/rust-runtime-hardening.md",
  "epoch": 17,
  "phase": "runtime-publish-normalization",
  "status": "prepared",
  "current_invariant": "normalize-before-bus-publish",
  "active_files": ["rust/runtime/src/runtime.rs"],
  "completed_invariants": [],
  "task_id": "epoch-17",
  "input_hash": "sha256:<hex>",
  "attempt": 1,
  "result_hash": "sha256:<hex-or-empty-before-result>",
  "last_committed_task_id": "epoch-16",
  "next_mode": "epoch-orchestrator",
  "checksum": "sha256:<canonical-ledger-without-checksum>"
}
```

## State transitions

Only these statuses are valid:

```text
prepared → running → committed
prepared → running → failed
failed → running
committed → prepared
```

Rules:

- Do not start a next task until the prior `STATE_DELTA_V1` is atomically committed and checksum-verified.
- `task_id` must be unique per epoch attempt unless an idempotent retry confirms the same `input_hash` and `result_hash`.
- A repeated `task_id` with a different `result_hash` is a duplicate commit conflict.
- A `running` ledger with no matching committed result is an interrupted task and must be retried idempotently or escalated to `recovery-supervisor`.
- `checksum` is computed over canonical JSON with sorted keys and the `checksum` field omitted.

## STATE_DELTA_V1 input

`state-ledger-writer` accepts only compact deltas:

```yaml
STATE_DELTA_V1:
  task_id: epoch-17
  terminal_outcome: completed
  changed_files:
    - rust/runtime/src/runtime.rs
  verified_facts:
    - validation occurs before bus publish
  artifacts: []
  unresolved: []
  recommended_next_phase: internal-handler-registration
```

The writer maps `terminal_outcome` to ledger status and computes `result_hash` from the canonical delta payload.
