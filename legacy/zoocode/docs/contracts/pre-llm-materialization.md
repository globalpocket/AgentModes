# Pre-LLM Materialization Boundary

AgentModes prompt contracts run only after a provider request reaches a model. Therefore AgentModes cannot prevent context overflow when the initial API request already exceeds the provider context limit.

ZooCodeCustom/runtime must provide pre-LLM materialization for oversized inline input before API send. That runtime materializer should preserve raw input into workspace artifacts, create a manifest/chunks, and pass only `RAW_INPUT_REF_V1` paths into AgentModes.

The `raw-input-materializer` mode is a fallback for large input that still fits in the active request; it is not the root defense against provider-context overflow. When started as the intake entry controller, it persists the raw input verbatim, emits `RAW_INPUT_REF_V1`, and continues the fixed intake chain via Boomerang `new_task`; when invoked by a parent controller, it may return the path-only handoff for that parent to dispatch. Semantic analysis still belongs to `gpt-oss-intake-analyzer`, and implementation/test work must not receive raw bodies.
