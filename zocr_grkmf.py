"""ZOCR ↔ GrokMediaFormat bridge — GRKMF1 proprietary cinema."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_GMF_ROOT = _ROOT / "GrokMediaFormat"
if not _GMF_ROOT.is_dir():
    _GMF_ROOT = _ROOT.parent / "GrokMediaFormat"
if _GMF_ROOT.is_dir() and str(_GMF_ROOT) not in sys.path:
    sys.path.insert(0, str(_GMF_ROOT))

import grkmf  # noqa: E402

__all__ = ["grkmf", "GMF_ROOT"]

GMF_ROOT = _GMF_ROOT