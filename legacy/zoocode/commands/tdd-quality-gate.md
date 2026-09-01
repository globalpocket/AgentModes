---
description: Workflow Orchestratorで軽量TDD品質ゲートを開始する
argument-hint: <task goal or implementation request>
mode: workflow-orchestrator
---

`tdd-quality-gate` Skill
を使用して、ユーザーがこのSlash Commandの後に指定したタスクを処理する。

必須条件:

- 最初のsubtask作成前に`tdd-quality-gate` Skillをロードする
- Skill内のphase順序を変更しない
- phaseごとに1つのTASK_PACKETだけを作成する
- 各delegation前にTASK_PACKET Preflightを行う
- visible TODOには現在phaseのtask 1件だけを置く
- visible TODOはZoo/Rooへ複数行本文として渡し、見出しと各チェック項目を実改行で区切る。単一のエスケープ済み文字列としてシリアライズせず、文字列 `\n` を含めない
- visible TODOのhandoffでは必ず`VISIBLE_TODO_V1`形式を使い、`title`と`items`を最終レンダリング境界まで分離する
- 親workflow全体をdelegated modeのREMINDERSへ残さない
- ユーザーの元入力をsource of truthとして維持する
