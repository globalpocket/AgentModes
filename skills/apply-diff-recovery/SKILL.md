---
name: apply-diff-recovery
description: apply_diffを使うコードまたはテスト編集、またはapply_diff mismatch後の安全な再試行で、最新target blockの再読、正しいdiff構文、1回限りのretry、未確認symbol禁止を適用する
modeSlugs:
  - code
  - debug
  - refactorer
  - test-writer
---

# Apply Diff Recovery

## Trigger

- Use this Skill before code or test edits that rely on `apply_diff`.
- Use this Skill immediately after an `apply_diff` mismatch, partial-match failure, or stale block suspicion.

## Before First Patch

- Before the first `apply_diff`, read the exact current target block.
- Do not use stale line numbers or a block copied from a condensed summary.
- Confirm the target file, symbol, imports, variants, fields, traits, and surrounding anchors from current workspace content.

## Valid Diff Structure

- `<<<<<<< SEARCH`, optional `:start_line:`, `-------`, `=======`, and `>>>>>>> REPLACE` must each follow valid tool syntax.
- `-------` must be on its own line.
- `:start_line:` may appear only immediately after `<<<<<<< SEARCH`.
- Never place `:start_line:` in the replacement section.
- Keep the SEARCH block small, unique, and copied exactly from the current target file.

## First Failure Recovery

- After the first mismatch or partial-match failure, call `read_file` on the current target before retrying.
- Build a smaller unique SEARCH block from the newly read content.
- Retry `apply_diff` at most once.

## Second Failure Stop

- After a second failure, stop editing and return terminal outcome `patch_application_failed`.
- Do not switch to blind whole-file overwrite as a fallback.
- Do not keep retrying with guessed anchors or stale line numbers.

## Symbol Verification

- Do not invent helper methods, variants, fields, imports, traits, or symbols that were not verified in current workspace content.
- If the symbol cannot be verified, return a scoped failure summary instead of patching.

## Completion

- Report changed files only after the patch applies.
- If stopped, report `patch_application_failed`, target file, failure count, and the last verified anchor.
