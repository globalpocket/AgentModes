# RAW_INPUT_MATERIALIZATION handoff contract

Large inline input has one deliberate exception to the compact packet rule: the orchestrator must pass the verbatim raw body to `raw-input-materializer` exactly once so it can be persisted.

## Required handoff

- The first subtask for large inline input is `raw-input-materializer`.
- That subtask's message must contain a fenced `RAW_INPUT_PAYLOAD` field with the exact raw input body.
- The packet must instruct the materializer to write only `artifacts/intake/<run-id>/raw-request.md`, optional size chunks, and `raw-request.manifest.json`.
- The materializer returns `RAW_INPUT_REF_V1` path metadata and stops.

## Forbidden after materialization

- No downstream mode may receive the raw body inline.
- GPT-OSS intake, epoch orchestrators, workers, reviewers, testers, documenters, and response composers must use `RAW_INPUT_REF_V1`, manifest paths, chunk paths, line ranges, or derived artifacts.
- If the raw body cannot fit into the first materializer handoff before API send, ZooCodeCustom/runtime pre-LLM materialization must create the artifacts instead.
