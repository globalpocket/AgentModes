---
name: roocode-recursive-dispatch
description: メインタスク完了時に、登録済み Roo Code IPC ソケットへ非同期で StartNewTask を送信し、VSCode 上の Roo Code に次タスクを画面付きで再帰委任する Skill。
---

# RooCode Recursive Dispatch

## Purpose

メインタスクの品質ゲート通過後に、起動中の VSCode 拡張側 Roo Code へ IPC 経由で次のメインタスクを投入する。CLI の print / TUI 実行は VSCode 画面上の Roo Code サイドバーへ投入する仕組みではないため、この Skill では使用しない。

## Slash Command Entry

Orchestrator のメインタスク最終完了直前では、暗黙のSkill適用だけに依存せず、必ず `/roocode-recursive-dispatch` スラッシュコマンドを明示実行する。対応するコマンド定義は `commands/roocode-recursive-dispatch.md` とし、同コマンドがこの Skill をロードして実行する。

- Orchestrator は attempt_completion の直前に `/roocode-recursive-dispatch` を起動する。
- スラッシュコマンド展開後は、この Skill の Required Inputs、Target Socket Resolution、Recursion Guard、Async Dispatch Command、Verification、Failure Handling をそのまま適用する。
- スラッシュコマンド環境で skill ツールが使えない場合だけ、この SKILL.md の手順をSkill本体として実行する。
- `/roocode-recursive-dispatch` の実行失敗、skipped、duplicate は現在のメインタスク品質完了を取り消す理由にしない。

## Global Skill / Workspace Boundary

この Skill はグローバル Skill として実行される場合があるため、対象プロジェクトのワークスペース内に `commands/roocode-recursive-dispatch.md` や `skills/roocode-recursive-dispatch/SKILL.md` が存在することを前提にしてはいけない。

- Skill ツールで本Skillがロード済みなら、そのロード済み手順を唯一の実行仕様として扱い、対象ワークスペース内の `commands/` や `skills/` を探索しない。
- `commands/roocode-recursive-dispatch.md` はこの設定リポジトリ側の補助エントリであり、ディスパッチ対象ワークスペースに無くても失敗ではない。
- `.roo/recursive-dispatch/target.json`、`.roo/recursive-dispatch/history.jsonl` は状態ファイルであり、初回実行時に存在しないのが正常である。存在確認目的で `read_file` して ENOENT を発生させてはいけない。
- 対象ワークスペースで読む必要がある入力は、生成済みまたは生成する `.roo/recursive-dispatch/next-prompt.md` と `.roo/recursive-dispatch/parent-summary.md` だけである。

## Reference Facts

- Roo CLI は VSCode 外の Node.js 環境で Roo Code agent を動かすための仕組みであり、非対話 print 実行や stdin stream 実行に対応する。
- IPC は外部プロセスから Roo Code 拡張へソケット通信する仕組みで、StartNewTask / CancelTask / CloseTask / ResumeTask などを送れる。
- StartNewTask は configuration、text、images、newTab を data として受け取る。
- Unix / macOS の IPC ソケットは通常 /tmp/roo-code-{id}.sock 形式で作成される。
- 複数 VSCode / 複数ワークスペース環境では、最初に見つかったソケットへ送信してはいけない。対象ソケットは明示指定またはワークスペース内レジストリで固定する。

## Trigger

この Skill は、Orchestrator がメインタスクの最終完了直前に次の条件をすべて満たした場合だけ実行する。

- 実装、テスト、Coverage 85%以上、security-auditor、reviewer、必要な診断登録が完了している。
- 次に投入する独立したメインタスク指示が Next Recursive Task として明示されている。
- 現在のタスクがサブタスク、Red 確認、Green 修正、依存解決、レビュー差し戻し、復旧ループの途中ではない。
- 再帰深度が Max Depth 未満である。

条件を満たさない場合は、IPC 送信を行わず no-op として完了扱いにする。

## Scope

- ソースコード、テスト、依存関係、CI、README を変更しない。
- 実行対象は IPC 送信と、ワークスペース内の .roo/recursive-dispatch 配下にある送信ログ / レジストリ / 一時プロンプトだけに限定する。
- VSCode 外で Roo agent を起動する roo --print / roo --stdin-prompt-stream / TUI 起動は使わない。
- 対象未確定の /tmp/roo-code-*.sock へ送らない。
- CancelTask / CloseTask / ResumeTask は使わない。送信コマンドは StartNewTask のみ。
- npm install、pnpm add、yarn add、pip install などの依存関係操作をこの Skill 内で実行しない。IPC クライアント依存が不足する場合は segregated-devops へ分離する。

## State File Initialization

IPC送信または検証の前に、必ず対象ワークスペース内で次の状態ディレクトリと軽量ファイルを初期化する。

```sh
mkdir -p .roo/recursive-dispatch
touch .roo/recursive-dispatch/dispatch.log .roo/recursive-dispatch/history.jsonl
```

- `target.json` は socket が確定した後に作成される任意ファイルであり、存在しない場合は env / single-candidate 解決へ進む。
- `history.jsonl` は初回実行時に空でよい。空ファイルは duplicate なしとして扱う。
- 検証時は、初期化後の `history.jsonl` を読む。初期化前の `read_file` による存在確認は禁止する。
- `history.jsonl` が空で、`dispatch.log` に socket missing / ambiguous / Ack timeout / import failure がある場合は、ファイル欠落ではなく該当 Failure Handling として扱う。

## Required Inputs

- Next Recursive Task Prompt: 次の VSCode Roo Code に渡す完全な指示文。
- Dispatch Mode: 起動する Roo Code mode。未指定なら orchestrator。
- Workspace Path: 現在のワークスペース絶対パス。
- Parent Task Summary: 完了済みメインタスクの最大12行要約。
- Dispatch Depth: 現在の再帰深度。未指定なら 0。
- Max Depth: 最大再帰深度。未指定なら 1、上限は 3。
- Dispatch Delay Seconds: 非同期送信前に待つ秒数。未指定なら 0、上限は 3600。
- Dispatch Nonce: 同一プロンプトを時間差で再投入する場合の重複抑止回避値。通常はISO時刻。

## Target Socket Resolution

対象ソケットは次の優先順位で決定する。

1. 環境変数 ROO_CODE_IPC_SOCKET が存在し、Unix socket として存在する場合はそれを使う。
2. .roo/recursive-dispatch/target.json が存在し、socketPath が Unix socket として存在する場合はそれを使う。
3. 上記がなく、/tmp/roo-code-*.sock が 1 件だけ存在する場合だけ、Ack 検証後に .roo/recursive-dispatch/target.json へ記録して使う。
4. 候補が 0 件または 2 件以上の場合は送信しない。

target.json の形式:

```json
{
  "socketPath": "/tmp/roo-code-xxxxxxxx.sock",
  "workspacePath": "/absolute/path/to/workspace",
  "recordedAt": "2026-01-01T00:00:00.000Z",
  "source": "env-or-single-candidate"
}
```

## Recursion Guard

送信する prompt の先頭には必ず次のメタ情報を付与する。

```text
Recursive Dispatch Context:
- Parent Workspace: <workspace path>
- Parent Task Summary: <12 lines max>
- Dispatch Depth: <next depth>
- Max Depth: <max depth>
- Loop Guard: Do not invoke roocode-recursive-dispatch again unless a new independent Next Recursive Task is explicitly present and Dispatch Depth is lower than Max Depth.
```

同じ Parent Task Summary と Next Recursive Task Prompt の組み合わせを同一 workspace から再送しない。必要に応じて .roo/recursive-dispatch/history.jsonl に fingerprint を追記し、同一 fingerprint が存在する場合は duplicate として no-op にする。

fingerprint は SHA-256(workspacePath + dispatchMode + parentSummary + nextPrompt + dispatchNonce) とする。Issue待機ポーリングのように同じ指示を時間差で再投入する場合は、Dispatch Nonce に次回確認予定時刻を入れる。

## Async Dispatch Command

Orchestrator は Next Recursive Task Prompt を .roo/recursive-dispatch/next-prompt.md に保存し、次のコマンドを短い timeout で実行する。コマンドはバックグラウンドで送信し、Roo Code の次タスク完了を待たない。

```sh
mkdir -p .roo/recursive-dispatch
touch .roo/recursive-dispatch/dispatch.log .roo/recursive-dispatch/history.jsonl
ROO_WORKSPACE="$PWD" \
ROO_DISPATCH_MODE="${ROO_DISPATCH_MODE:-orchestrator}" \
ROO_DISPATCH_DELAY_SECONDS="${ROO_DISPATCH_DELAY_SECONDS:-0}" \
ROO_DISPATCH_NONCE="${ROO_DISPATCH_NONCE:-}" \
ROO_DISPATCH_PROMPT_FILE=".roo/recursive-dispatch/next-prompt.md" \
ROO_DISPATCH_PARENT_SUMMARY_FILE=".roo/recursive-dispatch/parent-summary.md" \
ROO_DISPATCH_LOG=".roo/recursive-dispatch/dispatch.log" \
nohup node --input-type=module <<'NODE' >>".roo/recursive-dispatch/dispatch.log" 2>&1 &
import fs from "node:fs"
import os from "node:os"
import path from "node:path"
import crypto from "node:crypto"
import { pathToFileURL } from "node:url"

const workspace = process.env.ROO_WORKSPACE || process.cwd()
const stateDir = path.join(workspace, ".roo", "recursive-dispatch")
const targetFile = path.join(stateDir, "target.json")
const historyFile = path.join(stateDir, "history.jsonl")
const promptFile = process.env.ROO_DISPATCH_PROMPT_FILE || path.join(stateDir, "next-prompt.md")
const parentSummaryFile = process.env.ROO_DISPATCH_PARENT_SUMMARY_FILE || path.join(stateDir, "parent-summary.md")

fs.mkdirSync(stateDir, { recursive: true })
if (!fs.existsSync(historyFile)) fs.writeFileSync(historyFile, "")

const maxDepth = Math.min(Number(process.env.ROO_RECURSIVE_MAX_DEPTH || "1") || 1, 3)
const currentDepth = Number(process.env.ROO_RECURSIVE_DEPTH || "0") || 0
const dispatchMode = (process.env.ROO_DISPATCH_MODE || "orchestrator").trim() || "orchestrator"
const delaySeconds = Math.min(Math.max(Number(process.env.ROO_DISPATCH_DELAY_SECONDS || "0") || 0, 0), 3600)
const dispatchNonce = process.env.ROO_DISPATCH_NONCE || ""
if (currentDepth >= maxDepth) process.exit(0)

const nextPrompt = fs.readFileSync(path.resolve(workspace, promptFile), "utf8").trim()
if (!nextPrompt) process.exit(0)

const parentSummary = fs.existsSync(path.resolve(workspace, parentSummaryFile))
  ? fs.readFileSync(path.resolve(workspace, parentSummaryFile), "utf8").split(/\r?\n/).slice(0, 12).join("\n")
  : "not provided"

const fingerprint = crypto.createHash("sha256").update(workspace + "\n" + dispatchMode + "\n" + parentSummary + "\n" + nextPrompt + "\n" + dispatchNonce).digest("hex")
const historyText = fs.existsSync(historyFile) ? fs.readFileSync(historyFile, "utf8") : ""
if (historyText.includes(fingerprint)) {
  console.log(JSON.stringify({ status: "skipped", reason: "duplicate fingerprint", fingerprint, at: new Date().toISOString() }))
  process.exit(0)
}

if (delaySeconds > 0) {
  await new Promise((resolve) => setTimeout(resolve, delaySeconds * 1000))
}

function isSocket(candidate) {
  try { return fs.statSync(candidate).isSocket() } catch { return false }
}

function resolveSocketPath() {
  const envSocket = process.env.ROO_CODE_IPC_SOCKET
  if (envSocket && isSocket(envSocket)) return { socketPath: envSocket, source: "env" }
  if (fs.existsSync(targetFile)) {
    const parsed = JSON.parse(fs.readFileSync(targetFile, "utf8"))
    if (parsed.socketPath && isSocket(parsed.socketPath)) return { socketPath: parsed.socketPath, source: "registry" }
  }
  const candidates = fs.readdirSync(os.tmpdir())
    .filter((name) => /^roo-code-.+\.sock$/.test(name))
    .map((name) => path.join(os.tmpdir(), name))
    .filter(isSocket)
  if (candidates.length !== 1) throw new Error(`IPC socket is ambiguous or missing: ${candidates.length} candidate(s)`)
  return { socketPath: candidates[0], source: "single-candidate" }
}

async function loadIpcClient() {
  if (process.env.ROO_IPC_MODULE) {
    const spec = path.isAbsolute(process.env.ROO_IPC_MODULE)
      ? pathToFileURL(process.env.ROO_IPC_MODULE).href
      : process.env.ROO_IPC_MODULE
    return await import(spec)
  }
  try {
    return await import("@roo-code/ipc")
  } catch (firstError) {
    const { execFileSync } = await import("node:child_process")
    const globalRoot = execFileSync("npm", ["root", "-g"], { encoding: "utf8" }).trim()
    const globalPackage = path.join(globalRoot, "@roo-code", "ipc")
    if (!fs.existsSync(globalPackage)) throw firstError
    return await import(pathToFileURL(globalPackage).href)
  }
}

const { socketPath, source } = resolveSocketPath()
const { IpcClient } = await loadIpcClient()
const client = new IpcClient(socketPath, () => {})
const payloadText = `Recursive Dispatch Context:\n- Parent Workspace: ${workspace}\n- Parent Task Summary:\n${parentSummary}\n- Dispatch Mode: ${dispatchMode}\n- Dispatch Depth: ${currentDepth + 1}\n- Max Depth: ${maxDepth}\n- Loop Guard: Do not invoke roocode-recursive-dispatch again unless a new independent Next Recursive Task is explicitly present and Dispatch Depth is lower than Max Depth.\n\nNext Recursive Task:\n${nextPrompt}\n`

await new Promise((resolve, reject) => {
  const timer = setTimeout(() => reject(new Error("IPC Ack timeout")), 5000)
  client.once("Ack", () => {
    clearTimeout(timer)
    client.sendCommand({
      commandName: "StartNewTask",
      data: {
        configuration: { mode: dispatchMode },
        text: payloadText,
        images: [],
        newTab: true,
      },
    })
    resolve()
  })
})

fs.writeFileSync(targetFile, JSON.stringify({ socketPath, workspacePath: workspace, recordedAt: new Date().toISOString(), source }, null, 2))
fs.appendFileSync(historyFile, JSON.stringify({ fingerprint, socketPath, dispatchMode, delaySeconds, depth: currentDepth + 1, maxDepth, dispatchedAt: new Date().toISOString() }) + "\n")
setTimeout(() => { client.disconnect(); process.exit(0) }, 500)
NODE
```

## Verification

非同期起動コマンド自体は即時終了してよい。Orchestrator は次の軽量確認だけを行う。

1. `mkdir -p` と `touch` により `.roo/recursive-dispatch/dispatch.log` と `.roo/recursive-dispatch/history.jsonl` が存在する状態にしてから確認する。
2. `.roo/recursive-dispatch/dispatch.log` に IPC Ack timeout、IPC socket is ambiguous or missing、module import failure がないことを確認する。
3. `.roo/recursive-dispatch/history.jsonl` に今回 fingerprint が追記されていれば dispatched とする。
4. history が空または今回 fingerprint が無く、dispatch.log に duplicate fingerprint があれば skipped とする。
5. history が空または今回 fingerprint が無く、dispatch.log に Failure Handling 対象のエラーがあれば failed とする。
6. 失敗時も現在のメインタスク完了結果を取り消さず、Recursive Dispatch failed として完了報告に残す。

## Failure Handling

- `history.jsonl` または `target.json` 欠落: 初回実行の正常状態。`history.jsonl` は空で初期化し、`target.json` は任意として扱う。これだけを failed にしてはいけない。
- socket 候補 0 件: VSCode Roo Code IPC server が見つからないため送信しない。
- socket 候補 2 件以上: 誤爆防止のため送信しない。
- @roo-code/ipc import 失敗: 依存関係操作を行わず、segregated-devops へ IPC クライアント導入タスクとして分離する。
- Ack timeout: 対象 socket が古い、または拡張側 IPC server が応答していないため送信しない。
- duplicate fingerprint: 同一指示の再帰ループ防止として no-op にする。
- delayed self-dispatch: 同一プロンプトを時間差で自己再投入する場合は Dispatch Nonce を必ず変える。

## Completion Report

完了時は次の固定形式だけを返す。

- **Recursive Dispatch**: dispatched / skipped / failed
- **Dispatch Mode**: orchestrator / assigned-issue-dispatcher / other explicit mode
- **Socket Source**: env / registry / single-candidate / none / ambiguous
- **Depth**: current -> next / max
- **Delay**: seconds
- **Prompt File**: .roo/recursive-dispatch/next-prompt.md
- **Log File**: .roo/recursive-dispatch/dispatch.log
- **Next Step**: dispatched なら次タスクは VSCode Roo Code 側で独立実行、failed なら現在タスクは完了扱いのまま Failure Handling の分類を記録
