# AgentModes

## Zoo Code custom modes import

- Zoo Code へインポートする対象ファイルは `all-agents.yaml` です。
- `all-agents.yaml` は `modes/*.yaml` から生成される単一の `customModes` 配列です。
- 生成時は `python maintenance/generate-all-agents.py` を実行してください。
- 検証時は `python maintenance/validate-yaml.py` を実行してください。
- 契約検証時は `python maintenance/validate-contracts.py` を実行してください。
- `customInstructions` は block scalar、`groups` は YAML list として保持します。

## Global ~/.roo layout

このリポジトリのルートはグローバル `~/.roo/` 相当として扱います。したがって `rules/` は Zoo/Roo Global Rules の実配置（`~/.roo/rules/` 相当）であり、custom mode 定義の置き場ではありません。custom mode YAML の source of truth は `modes/` です。Zoo Code / Roo Code runtime が参照する入口は `rules/`、`skills/`、`commands/` で、保守スクリプトは runtime から自動実行されません。

| Repository path | Deployment target / usage |
| --- | --- |
| `rules/` | `~/.roo/rules/` 相当。Zoo/Roo Global Rules として runtime に注入される |
| `skills/` | `~/.roo/skills/` 相当 |
| `commands/` | `~/.roo/commands/` 相当 |
| `modes/` | custom mode YAML の source of truth。Global Rules ではない |
| `all-agents.yaml` | Zoo Code custom modes import 対象（`modes/*.yaml` から生成。直接編集しない） |
| `maintenance/` | 人間またはCIが明示的に実行する保守用。Zoo/Roo runtime は自動実行しない |

AgentModes の GitHub 更新だけでは既存の Zoo Code 設定へ反映されません。更新後は `all-agents.yaml` の再importが必要です。別ディレクトリで編集した場合だけ、更新済み `rules/` / `skills/` / `commands/` を対応する `~/.roo/` 配下へ同期してください。

Global Rules は `rules/*.md` としてこの repo root 直下に置きます。この repo を `~/.roo` として配置している場合、追加コピー手順は不要です。

`docs/contracts/compact-mode-contract.md` is the reviewed source contract. `rules/00-agentmodes-compact-mode-contract.md` is the live Global Rules copy and must remain byte-for-byte synchronized. `modes/*.yaml` should contain only mode-specific kernels; do not duplicate Global Rules boilerplate there. `all-agents.yaml` is generated from `modes/*.yaml`, so avoid editing it directly or treating it as a second source of truth.

保守コマンド:

```bash
python maintenance/generate-all-agents.py
python maintenance/validate-yaml.py
python maintenance/validate-contracts.py
```

## 推奨モデル割り当て設定例（全mode対応 / durable ledger方針）

以下は、`modes/*.yaml` に定義されている全 custom mode を対象にした推奨割り当て例です。source of truth は `modes/` であり、この表は運用時の model profile 選定例です。

前提:
- GPT系モデルは `GPT-OSS-*` のみを推奨表に含めるが、常用するのではなく「高リスクな分析・審査を構造化artifactに落とす」用途に限定する。
- `GPT-OSS-120B` の出力を後続の `Qwen3.6-9B` が活かせるのは、自由文の推論過程ではなく、`USER_NEEDS_V1`、`ORCHESTRATOR_BRIEF_V1`、review/security finding、recovery plan のような schema 化された decision artifact として渡す場合だけである。
- `Qwen3.6-9B` は GPT-OSS の判断を再推論・再解釈する担当ではない。後続の長寿命control-plane modeは、artifact path、優先度、制約、acceptance criteria、blocker、次mode候補などの明示フィールドを cursor として扱い、判断密度の高い再分解は `epoch-orchestrator` または該当review/audit modeへ委譲する。
- `qwen35-MTP` は `orchestrator`、`workflow-orchestrator`、`epoch-orchestrator`、`code`、`debug`、精密patch worker、`recovery-supervisor` には割り当てない。
- MTP系モデルはread-only索引、定型command実行、定型文生成など、control-plane判断や精密patch生成を必要としない責務に限定する。
- 推論設定はモデル能力ではなくモード責務で決める。
- `Qwen3.6-9B` は長寿命cursor管理、ledger I/O、構造化compaction、定型command metadataに使う。
- `Qwen3.5-122B` は短命な `epoch-orchestrator`、実装、レビュー、整合判定、DevOps など判断密度の高いローカル実行モードに使う。
- `Qwen3.5-9B` は限定的な読み取り、索引、単純実行に使う。
- `Gemma4-12B-it` は `documenter` / `user-response-composer` のような文章生成・整形系に使う。文書化の根拠収集は `doc-evidence-reader` に分離する。
- `tester` / `artifact-manager` / command runner系 atomic worker は推論オフを推奨し、過剰判断や completion ループを避ける。

### GPT-OSS → Qwen handoff policy

`GPT-OSS-120B` を使うmodeは、後続の `Qwen3.6-9B` に「考え方」を継承させる前提ではなく、後続が機械的に参照できる durable artifact を作る前提で使います。したがって、GPT-OSS mode の完了条件は「説明が詳しいこと」ではなく、次の条件を満たすことです。

- must: GPT-OSS mode は free-form advisor ではなく high-reasoning artifact producer として終了する。schema名、producer_mode、intended_consumer、source_of_truth、objective、artifact path、根拠path、決定事項、未決事項、制約、優先度、acceptance criteria、blocker、推奨next mode、confidenceを明示する。
- must: `handoff_policy` を含め、`downstream_must_not_reinfer: true`、`downstream_should_treat_as_advisory: true`、`downstream_should_escalate_if_fields_missing: true`、`downstream_high_reasoning_delegate: epoch-orchestrator` を宣言する。
- must not: Harmony-specific構造、長い自由文の推論過程、暗黙の前提、会話履歴だけに依存する判断、後続modeに再解釈を要求する曖昧な助言を渡す。
- if needed: `Qwen3.6-9B` が明示フィールドだけで実行管理できない粒度なら、handoffを薄めずに `Qwen3.5-122B` の `epoch-orchestrator`、`GPT-OSS-120B` の `reviewer` / `security-auditor` / `recovery-supervisor`、または該当 atomic classifier へ再委譲する。


Required GPT-OSS downstream-compatible output fields（canonical contract: `docs/contracts/gpt-oss-downstream-compatible-output-policy.md`）:

```yaml
GPT_OSS_DOWNSTREAM_COMPATIBLE_OUTPUT_POLICY:
  principle:
    - GPT-OSS modes must not hand off raw reasoning, long free-form advice, or Harmony-specific structure.
    - GPT-OSS modes must finish by producing a downstream-consumable schema artifact.
    - Downstream Qwen modes must not be required to reinterpret GPT-OSS reasoning.
  required_fields:
    - schema
    - producer_mode
    - intended_consumer
    - source_of_truth
    - objective
    - decisions
    - assumptions
    - constraints
    - acceptance_criteria
    - blockers
    - recommended_next_mode
    - confidence
  optional_but_recommended_fields:
    - artifact_path
    - evidence_paths
    - unresolved_questions
    - handoff_policy
    - loss_report
  handoff_policy:
    downstream_must_not_reinfer: true
    downstream_should_treat_as_advisory: true
    downstream_should_escalate_if_fields_missing: true
    downstream_high_reasoning_delegate: epoch-orchestrator
```

GPT-OSS推奨modeごとの標準artifact schema:

- `gpt-oss-needs-analyzer`: `ORCHESTRATOR_BRIEF_V1`
- `gpt-oss-intake-analyzer`: `USER_NEEDS_V1` / `USER_NEEDS_SLICE_V1`
- `gpt-oss-intake-supervisor`: `GPT_OSS_SHIM_HANDOFF_V1`（deprecated compatibility shim）
- `architect`: `ARCHITECTURE_PLAN_V1` / `TASK_DECOMPOSITION_V1`
- `reviewer` と atomic reviewer 群: `REVIEW_FINDING_V1` / `REVIEW_REPORT_V1`
- `security-auditor`、`security-risk-classifier`、atomic security auditor 群: `SECURITY_FINDING_V1` / `SECURITY_AUDIT_REPORT_V1`
- `recovery-supervisor`: `RECOVERY_PLAN_V1`

READMEで `GPT-OSS-120B` または `GPT-OSS-*` 推奨として列挙するmodeは、deprecated shimを含め、上記schemaまたは明示された互換schemaでこのpolicyを満たす。producer / consumer の対象一覧と schema field contract は `docs/contracts/gpt-oss-downstream-compatible-output-policy.md` を source of truth とし、validator はその一覧から検査対象を読む。

このため、`orchestrator` や `workflow-orchestrator` を `Qwen3.6-9B` にしても、GPT-OSS の成果は「会話の文脈」ではなく ledger / brief / finding / plan のフィールドとして利用できます。逆に、GPT-OSS の出力が schema 化されていない場合は、後続Qwenで活かせる保証がないため、その出力は不完全なhandoffとして扱います。

### Durable intake / control-plane modes

| モード | 推奨モデル | 推論設定 | 理由 |
|---|---|---|---|
| `raw-input-materializer` | `Qwen3.6-9B` | オフ〜低 | raw入力をartifactへ保存し、`RAW_INPUT_REF_V1`で次モードへ渡すだけ。要件分析・計画・実装を行わない |
| `gpt-oss-intake-analyzer` | `GPT-OSS-120B` | オン / 最高 | materialized inputからUSER_NEEDS_V1を生成する分析専任 |
| `gpt-oss-intake-supervisor` | `GPT-OSS-120B` | オン / 低 | 互換shim。主経路ではなく新intake modeへの誘導のみ |
| `intake-ledger-writer` | `Qwen3.6-9B` | オフ〜低 | RAW_INPUT_REF_V1とUSER_NEEDS_V1を永続化しSESSION_START_V1を返す |
| `state-ledger-reader` | `Qwen3.6-9B` | オフ〜低 | RUN_STATE_V1の検証とcursor復元に限定する |
| `state-ledger-writer` | `Qwen3.6-9B` | オフ〜低 | 状態遷移、hash、checksum、重複commit拒否を機械的に永続化する |
| `context-compactor` | `Qwen3.6-9B` | オン / 中 | conversationではなく永続state artifactを構造化compactionする |
| `orchestrator` | `Qwen3.6-9B` | オン / 中 | path-onlyのdurable continuity supervisor |
| `workflow-orchestrator` | `Qwen3.6-9B` | オン / 中 | 明示Workflowのcursor管理に限定し、高推論分解は短命epochへ委譲するため |
| `epoch-orchestrator` | `Qwen3.5-122B` | オン / 高 | 1 epoch / 1 invariantの短命高推論 |
| `gpt-oss-needs-analyzer` | `GPT-OSS-120B` | オン / 最高 | dispatchしない純粋分析worker。取得済み事実から ORCHESTRATOR_BRIEF_V1 だけを生成 |
| `recovery-supervisor` | `GPT-OSS-120B` | オン / 最高 | ループ脱出、失敗分類、再委任設計、停止条件判断が最も重い |

### Primary specialist modes

| モード | 推奨モデル | 推論設定 | 理由 |
|---|---|---|---|
| `architect` | `GPT-OSS-120B` | オン / 高 | 設計、責務分離、実行計画、TDD単位分解の判断密度が高い |
| `code` | `Qwen3.5-122B` | オン / 高 | 最小差分実装でも API 契約、スコープ、副作用確認が必要 |
| `debug` | `Qwen3.5-122B` | オン / 高 | 失敗シグネチャから根本原因を特定し、局所修正する必要がある |
| `refactorer` | `Qwen3.5-122B` | オン / 中〜高 | 振る舞い不変性を維持しながら構造改善する必要がある |
| `test-writer` | `Qwen3.5-122B` | オン / 高 | Red条件、境界値、契約テストの設計に推論が必要 |
| `tester` | `Qwen3.6-9B` | オフ | 指定コマンドの実行とメタデータ返却が主責務で、判断を持たせないため |
| `reviewer` | `GPT-OSS-120B` | オン / 高 | 最終品質レビュー、設計整合性、保守性、性能、残リスク判断が必要 |
| `security-auditor` | `GPT-OSS-120B` | オン / 高 | セキュリティ・依存関係・捏造ライブラリ検知は誤判定コストが高い |
| `consistency-checker` | `Qwen3.5-122B` | オン / 中 | Artifact、契約、Coverage、スコープ整合の判定が必要 |
| `librarian` | `Qwen3.5-9B` | オン / 中 | 探索順序、候補絞り込み、索引要約に限定的な推論が有効 |
| `analyzer` | `Qwen3.5-9B` | オン / 中 | 差分適用位置、行範囲、周辺アンカー抽出に局所推論が必要 |
| `artifact-manager` | `Qwen3.6-9B` | オフ | artifacts 配下の初期化・prepare・verifyのみで判断を膨らませないため |
| `issue-tracker` | `Qwen3.5-122B` | オン / 中 | Issue本文、親子Issue、進捗コメント、sub-issue選択の文脈判断が必要 |
| `release-manager` | `Qwen3.5-122B` | オン / 中 | version bump、tag、push単位の整合判断が必要 |
| `segregated-devops` | `Qwen3.5-122B` | オン / 高 | 依存関係、CI、環境、Provider復旧は判断密度が高い |
| `diagnostic-reporter` | `Qwen3.5-122B` | オン / 中 | 品質ゲート後の診断Issue本文を事実ベースで構成する必要がある |
| `doc-evidence-reader` | `Qwen3.5-9B` | オン / 中 | read-only の根拠付き事実抽出が主責務で、広範な設計判断や文章生成を行わないため |
| `documenter` | `Gemma4-12B-it` | オフ | `DOC_FACTS_V1` からMarkdown文書を生成・整形する専任で、事実収集や仕様解釈を行わないため |
| `ask` | `Qwen3.5-122B` | オン / 中 | 技術説明、既存コード理解、計画相談に文脈理解が必要 |
| `user-response-composer` | `Gemma4-12B-it` | オフ | 上流結果を最終ユーザー向け文面に整形するだけで、判断や追加事実生成を禁止するため |

### Atomic read / index workers

| モード | 推奨モデル | 推論設定 | 理由 |
|---|---|---|---|
| `tree-indexer` | `Qwen3.5-9B` | オフ〜低 | ファイル構造索引に限定し、設計判断を行わない |
| `text-searcher` | `Qwen3.5-9B` | オフ〜低 | 指定scopeの検索結果抽出だけを行う |
| `source-excerpt-reader` | `Qwen3.5-9B` | 低 | 指定範囲の抜粋と短い事実報告に限定する |
| `artifact-reader` | `Qwen3.5-9B` | 低 | artifact pathから必要事実だけを読む |
| `git-state-reader` | `Qwen3.6-9B` | オフ〜低 | git状態の読み取りとメタデータ返却に限定する |
| `dependency-manifest-reader` | `Qwen3.5-9B` | 低 | manifestの依存関係・script情報の抽出だけを行う |
| `issue-reader` | `Qwen3.5-9B` | 低 | Issue本文・関係情報の読み取りに限定する |

### Atomic edit / mutation workers

| モード | 推奨モデル | 推論設定 | 理由 |
|---|---|---|---|
| `patch-applier` | `Qwen3.5-122B` | オン / 中〜高 | allowed scope内で精密patchを適用するためMTPを避ける |
| `new-file-writer` | `Qwen3.5-122B` | オン / 中〜高 | 新規ファイル作成は契約・配置・命名の判断が必要 |
| `test-patch-writer` | `Qwen3.5-122B` | オン / 高 | テスト意図、失敗条件、既存fixture整合の判断が必要 |
| `manifest-editor` | `Qwen3.5-122B` | オン / 中 | package/pyproject等の影響範囲と整合性を判断する |
| `ci-workflow-writer` | `Qwen3.5-122B` | オン / 中〜高 | CI構文、secret境界、実行環境差分の判断が必要 |
| `dependency-editor` | `Qwen3.5-122B` | オン / 高 | 依存衝突、lockfile、peer rangeの判断が必要 |
| `issue-comment-writer` | `Qwen3.5-9B` | 低 | 事実に基づく短い定型コメント作成に限定する |
| `sub-issue-creator` | `Qwen3.5-122B` | オン / 中 | 親子Issue関係とTDD単位分解の判断が必要 |
| `issue-closer` | `Qwen3.5-9B` | オフ〜低 | 指定Issue closeと定型メタデータ返却に限定する |

### Atomic command / environment workers

| モード | 推奨モデル | 推論設定 | 理由 |
|---|---|---|---|
| `exact-command-runner` | `Qwen3.6-9B` | オフ | 指定コマンド実行と終了コード・stdout/stderr要約だけを行う |
| `test-runner` | `Qwen3.6-9B` | オフ | テストコマンド実行結果の機械的返却に限定する |
| `coverage-runner` | `Qwen3.6-9B` | オフ | coverageコマンド実行と出力path/数値返却に限定する |
| `format-lint-runner` | `Qwen3.6-9B` | オフ | format/lintコマンドの実行とメタデータ返却に限定する |
| `build-runner` | `Qwen3.6-9B` | オフ | buildコマンドの実行結果返却に限定する |
| `provider-operator` | `Qwen3.5-122B` | オン / 中〜高 | provider復旧や設定変更は環境判断と停止条件が必要 |
| `container-operator` | `Qwen3.5-122B` | オン / 中 | container操作は副作用範囲と復旧判断が必要 |
| `environment-inspector` | `Qwen3.6-9B` | 低 | 環境情報の取得と短い診断材料化に限定する |

### Atomic classifier / checker workers

| モード | 推奨モデル | 推論設定 | 理由 |
|---|---|---|---|
| `compiler-diagnostic-classifier` | `Qwen3.5-122B` | オン / 中 | compiler診断から原因カテゴリと次手を分類する |
| `test-result-classifier` | `Qwen3.5-122B` | オン / 中 | test failureの種類、flake、契約違反を分類する |
| `coverage-checker` | `Qwen3.5-9B` | 低 | coverage閾値と対象範囲の機械的照合に限定する |
| `scope-checker` | `Qwen3.5-9B` | 低 | 変更scopeとTASK_PACKET制約の照合に限定する |
| `contract-checker` | `Qwen3.5-122B` | オン / 中 | schema/protocol/state transitionの契約整合判断が必要 |
| `test-inventory-checker` | `Qwen3.5-9B` | 低 | テスト分類・件数・配置の棚卸しに限定する |
| `ledger-consistency-checker` | `Qwen3.6-9B` | 低 | RUN_STATE_V1、hash、transitionの整合照合に限定する |
| `handoff-consistency-checker` | `Qwen3.6-9B` | 低 | TASK_PACKET/STATE_DELTA/handoffの形式整合を照合する |
| `workflow-phase-checker` | `Qwen3.6-9B` | 低 | workflow phase cursorと完了条件の照合に限定する |
| `github-relationship-checker` | `Qwen3.5-9B` | 低 | GitHub親子Issue関係の読取・整合チェックに限定する |
| `review-risk-classifier` | `Qwen3.5-122B` | オン / 中 | review指摘の重大度・残リスク分類が必要 |
| `security-risk-classifier` | `GPT-OSS-120B` | オン / 高 | security findingの重大度・悪用可能性分類は誤判定コストが高い |
| `context-metrics-reader` | `Qwen3.6-9B` | 低 | context/ledger metricsの読み取りと集計に限定する |
| `rehydration-auditor` | `Qwen3.6-9B` | オン / 中 | durable ledgerからの再開可能性と欠落を照合する |
| `handoff-budget-checker` | `Qwen3.5-9B` | 低 | handoffサイズ・行数・budget違反の照合に限定する |
| `model-lifetime-checker` | `Qwen3.5-9B` | 低 | 長寿命/短命mode割り当て違反を機械的に検知する |

### Atomic security / review / artifact workers

| モード | 推奨モデル | 推論設定 | 理由 |
|---|---|---|---|
| `secret-auditor` | `GPT-OSS-120B` | オン / 高 | secret露出検知は誤判定コストが高い |
| `dependency-auditor` | `GPT-OSS-120B` | オン / 高 | 依存関係リスク、脆弱性、捏造ライブラリの判断が必要 |
| `unsafe-code-auditor` | `GPT-OSS-120B` | オン / 高 | unsafe patternや危険APIの文脈判断が必要 |
| `fabricated-package-auditor` | `GPT-OSS-120B` | オン / 高 | 実在しないpackageやtyposquatの検知が必要 |
| `implementation-reviewer` | `GPT-OSS-120B` | オン / 高 | 実装品質、保守性、契約遵守のレビュー判断が必要 |
| `architecture-reviewer` | `GPT-OSS-120B` | オン / 高 | 設計整合と境界責務のレビュー判断が必要 |
| `test-reviewer` | `GPT-OSS-120B` | オン / 高 | テスト妥当性、過不足、回帰価値の判断が必要 |
| `performance-risk-reviewer` | `GPT-OSS-120B` | オン / 高 | 性能リスクと複雑度の文脈判断が必要 |
| `artifact-indexer` | `Qwen3.5-9B` | オフ〜低 | artifact一覧・path索引作成に限定する |
| `artifact-conflict-checker` | `Qwen3.6-9B` | 低 | artifact重複、競合、所有境界の照合に限定する |
| `artifact-materializer` | `Qwen3.6-9B` | オフ〜低 | bulky evidenceをartifact化しpathを返すだけに限定する |
| `artifact-retention-planner` | `Qwen3.5-9B` | 低 | 保存/削除候補の定型分類に限定する |

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
| `commands/analysis.md` | Slash Command | project analysis / diagnostic issue workflow entrypoint; GitHub mutation remains delegated |
| `commands/analysys.md` | Slash Command | backward-compatible alias for the former misspelled analysis command |
| `skills/tdd-quality-gate/SKILL.md` | Skill | `/tdd-quality-gate` 専用phase定義 |
| `skills/github-issue-main-task/SKILL.md` | Skill | `/github-issue-main-task` 専用phase定義 |
| `skills/orchestrator-workflows/SKILL.md` | Skill | 旧参照向け互換shim。詳細phase定義のsource of truthではない |
| `skills/orchestrator-delegation-guardrails/SKILL.md` | Skill | 長寿命Orchestratorから外した詳細packet / command / artifact / GitHub / failure例の遅延ロード先 |
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
raw-input-materializer
→ gpt-oss-intake-analyzer
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


`gpt-oss-intake-supervisor` remains only as a deprecated compatibility shim and is not the primary ordinary-input route. Raw本文 must not be passed directly to GPT-OSS, epoch orchestrators, or workers; the only inline raw-body handoff is a single escape-safe `RAW_INPUT_PAYLOAD_V1` envelope subtask to `raw-input-materializer`, which creates `RAW_INPUT_REF_V1` for all later path-based analysis. `raw-input-materializer` is intentionally not an analyzer or worker: it stores the raw artifact, returns path metadata, and stops this mode only with `handoff_status: requires_parent_dispatch`, `workflow_complete: false`, `next_mode: gpt-oss-intake-analyzer`, and `next_action: {type: new_task, tool: new_task, mode: gpt-oss-intake-analyzer}` so Roo/Zoo runtimes can dispatch the required Boomerang `new_task` with its `mode` parameter and do not mistake materialization for final workflow completion. AgentModes Large Input Materialization Contract is a fallback after an LLM can start; provider requests that exceed context before API send require ZooCodeCustom/runtime pre-LLM materialization.

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
- `TASK_PACKET_V1` is sparse and compact: omit empty/default fields, include only current-subtask facts, and pass artifact paths instead of pasted bodies, except the required one-time `RAW_INPUT_PAYLOAD_V1` handoff to `raw-input-materializer`.
- All mode-level customInstructions are intentionally compact; common control-plane/slash/todo/routing/post-condense boilerplate is installed as Zoo/Roo Global Rules from `rules/`; `docs/contracts/compact-mode-contract.md` is the synchronized review copy.
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
| `TASK_PACKET_V1` | `docs/contracts/task-packet-v1.md` | Compact delegated-subtask prompt budget |
| Compact mode contract | `docs/contracts/compact-mode-contract.md` + `rules/00-agentmodes-compact-mode-contract.md` | Reviewed contract plus live Zoo/Roo Global Rules copy for common control-plane/slash/todo/routing/post-condense boilerplate |
| `USER_NEEDS_V1` | `docs/contracts/user-needs-v1.md` | Normalized intake artifact schema |
| Example ledger | `docs/examples/run-state-v1.json` | Minimal state ledger fixture for prompts and validators |
| Phase 3 | `docs/phases/phase-3-control-plane.md` | Control-plane recomposition scope |
| Phase 4 | `docs/phases/phase-4-intake.md` | Intake ledger path and artifact rules |
| Phase 5 | `docs/phases/phase-5-atomic-workers.md` | Atomic worker first-wave registry |
| Phase 6 | `docs/phases/phase-6-atomic-workers-second-wave.md` | Artifact, consistency, issue, security, and review split registry |
| Phase 7 | `docs/phases/phase-7-sliding-window.md` | Sliding-window, rehydration, and root-task rotation policy |
| Phase 8 | `docs/phases/phase-8-metrics-governance.md` | Migration metrics and governance checks |
| `MIGRATION_METRICS_V1` | `docs/contracts/migration-metrics-v1.md` | Observable migration metrics schema |

## Large input materialization policy

Large user inputs are still valid work items. AgentModes expects large specifications, logs, diffs, and handoffs to be persisted as raw artifacts and then processed by path, not rejected for size. The intake flow materializes raw input as `RAW_INPUT_REF_V1` with a `raw_request_path`, derives `USER_NEEDS_V1`, and starts Orchestrator with `SESSION_START_V1` paths. For model-side materialization, the orchestrator sends the raw body exactly once to `raw-input-materializer` in escape-safe `RAW_INPUT_PAYLOAD_V1` envelope; every subsequent subtask is path-only.

GPT-OSS intake must not keep carrying a raw huge body after materialization. Orchestrator proceeds path-only from `raw_request_path`, `user_needs_path`, and state ledger paths, using artifacts as the source of truth.

AgentModes alone cannot fully prevent provider-context overflow before the model receives control. ZooCodeCustom therefore needs a pre-LLM large input materializer for inputs that would exceed provider context. Once AgentModes receives control, the expected behavior is **materialize and continue**, not refusal. If the model-side materializer cannot promptly produce exact artifact metadata, it must fail fast with `MATERIALIZATION_STALLED_V1` and recommend runtime pre-LLM materialization instead of looping indefinitely.
