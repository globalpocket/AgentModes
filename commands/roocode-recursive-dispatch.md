---
description: "メインタスク完了時に roocode-recursive-dispatch Skill を明示実行"
---

# /roocode-recursive-dispatch

このスラッシュコマンドは、Orchestrator がメインタスク最終完了直前に `roocode-recursive-dispatch` Skill を明示実行するための終了ゲートです。ユーザー確認や承認待ちは行わず、条件不成立時は no-op として現在タスクを完了扱いにします。

## グローバルSkill前提

- このコマンド定義は設定リポジトリ側のエントリであり、ディスパッチ対象ワークスペースに `commands/roocode-recursive-dispatch.md` が存在することを要求しない。
- Skillツールで `roocode-recursive-dispatch` がロード済みなら、対象ワークスペース内の `skills/roocode-recursive-dispatch/SKILL.md` を探索せず、ロード済みSkill手順を実行仕様として扱う。
- 対象ワークスペースの `.roo/recursive-dispatch/target.json` と `.roo/recursive-dispatch/history.jsonl` は初回実行時に存在しなくてよい。存在確認のために `read_file` して ENOENT を発生させてはいけない。

## 実行条件

- 実装、テスト、Coverage 85%以上、security-auditor、reviewer、diagnostic-reporter、必要な issue-tracker 完了コメントが完了済みである。
- 現在のタスクがサブタスク、Red確認、Green修正、依存解決、レビュー差し戻し、復旧ループの途中ではない。
- 担当未対応Issue探索を次の独立メインタスクとして投入する終了段階である。

## 固定入力

- Dispatch Mode: `assigned-issue-dispatcher`
- Dispatch Delay Seconds: `0`
- Max Depth: `3` 以下
- Next Recursive Task Prompt: `認証済みGitHubユーザーにassignされたopen Issueを確認し、存在すればOrchestratorへ投入し、存在しなければ待機後に自己再投入してください。`
- Parent Task Summary: 最終統合結果、Diagnostic Issue URL、テスト・Coverage・監査結果を最大12行へ圧縮したもの。

## 実行手順

1. 最初に skill ツールで `roocode-recursive-dispatch` をロードして実行する。
2. Skill実行環境が使えない場合だけ、設定リポジトリで提供される `skills/roocode-recursive-dispatch/SKILL.md` の手順をSkill本体として扱い、対象ワークスペース側の同名ファイルは要求しない。
3. 対象ワークスペースで `mkdir -p .roo/recursive-dispatch` と `touch .roo/recursive-dispatch/dispatch.log .roo/recursive-dispatch/history.jsonl` を先に行い、`.roo/recursive-dispatch/next-prompt.md` と `.roo/recursive-dispatch/parent-summary.md` を作成して Async Dispatch Command を実行する。
4. VSCode外CLI agent、`roo --print`、`roo --stdin-prompt-stream`、TUI起動は使わない。IPC `StartNewTask` のみを使う。
5. socket 不明、socket 曖昧、Ack timeout、duplicate fingerprint、深度上限到達時は skipped / failed として記録し、現在のメインタスク完了を取り消さない。
6. 実行後は初期化済みの `.roo/recursive-dispatch/dispatch.log` と `.roo/recursive-dispatch/history.jsonl` の軽量確認だけを行い、次タスク完了を待たない。

## 出力形式

- **Recursive Dispatch**: dispatched / skipped / failed
- **Dispatch Mode**: assigned-issue-dispatcher
- **Socket Source**: env / registry / single-candidate / none / ambiguous
- **Depth**: current -> next / max
- **Delay**: seconds
- **Prompt File**: `.roo/recursive-dispatch/next-prompt.md`
- **Log File**: `.roo/recursive-dispatch/dispatch.log`
- **Next Step**: dispatched なら次タスクは VSCode Roo Code 側で独立実行、failed / skipped なら現在タスクは完了扱いのまま分類を記録
