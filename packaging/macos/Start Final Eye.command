#!/bin/bash
cd "$(dirname "$0")"
export FINAL_EYE_ASSIST=1
VER=$(cat "$(dirname "$0")/VERSION" 2>/dev/null | tr -d '\n')
echo "Final_Eye v${VER:-unknown} — http://127.0.0.1:9479/"
python3 gui/app.py