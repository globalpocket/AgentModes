---
name: orchestrator-workflows
description: Orchestratorで `/tdd-quality-gate` または `/github-issue-main-task` を実行するとき、固定phase順序、TASK_PACKET preflight、Scoped TODO Projection、条件付き品質ゲートを適用する
modeSlugs:
  - orchestrator
---

# Orchestrator Workflows

## Runtime Invariants

- The raw user prompt is the source of truth.
- This Skill provides runtime workflow procedure only and never overrides the raw user prompt.
- Apply `Scoped TODO Projection Protocol` before every delegation.
- Keep the visible TODO list to exactly the current single task.
- Do not call `new_task` before `TASK_PACKET Preflight Gate` passes.
- Do not pass parent workflow TODO items to delegated modes.
- Do not make a delegated mode retry the same `attempt_completion` payload after rejection.
- Do not ask the user for inspectable workspace facts; delegate inspection to the least-privilege mode.
- If a phase condition is false, explicitly skip that phase and proceed to the next phase.
- Advance exactly one phase at a time.
- Do not convert the full workflow into one oversized `TASK_PACKET`.

## Workflow Selection

- Use `Workflow: tdd-quality-gate` when `/tdd-quality-gate` is invoked.
- Use `Workflow: github-issue-main-task` when `/github-issue-main-task` is invoked.
- Preserve the slash-command argument as raw workflow input.
- Use one delegated `TASK_PACKET_V1` per phase when delegation is required.

## Workflow: tdd-quality-gate

### Phase: artifact-initialize
- Assigned Mode: `artifact-manager`
- Entry Condition: Workflow starts.
- Required Input: Artifact root `artifacts/`.
- Required Output: Initialized artifact directories or explicit skip/failure.
- Next Phase: `design-plan`

### Phase: design-plan
- Assigned Mode: `architect`
- Entry Condition: A design or implementation decomposition is needed.
- Required Input: Raw task goal and known constraints.
- Required Output: Lightweight TDD plan with Level, test classification, Red-Green-Refactor flow, Coverage 85% gate, security-auditor gate, reviewer gate, and artifact handoff.
- Next Phase: `red-write`

### Phase: red-write
- Assigned Mode: `test-writer`
- Entry Condition: Minimal Red tests are required by the plan.
- Required Input: Test target, contracts, exact imports, allowed test doubles, and expected Red signature.
- Required Output: Created or updated minimal contract, behavior, or regression tests.
- Next Phase: `red-contract-check`

### Phase: red-contract-check
- Assigned Mode: `consistency-checker`
- Entry Condition: Red tests were written.
- Required Input: Changed test files and expected contracts.
- Required Output: Pass/fail judgment for test contract scope and inventory risk.
- Next Phase: `red-artifact-prepare`

### Phase: red-artifact-prepare
- Assigned Mode: `artifact-manager`
- Entry Condition: Red command artifact path is known.
- Required Input: Red artifact path under `artifacts/`.
- Required Output: Prepared parent directory.
- Next Phase: `red-run`

### Phase: red-run
- Assigned Mode: `tester`
- Entry Condition: Red test command is specified.
- Required Input: One command writing stdout/stderr to the Red artifact path with preserved exit status.
- Required Output: Command metadata and artifact status.
- Next Phase: `red-judge`

### Phase: red-judge
- Assigned Mode: `consistency-checker`
- Entry Condition: Red command artifact exists or artifact status is known.
- Required Input: Red artifact path and expected Red signature.
- Required Output: Expected-red-match or failure classification.
- Next Phase: `green-implement`

### Phase: green-implement
- Assigned Mode: `code`
- Entry Condition: Red result matches the expected Red signature.
- Required Input: Allowed edit files, failing contract, and complete syntax blocks when needed.
- Required Output: Minimal Green implementation and tester command candidates.
- Next Phase: `green-artifact-prepare`

### Phase: green-artifact-prepare
- Assigned Mode: `artifact-manager`
- Entry Condition: Green command artifact path is known.
- Required Input: Green artifact path under `artifacts/`.
- Required Output: Prepared parent directory.
- Next Phase: `green-run`

### Phase: green-run
- Assigned Mode: `tester`
- Entry Condition: Green verification command is specified.
- Required Input: One command writing stdout/stderr to the Green artifact path with preserved exit status.
- Required Output: Command metadata and artifact status.
- Next Phase: `green-coverage-judge`

### Phase: green-coverage-judge
- Assigned Mode: `consistency-checker`
- Entry Condition: Green or coverage artifact exists or artifact status is known.
- Required Input: Green artifact path, coverage artifact path when applicable, and Coverage 85% threshold.
- Required Output: Test Green judgment and coverage pass/fail.
- Next Phase: `test-inventory-judge`

### Phase: test-inventory-judge
- Assigned Mode: `consistency-checker`
- Entry Condition: Final tests are available for review.
- Required Input: Test file list and lightweight TDD constraints.
- Required Output: Pass/fail judgment for over-testing, exploratory leftovers, and test classification.
- Next Phase: `security-audit`

### Phase: security-audit
- Assigned Mode: `security-auditor`
- Entry Condition: Green and coverage gates pass.
- Required Input: Changed files, dependency manifests when relevant, and known security constraints.
- Required Output: Security pass/fail, critical findings, evidence, and fix direction.
- Next Phase: `quality-review`

### Phase: quality-review
- Assigned Mode: `reviewer`
- Entry Condition: Security audit passes or has no blocking findings.
- Required Input: Changed files, verification results, plan, and remaining risks.
- Required Output: Final quality pass/fail, critical findings, suggestions, and remaining risks.
- Next Phase: `failure-recovery-conditional`

### Phase: failure-recovery-conditional
- Assigned Mode: `recovery-supervisor`
- Entry Condition: The same failure fingerprint repeats or a mode cannot converge.
- Required Input: Failure fingerprint, target, mode, signature, and prior handoff.
- Required Output: Revised delegation path or terminal failure recommendation.
- Next Phase: Workflow completion or redesigned phase.

## Workflow: github-issue-main-task

### Phase: artifact-initialize
- Assigned Mode: `artifact-manager`
- Entry Condition: Workflow starts.
- Required Input: Artifact root `artifacts/`.
- Required Output: Initialized artifact directories or explicit skip/failure.
- Next Phase: `github-origin-gate`

### Phase: github-origin-gate
- Assigned Mode: `orchestrator`
- Entry Condition: Raw workflow input is available.
- Required Input: GitHub Issue URL or explicit owner/repo/issue number.
- Required Output: GitHub Integration State classified as `github`, `non-github`, or `unknown-skipped`.
- Next Phase: `issue-intake-routing`

### Phase: issue-intake-routing
- Assigned Mode: `issue-tracker`
- Entry Condition: GitHub Integration State is `github`.
- Required Input: Issue URL or owner/repo/issue number.
- Required Output: Active issue context, parent/sub-issue route, and concise status comment when applicable.
- Next Phase: `sub-issue-decomposition-conditional`

### Phase: sub-issue-decomposition-conditional
- Assigned Mode: `architect`
- Entry Condition: Parent issue requires decomposition into sub-issues.
- Required Input: Parent issue context and acceptance criteria.
- Required Output: Sub-issue specifications or explicit skip.
- Next Phase: `sub-issue-create-conditional`

### Phase: sub-issue-create-conditional
- Assigned Mode: `issue-tracker`
- Entry Condition: Sub-issue specifications exist.
- Required Input: Parent issue and sub-issue specifications.
- Required Output: Created sub-issues with link status and inherited assignees, or explicit skip.
- Next Phase: `delegation-comment-conditional`

### Phase: delegation-comment-conditional
- Assigned Mode: `issue-tracker`
- Entry Condition: Active sub-issue is selected for execution.
- Required Input: Active issue, scope, next action, and quality gate summary.
- Required Output: Concise delegation/progress comment or explicit skip.
- Next Phase: `tdd-quality-gate`

### Phase: tdd-quality-gate
- Assigned Mode: Workflow `tdd-quality-gate`
- Entry Condition: Implementation is required for the active issue.
- Required Input: Active issue context and acceptance criteria.
- Required Output: Completed local quality workflow with tests, coverage, security audit, and reviewer result.
- Next Phase: `version-tag-push-conditional`

### Phase: version-tag-push-conditional
- Assigned Mode: `release-manager`
- Entry Condition: GitHub-origin task and all quality gates passed.
- Required Input: Version file, branch, quality gate summaries, and push target.
- Required Output: Version bump, `v<version>` tag, and branch/tag push result, or explicit skip.
- Next Phase: `diagnostic-issue-create-conditional`

### Phase: diagnostic-issue-create-conditional
- Assigned Mode: `diagnostic-reporter`
- Entry Condition: Release manager succeeded for a GitHub-origin task.
- Required Input: Source issue, quality gates, version, tag, and project state.
- Required Output: Diagnostic issue URL/number/title or explicit skip.
- Next Phase: `completion-comment-conditional`

### Phase: completion-comment-conditional
- Assigned Mode: `issue-tracker`
- Entry Condition: Active sub-issue work is complete.
- Required Input: Active issue, quality gates, artifacts, release, and diagnostic issue when present.
- Required Output: Completion comment and close only the active sub-issue when applicable.
- Next Phase: `return-to-parent-routing-conditional`

### Phase: return-to-parent-routing-conditional
- Assigned Mode: `issue-tracker`
- Entry Condition: Active issue is a sub-issue and parent routing is required.
- Required Input: Parent issue, completed sub-issue, and remaining open sub-issues.
- Required Output: Parent routing context or explicit skip.
- Next Phase: Workflow completion.

## Completion and Failure

- When a next phase exists, project only that phase into the visible TODO list.
- On successful workflow completion with no next phase, set the visible TODO to `[x] workflow: completed`.
- On terminal failure, set the visible TODO to `[x] workflow: failed`.
- `WAITING_EXTERNAL` is not terminal.
- Never report a failed command, unsatisfied done condition, or terminal unsuccessful outcome as `completed`.
- Do not leave pending or in-progress TODO items before the final `attempt_completion`.
