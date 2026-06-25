"""Final_Eye robotics arm — war/dishes + AI-tunable video on demand."""
from __future__ import annotations

from typing import Any

from zocr_eye import load_final_eyeball, set_final_mode
from zocr_product import product_info


def _mode_tune(mode_id: str) -> dict[str, Any]:
    doc = load_final_eyeball()
    m = doc.get("modes", {}).get(mode_id, {})
    vp = str(m.get("video_profile", "watch"))
    if mode_id == "war":
        return {"mode": "combat", "preset": "combat_tactical", "fps": 8, "max_width": 2560}
    return {"mode": "media", "preset": "legacy_hd", "fps": 2, "max_width": 1280, "video_profile": vp}


def arm_robotics(
    mode: str = "dishes",
    *,
    voice: str | None = None,
    start_stream: bool = False,
    tune: dict[str, Any] | None = None,
    prefer: str = "auto",
) -> dict[str, Any]:
    """Arm Final Eyeball for robotics — eye, rig, AI video tune, optional stream."""
    from zocr_video import video_start, video_tune

    final = set_final_mode(mode, voice=voice, source="robotics_arm")
    if not final.get("ok"):
        return {**final, "product": product_info()}

    tspec = {**_mode_tune(mode), **(tune or {})}
    tuned = video_tune(
        mode=tspec.get("mode"),
        fps=tspec.get("fps"),
        max_width=tspec.get("max_width"),
        width=tspec.get("width"),
        height=tspec.get("height"),
        preset=tspec.get("preset"),
        reason=f"robotics_arm:{mode}",
    )

    stream: dict[str, Any] | None = None
    if start_stream:
        prof = str(tspec.get("video_profile") or final.get("prescription", {}).get("video_profile") or "watch")
        stream = video_start(profile=prof, prefer=prefer, tune=tspec)

    return {
        "ok": True,
        "schema": "final-eye-robotics-arm/v1",
        "product": product_info(),
        "mode": mode,
        "final_eyeball": final,
        "sovereign_time": final.get("sovereign_time"),
        "redundancy": final.get("redundancy"),
        "video_tune": tuned.get("resolved"),
        "stream": stream,
        "affordances": {
            "look": "POST /api/look",
            "observe": "POST /api/observe",
            "mjpeg": "GET /api/stream/mjpeg",
            "ai_tune": "POST /api/video/ai-tune",
        },
    }


def robotics_doctrine() -> dict[str, Any]:
    doc = load_final_eyeball()
    return {
        "schema": "final-eye-robotics-doctrine/v1",
        "product": product_info(),
        "rule": doc.get("rule"),
        "vision_confidence": doc.get("vision_confidence"),
        "modes": list(doc.get("modes", {}).keys()),
        "combat": "AI-tunable 3–20 fps — POST /api/video/tune",
        "media": "Legacy through 16K, up to 240 fps — GRKMF1/GVC1",
        "arm": "POST /api/robotics/arm {\"mode\":\"war|dishes\",\"start_stream\":true}",
        "field_compiler": "Grok16 + FIELDC v4 — GET /api/field/compiler",
    }