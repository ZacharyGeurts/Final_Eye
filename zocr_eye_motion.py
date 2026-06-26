"""Eye time + movement tracking — sealed UTC, frame kinematics, stoard witness."""
from __future__ import annotations

import hashlib
import json
import math
import os
import struct
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from zocr_session import log_event

_ROOT = Path(__file__).resolve().parent
DOCTRINE_PATH = _ROOT / "data" / "eye-motion-doctrine.json"
STATE_PATH = _ROOT / "data" / "eye-motion-state.json"
LEDGER_PATH = _ROOT / "data" / "eye-motion.jsonl"

_lock = threading.Lock()
_runtime: dict[str, Any] = {
    "running": False,
    "interval_sec": 2.0,
    "started_utc": None,
    "thread": None,
    "stop_event": None,
}


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def load_doctrine() -> dict[str, Any]:
    doc = _read_json(DOCTRINE_PATH, {})
    if doc.get("schema"):
        return doc
    return {
        "schema": "zocr-eye-motion/v1",
        "policy": {"default_interval_sec": 2.0, "motion_score_alert": 0.12},
    }


def motion_doctrine() -> dict[str, Any]:
    return {"ok": True, **load_doctrine()}


def _sovereign_pulse() -> dict[str, Any]:
    """Optional link to NEXUS sovereign time — disk-only if unavailable."""
    state_dir = os.environ.get("NEXUS_STATE_DIR", "").strip()
    if not state_dir:
        return {"linked": False}
    anchor = Path(state_dir) / "sovereign-time-anchor.json"
    doc = _read_json(anchor, {})
    if not doc:
        return {"linked": False}
    return {
        "linked": True,
        "pulse": doc.get("pulse"),
        "sealed": doc.get("sealed"),
        "cycle": doc.get("cycle"),
    }


def _frame_fingerprint(path: Path) -> dict[str, Any]:
    """Cheap perceptual hash + centroid drift proxy — no heavy CV deps required."""
    try:
        data = path.read_bytes()
    except OSError as exc:
        return {"ok": False, "error": str(exc)}
    if len(data) < 64:
        return {"ok": False, "error": "frame_too_small"}

    sha = hashlib.sha256(data).hexdigest()
    try:
        from PIL import Image

        with Image.open(path) as img:
            gray = img.convert("L").resize((32, 32))
            pixels = list(gray.getdata())
            avg = sum(pixels) / len(pixels)
            bits = "".join("1" if p >= avg else "0" for p in pixels)
            ahash = int(bits, 2)
            w, h = gray.size
            total = sum(pixels) or 1
            cx = sum(x * pixels[y * w + x] for y in range(h) for x in range(w)) / total
            cy = sum(y * pixels[y * w + x] for y in range(h) for x in range(w)) / total
            return {
                "ok": True,
                "sha256": sha,
                "ahash": ahash,
                "centroid": {"x": round(cx, 3), "y": round(cy, 3)},
                "size": [w, h],
                "bytes": len(data),
            }
    except Exception:
        sample = data[:: max(1, len(data) // 4096)][:4096]
        digest = hashlib.sha256(sample).hexdigest()
        return {
            "ok": True,
            "sha256": sha,
            "ahash": int(digest[:16], 16),
            "centroid": None,
            "size": None,
            "bytes": len(data),
            "fallback": True,
        }


def _hamming64(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def _load_state() -> dict[str, Any]:
    doc = _read_json(STATE_PATH, {})
    if doc.get("schema"):
        return doc
    return {
        "schema": "zocr-eye-motion-state/v1",
        "session_start": None,
        "elapsed_sec": 0.0,
        "tick_count": 0,
        "motion_score": 0.0,
        "velocity": 0.0,
        "direction_deg": None,
        "stationary": True,
        "stationary_streak": 0,
        "alerts": 0,
        "last_tick": None,
        "last_frame": None,
        "prev_fingerprint": None,
        "prev_tick_mono": None,
    }


def _save_state(st: dict[str, Any]) -> None:
    st["updated"] = _ts()
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(st, indent=2) + "\n", encoding="utf-8")


def _append_ledger(row: dict[str, Any]) -> None:
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _acquire_frame() -> dict[str, Any]:
    from zocr_preserve import acquire_preserved

    t0 = time.monotonic()
    acq = acquire_preserved(prefer="auto", allow_hold=True, profile="sentinel")
    elapsed_ms = (time.monotonic() - t0) * 1000.0
    path = acq.get("path")
    fp: dict[str, Any] = {"ok": False}
    if path and Path(path).is_file():
        fp = _frame_fingerprint(Path(path))
    return {
        "acquire": acq,
        "fingerprint": fp,
        "elapsed_ms": round(elapsed_ms, 2),
        "path": path,
    }


def _compute_kinematics(
    st: dict[str, Any],
    fp: dict[str, Any],
    *,
    now_mono: float,
) -> dict[str, Any]:
    doc = load_doctrine()
    th = doc.get("thresholds") or {}
    alert_thr = float(th.get("motion_score_alert", 0.12))
    high_thr = float(th.get("motion_score_high", 0.35))

    prev = st.get("prev_fingerprint") or {}
    prev_mono = st.get("prev_tick_mono")
    dt = (now_mono - prev_mono) if prev_mono else 0.0

    motion_score = 0.0
    direction_deg = None
    velocity = 0.0
    stationary = True
    frame_delta = 0

    if fp.get("ok") and prev.get("ok"):
        ah_prev = int(prev.get("ahash") or 0)
        ah_cur = int(fp.get("ahash") or 0)
        frame_delta = _hamming64(ah_prev, ah_cur)
        motion_score = min(1.0, frame_delta / 512.0)
        if str(fp.get("sha256")) != str(prev.get("sha256")):
            motion_score = max(motion_score, 0.08)
        c0 = prev.get("centroid") or {}
        c1 = fp.get("centroid") or {}
        if c0 and c1 and dt > 0:
            dx = float(c1.get("x", 0)) - float(c0.get("x", 0))
            dy = float(c1.get("y", 0)) - float(c0.get("y", 0))
            dist = math.hypot(dx, dy)
            velocity = dist / dt
            if dist > 0.05:
                direction_deg = round(math.degrees(math.atan2(dy, dx)), 1)
                stationary = False

    if motion_score >= alert_thr:
        stationary = False

    streak = int(st.get("stationary_streak") or 0)
    reset_n = int(th.get("stationary_streak_reset", 8))
    if stationary:
        streak += 1
    else:
        streak = 0
    if streak >= reset_n:
        motion_score = min(motion_score, alert_thr * 0.5)

    level = "calm"
    if motion_score >= high_thr:
        level = "high"
    elif motion_score >= alert_thr:
        level = "alert"

    return {
        "motion_score": round(motion_score, 4),
        "velocity": round(velocity, 3),
        "direction_deg": direction_deg,
        "stationary": stationary,
        "stationary_streak": streak,
        "frame_delta": frame_delta,
        "dt_sec": round(dt, 3) if dt else 0.0,
        "level": level,
        "alert": level in ("alert", "high"),
    }


def motion_tick(*, source: str = "api", witness: bool | None = None) -> dict[str, Any]:
    """One sealed time + movement sample."""
    doc = load_doctrine()
    policy = doc.get("policy") or {}
    now_mono = time.monotonic()
    sealed = _ts()

    with _lock:
        st = _load_state()
        if not st.get("session_start"):
            st["session_start"] = sealed
        st["tick_count"] = int(st.get("tick_count") or 0) + 1
        if st.get("prev_tick_mono"):
            st["elapsed_sec"] = round(float(st.get("elapsed_sec") or 0) + (now_mono - float(st["prev_tick_mono"])), 3)
        st["prev_tick_mono"] = now_mono

    sample = _acquire_frame()
    fp = sample.get("fingerprint") or {}
    kin = _compute_kinematics(st, fp, now_mono=now_mono)

    row = {
        "ts": sealed,
        "event": "motion_tick",
        "source": source,
        "tick": st["tick_count"],
        "elapsed_sec": st.get("elapsed_sec"),
        "sovereign": _sovereign_pulse(),
        "kinematics": kin,
        "frame": {
            "path": sample.get("path"),
            "sha256": fp.get("sha256"),
            "bytes": fp.get("bytes"),
            "fallback": fp.get("fallback"),
        },
        "acquire_ms": sample.get("elapsed_ms"),
    }

    with _lock:
        st["motion_score"] = kin["motion_score"]
        st["velocity"] = kin["velocity"]
        st["direction_deg"] = kin["direction_deg"]
        st["stationary"] = kin["stationary"]
        st["stationary_streak"] = kin["stationary_streak"]
        st["last_tick"] = row
        st["last_frame"] = fp if fp.get("ok") else st.get("last_frame")
        st["prev_fingerprint"] = fp if fp.get("ok") else st.get("prev_fingerprint")
        if kin.get("alert"):
            st["alerts"] = int(st.get("alerts") or 0) + 1
        _save_state(st)

    _append_ledger(row)
    log_event("eye_motion_tick", **kin, source=source)

    do_witness = witness if witness is not None else bool(policy.get("stoard_witness_on_alert") and kin.get("alert"))
    witness_out = None
    if do_witness:
        try:
            from zocr_eye_stoard import witness_compiler

            witness_out = witness_compiler(reason=f"motion_alert_score_{kin.get('motion_score')}")
        except Exception as exc:
            witness_out = {"ok": False, "error": str(exc)}

    return {
        "ok": True,
        "schema": "zocr-eye-motion-tick/v1",
        "sealed_ts": sealed,
        "tick": st["tick_count"],
        "elapsed_sec": st.get("elapsed_sec"),
        "kinematics": kin,
        "stationary": kin["stationary"],
        "motion_score": kin["motion_score"],
        "velocity": kin["velocity"],
        "direction_deg": kin["direction_deg"],
        "sovereign": row["sovereign"],
        "witness": witness_out,
        "frame_path": sample.get("path"),
    }


def motion_status() -> dict[str, Any]:
    st = _load_state()
    doc = load_doctrine()
    with _lock:
        running = bool(_runtime.get("running"))
        interval = float(_runtime.get("interval_sec") or doc.get("policy", {}).get("default_interval_sec", 2.0))
    return {
        "ok": True,
        "schema": "zocr-eye-motion-status/v1",
        "version": doc.get("version", "1.3.0"),
        "running": running,
        "interval_sec": interval,
        "session_start": st.get("session_start"),
        "elapsed_sec": st.get("elapsed_sec"),
        "tick_count": st.get("tick_count"),
        "motion_score": st.get("motion_score"),
        "velocity": st.get("velocity"),
        "direction_deg": st.get("direction_deg"),
        "stationary": st.get("stationary"),
        "stationary_streak": st.get("stationary_streak"),
        "alerts": st.get("alerts"),
        "last_tick": st.get("last_tick"),
        "sovereign": _sovereign_pulse(),
        "ledger": str(LEDGER_PATH),
    }


def read_motion_ledger(*, n: int = 30) -> list[dict[str, Any]]:
    if not LEDGER_PATH.is_file():
        return []
    lines = LEDGER_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
    rows: list[dict[str, Any]] = []
    for line in lines[-max(1, n) :]:
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _motion_loop(interval: float, stop: threading.Event) -> None:
    min_iv = float(load_doctrine().get("policy", {}).get("min_interval_sec", 0.5))
    interval = max(min_iv, interval)
    while not stop.is_set():
        try:
            from zocr_kill import is_tripped

            if is_tripped("vision") or is_tripped("vigilance"):
                break
        except ImportError:
            pass
        with _lock:
            if not _runtime.get("running"):
                break
        try:
            motion_tick(source="loop")
        except Exception as exc:
            _append_ledger({"ts": _ts(), "event": "motion_error", "error": str(exc)})
        if stop.wait(interval):
            break


def motion_start(*, interval_sec: float | None = None) -> dict[str, Any]:
    doc = load_doctrine()
    iv = interval_sec or float(doc.get("policy", {}).get("default_interval_sec", 2.0))
    with _lock:
        if _runtime.get("running"):
            return {"ok": True, "already_running": True, **motion_status()}
        stop = threading.Event()
        th = threading.Thread(target=_motion_loop, args=(iv, stop), daemon=True, name="eye-motion")
        _runtime.update({
            "running": True,
            "interval_sec": iv,
            "started_utc": _ts(),
            "stop_event": stop,
            "thread": th,
        })
        th.start()
    return {"ok": True, "started": True, "interval_sec": iv}


def motion_stop() -> dict[str, Any]:
    with _lock:
        if not _runtime.get("running"):
            return {"ok": True, "running": False}
        stop = _runtime.get("stop_event")
        if stop:
            stop.set()
        _runtime["running"] = False
    return {"ok": True, "stopped": True, **motion_status()}