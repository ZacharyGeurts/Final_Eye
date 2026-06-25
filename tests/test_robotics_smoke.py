#!/usr/bin/env python3
"""Final_Eye v0.9 robotics smoke tests — run before review upload."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
GMF = ROOT.parent / "GrokMediaFormat"
if GMF.is_dir():
    sys.path.insert(0, str(GMF))


def test_product_version():
    from zocr_product import product_info
    p = product_info()
    assert p["product"] == "Final_Eye"
    assert p["version"] == "0.9.0"
    assert p["stack"]["vision"] == "ZOCRSM1"


def test_mandate_loads():
    from zocr_field import load_mandate
    m = load_mandate()
    assert m.get("mandate_id")


def test_final_eyeball_modes():
    from zocr_eye import list_final_modes, load_final_eyeball
    doc = load_final_eyeball()
    modes = list_final_modes()
    assert "war" in {m["id"] for m in modes}
    assert doc.get("rule")


def test_code_seal():
    from zocr_security import verify_code_seal
    v = verify_code_seal()
    assert v.get("ok") is True, v


def test_grkmf_tune():
    from grkmf.tune import resolve, tune_apply
    r = resolve("combat")
    assert 3 <= r["fps"] <= 20 or r["mode"] == "combat"
    t = tune_apply(fps=11, width=1920, mode="combat")
    assert t["fps"] == 11


def test_robotics_arm_dishes():
    from zocr_robotics import arm_robotics
    r = arm_robotics("dishes", start_stream=False)
    assert r.get("ok")
    assert r["mode"] == "dishes"


def test_video_profiles_ai_tunable():
    from zocr_video import profile_spec, video_tune_reset
    video_tune_reset()
    p = profile_spec("combat")
    assert p.get("ai_tunable") or p.get("mode") == "combat"


def main() -> int:
    tests = [
        test_product_version,
        test_mandate_loads,
        test_final_eyeball_modes,
        test_code_seal,
        test_grkmf_tune,
        test_robotics_arm_dishes,
        test_video_profiles_ai_tunable,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"ok {t.__name__}")
        except Exception as exc:
            failed += 1
            print(f"FAIL {t.__name__}: {exc}", file=sys.stderr)
    print(json.dumps({"tests": len(tests), "failed": failed, "version": "0.9.0"}))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())