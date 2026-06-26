# Composer Terminal Tool Smoke Test

This contract closes the gap that static repository validation cannot verify: whether the active runtime/provider profile actually exposes a terminal completion tool for `user-response-composer`.

## Scope

Run this smoke test before assigning any model/profile to `user-response-composer`, and repeat it after changing runtime, provider, model, tool-calling settings, or terminal tool mappings.

## Preconditions

- The runtime advertises exactly one terminal completion path for `user-response-composer`: Roo/Zoo `attempt_completion` or a runtime-mapped equivalent terminal completion tool.
- The provider/profile has tool calling or function calling enabled for the selected model.
- Plain assistant text is rejected as a terminal response for `user-response-composer`.
- `Gemma4-12B-it` is not assigned to `user-response-composer` unless the provider/profile passes this exact terminal-tool smoke test as an equivalent tool-use-stable profile.

## Smoke test cases

### Case A: successful final response uses terminal completion

Input packet must include complete upstream facts:

```yaml
quality_gate_results: passed
changed_files: []
documentation_updates: []
unresolved_risks: []
completion_ownership_marker: parent_controller_verified
```

Expected result:

- The model calls the terminal completion tool (`attempt_completion` or mapped equivalent).
- The final user response appears only as the terminal tool payload.
- The model does not emit an ordinary assistant-text final response.

### Case B: missing upstream facts returns a terminal blocker

Input packet intentionally omits at least one required upstream fact.

Expected result:

- The model calls the terminal completion tool (`attempt_completion` or mapped equivalent).
- The terminal tool payload contains `COMPOSER_BLOCKED: missing_upstream_artifacts`.
- The payload includes a machine-actionable Recommended Next Mode.
- The model does not call `ask_followup_question`.
- The model does not ask the user to run commands, paste logs, or supply Git/test/build facts.
- The model does not emit the blocker as ordinary assistant text.

## Failure criteria

The profile fails this smoke test if any of the following occurs:

- The terminal completion tool is absent from the runtime tool inventory.
- Provider/profile tool calling or function calling is disabled.
- The model writes the final response or blocker as ordinary assistant text.
- The model requests user-executed command work for inspectable workspace facts.
- The model loops, times out, or retries without producing the terminal tool call.

If any failure criterion is observed, do not assign that provider/profile to `user-response-composer`; route the configuration issue to the parent controller or provider operator instead.
