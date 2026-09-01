# GPT-OSS Downstream-Compatible Output Policy

This document is the canonical source of truth for GPT-OSS handoff behavior in AgentModes. GPT-OSS modes are high-reasoning artifact producers, not free-form advisors. Downstream Qwen modes consume explicit schema fields and must not reinterpret raw reasoning.

## Canonical policy

```yaml
gpt_oss_downstream_compatible_output_policy:
  required_fields:
    - schema
    - producer_mode
    - intended_consumer
    - source_of_truth
    - objective
    - decisions
    - assumptions
    - constraints
    - acceptance_criteria
    - blockers
    - recommended_next_mode
    - confidence
  optional_but_recommended_fields:
    - artifact_path
    - evidence_paths
    - unresolved_questions
    - handoff_policy
    - loss_report
  handoff_policy:
    downstream_must_not_reinfer: true
    downstream_should_treat_as_advisory: true
    downstream_should_escalate_if_fields_missing: true
    downstream_high_reasoning_delegate: epoch-orchestrator
```

## Producer and consumer coverage

```yaml
gpt_oss_policy_coverage:
  producer_slugs:
    - architect
    - gpt-oss-intake-analyzer
    - gpt-oss-intake-supervisor
    - gpt-oss-needs-analyzer
    - reviewer
    - security-auditor
    - recovery-supervisor
    - secret-auditor
    - dependency-auditor
    - unsafe-code-auditor
    - fabricated-package-auditor
    - implementation-reviewer
    - architecture-reviewer
    - test-reviewer
    - performance-risk-reviewer
    - security-risk-classifier
  consumer_slugs:
    - orchestrator
    - workflow-orchestrator
    - state-ledger-reader
    - artifact-reader
    - contract-checker
    - ledger-consistency-checker
    - handoff-consistency-checker
```

## Standard schema map

```yaml
gpt_oss_standard_schema_map:
  gpt-oss-needs-analyzer:
    - ORCHESTRATOR_BRIEF_V1
  gpt-oss-intake-analyzer:
    - USER_NEEDS_V1
    - USER_NEEDS_SLICE_V1
  gpt-oss-intake-supervisor:
    - GPT_OSS_SHIM_HANDOFF_V1
  architect:
    - ARCHITECTURE_PLAN_V1
    - TASK_DECOMPOSITION_V1
  reviewer:
    - REVIEW_FINDING_V1
    - REVIEW_REPORT_V1
  atomic_reviewers:
    - REVIEW_FINDING_V1
    - REVIEW_REPORT_V1
  security-auditor:
    - SECURITY_FINDING_V1
    - SECURITY_AUDIT_REPORT_V1
  security-risk-classifier:
    - SECURITY_FINDING_V1
    - SECURITY_AUDIT_REPORT_V1
  atomic_security_auditors:
    - SECURITY_FINDING_V1
    - SECURITY_AUDIT_REPORT_V1
  recovery-supervisor:
    - RECOVERY_PLAN_V1
```

## Schema field contracts

All schema artifacts listed above must include the canonical required fields. Domain-specific content should be placed inside explicit fields rather than prose-only reasoning:

- `ORCHESTRATOR_BRIEF_V1`: user objective, scope boundaries, constraints, risks, acceptance criteria, blockers, and recommended next mode.
- `USER_NEEDS_V1` / `USER_NEEDS_SLICE_V1`: explicit requirements, derived constraints, assumptions, required decisions, risks, and acceptance criteria.
- `GPT_OSS_SHIM_HANDOFF_V1`: compatibility route, source artifact reference, blocker state if routing metadata is incomplete, and next mode recommendation.
- `ARCHITECTURE_PLAN_V1` / `TASK_DECOMPOSITION_V1`: architectural decisions, task boundaries, dependencies, constraints, acceptance criteria, unresolved questions, and next delegation mode.
- `REVIEW_FINDING_V1` / `REVIEW_REPORT_V1`: findings, severity, evidence paths, affected scope, acceptance impact, residual risk, and recommended next mode.
- `SECURITY_FINDING_V1` / `SECURITY_AUDIT_REPORT_V1`: security findings, exploitability or risk class, evidence paths, affected assets, mitigation constraints, blockers, and recommended next mode.
- `RECOVERY_PLAN_V1`: failure class, loop/stall evidence, recovery decisions, constraints, stop conditions, blockers, and recommended next mode.

## Consumer rule

Qwen and other downstream modes must treat GPT-OSS artifacts as execution cursors. They must read explicit fields only. If required fields are missing, they must block or escalate instead of reconstructing intent from free-form reasoning.
