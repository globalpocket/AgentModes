---
name: orchestrator-delegation-guardrails
description: On-demand guardrails for detailed TASK_PACKET, command, artifact, GitHub, release, and failure handling that no longer belong in long-lived Orchestrator prompts.
modeSlugs:
  - orchestrator
  - workflow-orchestrator
  - epoch-orchestrator
---

# Orchestrator Delegation Guardrails

Load this Skill only when a short-lived planning step needs detailed packet, command, artifact, GitHub, release, or failure-handling examples.

## Scope

- Detailed `commands` schema examples.
- Artifact handoff conflict examples.
- Tester artifact authority examples.
- GitHub/release/diagnostic gate examples.
- Failure fingerprint and same-failure escalation examples.
- Documentation routing examples such as `doc-evidence-reader first, then analyzer, then librarian`.

Long-lived Orchestrator prompts must keep only durable cursor and sparse packet contracts; they should not inline these examples.
