# Phase 4: Intake Recomposition

Ordinary input path:

```text
raw-input-materializer
→ gpt-oss-intake-analyzer
→ intake-ledger-writer
→ orchestrator with SESSION_START_V1 paths only
```

## raw-input-materializer

- raw input preservation
- artifact creation
- manifest/chunk generation
- returns `RAW_INPUT_REF_V1` promptly
- returns `MATERIALIZATION_STALLED_V1` instead of looping if exact artifact metadata cannot be produced by the available workspace capability
- no semantic analysis
- no GPT-OSS analysis
- no Orchestrator dispatch

## gpt-oss-intake-analyzer

- semantic analysis from materialized input
- reads `RAW_INPUT_REF_V1`, manifest, and selected chunks/slices
- `USER_NEEDS_V1` generation
- `USER_NEEDS_SLICE_V1` generation for chunked large input
- no writing, no dispatch
- never re-injects the entire raw artifact as a giant context

## intake-ledger-writer

- accepts `RAW_INPUT_REF_V1` and `USER_NEEDS_V1`
- writes `artifacts/intake/<run-id>/user-needs.yaml`
- initializes `artifacts/state/<run-id>.json`
- returns `SESSION_START_V1` with raw path, manifest path, user-needs path, and state path
- never reposts raw本文

## Deprecated compatibility

`gpt-oss-intake-supervisor` is retained only as a compatibility shim. It is not the ordinary path and must recommend `raw-input-materializer` for raw input or `gpt-oss-intake-analyzer` for existing `RAW_INPUT_REF_V1`.

## pre-LLM limitation

- If the initial provider request itself exceeds context, AgentModes cannot intercept it.
- ZooCodeCustom/runtime pre-LLM materialization is required.
- `raw-input-materializer` is only a fallback for large input that still fits in the current model request.
