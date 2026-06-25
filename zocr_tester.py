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


def _copilot_probe() -> dict[str, Any]:
    from zocr_copilot import copilot_status
    c = copilot_status()
    hold = c.get("hold") or {}
    return {
        "integrity_pct": hold.get("integrity_pct"),
        "structure_held": hold.get("structure_held"),
        "sources_ok": hold.get("sources_ok"),
        "sources_total": hold.get("sources_total"),
        "speak": (c.get("speak") or "")[:120],
    }


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
        _subsystem("copilot", _copilot_probe),
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
            "id": "product_version",
            "group": "release",
            "label": f"Product version {product_info().get('version')}",
            "kind": "implemented",
            "check": lambda: product_info().get("version")
            == (_ROOT / "VERSION").read_text(encoding="utf-8").strip(),
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
            "id": "field_compile_c",
            "group": "compiler",
            "label": "Grok16 g16 C smoke (vision_probe.c)",
            "kind": "measured",
            "check": lambda: __import__("zocr_field_compile", fromlist=["compile_c_smoke"]).compile_c_smoke().get("ok") is True,
        },
        {
            "id": "field_compile_kernel",
            "group": "compiler",
            "label": "Grok16 g++16 field_dispatch kernel",
            "kind": "measured",
            "check": lambda: __import__("zocr_field_compile", fromlist=["compile_vision_kernel"]).compile_vision_kernel().get("ok") is True,
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
    matrix = tester_matrix(persist=False) if run_matrix else None
    all_ok = matrix and matrix.get("passed") == matrix.get("total")
    return {
        "schema": "final-eye-tester-full/v1",
        "ts": _ts(),
        "release_ready": bool(all_ok and snap.get("summary", {}).get("health_pct", 0) >= 80),
        "snapshot": snap,
        "matrix": matrix,
        "ops": ops_dashboard(include_matrix=False),
    }


def _load_entity_state() -> dict[str, Any]:
    path = _ROOT / "data" / "entity-eyeball-state.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _recent_forward(n: int = 8) -> list[dict[str, Any]]:
    ledger = _ROOT / "data" / "truth-forward-ledger.jsonl"
    if not ledger.is_file():
        return []
    try:
        lines = ledger.read_text(encoding="utf-8").strip().splitlines()[-n:]
        return [json.loads(ln) for ln in lines if ln.strip()]
    except (OSError, json.JSONDecodeError):
        return []


def ops_dashboard(*, include_matrix: bool = True) -> dict[str, Any]:
    """Single unified ops payload — AI & robotics first, all details."""
    product = product_info()

    def _section(name: str, fn: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        t0 = time.perf_counter()
        data = _safe(fn, {})
        return {
            "id": name,
            "ok": not (isinstance(data, dict) and data.get("error")),
            "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
            "data": data,
        }

    sections: dict[str, Any] = {}

    sections["robotics"] = _section("robotics", lambda: {
        "doctrine": __import__("zocr_robotics", fromlist=["robotics_doctrine"]).robotics_doctrine(),
        "final_eyeball": __import__("zocr_eye", fromlist=["final_eyeball_status"]).final_eyeball_status(),
        "final_modes": __import__("zocr_eye", fromlist=["list_final_modes"]).list_final_modes(),
        "eye": __import__("zocr_eye", fromlist=["eye_status"]).eye_status(),
        "rig": __import__("zocr_stereo", fromlist=["rig_status"]).rig_status(),
        "rig_presets": __import__("zocr_stereo", fromlist=["list_presets"]).list_presets(),
        "stream": __import__("zocr_stream", fromlist=["stream_status"]).stream_status(),
        "video": __import__("zocr_video", fromlist=["video_status"]).video_status(),
        "video_format": __import__("zocr_video", fromlist=["format_doctrine"]).format_doctrine(),
        "contract": __import__("zocr_contract", fromlist=["contract_status"]).contract_status(),
        "benchmark": _load_benchmark_cache().get("summary"),
        "arm_endpoints": {
            "war": 'POST /api/robotics/arm {"mode":"war","start_stream":false}',
            "dishes": 'POST /api/robotics/arm {"mode":"dishes"}',
            "tune": 'POST /api/video/tune {"fps":8,"width":1280}',
            "ai_tune": "POST /api/video/ai-tune",
        },
    })

    sections["ai"] = _section("ai", lambda: {
        "grok16": __import__("zocr_grok16", fromlist=["grok16_status"]).grok16_status(),
        "grok16_tune_war": __import__("zocr_grok16", fromlist=["grok16_eye_tune"]).grok16_eye_tune(mode="war", eye_profile="raptor"),
        "grok16_tune_patrol": __import__("zocr_grok16", fromlist=["grok16_eye_tune"]).grok16_eye_tune(mode="patrol", eye_profile="bird"),
        "field_compiler": __import__("zocr_field_compiler", fromlist=["field_compiler_status"]).field_compiler_status(),
        "compiler_probe": __import__("zocr_field_compiler", fromlist=["probe_compilers"]).probe_compilers(),
        "field_compile": __import__("zocr_field_compile", fromlist=["field_compile_status"]).field_compile_status(),
        "field_compile_endpoints": {
            "status": "GET /api/field/compile",
            "c_kernel": "GET /api/field/compile?mode=c",
            "optimize": "GET /api/field/compile/optimize",
            "full": "GET /api/field/compile/full",
        },
        "neural": __import__("zocr_neural", fromlist=["neural_status"]).neural_status(),
        "neural_verify": __import__("zocr_neural", fromlist=["verify_network_seal"]).verify_network_seal(),
        "grkmf": (lambda g=__import__("zocr_grkmf", fromlist=["grkmf"]).grkmf: {
            "format": g.FORMAT_ID,
            "codec": g.CODEC_ID,
        })(),
        "ai_context": __import__("zocr_ai", fromlist=["ai_context"]).ai_context(),
        "robotics_context": __import__("zocr_ai", fromlist=["robotics_context"]).robotics_context(),
    })

    sections["weapons"] = _section("weapons", lambda: {
        "racks": __import__("zocr_entity_eyeball", fromlist=["entity_weapon_racks"]).entity_weapon_racks(),
        "weapons": __import__("zocr_entity_eyeball", fromlist=["entity_weapons"]).entity_weapons(),
        "doctrine": __import__("zocr_entity_eyeball", fromlist=["entity_doctrine"]).entity_doctrine(),
        "state": _load_entity_state(),
        "threat_weapon_map": (
            __import__("zocr_entity_eyeball", fromlist=["load_entity_spec"]).load_entity_spec().get("forward", {}).get("threat_weapon_map")
        ),
        "lie_markers": (
            __import__("zocr_entity_eyeball", fromlist=["load_entity_spec"]).load_entity_spec().get("forward", {}).get("lie_markers")
        ),
        "fire_endpoint": 'POST /api/eye/weapons/fire {"weapon":"hell_rip","threat":"trust_breach"}',
        "weaponize_endpoint": 'POST /api/eye/weaponize {"mode":"war"}',
    })

    sections["entity"] = _section("entity", lambda: {
        "twins": __import__("zocr_entity_eyeball", fromlist=["twin_eyeball_status"]).twin_eyeball_status(),
        "living": __import__("zocr_entity_eyeball", fromlist=["living_eyeball_status"]).living_eyeball_status(),
        "truth": __import__("zocr_entity_eyeball", fromlist=["truth_eyeball_status"]).truth_eyeball_status(),
        "recent_forward": _recent_forward(),
        "sovereign_redundancy": __import__("zocr_sovereign_time", fromlist=["eyeball_time_and_redundancy"]).eyeball_time_and_redundancy(seal=False),
    })

    sections["vision"] = _section("vision", lambda: {
        "preserve": __import__("zocr_preserve", fromlist=["preserve_status"]).preserve_status(),
        "preserve_doctrine": __import__("zocr_preserve", fromlist=["threat_doctrine"]).threat_doctrine(),
        "offense": __import__("zocr_offense", fromlist=["offense_status"]).offense_status(),
        "offense_doctrine": __import__("zocr_offense", fromlist=["offense_doctrine"]).offense_doctrine(),
        "pattern": __import__("zocr_pattern", fromlist=["pattern_status"]).pattern_status(),
        "pattern_doctrine": __import__("zocr_pattern", fromlist=["pattern_doctrine"]).pattern_doctrine(),
        "vigilance": __import__("zocr_vigilance", fromlist=["vigilance_status"]).vigilance_status(),
        "additives": __import__("zocr_additives", fromlist=["additives_status"]).additives_status(),
        "spectrum": __import__("zocr_eye", fromlist=["spectrum_doctrine"]).spectrum_doctrine(),
        "ocular_profiles": __import__("zocr_eye", fromlist=["list_profiles"]).list_profiles(),
        "session": __import__("zocr_status", fromlist=["live_status"]).live_status(),
    })

    sections["truth"] = _section("truth", lambda: {
        "heaven_hell": __import__("zocr_heaven_hell", fromlist=["heaven_hell_truth_status"]).heaven_hell_truth_status(),
        "trust": __import__("zocr_trust", fromlist=["trust_network_status"]).trust_network_status(),
        "trust_mesh": __import__("zocr_trust", fromlist=["verify_trust_mesh"]).verify_trust_mesh(),
        "hostess7": __import__("zocr_trust", fromlist=["hostess7_bridge"]).hostess7_bridge(),
        "copilot": __import__("zocr_copilot", fromlist=["copilot_status"]).copilot_status(),
    })

    sections["field"] = _section("field", lambda: {
        "mandate": __import__("zocr_field", fromlist=["load_mandate"]).load_mandate(),
        "chain_verify": __import__("zocr_field", fromlist=["verify_chain"]).verify_chain(),
        "kill": __import__("zocr_kill", fromlist=["kill_status"]).kill_status(),
        "security": __import__("zocr_security", fromlist=["security_status"]).security_status(),
        "code_seal": __import__("zocr_security", fromlist=["verify_code_seal"]).verify_code_seal(),
        "gvc1": __import__("zocr_security", fromlist=["verify_gvc1_integrity"]).verify_gvc1_integrity(),
        "sovereign_time": __import__("zocr_sovereign_time", fromlist=["sovereign_time_status"]).sovereign_time_status(seal=False),
        "hud": __import__("zocr_hud", fromlist=["hud_status"]).hud_status(),
        "hud_modules": __import__("zocr_hud", fromlist=["list_modules"]).list_modules(),
    })

    sections["integration"] = _section("integration", lambda: {
        "zac": __import__("zocr_zac", fromlist=["zac_status"]).zac_status(),
        "hostess7_root": str(Path(os.environ.get("HOSTESS7_ROOT", str(_ROOT.parent / "Hostess7")))),
        "hostess7_script": (Path(os.environ.get("HOSTESS7_ROOT", str(_ROOT.parent / "Hostess7"))) / "Hostess7.sh").is_file(),
        "queen_root": str(Path(os.environ.get("QUEEN_ROOT", str(_ROOT.parent / "NewLatest" / "Queen")))),
        "grok16_root": str(Path(os.environ.get("GROK16_ROOT", str(_ROOT.parent / "Grok16")))),
        "environment": _environment(),
    })

    priority = ["robotics", "ai", "weapons", "entity", "vision", "truth", "field", "integration"]
    ok_n = sum(1 for k in priority if sections.get(k, {}).get("ok"))

    return {
        "schema": "final-eye-ops-dashboard/v1",
        "ts": _ts(),
        "product": product,
        "priority": priority,
        "summary": {
            "sections_ok": ok_n,
            "sections_total": len(priority),
            "health_pct": round(100 * ok_n / len(priority), 1),
        },
        "sections": {k: sections[k] for k in priority if k in sections},
        "matrix": tester_matrix(persist=False) if include_matrix else None,
        "copilot_hold": __import__("zocr_copilot", fromlist=["hold_together"]).hold_together(),
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
    if cmd == "ops":
        print(json.dumps(ops_dashboard(), indent=2))
        return 0
    print(json.dumps(tester_full(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())