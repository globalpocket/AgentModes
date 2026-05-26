# AgentModes

## 推奨モデル割り当て設定例

以下は、このワークスペースのモード設計に対応した推奨割り当て例です。

前提:
- `Qwen3.5-9B` は**推論レベル最高**前提
- Qwen担当モードは内部推論を使って事前点検と結果圧縮を行うが、外部出力はツール呼び出しと固定形式の短い事実報告に限定する
- write権限を持つQwen担当モードは、原則として低コスト運用を維持しつつ、推論をスコープ遵守・API意味確認・最小差分選定に使う
- 再設計、復旧監督、統括、監査のような判断密度が高いモードには、より強いGPT系モデルを割り当てる

| モード | 推奨モデル | 推論設定 | 理由 |
|---|---|---|---|
| `orchestrator` | `GPT-5.4` | オン / 高 | タスク分解、委任、エスカレーション判定、文脈圧縮の中心だから |
| `architect` | `GPT-5.4` | オン / 高 | 設計と責務分離の再構成が必要だから |
| `reviewer` | `GPT-5.4` | オン / 中〜高 | 品質監査、設計整合性、リスク判定を安定させるため |
| `recovery-supervisor` | `GPT-5.5` | オン / 高 | ループ脱出、失敗分類、再委任再設計の上位監督役だから |
| `ask` | `GPT-5.4` | オン / 中 | 設計・実装・計画の文脈説明を安全に返すため |
| `issue-tracker` | `Qwen3.5-9B` | オン / 最高 | GitHub Issue本文取得、親子Issue判定、未対応サブIssue選択、サブIssue作成、進捗コメント登録だけを固定手順で行い、実装推論を持たないため |
| `assigned-issue-dispatcher` | `Qwen3.5-9B` | オン / 最高 | 認証済みGitHubユーザーにassignされたopen Issue探索、固定パターンによる完了済みopen Issue除外、Orchestratorまたは自己待機ポーリングへのIPCディスパッチだけを担当するため |
| `code` | `Qwen3.5-9B` | オン / 最高 | Green実装前のスコープ・API・副作用チェックに内部推論を使い、最小差分へ責務を限定するため |
| `debug` | `Qwen3.5-9B` | オン / 最高 | Orchestratorが再現テスト、対象ファイル、失敗シグネチャを固定して渡す前提なら、根本原因修正を局所差分へ限定できるため |
| `test-writer` | `Qwen3.5-9B` | オン / 最高 | 境界値・異常系・Red成立条件の内部検討に推論を使い、編集対象はテストに限定するため |
| `tester` | `Qwen3.5-9B` | オン / 最高 | ログ圧縮、失敗テスト抽出、Coverage要約に推論を使い、修正提案は行わないため |
| `librarian` | `Qwen3.5-9B` | オン / 最高 | 探索順序と索引分類に推論を使い、全文読解や実装推測へ拡大しないため |
| `analyzer` | `Qwen3.5-9B` | オン / 最高 | 正確な行番号、前後文脈、差分位置の抽出だけを行う読み取り専任であり、設計判断を持たないため |
| `security-auditor` | `GPT-5.4` | オン / 中〜高 | 脆弱性検知と捏造ライブラリ判定の精度を優先するため |
| `refactorer` | `Qwen3.5-9B` | オン / 最高 | 振る舞い不変性と局所リスク確認に推論を使い、新機能追加を禁止するため |
| `segregated-devops` | `GPT-5.3-codex` | オン / 中 | 依存関係衝突、CI、環境構築はコマンド実行と設定整合の判断密度が高く、失敗時の復旧設計も必要だから |
| `technical-writer` | `Qwen3.5-9B` | オン / 最高 | 設計書と実装済み差分を基にMarkdown文書を整形する専任で、編集対象と出力形式を固定できるため |

## 最小運用ポリシー

- `Qwen3.5-9B` を割り当てるモードでは、推論レベルを最高に設定し、内部推論を事前チェック・ログ圧縮・スコープ検証に使う
- Qwen担当モードは推論過程や自己対話を出力せず、外部出力はツール実行または固定形式の短い事実報告に限定する
- write権限を持つモードのうち、`code` / `test-writer` / `refactorer` は、Orchestratorによる極小タスク分解を前提に運用
- `code` / `debug` は実装・修正の担当であり、テスト実行、Coverage測定、依存関係操作を行わない
- テスト実行とCoverage測定は `tester`、依存関係追加・peer依存衝突・lockfile更新は `segregated-devops` に分離する
- `npm install`、`pnpm add`、`yarn add`、`pip install` は `segregated-devops` 以外で実行しない
- coverage provider不足時は、既存テストフレームワークと同一バージョン帯のproviderを `segregated-devops` が選定し、`--force` や `--legacy-peer-deps` は原則使わない
- `recovery-supervisor` は、通常の差し戻しで収束しない場合のみ投入し、常用しない
- メインタスクがGitHub Issue URLだけで開始された場合は、`issue-tracker` がIssue本文を読み、親子Issueを判定する。指定IssueがサブIssueなら通常対応し、指定IssueがメインIssueかつ未対応サブIssueがある場合は番号が一番若い未対応サブIssueを通常対応する。未対応サブIssueがない場合は、1TDD単位のサブIssueを1件以上、最大8件推奨、絶対最大12件で作成し、Backlogization Completedとして終了する
- GitHub由来リポジトリでのメインタスク終了時のプロジェクト診断とGitHub Issue登録は `diagnostic-reporter` に分離する。非GitHubリポジトリでは診断Issue登録を起動しない
- `orchestrator` と `architect` は、タスクを直接実装せず、分解と委任に専念させる

## Roo Code ワークフロー

固定手順として扱える品質ゲートは `.roo/workflows/` に切り出しています。

| ワークフロー | 用途 |
|---|---|
| `.roo/workflows/tdd-quality-gate.json` | Red作成、Red実行、Red判定、Green実装、Coverage 85%以上、security-auditor、reviewerまでをSoD分離で実行する |
| `.roo/workflows/github-issue-main-task.json` | GitHub Issue URL起点のIssue Intake、サブIssue分解、TDD品質ゲート、診断Issue、完了コメント、次Issue探索までを処理する |
| `.roo/workflows/post-task-recursive-dispatch.json` | メインタスク完了直前に `/roocode-recursive-dispatch` を明示実行し、assigned-issue-dispatcherを非同期起動する |
| `.roo/workflows/provider-health-recovery.json` | `mlx_lm.server` の空応答・生成停止をProvider Health Failureとして隔離し、provider-health-recovery Skillで復旧する |

ワークフローは順序と責務境界を固定するための定義です。各ステップの実処理は既存のカスタムモード、スラッシュコマンド、Skillに委任し、ログ全文や長い診断結果はArtifact Pathで受け渡します。

## 代替割り当て例

コストやレイテンシを優先する場合の代替例:

- `orchestrator`: `GPT-5.4` → `GPT-5.2`
- `architect`: `GPT-5.4` → `GPT-5.2`
- `reviewer`: `GPT-5.4` → `GPT-5.2`
- `debug`: `GPT-5.4-mini` → `GPT-5.2-codex`
- `segregated-devops`: `GPT-5.3-codex` → `GPT-5.2-codex`

ただし、`recovery-supervisor` だけは、可能な限り最上位の推論性能を持つモデルを維持することを推奨します。
