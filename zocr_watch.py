#!/usr/bin/env python3
"""ZOCR CLI — look on demand, status without capture."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def _prefer_arg() -> str:
    for i, a in enumerate(sys.argv):
        if a in ("--prefer", "-p") and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return os.environ.get("ZOCR_PREFER", "auto")


def _gate(operation: str) -> dict | None:
    from zocr_security import mandate_enforce
    gate = mandate_enforce(operation)
    if not gate.get("ok"):
        return {"ok": False, "error": gate.get("error"), **gate}
    return None


def cmd_look() -> dict:
    blocked = _gate("look")
    if blocked:
        return blocked
    from zocr_vision import look
    return look(
        label=os.environ.get("ZOCR_LOOK_LABEL", "cli_look"),
        prefer=_prefer_arg(),
    )


def cmd_status() -> dict:
    from zocr_status import live_status
    return live_status()


def cmd_observe() -> dict:
    blocked = _gate("observe")
    if blocked:
        return blocked
    from zocr_ai import robotics_context
    cap = cmd_look()
    return {"ok": True, "look": cap, "robotics": robotics_context(capture=cap)}


def cmd_loop() -> int:
    """Opt-in loop only — set ZOCR_POLL_LOOPS or ZOCR_POLL_INTERVAL."""
    interval = float(os.environ.get("ZOCR_POLL_INTERVAL", "5"))
    loops = int(os.environ.get("ZOCR_POLL_LOOPS", "0"))
    n = 0
    while True:
        n += 1
        try:
            out = cmd_look()
            print(json.dumps({
                "loop": n,
                "source": out.get("source"),
                "stage": out.get("forge", {}).get("stage"),
            }), flush=True)
        except Exception as exc:
            print(json.dumps({"loop": n, "error": str(exc)}), flush=True)
        if loops > 0 and n >= loops:
            return 0
        time.sleep(interval)


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd in ("look", "poll", "once", "capture"):
        print(json.dumps(cmd_look(), indent=2))
        return 0
    if cmd in ("observe", "robotics"):
        print(json.dumps(cmd_observe(), indent=2))
        return 0
    if cmd in ("status", "json", "live"):
        print(json.dumps(cmd_status(), indent=2))
        return 0
    if cmd in ("loop", "watch"):
        return cmd_loop()
    if cmd == "capabilities":
        from zocr_ai import capabilities
        print(json.dumps(capabilities(), indent=2))
        return 0
    if cmd == "stream-status":
        from zocr_stream import stream_status
        print(json.dumps(stream_status(), indent=2))
        return 0
    if cmd in ("eye", "eye-status"):
        from zocr_eye import eye_status
        print(json.dumps(eye_status(), indent=2))
        return 0
    if cmd == "eye-profiles":
        from zocr_eye import list_profiles
        print(json.dumps({"profiles": list_profiles()}, indent=2))
        return 0
    if cmd in ("rig", "rig-status"):
        from zocr_stereo import rig_status
        print(json.dumps(rig_status(), indent=2))
        return 0
    if cmd == "rig-configure":
        from zocr_stereo import configure_rig
        preset = sys.argv[2] if len(sys.argv) > 2 else "monocular"
        print(json.dumps(configure_rig(preset=preset, source="cli"), indent=2))
        return 0
    if cmd == "neural":
        from zocr_neural import neural_status
        print(json.dumps(neural_status(), indent=2))
        return 0
    if cmd == "neural-seal":
        from zocr_neural import seal_network
        print(json.dumps(seal_network(), indent=2))
        return 0
    if cmd == "eye-teach":
        from zocr_eye import teach
        prof = sys.argv[2] if len(sys.argv) > 2 else "human"
        print(json.dumps(teach(prof, source="cli"), indent=2))
        return 0
    if cmd in ("kill", "kill-status"):
        from zocr_kill import kill_status
        print(json.dumps(kill_status(), indent=2))
        return 0
    if cmd == "kill-all":
        from zocr_kill import kill_all
        print(json.dumps(kill_all(), indent=2))
        return 0
    if cmd == "kill-release":
        from zocr_kill import release
        switch = sys.argv[2] if len(sys.argv) > 2 else "all"
        print(json.dumps(release(switch), indent=2))
        return 0
    if cmd == "seal":
        from zocr_security import seal_codebase
        print(json.dumps(seal_codebase(), indent=2))
        return 0
    if cmd == "security":
        from zocr_security import security_status
        print(json.dumps(security_status(), indent=2))
        return 0
    if cmd == "additives":
        from zocr_additives import additives_status
        print(json.dumps(additives_status(), indent=2))
        return 0
    if cmd in ("vigilance", "vigilance-status"):
        from zocr_vigilance import vigilance_status
        print(json.dumps(vigilance_status(), indent=2))
        return 0
    if cmd == "vigilance-start":
        blocked = _gate("vigilance_start")
        if blocked:
            print(json.dumps(blocked, indent=2))
            return 1
        from zocr_vigilance import vigilance_start
        prof = sys.argv[2] if len(sys.argv) > 2 else "sentinel"
        print(json.dumps(vigilance_start(profile=prof, prefer=_prefer_arg()), indent=2))
        return 0
    if cmd == "vigilance-stop":
        from zocr_vigilance import vigilance_stop
        print(json.dumps(vigilance_stop(), indent=2))
        return 0
    if cmd == "stream-start":
        blocked = _gate("stream_start")
        if blocked:
            print(json.dumps(blocked, indent=2))
            return 1
        from zocr_stream import stream_start
        prof = sys.argv[2] if len(sys.argv) > 2 else "watch"
        print(json.dumps(stream_start(profile=prof, prefer=_prefer_arg()), indent=2))
        return 0
    if cmd == "stream-stop":
        from zocr_stream import stream_stop
        print(json.dumps(stream_stop(), indent=2))
        return 0
    if cmd == "verify":
        blocked = _gate("verify")
        if blocked:
            print(json.dumps(blocked, indent=2))
            return 1
        from zocr_field import verify_chain
        print(json.dumps(verify_chain(), indent=2))
        return 0
    if cmd in ("preserve", "preserve-status"):
        from zocr_preserve import preserve_status
        print(json.dumps(preserve_status(), indent=2))
        return 0
    if cmd in ("trust", "irtn"):
        from zocr_trust import trust_network_status
        print(json.dumps(trust_network_status(), indent=2))
        return 0
    if cmd == "trust-verify":
        from zocr_trust import verify_trust_mesh
        print(json.dumps(verify_trust_mesh(), indent=2))
        return 0
    if cmd in ("offense", "offense-status"):
        from zocr_offense import offense_status
        print(json.dumps(offense_status(), indent=2))
        return 0
    if cmd in ("final", "final-eyeball"):
        from zocr_eye import final_eyeball_status
        print(json.dumps(final_eyeball_status(), indent=2))
        return 0
    if cmd == "final-mode" and len(sys.argv) > 2:
        from zocr_eye import set_final_mode
        voice = sys.argv[3] if len(sys.argv) > 3 else None
        print(json.dumps(set_final_mode(sys.argv[2], voice=voice, source="cli"), indent=2))
        return 0
    if cmd in ("pattern", "pattern-status"):
        from zocr_pattern import pattern_status
        print(json.dumps(pattern_status(), indent=2))
        return 0
    if cmd == "pattern-scan" and len(sys.argv) > 2:
        from zocr_pattern import scan_frame
        print(json.dumps(scan_frame(Path(sys.argv[2])), indent=2))
        return 0
    print(json.dumps({
        "error": "usage: zocr_watch.py [look|observe|status|seal|security|pattern|pattern-scan PATH|additives|vigilance-start|vigilance-stop|stream-start PROFILE|stream-stop|verify|capabilities]",
    }, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())