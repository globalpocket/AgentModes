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
