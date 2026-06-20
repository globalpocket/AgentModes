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
