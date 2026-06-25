"""ZOCR field compiler — SG/Grok16 primary; Queen forge + FIELDC RTX runtime."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from zocr_grok16 import grok16_status, load_toolchain as grok16_load_toolchain

_ROOT = Path(__file__).resolve().parent
SG = _ROOT.parent
QUEEN = Path(os.environ.get("QUEEN_ROOT", str(SG / "NewLatest" / "Queen")))
GROK16 = Path(os.environ.get("GROK16_ROOT", str(SG / "Grok16")))
RTX_BUILD = QUEEN / "build" / "rtx"
FORGE_LOG = QUEEN / ".queen-forge.log"
DOCTRINE_PATH = _ROOT / "data" / "field-compiler.json"
BIN_CANDIDATES = (
    RTX_BUILD / "bin" / "Linux" / "queen-browser",
    RTX_BUILD / "bin" / "queen-browser",
)
FIELD_COMPILER_VER = "4.0.2026"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_doctrine() -> dict[str, Any]:
    try:
        return json.loads(DOCTRINE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema": "zocr-field-compiler/v1", "layers": {}}


def _read_tail(path: Path, n: int = 18) -> str:
    if not path.is_file():
        return ""
    try:
        return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-n:])
    except OSError:
        return ""


def _find_rtx_binary() -> Path | None:
    for p in BIN_CANDIDATES:
        if p.is_file() and os.access(p, os.X_OK):
            return p
    return None


def _stage_from_tail(tail: str, *, binary_ready: bool) -> str:
    if binary_ready:
        return "binary_ready"
    if re.search(r"FORGE END rtx ok=True", tail):
        return "rtx_done"
    if re.search(r"FORGE END rtx ok=False|compile failed|CMake Error", tail):
        return "failed"
    if re.search(r"=== forge:compiler_probe", tail):
        return "compiler_probe"
    if re.search(r"=== forge:rtx_build|FORGE START rtx", tail):
        return "compiling"
    if re.search(r"rtx_configure|cmake -S", tail):
        return "cmake_configure"
    return "idle"


def _procs() -> list[str]:
    try:
        proc = subprocess.run(
            ["pgrep", "-af", "queen-forge|cmake.*rtx|cmake.*AMOURANTHRTX|g16|g\\+\\+16"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        return [ln.strip() for ln in (proc.stdout or "").splitlines() if ln.strip() and "pgrep" not in ln][:5]
    except (OSError, subprocess.TimeoutExpired):
        return []


def _grok16_layer() -> dict[str, Any]:
    g = grok16_status()
    queen_tc = grok16_load_toolchain()
    queen_probe = _read_json_if_exists(QUEEN / "data" / "g16-toolchain.json")
    ready_rtx = bool(
        queen_probe.get("ready_rtx")
        or (queen_probe.get("found") or {}).get("g16")
        or g.get("ready")
    )
    return {
        "product": "Grok16",
        "version": g.get("g16_version"),
        "dumpversion": g.get("dumpversion"),
        "driver": "g16",
        "cxx_driver": "g++16",
        "cxx_std": g.get("cxx_std", "gnu++26"),
        "profile": g.get("default_profile", "field_opt"),
        "ready": g.get("ready"),
        "ready_rtx": ready_rtx,
        "engine_real": g.get("ready"),
        "selfhosted": g.get("selfhosted"),
        "g16": g.get("g16"),
        "root": g.get("root"),
        "toolchain_source": g.get("toolchain_source") or queen_tc.get("_source"),
        "profiles": g.get("profiles"),
        "forge": g.get("forge"),
    }


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _fieldc_status(*, rtx_binary: Path | None) -> dict[str, Any]:
    doc = load_doctrine()
    layer = (doc.get("layers") or {}).get("fieldc") or {}
    return {
        "id": layer.get("id", "FIELDC"),
        "version": layer.get("version", FIELD_COMPILER_VER),
        "label": layer.get("label", "Field Compiler v4"),
        "pipeline": layer.get("pipeline", ".fld → ASM → AMMO .OBJ"),
        "engine": layer.get("engine", "FieldFieldCc.hpp"),
        "rtx_binary": str(rtx_binary) if rtx_binary else None,
        "rtx_ready": rtx_binary is not None,
        "host_compile": "FIELDC inside queen-browser / AmmoOS shell",
    }


def forge_posture() -> dict[str, Any]:
    """Queen forge stage + field compiler readiness — replaces bare forge_snapshot."""
    tail = _read_tail(FORGE_LOG)
    bin_path = _find_rtx_binary()
    grok16 = _grok16_layer()
    stage = _stage_from_tail(tail, binary_ready=bin_path is not None)
    rtx_files = 0
    if RTX_BUILD.is_dir():
        try:
            rtx_files = sum(1 for _ in RTX_BUILD.rglob("*") if _.is_file())
        except OSError:
            pass
    running = bool(_procs()) and stage not in ("binary_ready", "failed", "rtx_done", "idle")
    return {
        "ts": _ts(),
        "stage": stage,
        "binary_ready": bin_path is not None,
        "binary": str(bin_path) if bin_path else None,
        "compiler_ready": grok16.get("ready_rtx", False),
        "grok16_ready": grok16.get("ready", False),
        "fieldc_ready": bin_path is not None,
        "forge_log_bytes": FORGE_LOG.stat().st_size if FORGE_LOG.is_file() else 0,
        "rtx_file_count": rtx_files,
        "cmake_cache": (RTX_BUILD / "CMakeCache.txt").is_file(),
        "makefile": (RTX_BUILD / "Makefile").is_file(),
        "running": running,
        "procs": _procs(),
        "tail": tail,
        "queen_forge": str(QUEEN / "lib" / "queen-forge.py"),
        "grok16": grok16,
        "fieldc": _fieldc_status(rtx_binary=bin_path),
    }


def field_compiler_status() -> dict[str, Any]:
    doc = load_doctrine()
    forge = forge_posture()
    grok16 = forge.get("grok16") or _grok16_layer()
    fieldc = forge.get("fieldc") or _fieldc_status(rtx_binary=_find_rtx_binary())
    stoard: dict[str, Any] = {}
    try:
        from zocr_eye_stoard import stoard_for_field_compiler
        stoard = stoard_for_field_compiler()
    except ImportError:
        pass
    return {
        "schema": "zocr-field-compiler-status/v1",
        "ts": _ts(),
        "rule": doc.get("rule"),
        "mandate_id": doc.get("mandate_id"),
        "grok16": grok16,
        "fieldc": fieldc,
        "stoard": stoard,
        "forge": {k: v for k, v in forge.items() if k not in ("grok16", "fieldc", "tail")},
        "ready": bool(grok16.get("ready_rtx")) and bool(fieldc.get("rtx_ready") or grok16.get("ready")),
        "probe": f"python3 {QUEEN / 'lib' / 'queen-forge.py'} compiler_probe",
    }


def field_compiler_doctrine() -> dict[str, Any]:
    doc = load_doctrine()
    doc = {**doc, "ts": _ts(), "status": field_compiler_status()}
    return doc


def probe_compilers(*, timeout: int = 90) -> dict[str, Any]:
    """Bounded refresh via Queen Forge compiler_probe."""
    forge_py = QUEEN / "lib" / "queen-forge.py"
    if not forge_py.is_file():
        return {"ok": False, "error": "queen_forge_missing", "path": str(forge_py)}
    env = {
        **os.environ,
        "SG_ROOT": str(SG),
        "QUEEN_ROOT": str(QUEEN),
        "GROK16_ROOT": str(GROK16),
    }
    try:
        proc = subprocess.run(
            [sys.executable, str(forge_py), "run", "compiler_probe"],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            cwd=str(QUEEN),
        )
        payload: dict[str, Any] = {}
        if proc.stdout.strip():
            try:
                payload = json.loads(proc.stdout)
            except json.JSONDecodeError:
                payload = {"raw": proc.stdout[-800:]}
        ok = proc.returncode == 0 and payload.get("ok", proc.returncode == 0)
        stoard_witness = None
        if ok:
            try:
                from zocr_eye_stoard import witness_compiler
                stoard_witness = witness_compiler(reason="compiler_probe")
            except ImportError:
                pass
        return {
            "ok": ok,
            "forge": payload,
            "stoard_witness": stoard_witness,
            "status": field_compiler_status(),
            "stderr": (proc.stderr or "")[-400:] or None,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "probe_timeout", "status": field_compiler_status()}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower()
    if cmd in ("status", "json"):
        print(json.dumps(field_compiler_status(), indent=2))
        return 0
    if cmd == "doctrine":
        print(json.dumps(field_compiler_doctrine(), indent=2))
        return 0
    if cmd == "forge":
        print(json.dumps(forge_posture(), indent=2))
        return 0
    if cmd == "probe":
        print(json.dumps(probe_compilers(), indent=2))
        return 0
    print(json.dumps({
        "error": "usage: zocr_field_compiler.py [status|doctrine|forge|probe]",
    }, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())