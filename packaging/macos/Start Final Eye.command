#!/bin/bash
cd "$(dirname "$0")"
export FINAL_EYE_ASSIST=1
echo "Final_Eye v1.0 — http://127.0.0.1:9479/"
python3 gui/app.py