# 複数テスト対象の1ファイル単位分割委任 実行計画

## 前提

- 対象はプロンプト規約の文書・YAML改修であり、今回の計画作成自体には軽量TDDを適用しない。
- 後続実装では [rules/test-writer.yaml](../rules/test-writer.yaml:2), [rules/tester.yaml](../rules/tester.yaml:2), [all-agents.yaml](../all-agents.yaml:1783) を同期対象とする。
- 実装YAML全般は今回の Architect タスクでは編集しない。
- GitHub Integration State は unknown-skipped とし、GitHub MCP、Version Tag Push、Diagnostic Issue は対象外にする。

## 実行チェックリスト

- [x] 設計書レビューゲート
  - TDD Level: N/A 文書改修
  - Test Classification: design-contract
  - Red-Green-Refactor: 不適用
  - Acceptance Criteria:
    - [plans/one-file-test-target-design.md](one-file-test-target-design.md) に責任、インターフェース、データ構造相当の契約がある。
    - 複数テスト対象の検出条件と `Test Target Unit` が定義されている。
    - Coverage 85%以上は後続実装時の統合ゲートとして残されている。

- [x] test-writer 個別 rule 更新計画
  - TDD Level: N/A プロンプト改修
  - Test Classification: contract
  - Red-Green-Refactor: 不適用。編集後に output-contract 判定を行う。
  - Edit Files: [rules/test-writer.yaml](../rules/test-writer.yaml:2)
  - Acceptance Criteria:
    - 複数テスト対象を検出した場合、1委任1テストファイルへ分割する契約が明記される。
    - test-writer 自身が分割委任や tester 起動を行わないことが明記される。
    - Initial Test Count 最大3個は対象テストファイル単位で適用される。

- [x] tester 個別 rule 更新計画
  - TDD Level: N/A プロンプト改修
  - Test Classification: contract
  - Red-Green-Refactor: 不適用。編集後に output-contract 判定を行う。
  - Edit Files: [rules/tester.yaml](../rules/tester.yaml:2)
  - Acceptance Criteria:
    - tester 委任は1対象テストファイル、1コマンド、1 Artifact Path に限定される。
    - 複数コマンドまたは複数 Artifact Path が渡された場合は Failure Summary を返す。
    - 統合 Coverage コマンドは全 Unit Green 後の別委任だけで許可される。

- [x] all-agents 同期更新計画
  - TDD Level: N/A 集約定義同期
  - Test Classification: contract-sync
  - Red-Green-Refactor: 不適用。個別 rule 更新後に同期差分を入れる。
  - Edit Files: [all-agents.yaml](../all-agents.yaml:1783)
  - Acceptance Criteria:
    - test-writer ブロックが [rules/test-writer.yaml](../rules/test-writer.yaml:20) と同一文意になる。
    - tester ブロックが [rules/tester.yaml](../rules/tester.yaml:20) と同一文意になる。
    - 個別 rule と all-agents の分割契約に矛盾がない。

- [x] Orchestrator 委任文更新計画
  - TDD Level: N/A プロンプト改修
  - Test Classification: workflow-contract
  - Red-Green-Refactor: 不適用。必要な場合だけ別サブタスク化する。
  - Edit Files: Orchestrator 定義ファイル1件に限定する。
  - Acceptance Criteria:
    - Orchestrator が複数テスト対象を `Test Target Unit` へ分割する責務を持つ。
    - test-writer / tester へ複数ファイル委任しない制約が明記される。
    - 各 Unit 完了後に統合 Coverage 85%以上、security-auditor、reviewer へ進む。

- [x] 文書改修品質確認
  - TDD Level: N/A 品質ゲート
  - Test Classification: output-contract / regression
  - Red-Green-Refactor: 不適用。変更後に静的確認だけ行う。
  - Acceptance Criteria:
    - Markdown 設計と YAML 改修が同じ契約名、同じ分割単位、同じ禁止条件を使う。
    - 実装YAML以外の禁止ファイル、[storage/](../storage/)、[.git/](../.git/) に変更がない。
    - Coverage 85%以上、security-auditor、reviewer の後続ゲートが削除されていない。

## 後続モード分割案

1. analyzer: [rules/test-writer.yaml](../rules/test-writer.yaml:20), [rules/tester.yaml](../rules/tester.yaml:20), [all-agents.yaml](../all-agents.yaml:1783) の正確な更新範囲を特定する。
2. code または technical-writer: YAMLプロンプト文面だけを最小差分で更新する。実行コマンドは実行しない。
3. consistency-checker: output-contract と implementation-scope を判定する。
4. reviewer: プロンプト契約の矛盾、責務混在、Coverage 85%以上ゲート削除の有無を監査する。

## 同期順序

1. [rules/test-writer.yaml](../rules/test-writer.yaml:2) に1ファイル分割契約を追加する。
2. [rules/tester.yaml](../rules/tester.yaml:2) に1ファイル実行契約を追加する。
3. [all-agents.yaml](../all-agents.yaml:1783) の test-writer / tester 対応ブロックへ同一文意で同期する。
4. 必要な場合だけ Orchestrator 定義へ `Test Target Unit` 分割責務を追加する。
5. 変更後、文書と YAML の契約名・禁止条件・品質ゲートを照合する。

## リスクと抑止策

- リスク: test-writer が複数テストファイルを一括編集する。抑止策: Edit Files 1件制約と Failure Summary 条件を明記する。
- リスク: tester が全テスト実行を Red / Green 単体フェーズで実行する。抑止策: 統合 Coverage フェーズ以外の glob / all tests を禁止する。
- リスク: all-agents と個別 rule が同期漏れする。抑止策: 個別 rule 先行、all-agents 後追い、同一文意確認を計画へ固定する。
- リスク: Coverage 85%以上がファイル単位分割で曖昧になる。抑止策: Unit Green 後に統合 Coverage Gate を別委任として扱う。
