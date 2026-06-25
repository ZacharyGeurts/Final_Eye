#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export ZOCR_VISION_SESSION="$ROOT/data/vision-session.jsonl"
python3 zocr_security.py seal >/dev/null
export PYTHONPATH="$ROOT:$ROOT/GrokMediaFormat:${PYTHONPATH:-}"
[[ -d "$ROOT/../GrokMediaFormat" ]] && export PYTHONPATH="$ROOT/../GrokMediaFormat:$PYTHONPATH"
python3 tests/test_robotics_smoke.py
python3 tests/test_field_compiler_c.py
python3 tests/test_release_1_0.py