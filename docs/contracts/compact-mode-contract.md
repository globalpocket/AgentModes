# Compact Mode Global Rules Contract

This contract replaces repeated fixed prompt boilerplate. `rules/00-agentmodes-compact-mode-contract.md` is the live `~/.roo/rules/` Global Rules copy when this repository root is used as the global `.roo` folder, so Zoo/Roo injects it as Global Rules. Mode prompts must not restate it inline.

- Keep mode-local instructions small; mode prompts contain only the role kernel and task-specific boundaries.
- Use current task facts, artifact paths, line ranges, hashes, issue IDs, and exact commands instead of pasted bodies.
- Do not paste full specs, raw prompts, full logs, full diffs, full files, prior handoffs, parent plans, hidden reasoning, or condensed summaries.
- Do not call `run_slash_command` autonomously; slash commands, including `/init`, are user entrypoints only and require explicit user invocation.
- Do not self-dispatch with `new_task` or `switch_mode` unless the mode is an orchestrator.
- Keep visible todos scoped to the current delegated task when todos are needed; never copy parent plans into todos.
- When writing visible todos, use real line breaks between the heading and each checklist item; never emit literal `\n` escape sequences inside the todo text.
- Treat post-condense summaries as advisory; use current artifacts, paths, and cited evidence as source of truth.
- Return compact handoffs that prefer paths, citations, command metadata, and unresolved blockers over copied content.
