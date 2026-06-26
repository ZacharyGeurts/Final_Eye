#!/usr/bin/env pythong
"""Eye motion — time + movement tracking tests."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("FINAL_EYE_LOW_END", "1")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_motion_doctrine_and_status():
    from zocr_eye_motion import load_doctrine, motion_doctrine, motion_status

    doc = load_doctrine()
    assert doc.get("schema") == "zocr-eye-motion/v1"
    assert "time" in (doc.get("tracks") or {})
    d = motion_doctrine()
    assert d.get("ok") is True
    st = motion_status()
    assert st.get("schema") == "zocr-eye-motion-status/v1"
    assert st.get("version") == "1.3.0"


def test_motion_tick_and_ledger():
    with tempfile.TemporaryDirectory() as tmp:
        state = Path(tmp) / "eye-motion-state.json"
        ledger = Path(tmp) / "eye-motion.jsonl"
        os.environ["ZOCR_VISION_SESSION"] = str(Path(tmp) / "vision.jsonl")

        import zocr_eye_motion as mod

        mod.STATE_PATH = state
        mod.LEDGER_PATH = ledger
        mod._runtime["running"] = False

        out = mod.motion_tick(source="test")
        assert out.get("ok") is True
        assert out.get("sealed_ts")
        assert "kinematics" in out
        assert state.is_file()
        assert ledger.is_file()
        rows = mod.read_motion_ledger(n=5)
        assert len(rows) >= 1
        assert rows[-1].get("event") == "motion_tick"


def test_product_version_1_3():
    from zocr_product import product_info

    expected = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    p = product_info()
    assert p["version"] == expected
    assert p["codename"] == "motion-track"


def main() -> int:
    tests = [
        test_motion_doctrine_and_status,
        test_motion_tick_and_ledger,
        test_product_version_1_3,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"ok {t.__name__}")
        except Exception as exc:
            failed += 1
            print(f"FAIL {t.__name__}: {exc}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())