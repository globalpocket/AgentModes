---
name: provider-health-recovery-flow
description: recovery-supervisorがProvider Health Failureを確認した後だけ、Segregated DevOpsによる復旧とOrchestratorによる直前タスク再開を調整する
modeSlugs:
  - orchestrator
---

# Provider Health Recovery Flow

## Entry Contract

- Load this Skill only after `recovery-supervisor` explicitly returns `Provider Health Failure: confirmed` or an equivalent explicit confirmation.
- This Skill does not classify provider failures and must not repeat the classification phase.
- The observed symptom must be an actual empty response, empty stream, or generation stop.
- Tool errors, failed tests, incomplete todos, task confusion, and slash command mismatch are not valid entry conditions.
- Do not use this Skill as a recovery mechanism for incomplete TODO problems.
- Do not expose a user-facing Slash Command for this flow.

## Phase 1: provider-recovery

- Assigned Mode: `segregated-devops`.
- Entry Condition: Provider Health Failure has already been explicitly confirmed by `recovery-supervisor`.
- Required Input: Explicit Provider Recovery Contract including provider name, exact target terminal or process identifier, stop method, start command, health check, and minimal non-empty generation check.
- Required Output: Provider recovery result and minimal verification metadata.
- Required Skill: Load and follow `provider-health-recovery`.
- Next Phase: `resume-after-recovery` only when recovery succeeds.
- Terminal Failure: If the Provider Recovery Contract is missing or recovery fails, stop with workflow failure. Do not return to Code mode.

## Phase 2: resume-after-recovery

- Assigned Mode: `orchestrator`.
- Entry Condition: Phase 1 reports successful Provider recovery.
- Required Input: Latest workspace state summary and the smallest sufficient interrupted-task handoff.
- Required Output: Re-delegation of the interrupted task using the latest workspace state.
- Do not resend the full previous log.
- Do not reuse stale file contents, stale command results, or stale task packets.
- Preserve the raw user task as source of truth.

## Stop Conditions

- If Provider Health Failure has not been explicitly confirmed, do not load this Skill; route classification to `recovery-supervisor`.
- If the Provider Recovery Contract is incomplete, perform no stop, restart, port probe, or endpoint probe.
- If recovery fails, mark the flow terminally failed and do not route back to Code as a fallback.
- Never use this flow for incomplete todos, completion-gate rejection, failed tests, missing slash commands, or task confusion.
