#!/usr/bin/env bash
# Final_Eye Linux install — v1.0
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "Final_Eye v1.0 — installing Python dependencies…"
python3 -m pip install --user -r requirements.txt

echo "Sealing codebase…"
python3 zocr_security.py seal >/dev/null
python3 zocr_neural.py seal >/dev/null 2>&1 || true

mkdir -p data out addons
chmod +x start.sh install.sh 2>/dev/null || true

echo ""
echo "Installed. Start with:"
echo "  ./start.sh --no-open     # http://127.0.0.1:9479"
echo "  ./start.sh               # opens browser"
echo "  ./tests/run_tests.sh     # verify (FINAL_EYE_LOW_END=1)"