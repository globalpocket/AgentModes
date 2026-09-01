# SESSION_CURSOR_V1 Contract

Long-lived Orchestrator tasks keep only this cursor in active context:

```yaml
SESSION_CURSOR_V1:
  run_id: rust-runtime-hardening
  specification_path: docs/tasks/rust-runtime-hardening.md
  intake_path: artifacts/intake/rust-runtime-hardening/user-needs.yaml
  state_path: artifacts/state/rust-runtime-hardening.json
  current_epoch: 17
  current_phase: runtime-publish-normalization
  current_task_id: epoch-17
  next_action: dispatch_epoch
```

Rules:

- Do not paste raw user prompts, old handoffs, full logs, or full diffs into the cursor.
- On `/continue-from-state`, reconstruct this cursor from `RUN_STATE_V1` and durable intake paths.
- If cursor and ledger disagree, the ledger wins.
