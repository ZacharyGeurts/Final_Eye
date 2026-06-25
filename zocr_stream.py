"""ZOCR streaming — ZOCRSM1 whole new video (compat shim to zocr_video)."""
from __future__ import annotations

from typing import Any, Generator

from zocr_video import (
    format_doctrine,
    mjpeg_generator,
    video_profiles as fps_profiles,
    video_start as stream_start,
    video_status as stream_status,
    video_stop as stream_stop,
)

FORMAT = "ZOCRSM1"


def profile_fps(name: str) -> float:
    p = fps_profiles().get(name, {})
    return float(p.get("fps", 0))


def stream_set_profile(profile: str) -> dict[str, Any]:
    if not stream_status().get("running"):
        return {"ok": False, "error": "stream_not_running"}
    stream_stop()
    return stream_start(profile=profile, prefer=stream_status().get("prefer", "auto"))


__all__ = [
    "FORMAT",
    "fps_profiles",
    "format_doctrine",
    "mjpeg_generator",
    "profile_fps",
    "stream_set_profile",
    "stream_start",
    "stream_status",
    "stream_stop",
]