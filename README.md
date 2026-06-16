# AgentModes

## 推奨モデル割り当て設定例

以下は、このワークスペースのモード設計に対応した推奨割り当て例です。

前提:
- GPT系モデルは `GPT-OSS-*` のみを推奨表に含める
- 推論設定はモデル能力ではなくモード責務で決める
- `Qwen3.5-122B` は Orchestrator、実装、レビュー、整合判定、DevOps など判断密度の高いローカル実行モードに使う
- `Qwen3.5-9B` は限定的な読み取り、索引、単純実行に使う
- `Gemma4-12B-it` は documenter / user-response-composer のような文章生成・整形系に使う
- `tester` / `artifact-manager` は推論オフを推奨し、過剰判断や completion ループを避ける

| モード | 推奨モデル | 推論設定 | 理由 |
|---|---|---|---|
| `orchestrator` | `Qwen3.5-122B` | オン / 高 | 全体制御、分解、SoD、handoff、品質ゲート判断に広い文脈と推論が必要 |
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
| `documenter` | `Gemma4-12B-it` | オフ | Markdown文書生成・整形・説明文品質を優先し、過剰推論で事実を膨らませないため |
| `ask` | `Qwen3.5-122B` | オン / 中 | 技術説明、既存コード理解、計画相談に文脈理解が必要 |
| `user-response-composer` | `Gemma4-12B-it` | オフ | 上流結果を最終ユーザー向け文面に整形するだけで、判断や追加事実生成を禁止するため |

## 最小運用ポリシー

- GPT系モデルは `GPT-OSS-*` のみを推奨表に含める
- `Gemma4-12B-it` は `documenter` / `user-response-composer` のような文章生成・整形系に使う
- `tester` / `artifact-manager` は推論オフを推奨し、過剰判断や completion ループを避ける
- `Qwen3.5-122B` は Orchestrator、実装、レビュー、整合判定、DevOps など判断密度の高いローカル実行モードに使う
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
- `architect` は設計、計画、ADR、実装分解、TDD計画、品質ゲート設計を担当し、`documenter` は README、docs、API reference、architecture notes、handoff summary、利用者/開発者向け説明を担当する
- セキュリティ・依存関係・secret・unsafe pattern・fabricated libraries は `security-auditor` が担当し、`reviewer` は最終品質レビュー、設計整合、保守性、性能、テスト妥当性、残リスク確認を担当する
- `gpt-oss-needs-analyzer` はユーザーまたはランタイムが選択した分析用モデルで動作する任意前段モードとしてだけ使い、ツール実行、ファイル編集、サブタスク作成、他モード呼び出しを禁止する。出力は `ORCHESTRATOR_BRIEF_V1` YAML のみで、既存 Orchestrator はこれを advisory brief として扱い、raw user prompt を常に source of truth とする

## Roo Code ワークフロー

固定手順として扱える品質ゲートは `workflows/` に切り出しています。

| ワークフロー | 用途 |
|---|---|
| `workflows/tdd-quality-gate.json` | AI軽量TDDとして最小Red作成、Red実行、Red判定、Green実装、Coverage 85%以上、test-inventory判定、security-auditor、reviewerまでをSoD分離で実行する |
| `workflows/github-issue-main-task.json` | GitHub Issue URL起点のIssue Intake、サブIssue分解、軽量TDD品質ゲート、Version Tag Push、診断Issue、完了コメント、サブIssue単独close、親Issueへの再ルーティングまでを処理する |
| `workflows/provider-health-recovery.json` | ローカルProviderの空応答・生成停止をProvider Health Failureとして隔離し、provider-health-recovery Skillで復旧する |

ワークフローは順序と責務境界を固定するための定義です。各ステップの実処理は既存のカスタムモード、スラッシュコマンド、Skillに委任し、ログ全文や長い診断結果はArtifact Pathで受け渡します。

## 代替割り当て方針

- コストやレイテンシを優先する場合も、GPT系は `GPT-OSS-*` の範囲に限定する
- `recovery-supervisor` は可能な限り最上位の推論性能を持つモデルを維持する
- 文書生成・最終応答整形は `Gemma4-12B-it` を優先し、追加判断を持たせない
