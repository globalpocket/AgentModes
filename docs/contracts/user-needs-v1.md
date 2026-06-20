# USER_NEEDS_V1 Intake Contract

`USER_NEEDS_V1` is the normalized intake artifact produced before regular Orchestrator receives a task. It prevents large raw prompts from becoming long-lived Orchestrator context.

```yaml
USER_NEEDS_V1:
  source_kind: short_request | long_request | github_issue_url
  explicit_goal: ""
  explicit_requirements: []
  hard_constraints: []
  acceptance_criteria: []
  explicit_first_steps: []
  out_of_scope: []
  derived_constraints: []
  safe_assumptions: []
  inspection_requests: []
  required_user_decisions: []
  confidence: high | medium | low
```

Separation rules:

- `explicit_requirements`: only what the user directly stated.
- `derived_constraints`: constraints logically required by explicit requirements.
- `safe_assumptions`: reversible assumptions that allow work to proceed.
- `required_user_decisions`: product or policy choices the model must not decide.
- For GitHub Issue URLs, store the URL only; do not infer issue body, labels, or acceptance criteria until `issue-reader` fetches them.
