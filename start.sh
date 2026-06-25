#!/usr/bin/env bash
# ZOCR — on-demand vision server (no auto frame loop by default)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
HOST="${ZOCR_HOST:-127.0.0.1}"
PORT="${ZOCR_PORT:-9479}"
URL="http://${HOST}:${PORT}/"
LIVE="${URL}#live"
PIDFILE="$ROOT/data/zocr-server.pid"
LOGFILE="$ROOT/data/server.log"
POLL_PIDFILE="$ROOT/data/zocr-poll.pid"

stop_server() {
  cd "$ROOT"
  python3 zocr_watch.py stream-stop >/dev/null 2>&1 || true
  python3 zocr_watch.py vigilance-stop >/dev/null 2>&1 || true
  if [[ -f "$POLL_PIDFILE" ]]; then
    local ppid
    ppid="$(cat "$POLL_PIDFILE" 2>/dev/null || true)"
    [[ -n "${ppid:-}" ]] && kill -0 "$ppid" 2>/dev/null && kill -TERM "$ppid" 2>/dev/null || true
    rm -f "$POLL_PIDFILE"
  fi
  if [[ -f "$PIDFILE" ]]; then
    local pid
    pid="$(cat "$PIDFILE" 2>/dev/null || true)"
    if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
      kill -TERM "$pid" 2>/dev/null || true
      sleep 0.3
      kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$PIDFILE"
  fi
  command -v fuser >/dev/null 2>&1 && fuser -k "${PORT}/tcp" 2>/dev/null || true
}

start_server() {
  mkdir -p "$ROOT/data" "$ROOT/out" "$ROOT/addons"
  export ZOCR_VISION_SESSION="$ROOT/data/vision-session.jsonl"
  if [[ ! -f "$ROOT/data/code-seal.json" ]]; then
    python3 "$ROOT/zocr_security.py" seal >/dev/null 2>&1 || true
  fi
  if [[ ! -f "$ROOT/data/neural-seal.json" ]]; then
    python3 "$ROOT/zocr_neural.py" seal >/dev/null 2>&1 || true
  fi
  stop_server
  sleep 0.15
  cd "$ROOT"
  if command -v setsid >/dev/null 2>&1; then
    setsid nohup python3 gui/app.py >>"$LOGFILE" 2>&1 </dev/null &
  else
    nohup python3 gui/app.py >>"$LOGFILE" 2>&1 </dev/null &
  fi
  echo $! >"$PIDFILE"
  sleep 0.35
  curl -sf --connect-timeout 2 --max-time 4 "http://${HOST}:${PORT}/api/health" >/dev/null \
    || { echo "ZOCR failed — see $LOGFILE" >&2; stop_server; exit 1; }
}

start_poll_loop() {
  export ZOCR_VISION_SESSION="$ROOT/data/vision-session.jsonl"
  export ZOCR_POLL_INTERVAL="${ZOCR_POLL_INTERVAL:-5}"
  cd "$ROOT"
  nohup python3 zocr_watch.py loop >>"$ROOT/data/poll.log" 2>&1 </dev/null &
  echo $! >"$POLL_PIDFILE"
}

open_browser() {
  command -v xdg-open >/dev/null 2>&1 && xdg-open "${1:-$URL}" >/dev/null 2>&1 &
}

case "${1:-}" in
  --stop) stop_server; echo "ZOCR stopped."; exit 0 ;;
  --look)
    export ZOCR_VISION_SESSION="$ROOT/data/vision-session.jsonl"
    cd "$ROOT" && python3 zocr_watch.py look "${@:2}"
    exit 0
    ;;
  --observe)
    export ZOCR_VISION_SESSION="$ROOT/data/vision-session.jsonl"
    cd "$ROOT" && python3 zocr_watch.py observe "${@:2}"
    exit 0
    ;;
  --stream)
    export ZOCR_VISION_SESSION="$ROOT/data/vision-session.jsonl"
    cd "$ROOT" && python3 zocr_watch.py stream-start "${2:-watch}"
    exit 0
    ;;
  --stream-stop)
    export ZOCR_VISION_SESSION="$ROOT/data/vision-session.jsonl"
    cd "$ROOT" && python3 zocr_watch.py stream-stop
    exit 0
    ;;
  --verify)
    cd "$ROOT" && python3 zocr_watch.py verify
    exit 0
    ;;
  --seal)
    cd "$ROOT" && python3 zocr_security.py seal
    exit 0
    ;;
  --security)
    cd "$ROOT" && python3 zocr_watch.py security
    exit 0
    ;;
  --additives)
    cd "$ROOT" && python3 zocr_watch.py additives
    exit 0
    ;;
  --vigilance)
    export ZOCR_VISION_SESSION="$ROOT/data/vision-session.jsonl"
    cd "$ROOT" && python3 zocr_watch.py vigilance-start "${2:-sentinel}"
    exit 0
    ;;
  --eye)
    cd "$ROOT" && python3 zocr_watch.py eye-status
    exit 0
    ;;
  --rig)
    cd "$ROOT" && python3 zocr_watch.py rig-status
    exit 0
    ;;
  --rig-configure)
    cd "$ROOT" && python3 zocr_watch.py rig-configure "${2:-stereo_human}"
    exit 0
    ;;
  --neural-seal)
    cd "$ROOT" && python3 zocr_neural.py seal
    exit 0
    ;;
  --eye-teach)
    cd "$ROOT" && python3 zocr_watch.py eye-teach "${2:-bird}"
    exit 0
    ;;
  --kill)
    export ZOCR_VISION_SESSION="$ROOT/data/vision-session.jsonl"
    cd "$ROOT" && python3 zocr_kill.py all
    exit 0
    ;;
  --kill-release)
    cd "$ROOT" && python3 zocr_kill.py release "${2:-all}"
    exit 0
    ;;
  --vigilance-stop)
    export ZOCR_VISION_SESSION="$ROOT/data/vision-session.jsonl"
    cd "$ROOT" && python3 zocr_watch.py vigilance-stop
    exit 0
    ;;
  --status)
    if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null \
        && curl -sf "http://${HOST}:${PORT}/api/health" >/dev/null; then
      echo "running pid=$(cat "$PIDFILE") url=$URL"
      curl -sf "http://${HOST}:${PORT}/api/status" \
        | python3 -c "import sys,json; d=json.load(sys.stdin); print('doctrine:', d.get('doctrine','')); print('captures:', d.get('session',{}).get('captures'))" 2>/dev/null || true
      exit 0
    fi
    echo "stopped"; exit 1
    ;;
  --poll|--loop)
    start_server
    start_poll_loop
    echo "ZOCR $URL — opt-in poll loop (interval ${ZOCR_POLL_INTERVAL:-5}s)"
    ;;
  --no-open|--headless)
    start_server
    echo "ZOCR on-demand vision $URL — look: ./start.sh --look"
    ;;
  --live)
    start_server
    echo "ZOCR $LIVE — click Look to capture (no auto frames)"
    open_browser "$LIVE"
    ;;
  *)
    start_server
    echo "ZOCR on-demand vision $URL"
    open_browser "$URL"
    ;;
esac