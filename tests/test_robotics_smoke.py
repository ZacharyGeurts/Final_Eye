#!/usr/bin/env python3
"""Final_Eye v0.9 — low-end smoke only (no 4K/16K hammer). Benchmarks: ./tests/run_tests.sh"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("FINAL_EYE_LOW_END", "1")
os.environ.setdefault("FINAL_EYE_COOL", "1")
os.environ.setdefault("FINAL_EYE_ASSIST", "1")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
GMF = ROOT / "GrokMediaFormat"
if GMF.is_dir():
    sys.path.insert(0, str(GMF))


def test_product_version():
    from zocr_product import product_info
    p = product_info()
    assert p["product"] == "Final_Eye"
    assert p["version"] == "1.0.0"


def test_mandate_loads():
    from zocr_field import load_mandate
    assert load_mandate().get("mandate_id")


def test_final_eyeball_modes():
    from zocr_eye import list_final_modes
    assert "war" in {m["id"] for m in list_final_modes()}


def test_twin_entity_eyeballs():
    from zocr_entity_eyeball import (
        auto_weapon_for_threat,
        entity_weapon_racks,
        entity_weapons,
        twin_eyeball_status,
        truth_forward,
    )

    twins = twin_eyeball_status()
    assert twins.get("schema") == "zocr-twin-eyeball/v1"
    assert twins.get("living", {}).get("entity") == "Vita"
    assert twins.get("truth", {}).get("entity") == "Veritas"
    assert twins.get("truth", {}).get("always_forward") is True
    weapons = entity_weapons()
    assert len(weapons) >= 37
    racks = entity_weapon_racks()
    assert racks.get("weapons_total", 0) >= 37
    assert "thermo" in (racks.get("racks") or {})
    assert "nexus" in (racks.get("racks") or {})
    assert any(w.get("id") == "forward_truth" for w in weapons)
    assert any(w.get("id") == "queen_weaponize" for w in weapons)
    assert auto_weapon_for_threat("provenance_mismatch") == "autokill_certain"
    assert auto_weapon_for_threat("rf_jam") == "rf_jam_slice"
    fwd = truth_forward(fire_weapons=False)
    assert fwd.get("always_forward") is True


def test_eyeball_weaponize_posture():
    from zocr_entity_eyeball import fire_entity_weapon, weaponize_eyeball

    w = weaponize_eyeball(mode="dishes")
    assert w.get("schema") == "zocr-eyeball-weaponize/v1"
    assert w.get("weapons_total", 0) >= 37
    assert w.get("racks", 0) >= 8
    cool = fire_entity_weapon("cool_gate")
    assert cool.get("ok") is True
    assert cool.get("rack") == "thermo"


def test_eye_teach_weapon_authority():
    from zocr_entity_eyeball import (
        eye_teach,
        eye_targets_know,
        eye_understand_target,
        eye_weapon_authority,
        fire_entity_weapon,
    )

    auth = eye_weapon_authority()
    assert auth.get("schema") == "zocr-eye-weapon-authority/v1"
    assert auth.get("independent") is True
    assert auth.get("remote_puppet") is False
    assert auth.get("weapons_total", 0) >= 37
    assert auth.get("speak")

    targets = eye_targets_know()
    assert targets.get("schema") == "zocr-eye-targets/v1"
    assert targets.get("target_count", 0) > 0
    assert "provenance_mismatch" in (targets.get("targets_known") or [])
    assert targets.get("threat_weapon_map")

    understood = eye_understand_target("provenance_mismatch")
    assert understood.get("schema") == "zocr-eye-understand-target/v1"
    assert understood.get("weapon_selected") == "autokill_certain"
    assert understood.get("independent") is True

    lesson = eye_teach(lesson="authority")
    assert lesson.get("schema") == "zocr-eye-teach/v1"
    assert lesson.get("voice") == "Teach"
    assert lesson.get("lesson") == "authority"
    assert lesson.get("speak")

    auto_fire = fire_entity_weapon("auto", threat="provenance_mismatch")
    assert auto_fire.get("ok") is True
    assert auto_fire.get("weapon") == "autokill_certain"
    assert auto_fire.get("understood_target", {}).get("threat") == "provenance_mismatch"


def test_eyeball_sovereign_time_and_redundancy():
    from zocr_eye import eye_status, final_eyeball_status
    from zocr_sovereign_time import eyeball_time_and_redundancy

    witness = eyeball_time_and_redundancy(seal=True)
    st = witness["sovereign_time"]
    rd = witness["redundancy"]
    assert st.get("always") is True
    assert st.get("sealed_mono_ns")
    assert st.get("verdict") == "USER_OK"
    assert rd.get("always") is True
    assert rd.get("paths_total", 0) >= 5

    eye = eye_status()
    final = final_eyeball_status()
    assert eye.get("sovereign_time", {}).get("always") is True
    assert eye.get("redundancy", {}).get("always") is True
    assert final.get("sovereign_time", {}).get("always") is True
    assert final.get("redundancy", {}).get("paths_total", 0) >= 5


def test_code_seal():
    from zocr_security import verify_code_seal
    v = verify_code_seal()
    assert v.get("ok") is True, v


def test_grkmf_tune_lock_low_end():
    from grkmf.tune import resolve, tune_apply, tune_reset
    tune_reset()
    r = resolve("combat")
    assert r.get("preset") == "combat" or r.get("mode") == "combat"
    t = tune_apply(fps=8, width=640, height=480, mode="combat")
    assert t["width"] == 640
    assert t["fps"] == 8
    tune_reset()


def test_assist_contract_posture():
    from zocr_contract import acquire, contract_status, release
    st = contract_status()
    assert st["posture"] == "assistive"
    assert acquire("look", on_demand=True)["ok"]
    s1 = acquire("stream", slot=True)
    assert s1["ok"]
    s2 = acquire("stream", slot=True)
    assert not s2["ok"]
    release("stream", slot=True)


def test_grkmf_envelope_only():
    from grkmf.envelope import seal_payload, unpack_envelope
    sealed = seal_payload(b"low-end-bench")
    payload, _meta = unpack_envelope(sealed) or (None, {})
    assert payload == b"low-end-bench"


def test_field_compiler_wired():
    from zocr_field_compiler import field_compiler_status, load_doctrine
    from zocr_grok16 import grok16_eye_tune, grok16_profile_for_mode, grok16_status

    doc = load_doctrine()
    assert doc.get("primary", {}).get("product") == "Grok16"
    assert doc.get("layers", {}).get("grok16")

    g = grok16_status()
    assert g.get("schema") == "zocr-grok16-status/v1"
    assert g.get("cxx_std") == "gnu++26"
    assert "field_opt" in (g.get("profiles") or [])

    tune = grok16_eye_tune(mode="war", eye_profile="raptor")
    assert tune.get("grok16_profile") == "vulkan_rtx"
    assert grok16_profile_for_mode("dishes") == "ai"

    st = field_compiler_status()
    assert st.get("schema") == "zocr-field-compiler-status/v1"
    assert st.get("grok16", {}).get("cxx_std") == "gnu++26"
    assert "forge" in st


def test_eyeball_grok16_witness():
    from zocr_eye import eye_status, spectrum_doctrine

    eye = eye_status()
    assert eye.get("field_compiler", {}).get("field_compiler") == "Grok16"
    assert eye.get("grok16", {}).get("grok16_profile")
    doc = spectrum_doctrine()
    assert doc.get("grok16_profile")
    assert doc.get("field_compiler", {}).get("cxx_std") == "gnu++26"


def test_heaven_hell_truth_parameters():
    from zocr_entity_eyeball import fire_entity_weapon, truth_eyeball_status
    from zocr_heaven_hell import (
        heaven_hell_doctrine,
        heaven_hell_truth_status,
        heaven_pass,
        hell_rip,
        load_spec,
        threat_soul_map,
        truth_doctrine_status,
    )

    spec = load_spec()
    assert spec.get("schema") == "zocr-heaven-hell-truth/v1"
    assert spec.get("truth", {}).get("truth_adapt_floor") == 58
    assert spec.get("heaven_hell", {}).get("hostility_priority") == "hell_first"
    assert len(spec.get("sources") or []) >= 8

    doctrine = heaven_hell_doctrine()
    assert doctrine.get("truth", {}).get("noise_ratio") == 0.94
    kit_ids = [p.get("id") for p in (doctrine.get("heaven_hell", {}).get("hell_kit_profiles") or [])]
    assert "hell_rip" in kit_ids

    gates = truth_doctrine_status()
    assert gates.get("schema") == "zocr-truth-doctrine/v1"
    assert len(gates.get("truth_gates") or []) == 4

    status = heaven_hell_truth_status()
    assert status.get("schema") == "zocr-heaven-hell-truth/v1"
    assert status.get("heaven_hell", {}).get("hostility_priority") == "hell_first"
    assert "heaven_count" in status.get("heaven_hell", {})

    assert threat_soul_map("trust_breach")["soul_side"] == "hell"
    assert heaven_pass().get("ok") is True
    rip = hell_rip(threat="trust_breach", fire_offense=False)
    assert rip.get("soul_side") == "hell"

    truth = truth_eyeball_status()
    assert truth.get("truth_doctrine", {}).get("truth_adapt_floor") == 58
    assert truth.get("heaven_hell", {}).get("hostility_priority") == "hell_first"

    heaven_w = fire_entity_weapon("heaven_pass")
    assert heaven_w.get("ok") is True
    hell_w = fire_entity_weapon("hell_rip", threat="trust_breach")
    assert hell_w.get("ok") is True


def test_hud_whitelist_rejects_bullshit():
    from zocr_hud import hud_status, list_modules, request_hud

    mods = {m["id"] for m in list_modules()}
    assert "spectrum" in mods
    assert len(mods) >= 16
    assert "heaven_hell_truth" in mods

    bad_mod = request_hud({"action": "enable", "module": "evil_inject"})
    assert bad_mod.get("ok") is False
    assert bad_mod.get("error") == "unknown_module"

    bad_key = request_hud({"action": "toggle", "module": "spectrum", "script": "alert(1)"})
    assert bad_key.get("ok") is False
    assert bad_key.get("error") == "forbidden_key"
    assert bad_key.get("key") == "script"

    bad_action = request_hud({"action": "eval", "module": "spectrum"})
    assert bad_action.get("ok") is False
    assert bad_action.get("error") == "forbidden_action"

    st = hud_status()
    assert st.get("schema") == "zocr-hud-status/v1"
    assert st.get("posture", {}).get("rule")
    assert "spectrum" in (st.get("posture", {}).get("active") or [])


def main() -> int:
    tests = [
        test_product_version,
        test_mandate_loads,
        test_final_eyeball_modes,
        test_twin_entity_eyeballs,
        test_eyeball_weaponize_posture,
        test_eye_teach_weapon_authority,
        test_eyeball_sovereign_time_and_redundancy,
        test_code_seal,
        test_grkmf_tune_lock_low_end,
        test_assist_contract_posture,
        test_grkmf_envelope_only,
        test_field_compiler_wired,
        test_eyeball_grok16_witness,
        test_heaven_hell_truth_parameters,
        test_hud_whitelist_rejects_bullshit,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"ok {t.__name__}")
        except Exception as exc:
            failed += 1
            print(f"FAIL {t.__name__}: {exc}", file=sys.stderr)
    print(json.dumps({"tests": len(tests), "failed": failed, "low_end": True}))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())