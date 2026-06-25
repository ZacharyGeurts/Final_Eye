"""Assistive usage contract — Final_Eye is one tenant; never overflow or overdraw."""
from __future__ import annotations

import os
import threading
import time
from typing import Any

_lock = threading.RLock()
_frame_n = 0
_workers: dict[str, float] = {}
_counters: dict[str, list[float]] = {}
_slots: dict[str, int] = {}

POSTURE = "assistive"

# Shared-system rails — assist when asked; defer before flooding the host
_CONTRACT = {
    "posture": POSTURE,
    "rule": "Assistive tenant — on-demand first, bounded windows, no overflow",
    "window_sec": 60.0,
    "defer_ms": 300,
    "budgets": {
        "look": {"per_window": 12, "burst": 4},
        "capture": {"per_window": 24},
        "stream": {"concurrent_max": 1},
        "mjpeg": {"concurrent_max": 2},
        "vigilance": {"concurrent_max": 1},
        "neural": {"per_window": 8},
        "eye": {"per_window": 16},
        "bench": {"concurrent_max": 1},
    },
    "eye_rails": {
        "max_width_idle": 960,
        "max_width_share": 640,
        "max_width_on_demand": 1280,
        "share_every_n": 2,
        "worker_ttl_sec": 2.5,
        "yield_ms_idle": 1.0,
        "yield_ms_share": 4.0,
        "load_soft": 1.5,
        "load_hard": 2.5,
    },
}


def contract_enabled() -> bool:
    return os.environ.get("FINAL_EYE_ASSIST", "1").strip().lower() not in ("0", "false", "no")


def cool_enabled() -> bool:
    """Alias — assist contract includes cool-share behavior."""
    return contract_enabled()


def _load_avg() -> float:
    try:
        one, _five, _fifteen = os.getloadavg()
        return float(one)
    except (AttributeError, OSError):
        return 0.0


def _prune(op: str, *, window: float) -> list[float]:
    now = time.monotonic()
    with _lock:
        hits = [t for t in _counters.get(op, []) if now - t <= window]
        _counters[op] = hits
        return hits


def register_worker(name: str) -> None:
    """Mark hotter paths active — eye yields before overdrawing shared CPU."""
    with _lock:
        _workers[str(name)] = time.monotonic()


def _active_workers() -> list[str]:
    now = time.monotonic()
    ttl = _CONTRACT["eye_rails"]["worker_ttl_sec"]
    with _lock:
        stale = [k for k, t in _workers.items() if now - t > ttl]
        for k in stale:
            _workers.pop(k, None)
        return list(_workers.keys())


def acquire(
    operation: str,
    *,
    cost: int = 1,
    slot: bool = False,
    on_demand: bool = False,
) -> dict[str, Any]:
    """
    Draw from assist budget. Returns ok=False when contract would overflow/overdraw.
    On-demand look/eye may use burst headroom; background paths defer first.
    """
    op = str(operation)
    if not contract_enabled():
        return {"ok": True, "operation": op, "posture": POSTURE, "override": True}

    spec = _CONTRACT["budgets"].get(op, {})
    window = float(_CONTRACT["window_sec"])
    result: dict[str, Any] = {
        "ok": True,
        "operation": op,
        "posture": POSTURE,
        "on_demand": on_demand,
    }

    if slot:
        cap = int(spec.get("concurrent_max", 1))
        with _lock:
            cur = int(_slots.get(op, 0))
            if cur >= cap:
                result.update({
                    "ok": False,
                    "error": "contract_slot",
                    "reason": "concurrent_limit",
                    "limit": cap,
                    "active": cur,
                    "defer_ms": _CONTRACT["defer_ms"],
                })
                return result
            _slots[op] = cur + 1
        result["slot"] = {"active": _slots[op], "limit": cap}
        return result

    per_window = int(spec.get("per_window", 9999))
    burst = int(spec.get("burst", per_window))
    hits = _prune(op, window=window)
    limit = burst if on_demand else per_window
    if len(hits) + cost > limit:
        result.update({
            "ok": False,
            "error": "contract_budget",
            "reason": "window_exhausted",
            "limit": limit,
            "used": len(hits),
            "window_sec": window,
            "defer_ms": _CONTRACT["defer_ms"],
        })
        return result

    now = time.monotonic()
    with _lock:
        bucket = _counters.setdefault(op, [])
        for _ in range(max(1, cost)):
            bucket.append(now)
    result["budget"] = {
        "used": len(_counters.get(op, [])),
        "limit": limit,
        "remaining": max(0, limit - len(_counters.get(op, []))),
        "window_sec": window,
    }
    return result


def release(operation: str, *, slot: bool = False) -> None:
    op = str(operation)
    if not slot:
        return
    with _lock:
        cur = int(_slots.get(op, 0))
        _slots[op] = max(0, cur - 1)


def eye_budget(*, on_demand: bool = False) -> dict[str, Any]:
    rails = _CONTRACT["eye_rails"]
    sharing = bool(_active_workers())
    load = _load_avg()
    if on_demand and not sharing and load < rails["load_soft"]:
        max_w = rails["max_width_on_demand"]
        allow_stereo = True
        allow_foveal = True
        allow_thermal = True
        share_every_n = 1
        yield_ms = rails["yield_ms_idle"]
    elif sharing or load >= rails["load_soft"]:
        max_w = rails["max_width_share"]
        allow_stereo = on_demand and load < rails["load_hard"]
        allow_foveal = on_demand and load < rails["load_soft"]
        allow_thermal = False
        share_every_n = rails["share_every_n"]
        yield_ms = rails["yield_ms_share"]
    else:
        max_w = rails["max_width_idle"]
        allow_stereo = True
        allow_foveal = True
        allow_thermal = True
        share_every_n = 1
        yield_ms = rails["yield_ms_idle"]

    if load >= rails["load_hard"]:
        max_w = min(max_w, 480)
        allow_stereo = False
        allow_foveal = False

    return {
        "max_width": int(max_w),
        "allow_stereo": allow_stereo,
        "allow_foveal": allow_foveal,
        "allow_thermal": allow_thermal,
        "share_every_n": int(share_every_n),
        "yield_ms": float(yield_ms),
        "sharing": sharing,
        "load_1m": round(load, 2),
        "workers": _active_workers(),
    }


def eye_may_run(*, on_demand: bool = False) -> bool:
    if not contract_enabled():
        return True
    if on_demand:
        return acquire("eye", on_demand=True).get("ok", False)
    budget = eye_budget(on_demand=False)
    if budget["sharing"] or budget["load_1m"] >= _CONTRACT["eye_rails"]["load_soft"]:
        global _frame_n
        with _lock:
            _frame_n += 1
            n = _frame_n
        if n % max(1, budget["share_every_n"]) != 0:
            return False
    return acquire("eye", on_demand=False).get("ok", False)


def prepare_eye_image(img: Any, *, on_demand: bool = False) -> tuple[Any, dict[str, Any]]:
    budget = eye_budget(on_demand=on_demand)
    try:
        w, h = img.size
    except Exception:
        return img, budget
    max_w = budget["max_width"]
    if w <= max_w:
        return img, budget
    scale = max_w / w
    target = (max(1, int(w * scale)), max(1, int(h * scale)))
    try:
        from PIL import Image
        resample = Image.Resampling.BILINEAR
    except Exception:
        resample = 1
    return img.resize(target, resample), {**budget, "downscaled_from": f"{w}x{h}"}


def yield_share(*, on_demand: bool = False) -> None:
    if not contract_enabled():
        return
    ms = eye_budget(on_demand=on_demand)["yield_ms"]
    if ms > 0:
        time.sleep(ms / 1000.0)


def contract_status() -> dict[str, Any]:
    window = float(_CONTRACT["window_sec"])
    usage: dict[str, Any] = {}
    for op, spec in _CONTRACT["budgets"].items():
        if "per_window" in spec:
            hits = _prune(op, window=window)
            usage[op] = {
                "used": len(hits),
                "limit": spec["per_window"],
                "burst": spec.get("burst"),
                "remaining": max(0, int(spec["per_window"]) - len(hits)),
            }
        if "concurrent_max" in spec:
            with _lock:
                active = int(_slots.get(op, 0))
            usage[op] = {
                **usage.get(op, {}),
                "active": active,
                "concurrent_max": spec["concurrent_max"],
            }
    return {
        "schema": "final-eye-assist-contract/v1",
        "enabled": contract_enabled(),
        "posture": POSTURE,
        "rule": _CONTRACT["rule"],
        "contract": _CONTRACT,
        "usage": usage,
        "eye_budget": eye_budget(),
        "workers": _active_workers(),
        "load_1m": round(_load_avg(), 2),
    }


def cool_status() -> dict[str, Any]:
    """Backward-compatible status — same assist contract."""
    st = contract_status()
    st["schema"] = "zocr-cool/v1"
    st["rule"] = "Assistive tenant — share resources, never the hotspot"
    return st