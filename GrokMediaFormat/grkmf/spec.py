"""GRKMF1 format specification loader."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = _ROOT / "data" / "grkmf-v1.json"

FORMAT_ID = "GRKMF1"
CODEC_ID = "GVC1"
MAGIC = b"GRKM"


def load_spec() -> dict[str, Any]:
    try:
        return json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "format_id": FORMAT_ID,
            "codec_id": CODEC_ID,
            "profiles": {},
        }


def profiles() -> dict[str, Any]:
    return load_spec().get("profiles", {})


def profile(name: str) -> dict[str, Any]:
    return profiles().get(name, profiles().get("stream_4k", {"fps": 60, "width": 3840, "height": 2160}))


def bullet_profile(name: str | None = None, prof: dict[str, Any] | None = None) -> bool:
    spec = prof or profile(name or "dodge_4k")
    if spec.get("bullet_train"):
        return True
    return str(name or "").startswith("dodge") or spec.get("mode") == "intra" and float(spec.get("fps", 0)) >= 120