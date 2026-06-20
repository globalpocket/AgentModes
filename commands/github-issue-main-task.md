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
- 親workflow全体をdelegated modeのREMINDERSへ残さない
