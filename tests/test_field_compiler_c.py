#!/usr/bin/env python3
"""Final_Eye 1.0.0 — Grok16 C/C++ field compiler smoke + optimize bench."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("FINAL_EYE_LOW_END", "1")
os.environ.setdefault("FINAL_EYE_COOL", "1")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_field_compile_status():
    from zocr_field_compile import field_compile_status

    st = field_compile_status()
    assert st.get("schema") == "zocr-field-compile-status/v1"
    assert st.get("g16_ready") is True
    assert st.get("g++16_ready") is True
    assert st.get("g16_dumpversion")


def test_c_smoke_g16():
    from zocr_field_compile import compile_c_smoke

    r = compile_c_smoke(profile="field_opt")
    assert r.get("ok") is True, r
    assert r.get("schema") == "zocr-field-compile-c/v1"
    assert "final_eye_vision_probe" in (r.get("run") or {}).get("stdout", "")
    assert "FIELD_ENTROPY_DISPATCH=1" in (r.get("run") or {}).get("stdout", "")


def test_vision_kernel_gxx16():
    from zocr_field_compile import compile_vision_kernel

    r = compile_vision_kernel(profile="field_opt")
    assert r.get("ok") is True, r
    assert r.get("schema") == "zocr-field-compile-kernel/v1"
    assert r.get("cxx_std") == "gnu++26"
    metrics = r.get("metrics") or {}
    assert metrics.get("entropy_micro", 0) > 0
    assert metrics.get("phi_micro", 0) > 0


def test_field_compiler_optimize_bench():
    from zocr_field_compile import field_compiler_optimize

    doc = field_compiler_optimize(profiles=["field_opt", "field_compute"])
    assert doc.get("schema") == "zocr-field-compiler-bench/v1"
    assert doc.get("best_profile") in ("field_opt", "field_compute")
    ok_rows = [x for x in doc.get("results") or [] if x.get("c_ok") and x.get("kernel_ok")]
    assert len(ok_rows) >= 2


def test_field_compile_full_low_end():
    from zocr_field_compile import field_compile_full_test

    full = field_compile_full_test()
    assert full.get("ok") is True, full
    assert full.get("forge_probe", {}).get("skipped") is True


def main() -> int:
    tests = [
        test_field_compile_status,
        test_c_smoke_g16,
        test_vision_kernel_gxx16,
        test_field_compiler_optimize_bench,
        test_field_compile_full_low_end,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"ok {t.__name__}")
        except Exception as exc:
            failed += 1
            print(f"FAIL {t.__name__}: {exc}", file=sys.stderr)
    print(json.dumps({"tests": len(tests), "failed": failed, "release": "1.0.0"}))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())