---
description: Workflow OrchestratorでGitHub Issue起点のメインタスクWorkflowを開始する
argument-hint: <GitHub Issue URL>
mode: workflow-orchestrator
---

`github-issue-main-task` Skill
を使用して、ユーザーがこのSlash Commandの後に指定したGitHub Issueを処理する。

必須条件:

- 最初のsubtask作成前に`github-issue-main-task` Skillをロードする
- GitHub Issue URLをraw workflow inputとして扱う
- Skill内のphase順序とconditional gateを変更しない。実装phase到達時だけ`tdd-quality-gate` Skillをロードする
- phaseごとに1つのTASK_PACKETだけを作成する
- 各delegation前にTASK_PACKET Preflightを行う
- visible TODOには現在phaseのtask 1件だけを置く
- visible TODOはZoo/Rooへ複数行本文として渡し、見出しと各チェック項目を実改行で区切る。単一のエスケープ済み文字列としてシリアライズせず、文字列 `\n` を含めない
- visible TODOのhandoffでは必ず`VISIBLE_TODO_V1`形式を使い、`title`と`items`を最終レンダリング境界まで分離する
- 親workflow全体をdelegated modeのREMINDERSへ残さない
