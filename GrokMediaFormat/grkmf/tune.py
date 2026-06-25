"""GRKMF AI tune — fps and resolution to whatever, on demand."""
from __future__ import annotations

import math
import threading
import time
from typing import Any

from grkmf.spec import load_spec, profile as preset_profile

_lock = threading.RLock()
_active: dict[str, Any] = {
    "mode": "media",
    "width": None,
    "height": None,
    "fps": None,
    "gop": None,
    "jpeg_quality": None,
    "max_width": None,
    "refresh_hz": None,
    "ai_locked": False,
    "updated": None,
    "reason": "defaults",
}
_load_ema: float = 0.0

# Sanity ceiling — AI picks anything inside these rails
_ABS = {
    "width": (160, 15360),
    "height": (120, 8640),
    "fps": (0.1, 1000.0),
    "gop": (1, 240),
    "jpeg_quality": (40, 100),
    "refresh_hz": (0.1, 1000.0),
}


def _bounds() -> dict[str, Any]:
    return load_spec().get("ai_tunable", {}).get("bounds", {})


def _modes() -> dict[str, Any]:
    return load_spec().get("ai_tunable", {}).get("modes", {})


def _clamp(key: str, val: float | int) -> float | int:
    lo, hi = _ABS.get(key, (0, 1_000_000))
    b = _bounds().get(key)
    if b:
        lo = max(lo, float(b.get("min", lo)))
        hi = min(hi, float(b.get("max", hi)))
    if key in ("width", "height", "gop", "jpeg_quality"):
        return int(max(lo, min(hi, round(float(val)))))
    return round(max(lo, min(hi, float(val))), 3)


def _height_for_width(width: int, aspect: float = 16 / 9) -> int:
    return _clamp("height", max(120, int(round(width / aspect))))


def active_tune() -> dict[str, Any]:
    with _lock:
        return dict(_active)


def tune_apply(
    *,
    mode: str | None = None,
    width: int | float | None = None,
    height: int | float | None = None,
    max_width: int | float | None = None,
    fps: float | None = None,
    refresh_hz: float | None = None,
    gop: int | None = None,
    jpeg_quality: int | None = None,
    ai_locked: bool | None = None,
    reason: str = "api",
    preset: str | None = None,
) -> dict[str, Any]:
    """Apply AI/human tune — any fps/res inside sanity rails."""
    with _lock:
        if preset:
            base = preset_profile(preset)
            for k in ("width", "height", "fps", "gop", "jpeg_quality", "refresh_hz", "mode", "max_width"):
                if k in base and _active.get(k) is None:
                    _active[k] = base.get(k)
            if base.get("tier"):
                _active.setdefault("mode", base["tier"])
        if mode is not None:
            _active["mode"] = str(mode)
        if width is not None:
            _active["width"] = _clamp("width", width)
        if max_width is not None:
            _active["max_width"] = _clamp("width", max_width)
        if height is not None:
            _active["height"] = _clamp("height", height)
        if fps is not None:
            _active["fps"] = _clamp("fps", fps)
        if refresh_hz is not None:
            _active["refresh_hz"] = _clamp("refresh_hz", refresh_hz)
        if gop is not None:
            _active["gop"] = _clamp("gop", gop)
        if jpeg_quality is not None:
            _active["jpeg_quality"] = _clamp("jpeg_quality", jpeg_quality)
        if ai_locked is not None:
            _active["ai_locked"] = bool(ai_locked)
        _active["updated"] = time.time()
        _active["reason"] = reason
        return resolve(preset)


def tune_reset() -> dict[str, Any]:
    with _lock:
        _active.update({
            "mode": "media",
            "width": None,
            "height": None,
            "fps": None,
            "gop": None,
            "jpeg_quality": None,
            "max_width": None,
            "refresh_hz": None,
            "ai_locked": False,
            "reason": "reset",
        })
    return resolve()


def resolve(
    preset: str | None = None,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge preset + active tune + overrides → effective encode/stream params."""
    base: dict[str, Any] = dict(preset_profile(preset)) if preset else {}
    with _lock:
        merged: dict[str, Any] = {**base, **{k: v for k, v in _active.items() if v is not None}}
    if overrides:
        merged.update({k: v for k, v in overrides.items() if v is not None})

    mode = str(merged.get("mode") or merged.get("tier") or "media")
    mode_hint = _modes().get(mode, {})

    w = merged.get("width") or merged.get("max_width") or mode_hint.get("width_default") or base.get("width", 3840)
    h = merged.get("height") or mode_hint.get("height_default") or base.get("height") or _height_for_width(int(w))
    fps = merged.get("fps") or mode_hint.get("fps_default") or base.get("fps", 24)
    refresh = merged.get("refresh_hz") or fps
    gop = merged.get("gop") or base.get("gop", 24)
    jq = merged.get("jpeg_quality") or base.get("jpeg_quality", 88)

    w = _clamp("width", w)
    h = _clamp("height", h)
    fps = _clamp("fps", fps)
    refresh = _clamp("refresh_hz", refresh)
    gop = _clamp("gop", gop)
    jq = _clamp("jpeg_quality", jq)

    if mode == "combat" and not merged.get("ai_locked"):
        lo, hi = mode_hint.get("fps_range", [3, 20])
        if not (overrides and "fps" in overrides) and _active.get("fps") is None:
            fps = _clamp("fps", min(hi, max(lo, fps)))

    bullet = bool(merged.get("bullet_train") or mode in ("dodge", "bullet") or float(fps) >= 60)
    intra = merged.get("mode") == "intra" or bullet and gop <= 1

    return {
        "mode": mode,
        "preset": preset,
        "width": int(w),
        "height": int(h),
        "max_width": int(w),
        "fps": float(fps),
        "refresh_hz": float(refresh),
        "gop": int(1 if intra else gop),
        "jpeg_quality": int(jq),
        "bullet_train": bullet,
        "resolution": f"{w}x{h}",
        "ai_tunable": True,
        "ai_locked": bool(merged.get("ai_locked")),
        "target_mbps": merged.get("target_mbps"),
        "fabric_nm_per_px": merged.get("fabric_nm_per_px"),
    }


def ai_tune(
    *,
    mode: str | None = None,
    load_ms: float | None = None,
    preset: str | None = None,
    goal: str | None = None,
) -> dict[str, Any]:
    """Ride load — AI scales fps/res on demand. Combat 3–20, media to 240, whatever inside rails."""
    global _load_ema
    if load_ms is not None:
        _load_ema = _load_ema * 0.82 + float(load_ms) * 0.18

    cur = resolve(preset)
    m = mode or cur.get("mode") or "media"
    hint = _modes().get(m, {})
    fps_lo, fps_hi = hint.get("fps_range", [1, 240])
    w_lo, w_hi = hint.get("width_range", [640, 15360])

    target_ms = 1000.0 / max(cur["fps"], 0.1)
    ratio = _load_ema / target_ms if target_ms > 0 else 1.0

    new_fps = cur["fps"]
    new_w = cur["width"]

    if goal == "max_quality":
        new_fps = _clamp("fps", min(fps_hi, cur["fps"] * 1.1))
        new_w = _clamp("width", min(w_hi, int(cur["width"] * 1.05)))
    elif goal == "min_latency" or ratio > 1.2:
        new_fps = _clamp("fps", max(fps_lo, cur["fps"] * 0.75))
        new_w = _clamp("width", max(w_lo, int(cur["width"] * 0.85)))
    elif ratio < 0.55:
        new_fps = _clamp("fps", min(fps_hi, cur["fps"] * 1.15))
        new_w = _clamp("width", min(w_hi, int(cur["width"] * 1.08)))

    if m == "combat":
        new_fps = _clamp("fps", max(fps_lo, min(fps_hi, new_fps)))

    reason = f"ai_ride ratio={ratio:.2f} load_ms={_load_ema:.0f} goal={goal or 'auto'}"
    return tune_apply(
        mode=m,
        width=new_w,
        height=_height_for_width(int(new_w)),
        fps=float(new_fps),
        refresh_hz=float(new_fps),
        preset=preset,
        ai_locked=False,
        reason=reason,
    )


def tune_doctrine() -> dict[str, Any]:
    spec = load_spec()
    return {
        "schema": "grkmf-ai-tune/v1",
        "rule": spec.get("ai_tunable", {}).get("rule", "AI sets fps and resolution — whatever, on demand"),
        "bounds": _bounds() or _ABS,
        "modes": _modes(),
        "resolution_ladder": spec.get("ai_tunable", {}).get("resolution_ladder", []),
        "active": active_tune(),
        "resolved": resolve(),
    }