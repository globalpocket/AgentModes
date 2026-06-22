# Phase 7: Sliding-window Operation

Phase 7 operationalizes context reset around the durable ledger.

## Runtime policy

- Disable auto AI condensation after durable ledgers are available.
- Prefer non-LLM sliding-window truncation at context limits.
- Rehydrate from `RUN_STATE_V1`, `USER_NEEDS_V1`, and durable artifacts instead of conversation summaries.
- Keep the first Orchestrator message small: run ID, specification path, state path, and “resume exclusively from durable ledger”.

## Reset workflow

```text
context-compactor
→ state-ledger-writer
→ current task returns CONTINUATION_READY
→ /continue-from-state artifacts/state/<run-id>.json
→ new Orchestrator root task rehydrates from ledger
```

## Rotation triggers

- Every fixed epoch interval.
- After phase boundary compaction.
- After state rehydration.
- After large artifact receipt.
- When handoff count exceeds the configured threshold.

## Success metrics

- Long-lived task model remains Qwen3.6-9B.
- 122B epoch tasks finish before condensation.
- Ledger rehydration succeeds without conversation summaries.
- Duplicate task execution count remains zero.

## Raw large input under sliding windows

Sliding-window operation must keep raw large input in artifacts rather than conversation history. Once materialized, downstream modes use `RAW_INPUT_REF_V1`, `raw_request_path`, `USER_NEEDS_V1`, `SESSION_START_V1`, `SESSION_CURSOR_V1`, and `RUN_STATE_V1` paths as the source of truth.

If existing history becomes too large, resume with `/continue-from-state` or a new root task using path-only state instead of pasting the raw large input again. The state ledger and raw artifact are authoritative; raw large input should not be re-sent between modes or reintroduced into the chat transcript.
