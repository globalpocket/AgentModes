---
description: Workflow Orchestratorで軽量TDD品質ゲートを開始する
argument-hint: <task goal or implementation request>
mode: workflow-orchestrator
---

`orchestrator-workflows` Skillの
`Workflow: tdd-quality-gate`
を使用して、ユーザーがこのSlash Commandの後に指定したタスクを処理する。

必須条件:

- 最初のsubtask作成前にSkillをロードする
- Skill内のphase順序を変更しない
- phaseごとに1つのTASK_PACKETだけを作成する
- 各delegation前にTASK_PACKET Preflightを行う
- visible TODOには現在phaseのtask 1件だけを置く
- 親workflow全体をdelegated modeのREMINDERSへ残さない
- ユーザーの元入力をsource of truthとして維持する
