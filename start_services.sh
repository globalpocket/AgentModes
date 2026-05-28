#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${SCRIPT_DIR}/logs/services"
PID_DIR="${SCRIPT_DIR}/pids/services"

mkdir -p "${LOG_DIR}" "${PID_DIR}"

start_process() {
  local name="$1"
  shift

  local log_file="${LOG_DIR}/${name}.log"
  local pid_file="${PID_DIR}/${name}.pid"

  echo "Starting ${name}..."
  nohup "$@" >"${log_file}" 2>&1 < /dev/null &
  local pid="$!"

  echo "${pid}" >"${pid_file}"
  echo "${name}: PID ${pid} / log ${log_file}"
}

start_process "mlx_lm_server" \
  mlx_lm.server \
  --model mlx-community/Qwen3.5-4B-OptiQ-4bit \
  --prompt-concurrency 1 \
  --decode-concurrency 1 \
  --prompt-cache-size 1 \
  --max-tokens 8192 \
  --log-level DEBUG \
  --temp 0.1

start_process "infinity_emb" \
  infinity_emb v2 \
  --model-id BAAI/bge-m3 \
  --url-prefix /v1 \
  --port 7997

start_process "qdrant" \
  qdrant

echo "All processes started."
echo "PID files: ${PID_DIR}"
echo "Log files: ${LOG_DIR}"
