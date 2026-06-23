# TASK_PACKET_V1 Compact Prompt Contract

`TASK_PACKET_V1` is a compact control packet for one delegated subtask. It is not a copied prompt, mini specification, parent plan, or conversation summary. The only exception is the first `raw-input-materializer` handoff, which must carry the verbatim raw body as `RAW_INPUT_PAYLOAD_V1` so it can create `RAW_INPUT_REF_V1`.

## Compact construction

- Keep `new_task.message` small enough to carry only routing facts and current-subtask scope for all non-materializer subtasks.
- Include one short `goal`, a few concrete `steps`, a few concrete `done` checks, and explicit workspace paths only when needed.
- Optional sections are included only when they add current-subtask facts.
- If more context is needed, materialize that context as an artifact and pass the path.

## Forbidden packet content

- Do not paste raw user prompts, full specs, full logs, full diffs, full files, previous handoffs, or hidden reasoning, except the required escape-safe `RAW_INPUT_PAYLOAD_V1` envelope in the single `raw-input-materializer` subtask.
- Do not combine multiple invariants or multiple worker responsibilities in one packet.
- Do not use placeholders such as empty arrays, empty strings, or default objects to fill an old skeleton.

## Required pattern

Use artifact paths, line ranges, hashes, issue IDs, and exact commands as pointers. The goal is not to reject useful context; it is to keep fixed prompts small so the remaining context can carry the task evidence that the LLM actually needs.

## Broad edit worker dynamic scope

When assigning broad edit workers such as `patch-applier` or `new-file-writer`, the packet must include dynamic scope as `action_contract.allowed_file_regex` or `files.allowlist`; otherwise the parent controller must not dispatch the worker and must return `DELEGATION_BLOCKED`.

## Raw-input materializer exception

When the current user request is large inline input that has not already been materialized, the active parent controller must send exactly one subtask to `raw-input-materializer` with the verbatim body in an escape-safe `RAW_INPUT_PAYLOAD_V1` envelope. That materializer subtask is the only packet allowed to contain the raw body.

Every later packet must refer to `RAW_INPUT_REF_V1` artifacts by path and preserve `routing_control.completion_unwind` when present. Intermediate handoffs that require another mode must include `handoff_status: requires_parent_dispatch`, `workflow_complete: false`, and `next_action: {type: new_task, tool: new_task, mode: <next-mode>}` so Roo/Zoo runtimes can dispatch the required Boomerang `new_task` with its `mode` parameter and do not treat the handoff as final workflow completion.

`routing_control.allowed_next_modes` is current-hop only and may be replaced for the immediate next hop, but packets must not remove completion unwind metadata or concrete forbidden implementation/test/worker slugs/classes and terminal forbidden modes/classes.

Expected current-hop map:
- Non-slash intake: raw-input-materializer → gpt-oss-intake-analyzer → intake-ledger-writer → orchestrator, and state-ledger-writer → orchestrator.
- Slash workflows: raw-input-materializer → gpt-oss-intake-analyzer → intake-ledger-writer → workflow-orchestrator, and state-ledger-writer → workflow-orchestrator.

The next step after materialization is intake analysis, not `code`; implementation may start only after Orchestrator/epoch decomposition, and final completion must unwind to `return_to_mode: user-response-composer` instead of ending in `code`. See `docs/contracts/raw-input-materialization.md`.
