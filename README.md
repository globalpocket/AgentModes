# AgentModes

## Zoo Code custom modes import

- Zoo Code へインポートする対象ファイルは `all-agents.yaml` です。
- `all-agents.yaml` は `rules/*.yaml` から生成される単一の `customModes` 配列です。
- 生成時は `python maintenance/generate-all-agents.py` を実行してください。
- 検証時は `python maintenance/validate-yaml.py` を実行してください。
- 契約検証時は `python maintenance/validate-contracts.py` を実行してください。
- `customInstructions` は block scalar、`groups` は YAML list として保持します。

## Global ~/.roo deployment layout

このリポジトリは、内容をグローバル `~/.roo/` へコピーして使う配布物です。Zoo Code / Roo Code runtime が参照する入口は `skills/` と `commands/` で、保守スクリプトは runtime から自動実行されません。

| Repository path | Deployment target / usage |
| --- | --- |
| `skills/` | `~/.roo/skills/` へコピー |
| `commands/` | `~/.roo/commands/` へコピー |
| `all-agents.yaml` | Zoo Code custom modes import 対象 |
| `maintenance/` | 人間またはCIが明示的に実行する保守用。Zoo/Roo runtime は自動実行しない |

AgentModes の GitHub 更新だけでは既存の Zoo Code 設定へ反映されません。更新後は `all-agents.yaml` の再importと、更新済み `skills/` / `commands/` の `~/.roo/` へのコピーが必要です。

保守コマンド:

```bash
python maintenance/generate-all-agents.py
python maintenance/validate-yaml.py
python maintenance/validate-contracts.py
```

## 推奨モデル割り当て設定例（durable ledger方針に更新済み）

以下は、このワークスペースのモード設計に対応した推奨割り当て例です。

前提:
- GPT系モデルは `GPT-OSS-*` のみを推奨表に含める
- `qwen35-MTP` は `orchestrator`、`workflow-orchestrator`、`code`、`debug`、`recovery-supervisor` には割り当てない
- MTP系モデルはread-only索引、定型command実行、定型文生成など、control-plane判断や精密patch生成を必要としない責務に限定する
- 推論設定はモデル能力ではなくモード責務で決める
- `Qwen3.5-122B` は短命な `epoch-orchestrator`、実装、レビュー、整合判定、DevOps など判断密度の高いローカル実行モードに使う
- `Qwen3.5-9B` は限定的な読み取り、索引、単純実行に使う
- `Gemma4-12B-it` は documenter / user-response-composer のような文章生成・整形系に使う。文書化の根拠収集は `doc-evidence-reader` に分離する
- `tester` / `artifact-manager` は推論オフを推奨し、過剰判断や completion ループを避ける

| モード | 推奨モデル | 推論設定 | 理由 |
|---|---|---|---|
| `orchestrator` | `Qwen3.6-9B` | オン / 中 | 長寿命のdurable continuity supervisorとしてcursor管理とepoch dispatchに限定するため |
| `workflow-orchestrator` | `Qwen3.6-9B` | オン / 中 | 明示Workflowのcursor管理に限定し、高推論分解は短命epochへ委譲するため |
| `gpt-oss-needs-analyzer` | `GPT-OSS-120B` | オン / 最高 | raw user prompt を深く分析し、Orchestrator向け advisory brief を生成する専用前段 |
| `architect` | `GPT-OSS-120B` | オン / 高 | 設計、責務分離、実行計画、TDD単位分解の判断密度が高い |
| `recovery-supervisor` | `GPT-OSS-120B` | オン / 最高 | ループ脱出、失敗分類、再委任設計、停止条件判断が最も重い |
| `reviewer` | `GPT-OSS-120B` | オン / 高 | 最終品質レビュー、設計整合性、保守性、性能、残リスク判断が必要 |
| `security-auditor` | `GPT-OSS-120B` | オン / 高 | セキュリティ・依存関係・捏造ライブラリ検知は誤判定コストが高い |
| `code` | `Qwen3.5-122B` | オン / 高 | 最小差分実装でも API 契約、スコープ、副作用確認が必要 |
| `debug` | `Qwen3.5-122B` | オン / 高 | 失敗シグネチャから根本原因を特定し、局所修正する必要がある |
| `refactorer` | `Qwen3.5-122B` | オン / 中〜高 | 振る舞い不変性を維持しながら構造改善する必要がある |
| `test-writer` | `Qwen3.5-122B` | オン / 高 | Red条件、境界値、契約テストの設計に推論が必要 |
| `tester` | `Qwen3.5-9B` | オフ | 指定コマンドの実行とメタデータ返却が主責務で、判断を持たせないため |
| `consistency-checker` | `Qwen3.5-122B` | オン / 中 | Artifact、契約、Coverage、スコープ整合の判定が必要 |
| `librarian` | `Qwen3.5-9B` | オン / 中 | 探索順序、候補絞り込み、索引要約に限定的な推論が有効 |
| `analyzer` | `Qwen3.5-9B` | オン / 中 | 差分適用位置、行範囲、周辺アンカー抽出に局所推論が必要 |
| `artifact-manager` | `Qwen3.5-9B` | オフ | artifacts 配下の初期化・prepare・verifyのみで判断を膨らませないため |
| `issue-tracker` | `Qwen3.5-122B` | オン / 中 | Issue本文、親子Issue、進捗コメント、sub-issue選択の文脈判断が必要 |
| `release-manager` | `Qwen3.5-122B` | オン / 中 | version bump、tag、push単位の整合判断が必要 |
| `segregated-devops` | `Qwen3.5-122B` | オン / 高 | 依存関係、CI、環境、Provider復旧は判断密度が高い |
| `diagnostic-reporter` | `Qwen3.5-122B` | オン / 中 | 品質ゲート後の診断Issue本文を事実ベースで構成する必要がある |
| `doc-evidence-reader` | `Qwen3.5-9B` | オン / 中 | read-only の根拠付き事実抽出が主責務で、広範な設計判断や文章生成を行わないため |
| `documenter` | `Gemma4-12B-it` | オフ | `DOC_FACTS_V1` からMarkdown文書を生成・整形する専任で、事実収集や仕様解釈を行わないため |
| `ask` | `Qwen3.5-122B` | オン / 中 | 技術説明、既存コード理解、計画相談に文脈理解が必要 |
| `user-response-composer` | `Gemma4-12B-it` | オフ | 上流結果を最終ユーザー向け文面に整形するだけで、判断や追加事実生成を禁止するため |

## 最小運用ポリシー

- GPT系モデルは `GPT-OSS-*` のみを推奨表に含める
- `Gemma4-12B-it` は `documenter` / `user-response-composer` のような文章生成・整形系に使う
- 文書更新は `doc-evidence-reader` が根拠事実を `DOC_FACTS_V1` として抽出し、`documenter` が `DOC_FACTS_V1` に基づいてMarkdownを編集する二段構成にする
- `documenter` の編集対象は `README.md` と `docs/**/*.md` のみ。API reference、architecture notes、handoff summary も `docs/` 配下または `README.md` に割り当てる
- `plans/` 配下の計画文書は原則 `architect` 担当であり、`documenter` へ任意Markdownや `plans/**/*.md` を割り当てない
- `documenter` は実装コード、テスト、設定、CI、plans を読んで事実発見や仕様解釈を行わない
- `tester` / `artifact-manager` は推論オフを推奨し、過剰判断や completion ループを避ける
- `Qwen3.5-122B` は短命な `epoch-orchestrator`、実装、レビュー、整合判定、DevOps など判断密度の高いローカル実行モードに使う
- `Qwen3.5-9B` は限定的な読み取り、索引、単純実行に使う
- 推論設定は「モデル能力」ではなく「モード責務」で決める
- Qwen担当モードは推論過程や自己対話を出力せず、外部出力はツール実行または固定形式の短い事実報告に限定する
- write権限を持つモードのうち、`code` / `test-writer` / `refactorer` は、Orchestratorによる極小タスク分解を前提に運用
- `code` / `debug` は実装・修正の担当であり、テスト実行、Coverage測定、依存関係操作を行わない
- テスト実行とCoverage測定は `tester`、依存関係追加・peer依存衝突・lockfile更新は `segregated-devops` に分離する
- AIエージェント向け軽量TDDを標準とし、通常タスクはLevel 1 Contract TestまたはLevel 2 Behavior Testから開始する。Level 4 Full TDDを初手にしない
- テスト分類は `contract` / `behavior` / `regression` / `exploratory` に限定し、タスク開始時の新規テストは最大3個までにする
- 追加テストはバグ発見、契約変更、回帰防止、外部I/O境界追加の場合だけ許可し、安全性を理由に無限にテストを増やさない
- `exploratory` test は完了時に正式テストへ昇格するか削除し、最終的には contract、regression、必要最小限の behavior test だけを残す
- テスト対象は内部実装より schema、protocol、event、state transition、routing、external I/O の契約を優先し、UI文言、仮実装、表示整形、設計未確定部分を過剰テストしない
- `npm install`、`pnpm add`、`yarn add`、`pip install` は `segregated-devops` 以外で実行しない
- coverage provider不足時は、既存テストフレームワークと同一バージョン帯のproviderを `segregated-devops` が選定し、`--force` や `--legacy-peer-deps` は原則使わない
- `recovery-supervisor` は、通常の差し戻しで収束しない場合のみ投入し、常用しない
- メインタスクがGitHub Issue URLだけで開始された場合は、`issue-tracker` がIssue本文を読み、親子Issueを判定する。指定IssueがサブIssueなら通常対応し、指定IssueがメインIssueかつ未対応サブIssueがある場合は番号が一番若い未対応サブIssueを通常対応する。未対応サブIssueがない場合は、1TDD単位のサブIssueを1件以上、最大8件推奨、絶対最大12件で作成し、Backlogization Completedとして終了する。サブIssue完了時はサブIssueだけをcloseし、メインIssueはcloseしない。close後はメインIssueのルーティングへ戻り、未対応openサブIssueが残っていれば通常どおり次のサブIssue対応へ進む
- GitHub由来リポジトリでpushする場合は、`release-manager` がNode.jsなら `package.json`、Pythonなら `pyproject.toml` のversion末尾数字を繰り上げ、tag名を `v<version>` として新versionで終わる形式にし、branchとtagを同じ公開単位でpushする
- GitHub由来リポジトリでのメインタスク終了時のプロジェクト診断とGitHub Issue登録は `diagnostic-reporter` に分離する。非GitHubリポジトリでは診断Issue登録を起動しない
- `orchestrator` と `architect` は、タスクを直接実装せず、分解と委任に専念させる
- `architect` は設計、計画、ADR、実装分解、TDD計画、品質ゲート設計を担当する。文書化では `doc-evidence-reader` がコード・docs・plans・artifacts から根拠事実だけを抽出し、`documenter` は `README.md` と `docs/**/*.md` に限定してAPI reference、architecture notes、handoff summary、利用者/開発者向け説明のMarkdown編集だけを担当する
- セキュリティ・依存関係・secret・unsafe pattern・fabricated libraries は `security-auditor` が担当し、`reviewer` は最終品質レビュー、設計整合、保守性、性能、テスト妥当性、残リスク確認を担当する
- `gpt-oss-needs-analyzer` はユーザーまたはランタイムが選択した分析用モデルで動作する任意前段モードとしてだけ使い、ツール実行、ファイル編集、サブタスク作成、他モード呼び出しを禁止する。出力は `ORCHESTRATOR_BRIEF_V1` YAML のみで、既存 Orchestrator はこれを advisory brief として扱い、raw user prompt を常に source of truth とする

## Runtime Skills and Slash Commands

top-level `workflows/` は使用しません。Skill は必要時にオンデマンドロードされ、Slash Command はユーザーが明示的に workflow を開始する entrypoint です。`maintenance/` は runtime 機能ではありません。

| Path | Type | Purpose |
| --- | --- | --- |
| `commands/tdd-quality-gate.md` | Slash Command | 軽量TDD Workflowの明示的entrypoint |
| `commands/github-issue-main-task.md` | Slash Command | GitHub Issue Workflowの明示的entrypoint |
| `skills/tdd-quality-gate/SKILL.md` | Skill | `/tdd-quality-gate` 専用phase定義 |
| `skills/github-issue-main-task/SKILL.md` | Skill | `/github-issue-main-task` 専用phase定義 |
| `skills/orchestrator-workflows/SKILL.md` | Skill | 旧参照向け互換shim。詳細phase定義のsource of truthではない |
| `skills/provider-health-recovery-flow/SKILL.md` | Skill | Provider Health Failure分類済み後の復旧委任・再開フロー |
| `skills/provider-health-recovery/SKILL.md` | Skill | Segregated DevOpsによる実際のProvider復旧手順 |

固定手順は JSON workflow ではなく Slash Command と Skill に分けて管理します。ユーザーが Slash Command で workflow を開始し、Workflow Orchestrator は対応する Skill をロードして phase 順序、TASK_PACKET preflight、Scoped TODO Projection、条件付き品質ゲートを適用します。
Workflowの詳細phase順序は workflow-specific Skill（`skills/tdd-quality-gate/SKILL.md` または `skills/github-issue-main-task/SKILL.md`）をsource of truthとし、`skills/orchestrator-workflows/SKILL.md` は旧参照向け互換shimに限定します。

## 代替割り当て方針

- コストやレイテンシを優先する場合も、GPT系は `GPT-OSS-*` の範囲に限定する
- `recovery-supervisor` は可能な限り最上位の推論性能を持つモデルを維持する
- 文書生成・最終応答整形は `Gemma4-12B-it` を優先し、追加判断を持たせない

## Durable ledger architecture target

This repository now targets a state-machine architecture where conversation history is only a cache and workspace state ledgers are the source of truth.

### Control flow

Ordinary user input follows this path:

```text
gpt-oss-intake-supervisor
→ intake-ledger-writer
→ orchestrator
→ epoch-orchestrator
→ atomic workers
→ state-ledger-writer
→ orchestrator advances the next epoch
```

Explicit workflows bypass ordinary intake and enter `workflow-orchestrator` directly:

```text
/tdd-quality-gate
/github-issue-main-task
→ workflow-orchestrator
→ epoch-orchestrator
→ atomic workers
```

`/continue-from-state artifacts/state/<run-id>.json` starts a new root Orchestrator task from the durable ledger only.

### Durable state contracts

- `RUN_STATE_V1` is the committed source of truth for run progress.
- State transitions are limited to `prepared`, `running`, `committed`, and `failed`.
- `state-ledger-writer` owns atomic writes, task ID uniqueness, input/result hashes, duplicate commit rejection, interrupted task detection, idempotent retry, and checksum verification.
- `state-ledger-reader` verifies the current ledger before Orchestrator dispatches the next epoch.
- `context-compactor` compacts persistent state artifacts only; it does not replace native context condensation.

### Prompt and handoff contracts

- Long-lived `orchestrator` and `workflow-orchestrator` keep only `SESSION_CURSOR_V1` pointers.
- High-reasoning work moves to short-lived `epoch-orchestrator` tasks.
- Atomic workers return compact `STATE_DELTA_V1` handoffs.
- `TASK_PACKET_V1` is sparse: omit empty/default fields and include only current-subtask facts.
- Read/search workers obey the Context Budget Contract: two inspection tool calls per assistant message, normally 80 read lines, 20 search matches, no full tree/log/file handoffs.
- `apply-diff-recovery` is loaded only after the first patch mismatch and a target reread.

### Updated model allocation policy

| Mode group | Recommended model | Reason |
|---|---|---|
| `orchestrator` | `Qwen3.6-9B` | Long-lived cursor loop; fast native compression if runtime forces it |
| `workflow-orchestrator` | `Qwen3.6-9B` | Long-lived workflow cursor management |
| `context-compactor` | `Qwen3.6-9B` | Structured durable-state compaction |
| state ledger read/write | `Qwen3.6-9B` or smaller | Deterministic I/O contracts |
| `gpt-oss-intake-supervisor` | `GPT-OSS-*` high reasoning | User-need structuring |
| `gpt-oss-needs-analyzer` | `GPT-OSS-*` high reasoning | Pure reusable analysis |
| `epoch-orchestrator` | `Qwen3.5-122B` | Dense one-epoch decomposition |
| `recovery-supervisor` | `GPT-OSS-120B` | Exceptional recovery decisions |
| command runners | `Qwen3.6-9B`, reasoning off | Exact command metadata |
| atomic edit/judge workers | `9B` to `122B` | Match model size to atomic difficulty |

Do not assign `qwen35-MTP` to `orchestrator`, `workflow-orchestrator`, `epoch-orchestrator`, precision patch workers, debug workers, or `recovery-supervisor`.

### Phase implementation status

- Phase 1 context-reduction contracts are represented by sparse `TASK_PACKET_V1`, `STATE_DELTA_V1`, Context Budget Contract, workflow Skill splitting, and delayed `apply-diff-recovery` policy.
- Phase 2 durable-state contracts are represented by `RUN_STATE_V1`, `SESSION_CURSOR_V1`, `USER_NEEDS_V1`, state ledger reader/writer modes, checksum/idempotency rules, and durable examples under `docs/contracts/` and `docs/examples/`.
- Phase 3 control-plane recomposition is represented by durable-continuity Orchestrator contracts and `epoch-orchestrator` delegation boundaries.
- Phase 4 intake recomposition is represented by `gpt-oss-intake-supervisor`, `intake-ledger-writer`, and path-only `SESSION_START_V1` handoff rules.
- Phase 5 atomic-worker first wave is represented by read workers, edit workers, command runners, result classifiers, and the initial DevOps split in `rules/atomic-workers.yaml`.
- Phase 6 atomic-worker second wave is represented by artifact, consistency, GitHub relationship, security-risk, and review-risk split workers.
- Phase 7 sliding-window operation is represented by `/continue-from-state`, durable rehydration rules, root task rotation triggers, and no-summary ledger recovery policy.
- Phase 8 metrics/governance is represented by `MIGRATION_METRICS_V1`, governance workers, and checks that prevent regressions back to conversation-history state.
- Remaining work is runtime integration and collecting real Zoo/Roo telemetry against these metrics.

| Contract | Path | Purpose |
| --- | --- | --- |
| `RUN_STATE_V1` | `docs/contracts/run-state-v1.md` | Durable run status, hashes, checksum, transition, and retry contract |
| `SESSION_CURSOR_V1` | `docs/contracts/session-cursor-v1.md` | Long-lived Orchestrator pointer-only context |
| `USER_NEEDS_V1` | `docs/contracts/user-needs-v1.md` | Normalized intake artifact schema |
| Example ledger | `docs/examples/run-state-v1.json` | Minimal state ledger fixture for prompts and validators |
| Phase 3 | `docs/phases/phase-3-control-plane.md` | Control-plane recomposition scope |
| Phase 4 | `docs/phases/phase-4-intake.md` | Intake ledger path and artifact rules |
| Phase 5 | `docs/phases/phase-5-atomic-workers.md` | Atomic worker first-wave registry |
| Phase 6 | `docs/phases/phase-6-atomic-workers-second-wave.md` | Artifact, consistency, issue, security, and review split registry |
| Phase 7 | `docs/phases/phase-7-sliding-window.md` | Sliding-window, rehydration, and root-task rotation policy |
| Phase 8 | `docs/phases/phase-8-metrics-governance.md` | Migration metrics and governance checks |
| `MIGRATION_METRICS_V1` | `docs/contracts/migration-metrics-v1.md` | Observable migration metrics schema |
