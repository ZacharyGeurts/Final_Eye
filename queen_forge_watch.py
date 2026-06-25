#!/usr/bin/env python3
"""Queen forge watch → ZOCR live vision (thin bridge)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from zocr_vision import poll_once, forge_snapshot  # noqa: E402
from zocr_status import live_status  # noqa: E402


def watch_once(*, label: str = "queen_forge_watch") -> dict:
    return poll_once(label=label)


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "once"
    if cmd in ("once", "watch", "snapshot", "poll"):
        out = watch_once(label=sys.argv[2] if len(sys.argv) > 2 else "queen_forge_watch")
        print(json.dumps(out, indent=2))
        return 0
    if cmd == "status":
        print(json.dumps({"snapshot": forge_snapshot(), "live": live_status()}, indent=2))
        return 0
    print(json.dumps({"error": "usage: queen_forge_watch.py [once|status|poll]"}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())