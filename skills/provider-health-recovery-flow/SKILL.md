---
name: provider-health-recovery-flow
description: Providerの空応答または生成停止がProvider Health Failureとして分類された後だけ、Recovery Supervisor、Segregated DevOps、Orchestrator再開の順で復旧を調整する
modeSlugs:
  - recovery-supervisor
  - orchestrator
---

# Provider Health Recovery Flow

## Trigger Guard

- Use this flow only after a genuine Provider Health Failure is classified.
- Tool errors, failed tests, incomplete todos, task confusion, and slash command mismatch are not Provider Health Failure.
- Only actual empty response, empty stream, or generation stop are candidates.
- Do not use this flow as a recovery mechanism for incomplete TODO problems.
- Do not create a user-facing Slash Command for this flow.

## Phase 1: provider-failure-classification

- Assigned Mode: `recovery-supervisor`.
- Entry Condition: A provider empty response, empty stream, or generation stop was observed.
- Required Input: Failure fingerprint, observed provider symptom, target task, and last usable handoff.
- Required Output: Provider Health Failure classification or non-provider failure classification.
- Next Phase: `provider-recovery` only when Provider Health Failure is confirmed.

## Phase 2: provider-recovery

- Assigned Mode: `segregated-devops`.
- Entry Condition: Phase 1 confirms Provider Health Failure.
- Required Input: Explicit Provider Recovery Contract including provider name, stop/start commands, port, and health endpoint.
- Required Output: Provider recovery result and minimal verification metadata.
- Required Skill: Load and follow `provider-health-recovery`.
- Do not return to Code mode on recovery failure.

## Phase 3: resume-after-recovery

- Assigned Mode: `orchestrator`.
- Entry Condition: Provider recovery completed or returned a terminal failure.
- Required Input: Latest file state summary and minimal handoff only.
- Required Output: Re-delegation of the interrupted task or terminal workflow failure.
- Do not resend the full previous log after recovery.
- Resume by using latest workspace facts and the smallest sufficient handoff.

## Stop Conditions

- Stop when Phase 1 classifies the issue as non-provider failure.
- Stop when Phase 2 lacks an explicit Provider Recovery Contract.
- Stop when Provider recovery fails; do not route back to Code as a fallback.
- Stop when the original task can be safely re-delegated with minimal context.
