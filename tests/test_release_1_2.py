#!/usr/bin/env python3
"""Final_Eye 1.2.0 — heaven-hell-ops eye operations tests."""
from __future__ import annotations

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


def test_product_1_2():
    from zocr_product import product_info
    p = product_info()
    expected = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert p["version"] == expected == "1.2.0"
    assert p["codename"] == "heaven-hell-ops"


def test_eye_operations_doctrine():
    from zocr_eye_operations import load_operations_doctrine, qualify_enemy
    doc = load_operations_doctrine()
    assert doc.get("schema") == "zocr-eye-operations/v1"
    assert doc.get("version") == "1.2.0"
    enemy = qualify_enemy("provenance_mismatch")
    assert enemy.get("enemy_qualified") is True
    assert enemy.get("offense_allowed") is True
    heaven = qualify_enemy("woven_paths")
    assert heaven.get("enemy_qualified") is False


def test_heaven_blocks_weapon_fire():
    from zocr_entity_eyeball import fire_entity_weapon
    out = fire_entity_weapon("reject_lie", threat="woven_paths")
    assert out.get("ok") is True
    assert out.get("gated") is True or out.get("heaven_pass")


def test_enemy_strike_allowed():
    from zocr_entity_eyeball import eye_understand_target
    u = eye_understand_target("provenance_mismatch")
    assert u.get("enemy_qualified") is True
    assert u.get("weapon_discerned") is True
    assert u.get("weapon_selected") == "autokill_certain"


def test_teach_enemy_lesson():
    from zocr_entity_eyeball import eye_teach
    t = eye_teach(lesson="enemy")
    assert t.get("lesson") == "enemy"
    assert "roster" in (t.get("speak") or "").lower()


def test_authority_includes_operations():
    from zocr_entity_eyeball import eye_weapon_authority
    a = eye_weapon_authority()
    assert a.get("operations", {}).get("schema") == "zocr-eye-operations-status/v1"


def main() -> int:
    tests = [
        test_product_1_2,
        test_eye_operations_doctrine,
        test_heaven_blocks_weapon_fire,
        test_enemy_strike_allowed,
        test_teach_enemy_lesson,
        test_authority_includes_operations,
    ]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception as exc:
            failed += 1
            print(f"FAIL {fn.__name__}: {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())