"""ZOCR kill switches — one whole authority. Strength in vision, protect your eyes."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent
KILL_PATH = _ROOT / "data" / "kill-state.json"

# Tripped = subsystem killed. Default all armed (not tripped).
_SWITCHES = ("vision", "capture", "stream", "vigilance", "mjpeg", "egress")

_EYES_PROTECT = True


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> dict[str, Any]:
    if KILL_PATH.is_file():
        try:
            return json.loads(KILL_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "schema": "zocr-kill-state/v1",
        "tripped": {s: False for s in _SWITCHES},
        "eyes_protect": True,
        "last_trip": None,
        "history": [],
    }


def _save(st: dict[str, Any]) -> None:
    KILL_PATH.parent.mkdir(parents=True, exist_ok=True)
    st["updated"] = _ts()
    KILL_PATH.write_text(json.dumps(st, indent=2) + "\n", encoding="utf-8")


def _apply_env(st: dict[str, Any]) -> dict[str, Any]:
    """Environment may trip switches at boot — no redundant runtime checks elsewhere."""
    env_map = {
        "ZOCR_KILL_VISION": "vision",
        "ZOCR_KILL_CAPTURE": "capture",
        "ZOCR_KILL_STREAM": "stream",
        "ZOCR_KILL_VIGILANCE": "vigilance",
        "ZOCR_KILL_MJPEG": "mjpeg",
        "ZOCR_KILL_EGRESS": "egress",
        "ZOCR_KILL_ALL": None,
    }
    for env, switch in env_map.items():
        if os.environ.get(env, "").strip().lower() in ("1", "true", "yes"):
            if switch is None:
                for s in _SWITCHES:
                    st["tripped"][s] = True
            else:
                st["tripped"][switch] = True
    if os.environ.get("ZOCR_EYES_OFF", "").strip().lower() in ("1", "true", "yes"):
        st["eyes_protect"] = False
    return st


def is_tripped(switch: str) -> bool:
    st = _apply_env(_load())
    return bool(st.get("tripped", {}).get(switch, False))


def eyes_protect() -> bool:
    st = _apply_env(_load())
    return bool(st.get("eyes_protect", True))


def trip(switch: str, *, reason: str = "operator", source: str = "api") -> dict[str, Any]:
    st = _load()
    if switch == "all":
        for s in _SWITCHES:
            st["tripped"][s] = True
        switch = "all"
    elif switch in _SWITCHES:
        st["tripped"][switch] = True
    else:
        return {"ok": False, "error": "unknown_switch", "switch": switch}
    row = {"ts": _ts(), "switch": switch, "reason": reason, "source": source}
    st["last_trip"] = row
    hist = st.get("history", [])
    hist.append(row)
    st["history"] = hist[-24:]
    _save(st)
    _stop_running(switch)
    return {"ok": True, "tripped": switch, **row}


def release(switch: str) -> dict[str, Any]:
    st = _load()
    if switch == "all":
        st["tripped"] = {s: False for s in _SWITCHES}
    elif switch in _SWITCHES:
        st["tripped"][switch] = False
    else:
        return {"ok": False, "error": "unknown_switch", "switch": switch}
    _save(st)
    return {"ok": True, "released": switch, "ts": _ts()}


def _stop_running(switch: str) -> None:
    if switch in ("all", "stream", "vision", "capture"):
        try:
            from zocr_stream import stream_stop
            stream_stop()
        except Exception:
            pass
    if switch in ("all", "vigilance", "vision"):
        try:
            from zocr_vigilance import vigilance_stop
            vigilance_stop()
        except Exception:
            pass


def kill_all(*, reason: str = "operator", source: str = "kill_all") -> dict[str, Any]:
    """Whole-system kill — one switch, stops all vision activity."""
    return trip("all", reason=reason, source=source)


_ALWAYS_OK = frozenset({
    "stream_stop", "vigilance_stop", "kill_status", "kill_release", "kill_trip",
})


def check(operation: str) -> dict[str, Any]:
    """
    Single choke-point check. Returns ok=True or blocked with kill switch id.
    Stop/release ops always pass — you can always disengage.
    """
    if operation in _ALWAYS_OK:
        return {"ok": True, "operation": operation, "eyes_protect": eyes_protect()}

    op_map = {
        "look": "capture",
        "observe": "capture",
        "capture": "capture",
        "preserve": "vision",
        "stream_start": "stream",
        "mjpeg": "mjpeg",
        "vigilance_start": "vigilance",
        "verify": "vision",
        "additive_capture": "capture",
        "nn_analyze": "capture",
    }
    switch = op_map.get(operation, "vision")
    if is_tripped("vision"):
        return {"ok": False, "error": "kill_switch", "switch": "vision", "operation": operation}
    if is_tripped(switch):
        return {"ok": False, "error": "kill_switch", "switch": switch, "operation": operation}
    if operation in ("look", "observe", "capture", "additive_capture", "mjpeg") and is_tripped("capture"):
        return {"ok": False, "error": "kill_switch", "switch": "capture", "operation": operation}
    return {"ok": True, "operation": operation, "eyes_protect": eyes_protect()}


def kill_status() -> dict[str, Any]:
    st = _apply_env(_load())
    armed = {s: not st.get("tripped", {}).get(s, False) for s in _SWITCHES}
    return {
        "schema": "zocr-kill-status/v1",
        "ts": _ts(),
        "doctrine": "Confidence always in Vision. Defense requires offense. Kill switches at choke points only.",
        "eyes_protect": st.get("eyes_protect", True),
        "eyes_rule": "Silent capture only — flash forbidden, whiteout rejected, never harm the display path",
        "switches": {s: {"tripped": st.get("tripped", {}).get(s, False), "armed": armed[s]} for s in _SWITCHES},
        "last_trip": st.get("last_trip"),
        "whole": not any(st.get("tripped", {}).get(s, False) for s in _SWITCHES),
        "state_path": str(KILL_PATH),
    }


def main() -> int:
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        print(json.dumps(kill_status(), indent=2))
        return 0
    if cmd == "all":
        print(json.dumps(kill_all(), indent=2))
        return 0
    if cmd == "trip" and len(sys.argv) > 2:
        print(json.dumps(trip(sys.argv[2]), indent=2))
        return 0
    if cmd == "release" and len(sys.argv) > 2:
        print(json.dumps(release(sys.argv[2]), indent=2))
        return 0
    print(json.dumps({"error": "usage: zocr_kill.py [status|all|trip SWITCH|release SWITCH]"}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())