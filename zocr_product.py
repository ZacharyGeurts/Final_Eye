"""Final_Eye product metadata — v0.9 robotics release."""
from __future__ import annotations

from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent
_VERSION_FILE = _ROOT / "VERSION"
if not _VERSION_FILE.is_file():
    _VERSION_FILE = _ROOT.parent / "VERSION"

PRODUCT_ID = "Final_Eye"
PRODUCT_NAME = "The Final Eyeball"
VERSION = "0.9.0"
SCHEMA = "final-eye-product/v1"
CODENAME = "robotics-review"
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
        "review": {
            "target": "scientific robotics masters",
            "checklist": "docs/REVIEW_CHECKLIST.md",
        },
    }