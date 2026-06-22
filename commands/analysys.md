---
description: Backward-compatible alias for /analysis
argument-hint: <analysis scope or repository diagnosis request>
mode: workflow-orchestrator
---

`/analysys` は旧スペル互換のエイリアスです。新規利用では `/analysis` を使ってください。

以下は `/analysis` と同一の方針で実行すること:

プロジェクト分析・評価を行う。実装、削除、修正は行わない。

必須条件:

- 解析は `librarian` / `analyzer` / `security-auditor` / `reviewer` などの最小権限モードへ分割して委任する。
- GitHub Issue 作成やコメントなどのGitHub mutationは直接行わず、必要な場合だけ `diagnostic-reporter` または GitHub専用workerへ委任する。
- GitHubリポジトリURLが必要な場合は、専用workerに `git config --get remote.origin.url` の実行を委任する。
- 報告は根拠ファイル、行範囲、実行コマンド、未確認事項を含む compact handoff にする。
- 非GitHubリポジトリ、remote未設定、認証不足、またはIssue作成権限不足の場合はIssue作成を行わず blocked として返す。
