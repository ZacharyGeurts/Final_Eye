"""ZOCR AI / robotics — stream, field power, DARPA-style protection."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from zocr import latest, status as core_status, tesseract_available
from zocr_capture import capture_backends
from zocr_field import load_mandate, verify_chain
from zocr_additives import additives_status
from zocr_eye import eye_status, spectrum_doctrine
from zocr_neural import neural_status
from zocr_stereo import rig_status
from zocr_preserve import preserve_status, threat_doctrine
from zocr_security import security_status
from zocr_vigilance import vigilance_status
from zocr_session import vision_status
from zocr_stream import fps_profiles, stream_status
from zocr_video import format_doctrine, video_status
from zocr_field_compiler import field_compiler_status
from zocr_vision import forge_snapshot, look

_ROOT = Path(__file__).resolve().parent
SG = _ROOT.parent


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _assist_limits() -> dict[str, Any]:
    try:
        from zocr_contract import contract_status
        c = contract_status()
        return {
            "posture": c.get("posture", "assistive"),
            "flash_capture": False,
            "overflow": False,
            "contract": c.get("contract", {}).get("budgets", {}),
            "usage": c.get("usage", {}),
        }
    except ImportError:
        return {"posture": "assistive", "flash_capture": False}


def capabilities() -> dict[str, Any]:
    m = load_mandate()
    return {
        "schema": "zocr-capabilities/v2",
        "product": "ZOCR",
        "role": "robotics_ai_field_vision",
        "doctrine": "Confidence always in Vision — ZOCRSM1 sub-micron video, WRDT seals, adaptive tide. Look on demand.",
        "modes": {
            "look": "Single frame + OCR",
            "stream": "ZOCRSM1 background capture with WRDT envelopes + hash chain",
            "mjpeg": "Browser multipart stream — incremental, no white flash",
            "observe": "Look + robotics envelope",
            "verify": "Chain integrity check",
        },
        "sources": {
            "auto": "RTX ppm → silent screen",
            "rtx": "Engine grab only",
            "screen": "xwd silent only",
            "text": "Telemetry text",
        },
        "stream": {
            "format": "ZOCRSM1",
            "transport": "MJPEG multipart/x-mixed-replace",
            "profiles": fps_profiles(),
            "mandate_id": m.get("mandate_id"),
        },
        "protection": m.get("protection", {}),
        "preserve": m.get("preserve", {}),
        "security": m.get("security", {}),
        "vigilance": m.get("vigilance", {}),
        "display_additives": m.get("display_additives", {}),
        "threat_doctrine": threat_doctrine(),
        "additives": additives_status(),
        "ocular_spectrum": spectrum_doctrine(),
        "eye": eye_status(),
        "rig": rig_status(),
        "neural": neural_status(),
        "backends": capture_backends(),
        "limits": _assist_limits(),
        "endpoints": {
            "GET /api/stream/mjpeg?profile=watch": "MJPEG view — set FPS via profile",
            "POST /api/stream/start": "{\"profile\":\"tactical\",\"prefer\":\"auto\"}",
            "POST /api/stream/stop": "Stop ZOCRSM1 background stream",
            "GET /api/video": "ZOCRSM1 status — fabric nm/px, adaptive scale, fast path",
            "GET /api/video/format": "ZOCRSM1 doctrine — World_Redata + AMOURANTHRTX lineage",
            "GET /api/video/verify": "Verify .zocrsm WRDT envelopes in video index",
            "POST /api/video/enhance": "{\"enable\":true} — eye/stereo rig on video frames",
            "GET /api/trust": "IRTN — interwoven redundancies trust network",
            "GET /api/trust/mesh": "Verify woven paths across ZOCR + Hostess7 + Queen",
            "GET /api/trust/hostess7": "Hostess7 bridge — neural stack, nexus trust, gates",
            "GET /api/offense": "Vision offense status — strikes, preempt, streak",
            "GET /api/offense/doctrine": "Defense of vision requires offense",
            "GET /api/pattern": "Internal imaging pattern security status",
            "POST /api/pattern/scan": "Foreign grid/moiré/injection detect on frame",
            "POST /api/pattern/stamp": "Stamp 64-bit provenance weave on frame",
            "GET /api/stream/verify": "Hash chain integrity",
            "POST /api/look": "On-demand frame",
            "GET /api/mandate": "Field robotics mandate",
            "GET /api/security": "Code seal + mandate security status",
            "GET /api/vigilance/status": "Vigilance watch + modular additives",
            "POST /api/vigilance/start": "Start additive vigilance loop",
            "GET /api/eye": "Active ocular profile + spectrum teaching",
            "POST /api/eye/teach": "{\"profile\":\"bird\"} — teach eye avian/reptile/human spectrum",
            "GET /api/eye/final": "The Final Eyeball — active mode, prescription, speak",
            "POST /api/eye/final/mode": "{\"mode\":\"war\"} or {\"mode\":\"dishes\"} — arm sight stack",
            "GET /api/eye/final/speak?mode=war&voice=tactical": "Doctrine in chosen voice",
            "GET /api/rig": "Multi-eye rig + stereoscopic status",
            "POST /api/rig/configure": "{\"preset\":\"stereo_human\"} or custom eyes array",
            "POST /api/neural/analyze": "Protected NN assistance on frame",
            "GET /api/field/compiler": "Grok16 + FIELDC v4 + Queen forge posture",
            "POST /api/field/compiler/probe": "Refresh Queen compiler_probe",
        },
        "paths": {
            "root": str(_ROOT),
            "stream_dir": str(_ROOT / "out" / "stream"),
            "mandate": str(_ROOT / "data" / "zocr-field-mandate.json"),
        },
    }


def robotics_context(*, capture: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        from zocr_grkmf import grkmf
        tune = grkmf.tune_doctrine()
    except ImportError:
        tune = {}
    forge = forge_snapshot()
    cap = capture or {}
    row = cap.get("capture") or {}
    meta = row.get("meta") or {}
    st = stream_status()
    return {
        "schema": "zocr-robotics-observe/v2",
        "ts": _ts(),
        "perception": {
            "source": cap.get("source", "none"),
            "silent_capture": meta.get("silent", True),
            "image": row.get("image"),
            "ocr_len": row.get("ocr_len", 0),
            "ocr_excerpt": (row.get("ocr") or "")[:1200],
        },
        "stream": st,
        "field_power": {
            "profile": st.get("profile", "idle"),
            "fps": st.get("fps", 0),
            "power": st.get("field_power", "minimal"),
            "ai_tunable": True,
            "resolved": st.get("resolved"),
        },
        "grkmf_ai_tune": tune,
        "forge": {k: v for k, v in forge.items() if k not in ("tail", "grok16", "fieldc")},
        "field_compiler": field_compiler_status(),
        "protection": {
            "mandate_id": load_mandate().get("mandate_id"),
            "chain": verify_chain(tail=3),
            "no_flash": True,
            "security": security_status(),
            "preserve": preserve_status(),
            "vigilance": vigilance_status(),
        },
        "affordances": {
            "start_stream": "POST /api/stream/start",
            "mjpeg_watch": "GET /api/stream/mjpeg?profile=watch",
            "look": "POST /api/look",
        },
    }


def ai_context(*, include_look: bool = False, prefer: str = "auto") -> dict[str, Any]:
    ctx = {
        "schema": "zocr-ai-context/v2",
        "ts": _ts(),
        "capabilities": capabilities(),
        "mandate": load_mandate(),
        "zocr": core_status(),
        "session": vision_status(),
        "stream": stream_status(),
        "video": video_status(),
        "video_format": format_doctrine(),
        "forge": forge_snapshot(),
        "tesseract": tesseract_available(),
        "latest_captures": latest(5),
    }
    if include_look:
        ctx["look"] = look(label="ai_look", prefer=prefer)
        ctx["robotics"] = robotics_context(capture=ctx["look"])
    return ctx