# RAW_INPUT_MATERIALIZATION handoff contract

Large inline input has one deliberate exception to the compact packet rule: the orchestrator must pass the verbatim raw body to `raw-input-materializer` exactly once so it can be persisted. Because the raw body may itself contain Markdown fences, logs, or arbitrary delimiter-looking text, the handoff must use an escape-safe `RAW_INPUT_PAYLOAD_V1` envelope instead of a fixed fence.

## Required handoff

- The first subtask for large inline input is `raw-input-materializer`.
- That subtask's message must contain exactly one escape-safe `RAW_INPUT_PAYLOAD_V1` envelope carrying the exact raw input body.
- The envelope declares `delimiter`, `byte_count`, and `sha256` metadata before the body.
- The orchestrator must choose a delimiter string that does not occur anywhere in the raw body; if no safe delimiter can be selected within the current request, it must use ZooCodeCustom/runtime pre-LLM materialization instead.
- The materializer must verify the closing delimiter, byte count, and sha256 before writing artifacts; mismatches produce `MATERIALIZATION_STALLED_V1` and must not create a best-effort raw artifact.
- The packet must instruct the materializer to write only `artifacts/intake/<run-id>/raw-request.md`, optional size chunks, and `raw-request.manifest.json`.
- The materializer returns `RAW_INPUT_REF_V1` path metadata and stops.

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

## Forbidden after materialization

- No downstream mode may receive the raw body inline.
- GPT-OSS intake, epoch orchestrators, workers, reviewers, testers, documenters, and response composers must use `RAW_INPUT_REF_V1`, manifest paths, chunk paths, line ranges, or derived artifacts.
- If the raw body cannot fit into the first materializer handoff before API send, ZooCodeCustom/runtime pre-LLM materialization must create the artifacts instead.
