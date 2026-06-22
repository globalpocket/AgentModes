# Phase 4: Intake Recomposition

Phase 4 makes ordinary user input durable before Orchestrator starts.

## Ordinary input path

```text
gpt-oss-intake-supervisor
→ intake-ledger-writer
→ orchestrator with SESSION_START_V1 paths only
```

## Contracts

- `gpt-oss-intake-supervisor` classifies input as `short_request`, `long_request`, or `github_issue_url`.
- It must not infer GitHub Issue contents from a URL.
- `intake-ledger-writer` persists raw input and `USER_NEEDS_V1` artifacts.
- Orchestrator receives only `run_id`, `raw_request_path`, `user_needs_path`, `state_path`, and `next_action`.
- Explicit slash commands bypass intake and enter `workflow-orchestrator`.

## Stored artifacts

```text
artifacts/intake/<run-id>/raw-request.md
artifacts/intake/<run-id>/user-needs.yaml
artifacts/state/<run-id>.json
```

## Large input materialization

Ordinary user input enters `gpt-oss-intake-supervisor`. Small input can be organized directly into `USER_NEEDS_V1`. Large input is not rejected; it is first materialized as a raw artifact, represented by `RAW_INPUT_REF_V1` and `raw_request_path`, and then organized into `USER_NEEDS_V1`.

The expected path-only flow is:

1. User request enters `gpt-oss-intake-supervisor`.
2. Large inline or host-materialized input becomes `RAW_INPUT_REF_V1` with `raw_request_path`.
3. `intake-ledger-writer` persists or adopts `artifacts/intake/<run-id>/raw-request.md`, writes `USER_NEEDS_V1` to `user-needs.yaml`, and initializes state.
4. Orchestrator receives `SESSION_START_V1` containing paths only.

This is not a design that refuses large input. However, truly oversized input cannot reach the LLM if it exceeds provider context before request generation. ZooCodeCustom must provide a pre-LLM large input materializer for that case.
