# TASK_PACKET_V1 Compact Prompt Contract

`TASK_PACKET_V1` is a compact control packet for one delegated subtask. It is not a copied prompt, mini specification, parent plan, or conversation summary. The only exception is the first `raw-input-materializer` handoff, which must carry the verbatim raw body as `RAW_INPUT_PAYLOAD` so it can create `RAW_INPUT_REF_V1`.

## Compact construction

- Keep `new_task.message` small enough to carry only routing facts and current-subtask scope for all non-materializer subtasks.
- Include one short `goal`, a few concrete `steps`, a few concrete `done` checks, and explicit workspace paths only when needed.
- Optional sections are included only when they add current-subtask facts.
- If more context is needed, materialize that context as an artifact and pass the path.

## Forbidden packet content

- Do not paste raw user prompts, full specs, full logs, full diffs, full files, previous handoffs, or hidden reasoning, except the required fenced `RAW_INPUT_PAYLOAD` in the single `raw-input-materializer` subtask.
- Do not combine multiple invariants or multiple worker responsibilities in one packet.
- Do not use placeholders such as empty arrays, empty strings, or default objects to fill an old skeleton.

## Required pattern

Use artifact paths, line ranges, hashes, issue IDs, and exact commands as pointers. The goal is not to reject useful context; it is to keep fixed prompts small so the remaining context can carry the task evidence that the LLM actually needs.

## Raw-input materializer exception

When the current user request is large inline input that has not already been materialized, the orchestrator must send exactly one subtask to `raw-input-materializer` with the verbatim body in fenced `RAW_INPUT_PAYLOAD`. That materializer subtask is the only packet allowed to contain the raw body. Every later packet must refer to `RAW_INPUT_REF_V1` artifacts by path. See `docs/contracts/raw-input-materialization.md`.
