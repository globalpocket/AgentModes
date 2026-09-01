# Phase 5: Atomic Worker First Wave

Phase 5 introduces the first operational worker split. Each worker owns one side-effect region, one failure pattern, one fixed output contract, and normally one to three tool calls.

Each worker must receive a compact `TASK_PACKET_V1` for one invariant only; use artifact paths, line ranges, and exact commands instead of pasted bodies.

## Read workers

- `tree-indexer`
- `text-searcher`
- `source-excerpt-reader`
- `artifact-reader`
- `git-state-reader`
- `dependency-manifest-reader`

## Edit workers

- `patch-applier`
- `new-file-writer`
- `test-patch-writer`
- `manifest-editor`
- `ci-workflow-writer`

## Command workers

- `exact-command-runner`
- `test-runner`
- `coverage-runner`
- `format-lint-runner`
- `build-runner`
- `provider-operator`

## Result classifiers

- `compiler-diagnostic-classifier`
- `test-result-classifier`
- `coverage-checker`
- `scope-checker`
- `contract-checker`
- `test-inventory-checker`

## DevOps first split

- `dependency-editor`
- `ci-workflow-writer`
- `container-operator`
- `provider-operator`
- `environment-inspector`

All first-wave workers return compact `STATE_DELTA_V1`; command workers return command metadata only and leave pass/fail interpretation to classifier workers.
