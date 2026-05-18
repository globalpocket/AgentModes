---
name: provider-health-recovery
description: mlx_lm.server が空応答または生成停止状態に陥った場合に、停止シグナルで安全に停止し、Qwen3.5-9B の固定設定で再起動して疎通確認する復旧Skill。
---

# Provider Health Recovery

## Trigger

このSkillは、ローカルProviderが次の症状を示した場合だけ実行する。

- Roo Code が「テキストやツール呼び出しのない空の応答」を受け取った。
- `mlx_lm.server` 再起動後に同じタスクが正常化した実績がある。
- 同一Providerへ何を送っても空文字または空ストリームだけが返る。
- Code / Debug / Test Writer などの実装失敗ではなく、Providerプロセス健全性の問題として分類できる。

## Scope

- プロジェクトのコード、テスト、設定ファイルは編集しない。
- 依存関係の追加や package 系ファイルの変更は行わない。
- 復旧操作は `mlx_lm.server` の停止、再起動、疎通確認だけに限定する。
- 停止は Terminal の停止シグナル、つまり Ctrl+C 相当の SIGINT を使う。
- 強制終了シグナル SIGKILL は使わない。

## Recovery Steps

1. **対象確認**
   - Actively Running Terminals またはプロセス一覧から `mlx_lm.server` を探す。
   - 対象は `mlx-community/Qwen3.5-9B-4bit` を実行している `mlx_lm.server` を優先する。

2. **停止シグナル送信**
   - Roo Code または VS Code の Terminal 操作で、対象Terminalへ Ctrl+C を1回送る。
   - 5秒待っても停止しない場合は、最大3回まで Ctrl+C を繰り返す。
   - Terminal停止操作が使えない実行環境では、Ctrl+C 相当の SIGINT だけを送る。

   ```sh
   for i in 1 2 3; do
     pkill -INT -f 'mlx_lm.server.*Qwen3.5-9B-4bit' || pkill -INT -f 'mlx_lm.server' || true
     sleep 5
     pgrep -fl 'mlx_lm.server' >/dev/null || break
   done
   ```

3. **停止確認**
   - `pgrep -fl 'mlx_lm.server'` で残存プロセスを確認する。
   - 3回の停止シグナル後も残る場合は、再起動せずに失敗として報告する。

4. **再起動**
   - 次のコマンドをそのまま使って新しいTerminalで起動する。
   - 長時間動作するサーバーなので、コマンド実行時は短い timeout を設定し、起動後はTerminalをバックグラウンド実行状態に残す。

   ```sh
   mlx_lm.server --model mlx-community/Qwen3.5-9B-4bit --prompt-concurrency 1 --decode-concurrency 1 --prompt-cache-size 2 --max-tokens 8192
   ```

5. **疎通確認**
   - 既定ポート `8080` の OpenAI互換APIへ到達確認する。
   - 最大60秒程度まで短い間隔で再試行する。

   ```sh
   for i in {1..30}; do
     curl -fsS http://127.0.0.1:8080/v1/models && exit 0
     sleep 2
   done
   exit 1
   ```

6. **空応答の再発確認**
   - 可能なら最小の非ストリーミング生成を1回実行し、本文が空でないことを確認する。
   - 応答本文が空の場合は復旧失敗として扱い、Code へ戻さない。

   ```sh
   python3 - <<'PY'
   import json
   import urllib.request

   payload = json.dumps({
       "model": "mlx-community/Qwen3.5-9B-4bit",
       "messages": [{"role": "user", "content": "ping"}],
       "max_tokens": 8,
       "stream": False,
   }).encode()
   request = urllib.request.Request(
       "http://127.0.0.1:8080/v1/chat/completions",
       data=payload,
       headers={"Content-Type": "application/json"},
       method="POST",
   )
   with urllib.request.urlopen(request, timeout=60) as response:
       body = json.loads(response.read().decode())
   content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
   print(content)
   raise SystemExit(0 if content.strip() else 2)
   PY
   ```

## Completion Report

完了時は次の固定形式だけを返す。

- **Provider Health**: recovered / failed
- **Stop Signal Attempts**: Ctrl+C または SIGINT の回数
- **Start Command**: 実行した起動コマンド
- **Verification**: `/v1/models` と最小生成の結果
- **Next Step**: 復旧成功なら直前タスクを最新ファイル状態で再委任、失敗なら recovery-supervisor へ環境問題として差し戻し
