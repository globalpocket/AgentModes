# RAW_INPUT_MATERIALIZATION handoff contract

Large inline input has one deliberate exception to the compact packet rule: `raw-input-materializer` may receive the verbatim raw body exactly once so it can be persisted. It can be started directly as the intake entry mode, or invoked by a parent controller. When a parent controller wraps the raw body, the handoff must use an escape-safe `RAW_INPUT_PAYLOAD_V1` envelope instead of a fixed fence because the raw body may itself contain Markdown fences, logs, or arbitrary delimiter-looking text.

## Required handoff

- The first intake mode for large inline input is `raw-input-materializer`; it may be the user entry mode.
- If a parent controller invokes it as a subtask, that subtask's message must contain exactly one escape-safe `RAW_INPUT_PAYLOAD_V1` envelope carrying the exact raw input body.
- Envelope handoffs declare `delimiter`, `byte_count`, and `sha256` metadata before the body.
- A controller that builds an envelope must choose a delimiter string that does not occur anywhere in the raw body; if no safe delimiter can be selected within the current request, it must use ZooCodeCustom/runtime pre-LLM materialization instead.
- When delimiter/byte_count/sha256 metadata is present, the materializer must verify the closing delimiter, byte count, and sha256 before writing artifacts; mismatches produce `MATERIALIZATION_STALLED_V1` and must not create a best-effort raw artifact. Direct user-entry raw input without declared integrity metadata is valid: the materializer must save the exact received body and mark `integrity_status: deferred_to_verified_integrator` instead of stalling solely because metadata is absent.
- The packet must instruct the materializer to write only `artifacts/intake/<run-id>/raw-request.md`, optional size chunks, and `raw-request.manifest.json`.
- The materializer produces `RAW_INPUT_REF_V1` path metadata with `handoff_status: requires_parent_dispatch`, `workflow_complete: false`, `recommended_next_mode: gpt-oss-intake-analyzer`, `next_mode: gpt-oss-intake-analyzer`, `next_action: {type: new_task, tool: new_task, mode: gpt-oss-intake-analyzer}`, and `routing_control`; it must never recommend or route to `code`, implementation, test, or worker modes. `requires_parent_dispatch` is retained for compatibility; when raw-input-materializer is the entry controller, treat it as `requires_active_controller_dispatch`.
- `handoff_status`, `workflow_complete`, `recommended_next_mode`, `next_mode`, and `next_action` are mandatory completion-disambiguation fields. They make the result machine-readable as an incomplete workflow handoff so the active controller can dispatch the required Boomerang `new_task` with its `mode` parameter and does not treat successful materialization as final task completion; `next_mode` without `recommended_next_mode` is non-compliant.
- `routing_control` must include current-hop `allowed_next_modes: [gpt-oss-intake-analyzer]`, `forbidden_next_modes` containing concrete implementation/test/worker slugs such as `code`, `tester`, `test-writer`, `refactorer`, `patch-applier`, and `new-file-writer`, `forbidden_next_mode_classes: [implementation, test, worker]` for future modes, and `completion_unwind` with `return_to_mode: user-response-composer` plus `policy: unwind_parent_chain`.
- The canonical post-materialization chain is context-aware. The canonical non-slash post-materialization chain is `raw-input-materializer → gpt-oss-intake-analyzer → intake-ledger-writer → orchestrator → epoch-orchestrator → atomic workers → state-ledger-writer → orchestrator advances the next epoch`. The canonical slash workflow chain is `raw-input-materializer → gpt-oss-intake-analyzer → intake-ledger-writer → workflow-orchestrator → epoch-orchestrator → atomic workers → state-ledger-writer → workflow-orchestrator advances the next epoch`. Completion must preserve `routing_control.completion_unwind` and unwind through the parent/controller chain to `return_to_mode: user-response-composer` instead of ending in an implementation mode.

## Envelope format

```text
RAW_INPUT_PAYLOAD_V1
delimiter: <opaque delimiter absent from payload>
byte_count: <decimal UTF-8 byte length of payload>
sha256: sha256:<hex of exact payload bytes>

<delimiter>
<exact raw payload bytes>
<delimiter>
END_RAW_INPUT_PAYLOAD_V1
```

The delimiter line is control metadata, not part of the payload. The payload starts immediately after the first delimiter line ending and ends immediately before the second delimiter line ending. The selected delimiter must be high-entropy enough to make accidental collision unlikely and must be scanned against the payload before send. The length and hash are authoritative integrity checks so delimiter parsing cannot silently truncate, extend, or alter the body.

## Routing control

After writing artifacts, raw-input-materializer must use this current-hop handoff metadata and then either call Boomerang `new_task` itself when it is the active intake entry controller, or return it to an existing parent controller:

```yaml
handoff_status: requires_parent_dispatch
workflow_complete: false
recommended_next_mode: gpt-oss-intake-analyzer
next_mode: gpt-oss-intake-analyzer
next_action:
  type: new_task
  tool: new_task
  mode: gpt-oss-intake-analyzer
```

`recommended_next_mode`, `next_mode`, and `next_action` are current-hop dispatch instructions. When `raw-input-materializer` is the entry controller, it must call Boomerang `new_task` for `gpt-oss-intake-analyzer` rather than relying on same-task prose or a bare `switch_mode`; when it was invoked by a parent controller, it returns the same handoff for that parent to dispatch. These fields are not metadata to preserve verbatim: each downstream handoff must update `recommended_next_mode`, `next_mode`, `next_action.mode`, and `routing_control.allowed_next_modes` for its own immediate expected hop (`gpt-oss-intake-analyzer → intake-ledger-writer`, then `intake-ledger-writer → orchestrator` for non-slash intake or `intake-ledger-writer → workflow-orchestrator` for slash workflows). For intake-chain continuation, the active controller should use Boomerang `new_task` and pass the current target slug from `next_action.mode` in the required `mode` parameter; materializer output must not rely on free-form prose or `next_mode` alone to trigger this. `switch_mode` is not the primary intake-chain continuation primitive because it requests a session-level mode change rather than creating the next scoped subtask. `workflow_complete: false` means the overall user request is not complete after raw materialization; the chain must continue until orchestrator/workflow-orchestrator completes or reports a blocker.

Entry-controller tool sequence:

1. Write `RAW_INPUT_REF_V1` artifacts.
2. Call Boomerang `new_task` with `mode: gpt-oss-intake-analyzer` and a path-only message containing `RAW_INPUT_REF_V1`.
3. Wait for the analyzer child and validate it returned `USER_NEEDS_V1` or `USER_NEEDS_SLICE_V1`, `recommended_next_mode: intake-ledger-writer`, `next_action.mode: intake-ledger-writer`, and preserved `routing_control.completion_unwind`.
4. Call Boomerang `new_task` with `mode: intake-ledger-writer` and a path-only message containing `RAW_INPUT_REF_V1` and `USER_NEEDS_V1`.
5. Wait for `SESSION_START_V1`, validate `recommended_next_mode` and `next_action.mode` are `orchestrator` for ordinary intake or `workflow-orchestrator` for slash workflow intake, then call that mode with Boomerang `new_task`.
6. Do not call `attempt_completion` while `workflow_complete: false`; complete only after the orchestrator/workflow-orchestrator child returns final completion or a blocker. If any child task is unavailable, rejected, or malformed, report `DELEGATION_BLOCKED` or `MATERIALIZATION_STALLED_V1`.

```yaml
routing_control:
  # Current-hop allowlist; downstream modes may replace it for their immediate next hop.
  allowed_next_modes:
    - gpt-oss-intake-analyzer
  forbidden_next_modes:
    - code
    - tester
    - test-writer
    - refactorer
    - patch-applier
    - new-file-writer
    - implementation
    - test
    - worker
  forbidden_next_mode_classes:
    - implementation
    - test
    - worker
  completion_unwind:
    return_to_mode: user-response-composer
    policy: unwind_parent_chain
    terminal_mode_must_not_be: code
    terminal_forbidden_modes:
      - code
      - tester
      - test-writer
      - refactorer
      - patch-applier
      - new-file-writer
    terminal_forbidden_mode_classes:
      - implementation
      - test
      - worker
```

`allowed_next_modes` is a current-hop allowlist, not a full chain history. Downstream modes may replace it for their immediate next hop according to the expected-hop map below, but must not remove `completion_unwind`, replace the original `return_to_mode`, or delete concrete implementation/test/worker slugs/classes from `forbidden_next_modes`, `forbidden_next_mode_classes`, `terminal_forbidden_modes`, or `terminal_forbidden_mode_classes`.

### Expected current-hop allowlists

```yaml
expected_allowed_next_modes:
  raw-input-materializer:
    - gpt-oss-intake-analyzer
  gpt-oss-intake-analyzer:
    - intake-ledger-writer
  intake-ledger-writer:
    - orchestrator
  state-ledger-writer:
    - orchestrator
expected_allowed_next_modes_slash_workflow:
  raw-input-materializer:
    - gpt-oss-intake-analyzer
  gpt-oss-intake-analyzer:
    - intake-ledger-writer
  intake-ledger-writer:
    - workflow-orchestrator
  state-ledger-writer:
    - workflow-orchestrator
```

### Routing mode classes

Runtime enforcement should classify concrete mode slugs with this registry in addition to reading the class-level forbidden lists:

```yaml
routing_mode_classes:
  code: implementation
  refactorer: implementation
  tester: test
  test-writer: test
  patch-applier: worker
  new-file-writer: worker
```

## Runtime integration verification boundary

Repository contract validation can verify mode text, routing metadata, and stale wording, but it cannot execute Zoo/Roo Boomerang tools. A runtime integration check outside this repository must verify that starting in `raw-input-materializer` can create child tasks in order (`gpt-oss-intake-analyzer`, `intake-ledger-writer`, then `orchestrator` or `workflow-orchestrator`), that each child completion is returned to the active controller, and that unavailable/rejected `new_task` produces `DELEGATION_BLOCKED` or `MATERIALIZATION_STALLED_V1` instead of same-task continuation.

## Forbidden after materialization

- No downstream mode may receive the raw body inline.
- No intake handoff may skip directly from raw materialization or intake analysis to `code`; implementation starts only after Orchestrator/epoch decomposition.
- GPT-OSS intake, epoch orchestrators, workers, reviewers, testers, documenters, and response composers must use `RAW_INPUT_REF_V1`, manifest paths, chunk paths, line ranges, or derived artifacts.
- If the raw body cannot fit into the first materializer handoff before API send, ZooCodeCustom/runtime pre-LLM materialization must create the artifacts instead.
