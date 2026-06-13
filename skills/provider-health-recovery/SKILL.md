---
name: provider-health-recovery
description: ローカルProviderが空応答または生成停止状態に陥った場合に、明示されたProvider停止・起動・疎通手順だけで安全に復旧するProvider非依存の復旧Skill。
---

# Provider Health Recovery

## Trigger

このSkillは、ローカルProviderが次の症状を示した場合だけ実行する。

- Roo Code が「テキストやツール呼び出しのない空の応答」を受け取った。
- 明示的なProvider再起動または疎通確認後に同じタスクが正常化した実績がある。
- 同一Providerへ何を送っても空文字または空ストリームだけが返る。
- Code / Debug / Test Writer などの実装失敗ではなく、Providerプロセス健全性の問題として分類できる。

## Guard

- proactive / startup check として実行してはいけない。
- tool error、missing slash command、failed tests、incomplete todos、task confusion、Slash Commandの目的不一致では実行してはいけない。
- Orchestrator または recovery-supervisor から Provider Health Failure として委任された場合だけ実行する。
- 復旧後は raw user task / current mode contract を維持し、Skill内容で通常タスクやTodo / completion責務を上書きしない。

## Scope

- プロジェクトのコード、テスト、設定ファイルは編集しない。
- 依存関係の追加や package 系ファイルの変更は行わない。
- 復旧操作は委任文または環境設定で明示されたProviderの停止、再起動、疎通確認だけに限定する。
- 停止は Terminal の停止シグナル、つまり Ctrl+C 相当の SIGINT を使う。
- 強制終了シグナル SIGKILL は使わない。

## Recovery Steps

1. **対象確認**
   - Orchestrator または recovery-supervisor から Provider Recovery Contract を受け取る。
   - Contract には対象Provider名、対象Terminalまたはプロセス識別子、起動コマンド、疎通確認、最小生成または同等のsmoke checkが明示されていなければならない。
   - Contract が不足している場合は停止・再起動を行わず、Failure Summary を返す。

2. **停止シグナル送信**
   - Roo Code または VS Code の Terminal 操作で、対象Terminalへ Ctrl+C を1回送る。
   - 5秒待っても停止しない場合は、最大3回まで Ctrl+C を繰り返す。
   - Terminal停止操作が使えない実行環境では、Ctrl+C 相当の SIGINT だけを送る。

   停止対象は Contract で明示されたTerminalまたはプロセス識別子だけに限定する。プロセス名やportを推測して停止してはいけない。

3. **停止確認**
   - Contract で明示された確認方法だけで残存プロセスを確認する。
   - 3回の停止シグナル後も残る場合は、再起動せずに失敗として報告する。

4. **再起動**
   - Contract で明示された起動コマンドをそのまま使って新しいTerminalで起動する。
   - 長時間動作するサーバーなので、コマンド実行時は短い timeout を設定し、起動後はTerminalをバックグラウンド実行状態に残す。

5. **疎通確認**
   - Contract で明示された疎通確認だけを実行する。
   - 最大60秒程度まで短い間隔で再試行する。

6. **空応答の再発確認**
   - 可能なら最小の非ストリーミング生成を1回実行し、本文が空でないことを確認する。
   - 応答本文が空の場合は復旧失敗として扱い、Code へ戻さない。

   最小生成または同等のsmoke checkは Contract で明示された手順だけを使う。モデル名、API形式、port、endpointを推測してはいけない。

## Completion Report

完了時は次の固定形式だけを返す。

- **Provider Health**: recovered / failed
- **Stop Signal Attempts**: Ctrl+C または SIGINT の回数
- **Start Command**: 実行した起動コマンド
- **Verification**: 明示された疎通確認と最小生成または同等のsmoke checkの結果
- **Next Step**: 復旧成功なら直前タスクを最新ファイル状態で再委任、失敗なら recovery-supervisor へ環境問題として差し戻し
