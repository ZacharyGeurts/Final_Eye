"""ZOCR vision offense — defense of vision requires offense."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from zocr_session import log_event

_ROOT = Path(__file__).resolve().parent
SPEC_PATH = _ROOT / "data" / "vision-offense.json"
STATE_PATH = _ROOT / "data" / "offense-state.json"
LEDGER_PATH = _ROOT / "data" / "offense-ledger.jsonl"

OFFENSE_RULE = "Defense of vision requires offense."


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_spec() -> dict[str, Any]:
    try:
        return json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"rule": OFFENSE_RULE, "countermeasures": {}, "preempt": {}}


def _load_state() -> dict[str, Any]:
    if STATE_PATH.is_file():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "schema": "zocr-offense-state/v1",
        "strikes_total": 0,
        "threat_streak": 0,
        "preempt_armed": False,
        "last_strike": None,
    }


def _save_state(st: dict[str, Any]) -> None:
    st["updated"] = _ts()
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(st, indent=2) + "\n", encoding="utf-8")


def _ledger(row: dict[str, Any]) -> None:
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def countermeasure_for(threat: str) -> dict[str, Any]:
    spec = load_spec()
    cm = spec.get("countermeasures", {}).get(threat, {})
    return {
        "threat": threat,
        "strike": cm.get("strike", "reject_and_failover"),
        "offense": cm.get("offense", "seal_threat"),
        "severity": cm.get("severity", "medium"),
    }


def _execute_offense(offense: str, *, threat: str, **ctx: Any) -> dict[str, Any]:
    acted: list[str] = []
    if offense in ("trip_capture", "kill_strike") and threat in ("whiteout", "provenance_mismatch"):
        from zocr_kill import trip
        trip("capture", reason=f"offense:{threat}")
        acted.append("trip_capture")
    if offense == "trip_vision" or (offense == "kill_strike" and threat == "provenance_mismatch"):
        from zocr_kill import trip
        trip("vision", reason=f"offense:{threat}")
        acted.append("trip_vision")
    if offense == "preempt_rtx":
        st = _load_state()
        st["preempt_armed"] = True
        _save_state(st)
        acted.append("preempt_rtx")
    if offense == "pattern_strike":
        acted.append("pattern_strike")
    if offense in ("seal_threat", "pattern_strike", "reject_and_failover"):
        acted.append("seal_threat")
    return {"offense": offense, "acted": acted or ["logged"]}


def offense_strike(threat: str, **ctx: Any) -> dict[str, Any]:
    """Active countermeasure — defense through offense."""
    cm = countermeasure_for(threat)
    result = _execute_offense(cm["offense"], threat=threat, **ctx)

    st = _load_state()
    st["strikes_total"] = int(st.get("strikes_total", 0)) + 1
    st["threat_streak"] = int(st.get("threat_streak", 0)) + 1
    if st["threat_streak"] >= int(load_spec().get("preempt", {}).get("threat_streak_threshold", 2)):
        st["preempt_armed"] = True

    row = {
        "schema": "zocr-offense-strike/v1",
        "ts": _ts(),
        "threat": threat,
        "strike": cm["strike"],
        "offense": cm["offense"],
        "severity": cm["severity"],
        "acted": result.get("acted"),
        **{k: v for k, v in ctx.items() if k in ("source", "profile", "path")},
    }
    st["last_strike"] = row
    _save_state(st)
    _ledger(row)
    log_event("offense_strike", ok=True, threat=threat, offense=cm["offense"], **ctx)
    return {"ok": True, "rule": OFFENSE_RULE, **row}


def offense_clear_streak(*, reason: str = "clean_acquire") -> None:
    st = _load_state()
    if st.get("threat_streak", 0) > 0:
        st["threat_streak"] = 0
        st["preempt_armed"] = False
        _save_state(st)
        log_event("offense_clear", ok=True, reason=reason)


def offense_cascade_bias(prefer: str) -> tuple[str, list[str] | None]:
    """Preemptive offense — front-load RTX when threat streak is hot."""
    st = _load_state()
    spec = load_spec().get("preempt", {})
    if not st.get("preempt_armed") and st.get("threat_streak", 0) < int(spec.get("threat_streak_threshold", 2)):
        return prefer, None
    bias = str(spec.get("bias_prefer", "rtx"))
    front = spec.get("cascade_front")
    return bias, front if isinstance(front, list) else None


def offense_doctrine() -> dict[str, Any]:
    spec = load_spec()
    return {
        "schema": "zocr-offense-doctrine/v1",
        "title": spec.get("title", "Vision Offense"),
        "rule": spec.get("rule", OFFENSE_RULE),
        "paired_with": spec.get("paired_with"),
        "doctrine": spec.get("doctrine", []),
        "countermeasures": list(spec.get("countermeasures", {}).keys()),
        "preempt": spec.get("preempt", {}),
    }


def offense_status() -> dict[str, Any]:
    spec = load_spec()
    st = _load_state()
    recent: list[dict[str, Any]] = []
    if LEDGER_PATH.is_file():
        try:
            for line in LEDGER_PATH.read_text(encoding="utf-8").splitlines()[-6:]:
                if line.strip():
                    recent.append(json.loads(line))
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "schema": "zocr-offense-status/v1",
        "ts": _ts(),
        "rule": spec.get("rule", OFFENSE_RULE),
        "paired_with": spec.get("paired_with"),
        "strikes_total": int(st.get("strikes_total", 0)),
        "threat_streak": int(st.get("threat_streak", 0)),
        "preempt_armed": bool(st.get("preempt_armed", False)),
        "last_strike": st.get("last_strike"),
        "recent": recent,
        "spec": str(SPEC_PATH),
    }


def main() -> int:
    import sys

    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        print(json.dumps(offense_status(), indent=2))
        return 0
    if cmd == "doctrine":
        print(json.dumps(offense_doctrine(), indent=2))
        return 0
    if cmd == "strike" and len(sys.argv) > 2:
        print(json.dumps(offense_strike(sys.argv[2], source="cli"), indent=2))
        return 0
    print(json.dumps({"error": "usage: zocr_offense.py [status|doctrine|strike THREAT]"}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())