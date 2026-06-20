# MIGRATION_METRICS_V1 Contract

`MIGRATION_METRICS_V1` captures phase-8 observability without making conversation history a source of truth.

```yaml
MIGRATION_METRICS_V1:
  run_id: rust-runtime-hardening
  state_path: artifacts/state/rust-runtime-hardening.json
  measured_at: "2026-06-20T00:00:00Z"
  mode_instruction_tokens:
    orchestrator: 0
  skill_loaded_max_tokens: 0
  worker_tool_calls:
    epoch-17: 0
  handoff_line_counts:
    epoch-17: 0
  parent_return_chars:
    epoch-17: 0
  context_condensation_count: 0
  sliding_window_truncation_count: 0
  state_rehydration_success_rate: 1.0
  duplicate_task_execution_count: 0
  epoch_average_duration_ms: 0
  large_model_compression_count: 0
```

Rules:

- Metrics are derived from durable artifacts, task metadata, command metadata, and explicit runtime observations.
- Do not use conversation summaries as evidence.
- Missing telemetry is reported as `unavailable`, not guessed.
- Metrics artifacts are read-only inputs for governance checks; they do not advance the run state by themselves.
