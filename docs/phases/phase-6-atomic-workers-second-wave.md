# Phase 6: Atomic Worker Second Wave

Phase 6 continues splitting large legacy modes after the first read/edit/command/judge wave is available.

## Artifact manager split

- `artifact-indexer`: lists artifact names and metadata only.
- `artifact-conflict-checker`: detects path collisions, stale artifacts, and write ownership conflicts.
- `artifact-materializer`: writes one assigned artifact with atomic semantics.
- `artifact-retention-planner`: recommends artifact rotation or retention without deleting anything.

## Consistency checker split

- `ledger-consistency-checker`: checks `RUN_STATE_V1` checksum, status, hashes, and task linkage.
- `handoff-consistency-checker`: checks `STATE_DELTA_V1` against the current task packet.
- `workflow-phase-checker`: checks that the current workflow phase matches the durable cursor.

## Issue / security / review split

- GitHub work stays separated into read and mutation workers; `github-relationship-checker` classifies parent/sub-issue relationships from fetched facts.
- Security work stays separated into secret, dependency, unsafe-code, fabricated-package, and risk-classifier workers.
- Review work stays separated into implementation, architecture, test, performance-risk, and risk-classifier workers.

All second-wave workers keep the `STATE_DELTA_V1` handoff and must not paste full logs, full diffs, or parent plans.
