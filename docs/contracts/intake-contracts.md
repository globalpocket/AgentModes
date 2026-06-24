# Intake Contracts

## RAW_INPUT_REF_V1

```yaml
RAW_INPUT_REF_V1:
  run_id: ""
  source_kind: inline_spec | short_request | github_issue_url | existing_file_ref
  raw_request_path: "artifacts/intake/<run-id>/raw-request.md"
  manifest_path: "artifacts/intake/<run-id>/raw-request.manifest.json"
  chunk_paths:
    - "artifacts/intake/<run-id>/chunks/chunk-0001.md"
  sha256: ""
  byte_count: 0
  token_estimate: 0
  materialized_by: raw-input-materializer
  integrity_status: verified | deferred_to_verified_integrator
  dispatch_owner: parent_controller | active_controller
  handoff_status: requires_parent_dispatch
  workflow_complete: false
  recommended_next_mode: gpt-oss-intake-analyzer
  next_mode: gpt-oss-intake-analyzer
  next_action:
    type: new_task
    tool: new_task
    mode: gpt-oss-intake-analyzer
```

`integrity_status: deferred_to_verified_integrator` is used when direct user-entry raw input has no declared delimiter/byte_count/sha256 metadata; downstream verified-integrator or runtime evidence must perform any required checksum validation. `requires_parent_dispatch` is retained for compatibility; when `dispatch_owner: active_controller`, interpret it as `requires_active_controller_dispatch` by `raw-input-materializer`.

## RAW_INPUT_MANIFEST_V1

`raw-request.manifest.json` records only mechanical materialization metadata: raw path, sha256, byte count, token estimate, source kind, and chunk metadata. It must not contain requirement analysis, summaries, implementation plans, risk analysis, TODOs, or answers to the user request; those belong to `gpt-oss-intake-analyzer` and later modes.

## MATERIALIZATION_STALLED_V1

`MATERIALIZATION_STALLED_V1` is a fail-fast output for cases where the model-side materializer cannot promptly create exact artifacts or metadata. It records the blocker, any pending fields such as `sha256`, `byte_count`, or chunk metadata, and `recommended_next: runtime_pre_llm_materialization`. The materializer must use this instead of retrying indefinitely or doing downstream analysis to appear productive.

## USER_NEEDS_SLICE_V1

Chunk-level GPT-OSS analysis output used before merge.

## USER_NEEDS_V1

Final GPT-OSS intake analysis output. It separates explicit requirements from derived constraints, safe assumptions, required user decisions, risks, and acceptance criteria.

## SESSION_START_V1

```yaml
SESSION_START_V1:
  run_id: ""
  raw_request_path: "artifacts/intake/<run-id>/raw-request.md"
  raw_manifest_path: "artifacts/intake/<run-id>/raw-request.manifest.json"
  user_needs_path: "artifacts/intake/<run-id>/user-needs.yaml"
  state_path: "artifacts/state/<run-id>.json"
  next_action: load_durable_intake
```
