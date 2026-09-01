# AgentModes v2

AgentModes v2 is a Brownie Runtime contract library. It is no longer a ZooCodeCustom or RooCode custom-mode import bundle.

In v2, an AgentMode is a single-pass, bounded role contract invoked by Brownie Runtime. The Runtime owns loop control, phase management, retries, stop decisions, next-role selection, context assembly, Git operations, and model routing.

## Distribution Model

The free and open-source AgentModes distribution includes AgentModes Core only.

AgentModes Core includes:

- `schemas/`
- `core/`
- `runtime-policies/brownie/`
- `maintenance/`

AgentModes Core does not include full workflow packs. The `packs/development` role contracts are part of the member-only pack distribution delivered through GitHub Sponsors or another private member channel. The development pack is expected to move to a separate repository as the distribution matures.

This keeps the open-source project useful as a stable contract OS for Brownie while making specialized execution packs a sustainable paid layer.

## Core Principles

- An AgentMode is one bounded execution unit.
- An AgentMode does not control a loop.
- An AgentMode does not directly call another mode.
- An AgentMode does not update workflow phase on behalf of the Runtime.
- An AgentMode uses only the permissions granted in its invocation.
- An AgentMode returns a structured result that Brownie Runtime can parse.
- Brownie Runtime controls loop, retry, stop, phase transition, context assembly, Git operation, and model selection.

## Responsibility Boundary

Brownie Runtime owns:

- Development-loop state such as `DISCOVER -> PLAN -> IMPLEMENT -> TEST -> REVIEW -> INTEGRATE -> REPORT -> NEXT_PHASE or STOP`.
- Phase transitions and stop conditions.
- Retry scheduling and retry budgets.
- Context assembly, compaction, source selection, and durable state hydration.
- Selection of the next role and invocation ordering.
- Model routing and reasoning budget selection.
- Git status, branch, commit, merge, revert, and integration workflow policy.
- Permission grants for each role invocation.

AgentModes own:

- A bounded behavior objective for one role.
- Required inputs and required outputs.
- Permission declarations and prohibited actions.
- Quality gates the role must satisfy before returning.
- Structured result production.
- Local judgment inside the assigned scope only.

AgentModes must not:

- Dispatch or call another mode.
- Continue the conversation as a workflow controller.
- Decide that the global workflow should loop, stop, or advance phase.
- Mutate Runtime phase, durable ledger, Git state, or model configuration unless explicitly granted for the single invocation.
- Embed ZooCodeCustom/RooCode UI metadata, mode-switching prose, Boomerang `new_task` instructions, or recursive handoff instructions in v2 core definitions.

## Repository Layout

| Path | Purpose |
| --- | --- |
| `schemas/` | Shared schemas for roles, invocations, results, permissions, and quality gates. |
| `core/` | Runtime-neutral role contracts such as orchestrator, reviewer, and reporter. |
| `packs/` | Pack extension points and placeholders. Full workflow packs are distributed separately when they are member-only, and may live in separate repositories. |
| `runtime-policies/brownie/` | Brownie-owned policies for loop, phase, context, retry, Git, and model routing. |
| `legacy/zoocode/` | ZooCodeCustom/RooCode v1 compatibility material. v2 core must not reference it. |
| `maintenance/` | v2 repository checks. |

## Invocation Model

Brownie Runtime invokes a role with `ROLE_INVOCATION_V1`:

```yaml
schema: ROLE_INVOCATION_V1
role_id: core.orchestrator
work_unit:
  id: work-unit-id
  objective: bounded objective
  acceptance_criteria: []
context:
  artifacts: []
  files: []
  prior_results: []
permissions:
  read: true
  edit: false
  command: false
  git: false
  network: false
budgets:
  max_files: 5
  max_commands: 0
  max_iterations: 1
```

Every role returns `ROLE_RESULT_V1` or a role-specific schema that includes the shared result fields:

```yaml
schema: ROLE_RESULT_V1
role_id: core.orchestrator
status: completed
summary: concise result summary
changed_files: []
verification: []
risks: []
blockers: []
next_recommendation:
  type: continue
  recommended_role: external.pack.role
  rationale: why this is useful
confidence: medium
```

`next_recommendation` is advisory. Brownie Runtime decides whether to use it.

## Core Role Set

The open-source Core role set is intentionally small:

- `core.orchestrator`
- `core.reviewer`
- `core.reporter`

Member-only development pack roles are distributed outside the Core repository and are expected to move to a dedicated development-pack repository. The initial development pack is expected to include:

- `packs.development.requirements-analyst`
- `packs.development.implementation-worker`
- `packs.development.test-writer`
- `packs.development.verification-reviewer`
- `packs.development.documentation-updater`
- `packs.development.verified-integrator`

Brownie policies:

- `runtime-policies/brownie/loop-policy.yaml`
- `runtime-policies/brownie/phase-policy.yaml`
- `runtime-policies/brownie/context-policy.yaml`
- `runtime-policies/brownie/retry-policy.yaml`
- `runtime-policies/brownie/git-policy.yaml`
- `runtime-policies/brownie/model-routing-policy.yaml`

## Legacy Boundary

The legacy ZooCodeCustom/RooCode material is preserved under `legacy/zoocode/`.

That material may contain custom-mode fields, UI labels, slash-command entrypoints, Boomerang handoff language, `switch_mode`, `new_task`, self-loop instructions, and old completion semantics. Those are compatibility artifacts only. v2 definitions in `schemas/`, `core/`, `packs/`, and `runtime-policies/brownie/` must not depend on or import anything from `legacy/zoocode/`.

## Validation

Run:

```bash
python maintenance/validate-v2.py
```

The validator checks that required v2 Core files exist, Core role definitions contain the required contract fields, member-only pack role YAML is not present in the open-source tree, and v2 role/policy contracts do not contain legacy dispatch markers.
