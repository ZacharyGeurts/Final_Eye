"""Final_Eye product metadata — v0.9.9 field compiler review release."""
from __future__ import annotations

from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent
_VERSION_FILE = _ROOT / "VERSION"
if not _VERSION_FILE.is_file():
    _VERSION_FILE = _ROOT.parent / "VERSION"

PRODUCT_ID = "Final_Eye"
PRODUCT_NAME = "The Final Eyeball"
VERSION = "0.9.9"
SCHEMA = "final-eye-product/v1"
CODENAME = "field-forge-opt"
LICENSE = "proprietary"
REPO = "https://github.com/ZacharyGeurts/Final_Eye"


def product_info() -> dict[str, Any]:
    try:
        from zocr_grkmf import grkmf
        grkmf_id = grkmf.FORMAT_ID
        codec = grkmf.CODEC_ID
    except ImportError:
        grkmf_id = "GRKMF1"
        codec = "GVC1"
    return {
        "schema": SCHEMA,
        "product": PRODUCT_ID,
        "name": PRODUCT_NAME,
        "version": VERSION,
        "codename": CODENAME,
        "license": LICENSE,
        "repository": REPO,
        "stack": {
            "vision": "ZOCRSM1",
            "media": grkmf_id,
            "codec": codec,
            "mandate": "ZOCR_FIELD_ROBOTICS_MANDATE_v1",
            "field_compiler": {
                "grok16": "G16 @ gnu++26 — Queen Forge compiler_probe",
                "fieldc": "FIELDC v4 — .fld → AMMO .OBJ (FieldFieldCc)",
            },
            "forge": "Queen lib/queen-forge.py",
        },
        "robotics": {
            "on_demand_capture": True,
            "silent_capture": True,
            "ai_tunable_video": True,
            "modes": ["war", "dishes"],
            "combat_fps_range": [3, 20],
            "media_fps_max": 240,
            "resolution_max": "15360x8640",
        },
        "assist_contract": {
            "posture": "assistive",
            "rule": "One tenant in a shared system — bounded usage, no overflow or overdraw",
            "env": "FINAL_EYE_ASSIST=1",
            "module": "zocr_contract.py",
        },
        "review": {
            "target": "scientific robotics masters",
            "checklist": "docs/REVIEW_CHECKLIST.md",
        },
    }