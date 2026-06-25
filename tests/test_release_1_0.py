#!/usr/bin/env python3
"""Final_Eye 0.9.9 release tests — security, matrix, ZAC, Grok16, war/dishes."""
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


def test_product_0_9_9():
    from zocr_product import product_info
    p = product_info()
    assert p["version"] == "0.9.9"
    assert p["product"] == "Final_Eye"


def test_security_gvc1_and_stream():
    from zocr_security import (
        decrypt_stream_payload,
        encrypt_stream_payload,
        security_model,
        silent_capture_policy,
        verify_gvc1_integrity,
        verify_operator_token,
        issue_operator_token,
    )
    gvc1 = verify_gvc1_integrity()
    assert gvc1.get("ok") is True, gvc1
    assert gvc1.get("tamper_rejected") is True
    enc = encrypt_stream_payload(b"war-mode-probe")
    assert enc.get("ok") is True
    dec = decrypt_stream_payload(enc["blob"])
    assert dec.get("ok") is True
    assert dec["payload"] == b"war-mode-probe"
    tok = issue_operator_token(subject="tester")
    assert verify_operator_token(tok["token"]).get("ok") is True
    pol = silent_capture_policy()
    assert pol.get("silent_by_default") is True
    model = security_model()
    assert "GVC1" in str(model.get("codec", {}))


def test_tester_matrix_all_pass():
    from zocr_tester import tester_matrix
    m = tester_matrix(persist=False)
    assert m.get("total", 0) >= 12
    failed = [c for c in m.get("cases", []) if not c.get("ok")]
    assert not failed, failed


def test_zac_roundtrip():
    from zocr_zac import zac_self_test
    r = zac_self_test()
    assert r.get("ok") is True, r


def test_grok16_field_opt():
    from zocr_grok16 import grok16_eye_tune, grok16_profile_for_mode, grok16_status
    st = grok16_status()
    assert st.get("schema") == "zocr-grok16-status/v1"
    assert "field_opt" in (st.get("profiles") or [])
    assert grok16_profile_for_mode("patrol") == "field_opt"
    tune = grok16_eye_tune(mode="patrol", eye_profile="bird")
    assert tune.get("grok16_profile") == "field_opt"
    assert tune.get("engine") == "cone_v2_field_opt"


def test_war_dishes_cycles():
    from zocr_entity_eyeball import weaponize_eyeball
    from zocr_robotics import arm_robotics

    war = arm_robotics("war", start_stream=False)
    assert war.get("ok") is True
    dishes = arm_robotics("dishes", start_stream=False)
    assert dishes.get("ok") is True
    w = weaponize_eyeball(mode="war")
    assert w.get("weapons_total", 0) >= 37


def test_copilot_foundations():
    from zocr_copilot import copilot_ask, copilot_status, hold_together, load_foundations

    spec = load_foundations()
    assert len(spec.get("sources") or []) >= 12
    hold = hold_together()
    assert hold.get("integrity_pct", 0) >= 50
    assert "pillars" in hold
    st = copilot_status()
    assert st.get("schema") == "final-eye-copilot/v1"
    ask = copilot_ask("what holds the code seal and trust mesh together")
    assert ask.get("ok") is True
    assert ask.get("answer")


def test_ops_dashboard_full():
    from zocr_tester import ops_dashboard
    ops = ops_dashboard(include_matrix=False)
    assert ops.get("schema") == "final-eye-ops-dashboard/v1"
    assert ops.get("priority", [])[0] == "robotics"
    weapons = (ops.get("sections") or {}).get("weapons", {}).get("data", {})
    assert len(weapons.get("weapons") or []) >= 37
    assert weapons.get("threat_weapon_map")


def test_tester_snapshot_schema():
    from zocr_tester import tester_snapshot
    snap = tester_snapshot()
    assert snap.get("schema") == "final-eye-tester-snapshot/v1"
    assert len(snap.get("subsystems", [])) >= 10


def main() -> int:
    tests = [
        test_product_0_9_9,
        test_security_gvc1_and_stream,
        test_tester_matrix_all_pass,
        test_zac_roundtrip,
        test_grok16_field_opt,
        test_war_dishes_cycles,
        test_copilot_foundations,
        test_ops_dashboard_full,
        test_tester_snapshot_schema,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"ok {t.__name__}")
        except Exception as exc:
            failed += 1
            print(f"FAIL {t.__name__}: {exc}", file=sys.stderr)
    print(json.dumps({"tests": len(tests), "failed": failed, "release": "0.9.9"}))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())