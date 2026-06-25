"""Grok16 field compiler — canonical reader from SG/Grok16 for ZOCR eyeball + forge."""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent
SG = _ROOT.parent
GROK16 = Path(os.environ.get("GROK16_ROOT", str(SG / "Grok16")))
QUEEN = Path(os.environ.get("QUEEN_ROOT", str(SG / "NewLatest" / "Queen")))

VERSION_PATH = GROK16 / "data" / "grok16-version.json"
PROFILES_PATH = GROK16 / "data" / "grok16-profiles.json"
TOOLCHAIN_PATH = GROK16 / "data" / "grok16-toolchain.json"
QUEEN_TOOLCHAIN = QUEEN / "data" / "g16-toolchain.json"
G16_BIN = GROK16 / "bin" / "g16"

MODE_PROFILE_MAP = {
    "war": "vulkan_rtx",
    "dishes": "ai",
    "patrol": "field_opt",
    "engage": "field_compute",
    "night_watch": "field_opt",
    "submicron": "field_opt",
    "preserve": "field_opt",
}

EYE_PROFILE_MAP = {
    "human": "ai",
    "bird": "field_opt",
    "reptile": "field_opt",
    "snake_pit": "field_compute",
    "fish": "ai",
    "insect": "field_opt",
    "mammal_night": "field_opt",
    "raptor": "vulkan_rtx",
}


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def load_version() -> dict[str, Any]:
    return _read_json(VERSION_PATH) or {"g16_version": "16.1.1", "cxx_std_default": "gnu++26"}


def load_profiles() -> dict[str, Any]:
    doc = _read_json(PROFILES_PATH)
    if doc.get("profiles"):
        return doc
    tc = load_toolchain()
    return {"profiles": tc.get("profiles", {}), "schema": "grok16-profiles/v2"}


def load_toolchain() -> dict[str, Any]:
    doc = _read_json(TOOLCHAIN_PATH)
    if doc:
        doc["_source"] = str(TOOLCHAIN_PATH)
        return doc
    queen = _read_json(QUEEN_TOOLCHAIN)
    if queen:
        queen["_source"] = str(QUEEN_TOOLCHAIN)
        return queen
    return {}


def _probe_g16() -> dict[str, Any]:
    g16 = G16_BIN
    if not g16.is_file() or not os.access(g16, os.X_OK):
        env_g16 = os.environ.get("G16_PREFIX", "").strip()
        if env_g16:
            g16 = Path(env_g16) / "bin" / "g16"
    if not g16.is_file():
        return {"ok": False, "path": None}
    try:
        proc = subprocess.run(
            [str(g16), "-dumpversion"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        ver = (proc.stdout or "").strip()
        return {"ok": proc.returncode == 0, "path": str(g16), "dumpversion": ver}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "path": str(g16), "error": str(exc)[:120]}


def grok16_status() -> dict[str, Any]:
    ver = load_version()
    tc_doc = load_toolchain()
    probe = _probe_g16()
    profiles = (load_profiles().get("profiles") or {})
    field_opt = profiles.get("field_opt") or {}
    return {
        "schema": "zocr-grok16-status/v1",
        "ts": _ts(),
        "product": "Grok16",
        "root": str(GROK16),
        "g16_version": ver.get("g16_version"),
        "pkgversion": ver.get("pkgversion"),
        "driver": ver.get("driver", "unified"),
        "cxx_std": ver.get("cxx_std_default", "gnu++26"),
        "c_std": ver.get("c_std_default", "gnu17"),
        "default_profile": "field_opt",
        "g16": probe.get("path"),
        "dumpversion": probe.get("dumpversion") or tc_doc.get("dumpversion"),
        "ready": bool(probe.get("ok") or tc_doc.get("engine_real")),
        "selfhosted": bool(tc_doc.get("selfhosted")),
        "toolchain_source": tc_doc.get("_source"),
        "profiles": list(profiles.keys()),
        "field_macros": (load_profiles().get("field_macros") or {}),
        "field_opt_definitions": field_opt.get("definitions", []),
        "forge": str(GROK16 / "forge" / "grok16-forge.py"),
        "toolchain_sh": str(GROK16 / "scripts" / "grok16-toolchain.sh"),
    }


def grok16_profile_for_mode(mode: str | None) -> str:
    return MODE_PROFILE_MAP.get(str(mode or "").strip(), "field_opt")


def grok16_profile_for_eye(eye_profile: str | None) -> str:
    return EYE_PROFILE_MAP.get(str(eye_profile or "").strip(), "field_opt")


def grok16_eye_tune(
    *,
    mode: str | None = None,
    eye_profile: str | None = None,
    grok16_profile: str | None = None,
) -> dict[str, Any]:
    """Map Grok16 consumer profile → ocular perceive tuning (field_opt primary)."""
    pid = grok16_profile or grok16_profile_for_mode(mode) or grok16_profile_for_eye(eye_profile)
    profiles = (load_profiles().get("profiles") or {})
    spec = profiles.get(pid) or profiles.get("field_opt") or {}
    defs = set(spec.get("definitions") or [])
    tune = {
        "grok16_profile": pid,
        "cxx_std": spec.get("cxx_std", "gnu++26"),
        "vectorize": "-ftree-vectorize" in " ".join(spec.get("cxx_flags") or []),
        "adaptation_scale": 1.0,
        "foveal_scale": 1.0,
        "entropy_dispatch": "FIELD_ENTROPY_DISPATCH=1" in defs or "GROK16_PROFILE_FIELD_OPT=1" in defs,
        "wave_phase": "FIELD_WAVE_PHASE=1" in defs,
        "field_speed": "G16_FIELD_SPEED=1" in defs,
        "engine": "cone_v2_field_opt" if pid == "field_opt" else f"cone_v2_{pid}",
    }
    if pid == "field_opt":
        tune["adaptation_scale"] = 0.88
        tune["foveal_scale"] = 1.08
    elif pid == "vulkan_rtx":
        tune["adaptation_scale"] = 0.92
        tune["foveal_scale"] = 1.18
    elif pid == "ai":
        tune["adaptation_scale"] = 1.0
        tune["foveal_scale"] = 1.0
    elif pid == "field_compute":
        tune["adaptation_scale"] = 0.95
        tune["foveal_scale"] = 1.05
    return tune


def grok16_eye_witness(*, mode: str | None = None, eye_profile: str | None = None) -> dict[str, Any]:
    st = grok16_status()
    tune = grok16_eye_tune(mode=mode, eye_profile=eye_profile)
    return {
        "field_compiler": "Grok16",
        "g16_version": st.get("g16_version"),
        "dumpversion": st.get("dumpversion"),
        "ready": st.get("ready"),
        "cxx_std": st.get("cxx_std"),
        "profile": tune.get("grok16_profile"),
        "engine": tune.get("engine"),
        "entropy_dispatch": tune.get("entropy_dispatch"),
        "wave_phase": tune.get("wave_phase"),
        "root": st.get("root"),
    }