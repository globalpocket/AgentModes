# RAW_INPUT_MATERIALIZATION handoff contract

Large inline input has one deliberate exception to the compact packet rule: the orchestrator must pass the verbatim raw body to `raw-input-materializer` exactly once so it can be persisted. Because the raw body may itself contain Markdown fences, logs, or arbitrary delimiter-looking text, the handoff must use an escape-safe `RAW_INPUT_PAYLOAD_V1` envelope instead of a fixed fence.

## Required handoff

- The first subtask for large inline input is `raw-input-materializer`.
- That subtask's message must contain exactly one escape-safe `RAW_INPUT_PAYLOAD_V1` envelope carrying the exact raw input body.
- The envelope declares `delimiter`, `byte_count`, and `sha256` metadata before the body.
- The orchestrator must choose a delimiter string that does not occur anywhere in the raw body; if no safe delimiter can be selected within the current request, it must use ZooCodeCustom/runtime pre-LLM materialization instead.
- The materializer must verify the closing delimiter, byte count, and sha256 before writing artifacts; mismatches produce `MATERIALIZATION_STALLED_V1` and must not create a best-effort raw artifact.
- The packet must instruct the materializer to write only `artifacts/intake/<run-id>/raw-request.md`, optional size chunks, and `raw-request.manifest.json`.
- The materializer returns `RAW_INPUT_REF_V1` path metadata with `handoff_status: requires_parent_dispatch`, `workflow_complete: false`, `next_mode: gpt-oss-intake-analyzer`, `next_action: {type: new_task, tool: new_task, mode: gpt-oss-intake-analyzer}`, and `routing_control`, then stops this mode only; it must never recommend or route to `code`, implementation, test, or worker modes.
- `handoff_status`, `workflow_complete`, and `next_action` are mandatory completion-disambiguation fields. They make the result machine-readable as an incomplete workflow handoff so Roo/Zoo runtimes can dispatch the required Boomerang `new_task` with its `mode` parameter and do not treat successful materialization as final task completion.
- `routing_control` must include current-hop `allowed_next_modes: [gpt-oss-intake-analyzer]`, `forbidden_next_modes` containing concrete implementation/test/worker slugs such as `code`, `tester`, `test-writer`, `refactorer`, `patch-applier`, and `new-file-writer`, `forbidden_next_mode_classes: [implementation, test, worker]` for future modes, and `completion_unwind` with `return_to_mode: user-response-composer` plus `policy: unwind_parent_chain`.
- The canonical post-materialization chain is `raw-input-materializer → gpt-oss-intake-analyzer → intake-ledger-writer → orchestrator → epoch-orchestrator → atomic workers → state-ledger-writer → orchestrator advances the next epoch`. Completion must preserve `routing_control.completion_unwind` and unwind through the parent/controller chain to `return_to_mode: user-response-composer` instead of ending in an implementation mode.

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

Every post-materialization handoff must preserve this routing metadata until final completion:

```yaml
handoff_status: requires_parent_dispatch
workflow_complete: false
next_mode: gpt-oss-intake-analyzer
next_action:
  type: new_task
  tool: new_task
  mode: gpt-oss-intake-analyzer
```

`next_mode` and `next_action` are advisory instructions for the parent/runtime controller, not permission for the materializer to self-dispatch. For intake-chain continuation, the controller should use Boomerang `new_task` and pass the target slug in the required `mode` parameter. `switch_mode` is not the primary intake-chain continuation primitive because it requests a session-level mode change rather than creating the next scoped subtask. `workflow_complete: false` means the overall user request is not complete even though the materializer mode must stop after returning the handoff.

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

## Forbidden after materialization

- No downstream mode may receive the raw body inline.
- No intake handoff may skip directly from raw materialization or intake analysis to `code`; implementation starts only after Orchestrator/epoch decomposition.
- GPT-OSS intake, epoch orchestrators, workers, reviewers, testers, documenters, and response composers must use `RAW_INPUT_REF_V1`, manifest paths, chunk paths, line ranges, or derived artifacts.
- If the raw body cannot fit into the first materializer handoff before API send, ZooCodeCustom/runtime pre-LLM materialization must create the artifacts instead.
