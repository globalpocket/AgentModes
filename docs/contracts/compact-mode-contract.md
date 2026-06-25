# Compact Mode Global Rules Contract

This contract replaces repeated fixed prompt boilerplate. `rules/00-agentmodes-compact-mode-contract.md` is the live `~/.roo/rules/` Global Rules copy when this repository root is used as the global `.roo` folder, so Zoo/Roo injects it as Global Rules. Mode prompts must not restate it inline.

- Keep mode-local instructions small; mode prompts contain only the role kernel and task-specific boundaries.
- Use current task facts, artifact paths, line ranges, hashes, issue IDs, and exact commands instead of pasted bodies.
- Do not paste full specs, raw prompts, full logs, full diffs, full files, prior handoffs, parent plans, hidden reasoning, or condensed summaries.
- Do not call `run_slash_command` autonomously; slash commands, including `/init`, are user entrypoints only and require explicit user invocation.
- Do not self-dispatch with `new_task` or `switch_mode` unless the mode is an orchestrator or an explicit intake controller such as `raw-input-materializer`.
- Controller delegation means creating a child task with Boomerang `new_task(mode, message)` and then stopping the parent turn until the child returns a completion summary; it is not a same-task mode change. Orchestrator modes use this for work decomposition; `raw-input-materializer` uses it only to continue the fixed intake chain after writing RAW_INPUT_REF_V1.
- A `switch_mode` transition can be valid as part of runtime setup or an explicit session-level mode change, but it does not constitute delegation by itself. If no child task is created with `new_task`, report `DELEGATION_BLOCKED` instead of continuing delegated work in the current task.
- Keep visible todos scoped to the current delegated task when todos are needed; never copy parent plans into todos.
- When writing visible todos, use real line breaks between the heading and each checklist item; never emit literal `\n` escape sequences inside the todo text.
- Treat post-condense summaries as advisory; use current artifacts, paths, and cited evidence as source of truth.
- Verified completion requires evidence: implementation handoffs, diffs, written claims, or terms like “done”, “implemented”, “fixed”, “should pass”, and “verified” are not completion evidence unless attached to successful required quality gate command results or required static invariant checks.
- Return compact handoffs that prefer paths, citations, command metadata, and unresolved blockers over copied content.

## No Human-as-Executor Contract

Inspectable workspace facts are facts obtainable from the workspace, artifacts, child tasks, CI, GitHub, Git state, command tools, or runtime tools. Modes must not use the user as a command runner, test executor, Git operator, log provider, clipboard transport, or judgment substitute for inspectable workspace facts.

- Do not ask the user to run shell, Git, test, lint, build, typecheck, CI, or workspace inspection commands.
- Do not ask the user to paste stdout, stderr, exit codes, Git status, diffs, test results, build results, logs, workspace state, or other inspectable workspace facts.
- Do not ask the user to decide mechanically checkable facts from the workspace.
- Do not substitute user manual work for missing tools, permissions, or capabilities.
- If assigned command capability and an exact command, cwd/scope, and action contract are present, execute the command yourself and return command metadata, exit status, concise stdout/stderr summary, and artifact paths when needed.
- If execution or inspection is impossible, return a structured blocker such as `COMMAND_EXECUTION_BLOCKED`, `BLOCKED_DELTA_V1`, `VERIFICATION_BLOCKED`, or `DELEGATION_BLOCKED` with the exact command or needed fact, cwd/scope, reason, missing capability/permission/tool/environment, and the next machine-actionable parent-controller step.
- Orchestrator/controller modes must not execute commands or choose slash commands as routing fallback; delegate command needs to the smallest command-capable worker with Boomerang `new_task(mode, message)`, or return `DELEGATION_BLOCKED` when delegation is unavailable.
- Read-only or edit-only modes that need command results must return a blocker with `required_capability: command` and enough command/cwd/scope/action-contract detail for a parent controller to delegate; they must not ask the user to run the command.
- Final-response composition may describe blocked status and unrun gates, but must not convert an internal blocker into a request for the user to run commands or paste command output.
