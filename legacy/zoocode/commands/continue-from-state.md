---
description: Continue a task from a durable RUN_STATE_V1 ledger without relying on conversation history.
mode: orchestrator
---

Continue from the provided durable state ledger path.

Input format:

```text
/continue-from-state artifacts/state/<run-id>.json
```

The Orchestrator must start with only this pointer:

```text
State: <provided path>
Resume exclusively from the durable ledger.
```

Do not paste prior conversation summaries, raw prompts, full logs, or prior handoffs into the new root task.
