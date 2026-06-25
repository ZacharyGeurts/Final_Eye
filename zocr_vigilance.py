"""ZOCR vigilance — continuous display watch with modular additive orchestration."""
from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from zocr_additives import additives_status, cascade_for_prefer, list_additives
from zocr_session import log_event

_ROOT = Path(__file__).resolve().parent
VIGILANCE_PATH = _ROOT / "data" / "vigilance-state.json"
VIGILANCE_LOG = _ROOT / "data" / "vigilance-log.jsonl"

_lock = threading.Lock()
_state: dict[str, Any] = {
    "running": False,
    "profile": "sentinel",
    "prefer": "auto",
    "interval_sec": 4.0,
    "started": None,
    "checks": 0,
    "alerts": 0,
    "last_check": None,
    "thread": None,
    "stop_event": None,
}


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _persist() -> None:
    VIGILANCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        doc = {k: v for k, v in _state.items() if k not in ("thread", "stop_event")}
    VIGILANCE_PATH.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def _log_vigilance(event: str, **fields: Any) -> None:
    row = {"ts": _ts(), "event": event, **fields}
    VIGILANCE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with VIGILANCE_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _vigilance_check(prefer: str, profile: str) -> dict[str, Any]:
    from zocr_preserve import acquire_preserved, classify_threat

    t0 = time.monotonic()
    acq = acquire_preserved(prefer=prefer, allow_hold=True, profile=profile)
    elapsed_ms = (time.monotonic() - t0) * 1000.0
    path = acq.get("path")
    threats: list[str] = []
    if path and Path(path).is_file():
        threats = classify_threat(Path(path), source=acq.get("source", "none"), elapsed_ms=elapsed_ms)
    alert = bool(threats) or acq.get("preserved", False)
    return {
        "ok": acq.get("ok", False),
        "source": acq.get("source"),
        "preserved": acq.get("preserved", False),
        "threats": threats or acq.get("threats", []),
        "tried": acq.get("tried", []),
        "alert": alert,
        "elapsed_ms": round(elapsed_ms, 2),
    }


def _vigilance_loop(prefer: str, profile: str, interval: float, stop: threading.Event) -> None:
    while not stop.is_set():
        from zocr_kill import is_tripped
        if is_tripped("vigilance") or is_tripped("vision"):
            break
        with _lock:
            if not _state.get("running"):
                break
        try:
            result = _vigilance_check(prefer, profile)
            with _lock:
                _state["checks"] = int(_state.get("checks", 0)) + 1
                _state["last_check"] = {"ts": _ts(), **result}
                if result.get("alert"):
                    _state["alerts"] = int(_state.get("alerts", 0)) + 1
            _log_vigilance("check", profile=profile, prefer=prefer, **result)
            log_event("vigilance_check", ok=result.get("ok", False), **result)
        except Exception as exc:
            _log_vigilance("error", error=str(exc))
        if stop.wait(interval):
            break
    _persist()


def vigilance_start(
    *,
    profile: str = "sentinel",
    prefer: str = "auto",
    interval_sec: float | None = None,
) -> dict[str, Any]:
    from zocr_security import mandate_enforce

    gate = mandate_enforce("vigilance_start")
    if not gate.get("ok"):
        return {"ok": False, "error": gate.get("error"), **gate}

    interval = interval_sec or float(os.environ.get("ZOCR_VIGILANCE_INTERVAL", "4"))
    with _lock:
        if _state.get("running"):
            vigilance_stop()
        stop = threading.Event()
        _state.update({
            "running": True,
            "profile": profile,
            "prefer": prefer,
            "interval_sec": interval,
            "started": _ts(),
            "checks": 0,
            "alerts": 0,
            "stop_event": stop,
        })
        th = threading.Thread(
            target=_vigilance_loop,
            args=(prefer, profile, interval, stop),
            name="zocr-vigilance",
            daemon=True,
        )
        _state["thread"] = th
        th.start()
    _persist()
    log_event("vigilance_start", ok=True, profile=profile, prefer=prefer, interval_sec=interval)
    st = vigilance_status()
    st["ok"] = True
    st["gate"] = gate
    return st


def vigilance_stop() -> dict[str, Any]:
    with _lock:
        stop = _state.get("stop_event")
        if stop:
            stop.set()
        _state["running"] = False
        th = _state.get("thread")
    if th and th.is_alive():
        th.join(timeout=3.0)
    with _lock:
        _state["thread"] = None
        _state["stop_event"] = None
    _persist()
    log_event("vigilance_stop", ok=True)
    st = vigilance_status()
    st["ok"] = True
    return st


def vigilance_status() -> dict[str, Any]:
    with _lock:
        st = dict(_state)
    st.pop("thread", None)
    st.pop("stop_event", None)
    recent: list[dict] = []
    if VIGILANCE_LOG.is_file():
        try:
            for line in VIGILANCE_LOG.read_text(encoding="utf-8").splitlines()[-6:]:
                if line.strip():
                    recent.append(json.loads(line))
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "schema": "zocr-vigilance-status/v1",
        "ts": _ts(),
        "running": st.get("running", False),
        "profile": st.get("profile", "sentinel"),
        "prefer": st.get("prefer", "auto"),
        "interval_sec": st.get("interval_sec", 4.0),
        "checks": st.get("checks", 0),
        "alerts": st.get("alerts", 0),
        "started": st.get("started"),
        "last_check": st.get("last_check"),
        "cascade": cascade_for_prefer(st.get("prefer", "auto")),
        "additives": list_additives(available_only=True),
        "recent": recent,
        "accessibility": {
            "modular_additives": True,
            "display_never_blank": True,
            "api": {
                "status": "GET /api/vigilance/status",
                "start": "POST /api/vigilance/start",
                "stop": "POST /api/vigilance/stop",
                "additives": "GET /api/vigilance/additives",
            },
        },
        "additives_detail": additives_status(),
    }