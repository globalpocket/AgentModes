# Phase 3: Control Plane Recomposition

Phase 3 narrows long-lived control modes and pushes high-reasoning planning into short-lived epochs.

## Implemented contracts

- `orchestrator` and `workflow-orchestrator` keep `SESSION_CURSOR_V1` only.
- Current state is loaded through `state-ledger-reader`.
- Exactly one visible TODO represents the current epoch.
- The current phase is delegated to `epoch-orchestrator` only.
- `STATE_DELTA_V1` is committed through `state-ledger-writer` before the next epoch starts.
- Long-lived modes do not perform detailed design, edit-file selection, TDD judgment, failure fingerprint analysis, or direct code/artifact/GitHub interpretation.
- Delegated `TASK_PACKET_V1` messages are compact control packets that carry pointers rather than pasted specs, logs, diffs, or parent plans.

## Model lifetime split

- Long-lived control: `orchestrator`, `workflow-orchestrator` → Qwen3.6-9B.
- Short-lived high reasoning: `epoch-orchestrator` → Qwen3.5-122B.
- Exceptional recovery: `recovery-supervisor` → GPT-OSS-120B class.
