"""ZOCR live status — telemetry only, no automatic capture."""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path

from zocr import latest, status as zocr_core_status, tesseract_available
from zocr_ai import capabilities
from zocr_capture import capture_backends
from zocr_field import load_mandate, verify_chain
from zocr_session import vision_status
from zocr_additives import additives_status
from zocr_preserve import preserve_status, threat_doctrine
from zocr_security import security_status
from zocr_stream import stream_status
from zocr_video import video_status
from zocr_eye import eye_status, final_eyeball_status
from zocr_neural import neural_status
from zocr_stereo import rig_status
from zocr_kill import kill_status
from zocr_vigilance import vigilance_status
from zocr_pattern import pattern_status
from zocr_offense import offense_status
from zocr_trust import trust_network_status
from zocr_product import product_info
from zocr_vision import forge_snapshot

_START = time.time()
_ROOT = Path(__file__).resolve().parent
SG = _ROOT.parent


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def product_guide() -> dict:
    return {
        "scope": {
            "zocr": "Robotics/AI vision sink — look on demand, silent capture, OCR → out/",
            "session": "Append-only vision-session.jsonl",
            "viewing": "GET /api/status refreshes telemetry only — no screen grab, no flash",
        },
        "sources": [
            {"id": "xwd_silent", "when": "DISPLAY + xwd", "how": "Root framebuffer read — no flash"},
            {"id": "rtx_grab", "when": "Queen RTX headless ppm", "how": "Engine frame — no OS screen"},
            {"id": "text", "when": "prefer=text or no frame", "how": "Forge/log context"},
        ],
        "commands": {
            "start": "./start.sh --no-open",
            "look": "python3 zocr_watch.py look",
            "observe": "curl -s -X POST http://127.0.0.1:9479/api/observe",
            "status": "curl -s http://127.0.0.1:9479/api/status",
        },
    }


def live_status() -> dict:
    core = zocr_core_status()
    vs = vision_status()
    forge = forge_snapshot()
    caps = latest(5)
    thumb = None
    for c in reversed(caps):
        img = c.get("image")
        if img and Path(img).is_file():
            thumb = img
            break
    pinfo = product_info()
    return {
        "ok": True,
        "product": pinfo["product"],
        "version": pinfo["version"],
        "service": "zocr-vision",
        "schema": "zocr-live-status/v2",
        "ts": _ts(),
        "uptime_sec": round(time.time() - _START, 3),
        "doctrine": "Confidence always in Vision — defense requires offense — ZOCRSM1, WRDT seals, adaptive tide.",
        "session": vs,
        "forge": forge,
        "stream": stream_status(),
        "video": video_status(),
        "field": {
            "mandate_id": load_mandate().get("mandate_id"),
            "chain_verify": verify_chain(tail=5),
        },
        "preserve": preserve_status(),
        "security": security_status(),
        "pattern": pattern_status(),
        "offense": offense_status(),
        "trust": trust_network_status(full_mesh=False),
        "eye": eye_status(),
        "final_eyeball": final_eyeball_status(),
        "rig": rig_status(),
        "neural": neural_status(),
        "kill": kill_status(),
        "vigilance": vigilance_status(),
        "additives": additives_status(),
        "threat_doctrine": threat_doctrine(),
        "robotics": {
            "on_demand": True,
            "frame_limit": None,
            "silent_capture": True,
            "backends": capture_backends(),
            "stream_format": "ZOCRSM1",
            "mjpeg": "/api/stream/mjpeg",
        },
        "zocr": {
            **core,
            "tesseract": tesseract_available(),
            "display": os.environ.get("DISPLAY"),
            "sg_root": str(SG),
            "queen_root": str(SG / "NewLatest" / "Queen"),
        },
        "latest_thumb": thumb,
        "latest_captures": caps,
        "guide": product_guide(),
        "capabilities": capabilities(),
        "terminal": {
            "look": "python3 zocr_watch.py look",
            "look_rtx": "python3 zocr_watch.py look --prefer rtx",
            "status": "python3 zocr_watch.py status",
            "api_look": "curl -s -X POST http://127.0.0.1:9479/api/look",
            "api_observe": "curl -s -X POST http://127.0.0.1:9479/api/observe",
        },
    }