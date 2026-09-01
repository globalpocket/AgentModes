# Verified Completion Contract

This contract applies to implementation, configuration, CI, docs, schema, generated artifact, workflow, infrastructure, and test-framework changes. Completion is based on verification evidence, not self-attestation.

## Principle

* A diff is not completion.
* A mode handoff is not completion.
* A written claim is not completion.
* Completion requires evidence that the delegated acceptance criteria and quality gates passed.

## Completion statuses

* COMPLETE: all required gates passed
* FAILED: implementation or verification failed
* PARTIAL: some gates passed but not all
* VERIFICATION_BLOCKED: verification could not be run
* IMPLEMENTATION_ONLY: code/config/docs were changed but not verified

## Generic required evidence

* command
* cwd
* exit_status
* artifact_path or compact output summary
* static check result when applicable

## Quality gates by task type

* Implementation: format/lint/typecheck/build/test as relevant
* Library/API change: compile/typecheck/tests and API contract checks
* Runtime/behavior change: targeted tests and regression tests
* Schema/config change: schema validation and generator/contract checks
* CI change: workflow file validation and repository verification scripts when available
* Docs change: docs generation, markdown validation, links or configured docs checks when available
* Generated artifact change: generator command plus diff/validation of generated output
* Security-sensitive change: security/audit mode or configured scanner when delegated

## Invalid completion

* “Implemented” without verification
* “Looks good” without command evidence
* “Tests should pass” without execution
* Only running one gate when multiple required gates exist
* Ignoring failed or unavailable commands
* Treating code mode output as verified completion

## Required Orchestrator behavior

* Treat specialist completion claims as advisory unless evidence is present.
* If evidence is missing, dispatch verification or report VERIFICATION_BLOCKED.
* Do not produce final completion until required gates pass.
