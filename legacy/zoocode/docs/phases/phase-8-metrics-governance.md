# Phase 8: Metrics and Governance

Phase 8 makes the migration measurable and prevents regressions back to conversation-history state.

## Measurement scope

Track the indicators defined by the architecture decision:

- Estimated customInstructions tokens per mode.
- Maximum token load after Skill loading.
- Tool calls per worker session.
- Handoff line count.
- Bytes/characters returned to parent Orchestrator.
- Context condensation and sliding-window truncation counts.
- Ledger rehydration success rate.
- Duplicate task execution count.
- Average epoch duration.
- Number of times large models are used for compression.

## Governance checks

- Long-lived tasks must remain assigned to 9B-class models.
- 122B-class tasks must be short-lived and finish before condensation.
- `/continue-from-state` must resume without conversation summaries.
- Any worker handoff exceeding the `STATE_DELTA_V1` line budget is a contract violation.
- Any Orchestrator task that embeds raw prompts or full logs after intake is a regression.

## Workers

- `context-metrics-reader`: reads durable artifacts and command metadata for migration metrics.
- `rehydration-auditor`: checks whether a new root task can reconstruct `SESSION_CURSOR_V1` from ledger artifacts only.
- `handoff-budget-checker`: checks worker output against the 8-line handoff budget and full-log/full-diff prohibitions.
- `model-lifetime-checker`: checks configured model allocation against long-lived vs short-lived mode policy.
