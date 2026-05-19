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
| `code` | `Qwen3.5-9B` | オン / 最高 | Green実装前のスコープ・API・副作用チェックに内部推論を使い、最小差分へ責務を限定するため |
| `debug` | `GPT-5.4-mini` | オン / 中 | 再現テスト起点の原因特定は必要だが、復旧監督ほど高コストにしないため |
| `test-writer` | `Qwen3.5-9B` | オン / 最高 | 境界値・異常系・Red成立条件の内部検討に推論を使い、編集対象はテストに限定するため |
| `tester` | `Qwen3.5-9B` | オン / 最高 | ログ圧縮、失敗テスト抽出、Coverage要約に推論を使い、修正提案は行わないため |
| `librarian` | `Qwen3.5-9B` | オン / 最高 | 探索順序と索引分類に推論を使い、全文読解や実装推測へ拡大しないため |
| `analyzer` | `GPT-5.4-mini` | オン / 低 | パッチ位置の正確性は必要だが、長い設計推論は不要だから |
| `security-auditor` | `GPT-5.4` | オン / 中〜高 | 脆弱性検知と捏造ライブラリ判定の精度を優先するため |
| `refactorer` | `Qwen3.5-9B` | オン / 最高 | 振る舞い不変性と局所リスク確認に推論を使い、新機能追加を禁止するため |
| `segregated-devops` | `GPT-5.3-codex` | オン / 中 | 依存関係・CI・環境構築はコマンドと設定整合の両方が必要だから |
| `release-manager` | `Qwen3.5-9B` | オン / 最高 | Orchestratorが品質ゲート通過後の入力を固定し、GitHub MCP操作を定型順序で実行するだけに限定できるため |
| `technical-writer` | `GPT-5.4-mini` | オン / 低 | 文書整形と説明が主で、深い探索推論は不要だから |
| `documenter` | `GPT-5.4-mini` | オン / 低 | 後方互換モードとして、軽量な文書更新に向くため |
| `platform-sre` | `GPT-5.3-codex` | オン / 中 | 後方互換のインフラ・CIモードとして整合的だから |

## 最小運用ポリシー

- `Qwen3.5-9B` を割り当てるモードでは、推論レベルを最高に設定し、内部推論を事前チェック・ログ圧縮・スコープ検証に使う
- Qwen担当モードは推論過程や自己対話を出力せず、外部出力はツール実行または固定形式の短い事実報告に限定する
- write権限を持つモードのうち、`code` / `test-writer` / `refactorer` は、Orchestratorによる極小タスク分解を前提に運用
- `code` / `debug` は実装・修正の担当であり、テスト実行、Coverage測定、依存関係操作を行わない
- テスト実行とCoverage測定は `tester`、依存関係追加・peer依存衝突・lockfile更新は `segregated-devops` に分離する
- `npm install`、`pnpm add`、`yarn add`、`pip install` は `segregated-devops` 以外で実行しない
- coverage provider不足時は、既存テストフレームワークと同一バージョン帯のproviderを `segregated-devops` が選定し、`--force` や `--legacy-peer-deps` は原則使わない
- `recovery-supervisor` は、通常の差し戻しで収束しない場合のみ投入し、常用しない
- `release-manager` は、テスト、Coverage 85%以上、security-auditor、reviewer の品質ゲート通過後にのみ投入し、Qwen担当の定型実行モードとしてGitHub MCPによる公開手順だけを担当する
- `orchestrator` と `architect` は、タスクを直接実装せず、分解と委任に専念させる

## 代替割り当て例

コストやレイテンシを優先する場合の代替例:

- `orchestrator`: `GPT-5.4` → `GPT-5.2`
- `architect`: `GPT-5.4` → `GPT-5.2`
- `reviewer`: `GPT-5.4` → `GPT-5.2`
- `debug`: `GPT-5.4-mini` → `GPT-5.2-codex`
- `segregated-devops`: `GPT-5.3-codex` → `GPT-5.2-codex`

ただし、`recovery-supervisor` だけは、可能な限り最上位の推論性能を持つモデルを維持することを推奨します。
