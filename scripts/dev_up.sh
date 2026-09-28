#!/usr/bin/env bash
# 서비스 5개를 로컬 포트 8001~8005 에 띄운다 (SQLite). 종료: scripts/dev_down.sh
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$ROOT/.run"
i=1
for svc in market-data youtube mentions stats; do
  port=$((8000 + i))
  cd "$ROOT/services/$svc"
  PORT=$port nohup "$ROOT/.venv/bin/uvicorn" main:app --host 127.0.0.1 --port $port > "$ROOT/.run/$svc.log" 2>&1 &
  echo $! > "$ROOT/.run/$svc.pid"
  echo "$svc -> http://127.0.0.1:$port/docs"
  i=$((i + 1))
done
