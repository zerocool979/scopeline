#!/usr/bin/env bash
# Menjalankan server SCOPELINE sementara (SQLite) lalu uji UI. Butuh: python (requirements-dev), node >= 18.
set -euo pipefail
cd "$(dirname "$0")"
PORT="${PORT:-$(python3 -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1])')}"  # port bebas, hindari tabrakan
TMP="$(mktemp -d)"
cleanup() {
  local pid; pid="$(cat "$TMP/pid" 2>/dev/null || true)"
  if [ -n "$pid" ]; then kill "$pid" 2>/dev/null || true; while kill -0 "$pid" 2>/dev/null; do sleep 0.1; done; fi
  rm -rf "$TMP"
}
trap cleanup EXIT
[ -d node_modules ] || npm install --silent --no-audit --no-fund
python3 make_sample_docx.py "$TMP/sample.docx"
(cd ../backend && DATA_DIR="$TMP/data" DATABASE_URL="sqlite:///$TMP/e2e.db" SECRET_KEY="e2e-secret-key-e2e-secret-key-e2e-1234" \
  ADMIN_PASSWORD="Admin-Password-123" LOGIN_RATE_PER_MIN=100000 \
  python3 -m uvicorn app.main:app --port "$PORT" >"$TMP/server.log" 2>&1 & echo $! >"$TMP/pid")
for _ in $(seq 1 60); do curl -sf "http://127.0.0.1:$PORT/api/health" >/dev/null && break; sleep 0.5; done
BASE_URL="http://127.0.0.1:$PORT" SAMPLE_DOCX="$TMP/sample.docx" node ui.test.js || { echo "--- server.log"; tail -30 "$TMP/server.log"; exit 1; }
