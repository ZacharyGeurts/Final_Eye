"""Final_Eye internal tester — factual live snapshot for 1.0 release validation."""
from __future__ import annotations

import json
import os
import platform
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from zocr_product import product_info
from zocr_session import log_event

_ROOT = Path(__file__).resolve().parent
_BENCH_PATH = _ROOT / "data" / "zocrsm1-benchmark.json"
_MATRIX_PATH = _ROOT / "data" / "release-test-matrix.json"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _label(value: Any, *, kind: str = "implemented", source: str = "") -> dict[str, Any]:
    return {"value": value, "label": kind, "source": source or None}


def _safe(fn: Callable[[], Any], default: Any = None) -> Any:
    try:
        return fn()
    except Exception as exc:
        return {"error": str(exc)[:200], "_fallback": default}


def _subsystem(name: str, fn: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    t0 = time.perf_counter()
    data = _safe(fn, {})
    ms = round((time.perf_counter() - t0) * 1000, 2)
    ok = not (isinstance(data, dict) and data.get("error"))
    return {"id": name, "ok": ok, "latency_ms": ms, "data": data}


def _load_benchmark_cache() -> dict[str, Any]:
    try:
        return json.loads(_BENCH_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _hostess7_probe() -> dict[str, Any]:
    h7 = Path(os.environ.get("HOSTESS7_ROOT", str(_ROOT.parent / "Hostess7")))
    script = h7 / "Hostess7.sh"
    return {
        "root": str(h7),
        "script_present": script.is_file(),
        "executable": script.is_file() and os.access(script, os.X_OK),
        "label": _label(script.is_file(), kind="implemented", source="filesystem"),
    }


def _queen_probe() -> dict[str, Any]:
    queen = Path(os.environ.get("QUEEN_ROOT", str(_ROOT.parent / "NewLatest" / "Queen")))
    forge = queen / "lib" / "queen-forge.py"
    return {
        "root": str(queen),
        "forge_present": forge.is_file(),
        "label": _label(forge.is_file(), kind="implemented", source="filesystem"),
    }


def _grok16_probe() -> dict[str, Any]:
    from zocr_grok16 import grok16_status, grok16_eye_tune
    st = grok16_status()
    tune = grok16_eye_tune(mode="war", eye_profile="raptor")
    return {
        "status": st,
        "field_opt_tune": tune,
        "g16_ready": _label(st.get("ready") or st.get("ready_rtx"), kind="measured", source="grok16_status"),
        "cxx_std": _label(st.get("cxx_std"), kind="doctrine", source="Grok16/data"),
    }


def _security_probe() -> dict[str, Any]:
    from zocr_security import security_model, security_status, verify_code_seal, verify_gvc1_integrity
    seal = verify_code_seal()
    gvc1 = verify_gvc1_integrity()
    return {
        "status": security_status(),
        "model": security_model(),
        "code_seal": seal,
        "gvc1": gvc1,
        "seal_ok": _label(seal.get("ok"), kind="measured", source="zocr_security.verify_code_seal"),
        "gvc1_ok": _label(gvc1.get("ok"), kind="measured", source="zocr_security.verify_gvc1_integrity"),
    }


def _video_probe() -> dict[str, Any]:
    from zocr_video import video_status
    st = video_status()
    bench = _load_benchmark_cache()
    return {
        "live": st,
        "benchmark_cache": bench.get("summary"),
        "profiles_cached": [p.get("profile") for p in (bench.get("profiles") or [])],
        "format": _label(st.get("format"), kind="implemented", source="zocr_video"),
        "best_emit_fps": _label(
            (bench.get("summary") or {}).get("best_emit_fps"),
            kind="measured",
            source="data/zocrsm1-benchmark.json",
        ),
    }


def _robotics_probe() -> dict[str, Any]:
    from zocr_robotics import robotics_doctrine
    from zocr_eye import final_eyeball_status, list_final_modes
    final = final_eyeball_status()
    modes = list_final_modes()
    doc = robotics_doctrine()
    return {
        "doctrine": doc,
        "final_eyeball": final,
        "modes": [m["id"] for m in modes],
        "active_mode": _label(final.get("active_mode"), kind="measured", source="final_eyeball_state"),
        "war_mode": _label("war" in {m["id"] for m in modes}, kind="implemented", source="final-eyeball.json"),
        "dishes_mode": _label("dishes" in {m["id"] for m in modes}, kind="implemented", source="final-eyeball.json"),
    }


def _entity_probe() -> dict[str, Any]:
    from zocr_entity_eyeball import entity_weapon_racks, twin_eyeball_status
    twins = twin_eyeball_status()
    racks = entity_weapon_racks()
    return {
        "twins": twins,
        "racks": racks,
        "weapons_total": _label(racks.get("weapons_total"), kind="measured", source="entity-eyeball.json"),
    }


def _heaven_hell_probe() -> dict[str, Any]:
    from zocr_heaven_hell import heaven_hell_truth_status
    return heaven_hell_truth_status()


def _trust_probe() -> dict[str, Any]:
    from zocr_trust import trust_network_status, verify_trust_mesh
    return {"network": trust_network_status(), "mesh": verify_trust_mesh()}


def _compiler_probe() -> dict[str, Any]:
    from zocr_field_compiler import field_compiler_status, probe_compilers
    return {"status": field_compiler_status(), "probe": probe_compilers()}


def _sovereign_probe() -> dict[str, Any]:
    from zocr_sovereign_time import sovereign_time_status
    return sovereign_time_status(seal=False)


def _hud_probe() -> dict[str, Any]:
    from zocr_hud import hud_status, list_modules
    return {"status": hud_status(), "module_count": len(list_modules())}


def _zac_probe() -> dict[str, Any]:
    from zocr_zac import zac_status
    return zac_status()


def _environment() -> dict[str, Any]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cwd": str(_ROOT),
        "sg_root": str(_ROOT.parent),
        "assist": os.environ.get("FINAL_EYE_ASSIST", "0"),
        "low_end": os.environ.get("FINAL_EYE_LOW_END", "0"),
        "mandate_off": os.environ.get("ZOCR_MANDATE_OFF", "0"),
    }


def tester_snapshot(*, include_slow: bool = False) -> dict[str, Any]:
    """Single poll — all subsystems with factual labels."""
    product = product_info()
    subsystems = [
        _subsystem("security", _security_probe),
        _subsystem("video", _video_probe),
        _subsystem("robotics", _robotics_probe),
        _subsystem("grok16", _grok16_probe),
        _subsystem("field_compiler", _compiler_probe),
        _subsystem("entity_eyeballs", _entity_probe),
        _subsystem("heaven_hell_truth", _heaven_hell_probe),
        _subsystem("trust", _trust_probe),
        _subsystem("sovereign_time", _sovereign_probe),
        _subsystem("hud", _hud_probe),
        _subsystem("zac", _zac_probe),
        _subsystem("hostess7", _hostess7_probe),
        _subsystem("queen", _queen_probe),
    ]
    ok_count = sum(1 for s in subsystems if s.get("ok"))
    return {
        "schema": "final-eye-tester-snapshot/v1",
        "ts": _ts(),
        "product": product,
        "environment": _environment(),
        "summary": {
            "subsystems_ok": ok_count,
            "subsystems_total": len(subsystems),
            "health_pct": round(100 * ok_count / max(1, len(subsystems)), 1),
        },
        "subsystems": subsystems,
        "label_legend": {
            "implemented": "Code path exists and responds",
            "measured": "Numeric value from benchmark or live probe",
            "doctrine": "Declared policy from manifest/Field stack",
            "metaphor": "NEXUS/Queen metaphor layer — not literal hardware",
        },
        "include_slow": include_slow,
    }


def _matrix_cases() -> list[dict[str, Any]]:
    return [
        {
            "id": "product_1_0",
            "group": "release",
            "label": "Product version 1.0.0",
            "kind": "implemented",
            "check": lambda: product_info().get("version") == "1.0.0",
        },
        {
            "id": "code_seal",
            "group": "security",
            "label": "Code seal verifies",
            "kind": "measured",
            "check": lambda: __import__("zocr_security").verify_code_seal().get("ok") is True,
        },
        {
            "id": "gvc1_envelope",
            "group": "security",
            "label": "GVC1 envelope round-trip",
            "kind": "measured",
            "check": lambda: __import__("zocr_security").verify_gvc1_integrity().get("ok") is True,
        },
        {
            "id": "war_mode",
            "group": "robotics",
            "label": "War mode listed",
            "kind": "implemented",
            "check": lambda: "war" in {m["id"] for m in __import__("zocr_eye", fromlist=["list_final_modes"]).list_final_modes()},
        },
        {
            "id": "dishes_mode",
            "group": "robotics",
            "label": "Dishes mode listed",
            "kind": "implemented",
            "check": lambda: "dishes" in {m["id"] for m in __import__("zocr_eye", fromlist=["list_final_modes"]).list_final_modes()},
        },
        {
            "id": "silent_capture_policy",
            "group": "security",
            "label": "Silent capture policy defined",
            "kind": "doctrine",
            "check": lambda: bool(__import__("zocr_security", fromlist=["silent_capture_policy"]).silent_capture_policy().get("silent_by_default")),
        },
        {
            "id": "grok16_profile",
            "group": "compiler",
            "label": "Grok16 field_opt profile",
            "kind": "implemented",
            "check": lambda: "field_opt" in (__import__("zocr_grok16", fromlist=["grok16_status"]).grok16_status().get("profiles") or []),
        },
        {
            "id": "twin_eyeballs",
            "group": "entity",
            "label": "Twin entity eyeballs",
            "kind": "implemented",
            "check": lambda: __import__("zocr_entity_eyeball", fromlist=["twin_eyeball_status"]).twin_eyeball_status().get("schema") == "zocr-twin-eyeball/v1",
        },
        {
            "id": "heaven_hell",
            "group": "truth",
            "label": "Heaven/Hell parameters loaded",
            "kind": "implemented",
            "check": lambda: __import__("zocr_heaven_hell", fromlist=["load_spec"]).load_spec().get("schema") == "zocr-heaven-hell-truth/v1",
        },
        {
            "id": "zac_pack",
            "group": "integration",
            "label": "ZAC pack round-trip",
            "kind": "measured",
            "check": lambda: __import__("zocr_zac", fromlist=["zac_self_test"]).zac_self_test().get("ok") is True,
        },
        {
            "id": "hud_manifest",
            "group": "ui",
            "label": "HUD closed manifest",
            "kind": "implemented",
            "check": lambda: len(__import__("zocr_hud", fromlist=["list_modules"]).list_modules()) >= 16,
        },
        {
            "id": "grkmf_format",
            "group": "codec",
            "label": "GRKMF1 proprietary format",
            "kind": "implemented",
            "check": lambda: __import__("zocr_grkmf", fromlist=["grkmf"]).grkmf.FORMAT_ID == "GRKMF1",
        },
        {
            "id": "not_mpeg",
            "group": "codec",
            "label": "Not MPEG — doctrine",
            "kind": "doctrine",
            "check": lambda: product_info().get("stack", {}).get("codec") == "GVC1",
        },
        {
            "id": "sovereign_witness",
            "group": "field",
            "label": "Sovereign time witness",
            "kind": "measured",
            "check": lambda: bool(__import__("zocr_sovereign_time", fromlist=["sovereign_time_status"]).sovereign_time_status(seal=False).get("sealed_mono_ns")),
        },
    ]


def tester_matrix(*, persist: bool = True) -> dict[str, Any]:
    """Run release test matrix — factual pass/fail per case."""
    cases_out: list[dict[str, Any]] = []
    passed = 0
    for case in _matrix_cases():
        t0 = time.perf_counter()
        try:
            ok = bool(case["check"]())
            err = None
        except Exception as exc:
            ok = False
            err = str(exc)[:200]
        ms = round((time.perf_counter() - t0) * 1000, 2)
        row = {
            "id": case["id"],
            "group": case["group"],
            "label": case["label"],
            "kind": case["kind"],
            "ok": ok,
            "latency_ms": ms,
            "error": err,
        }
        cases_out.append(row)
        if ok:
            passed += 1

    doc = {
        "schema": "final-eye-test-matrix/v1",
        "ts": _ts(),
        "version": product_info().get("version"),
        "passed": passed,
        "total": len(cases_out),
        "pass_pct": round(100 * passed / max(1, len(cases_out)), 1),
        "cases": cases_out,
    }
    if persist:
        _MATRIX_PATH.parent.mkdir(parents=True, exist_ok=True)
        _MATRIX_PATH.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    log_event("tester_matrix", ok=passed == len(cases_out), passed=passed, total=len(cases_out))
    return doc


def tester_full(*, run_matrix: bool = True) -> dict[str, Any]:
    snap = tester_snapshot()
    matrix = tester_matrix() if run_matrix else None
    all_ok = matrix and matrix.get("passed") == matrix.get("total")
    return {
        "schema": "final-eye-tester-full/v1",
        "ts": _ts(),
        "release_ready": bool(all_ok and snap.get("summary", {}).get("health_pct", 0) >= 80),
        "snapshot": snap,
        "matrix": matrix,
    }


def main() -> int:
    import sys
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "full").strip().lower()
    if cmd == "snapshot":
        print(json.dumps(tester_snapshot(), indent=2))
        return 0
    if cmd == "matrix":
        print(json.dumps(tester_matrix(), indent=2))
        return 0
    print(json.dumps(tester_full(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())