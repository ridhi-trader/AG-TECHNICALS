#!/bin/bash
set -e

# ── Start nginx in background ────────────────────────────────────────────────
nginx -g "daemon off;" &
NGINX_PID=$!

# ── Auto-restart loop for uvicorn ────────────────────────────────────────────
# If uvicorn crashes, restart it automatically — max 10 times then give up
RESTARTS=0
MAX_RESTARTS=10

while [ $RESTARTS -lt $MAX_RESTARTS ]; do
    echo "[AG] Starting uvicorn (attempt $((RESTARTS+1)))"
    uvicorn chat_backend:app --host 127.0.0.1 --port 8000 \
        --workers 1 \
        --timeout-keep-alive 75 \
        --log-level info || true

    RESTARTS=$((RESTARTS+1))
    echo "[AG] Uvicorn crashed — restarting in 3s (attempt $RESTARTS/$MAX_RESTARTS)"
    sleep 3
done

echo "[AG] Max restarts reached — killing nginx to trigger Railway redeploy"
kill $NGINX_PID
exit 1
