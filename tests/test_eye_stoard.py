#!/usr/bin/env python3
"""Eye stoard — secure expanding storage for field compiler witness."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("FINAL_EYE_LOW_END", "1")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_stoard_status_and_witness():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["FINAL_EYE_STOARD_ROOT"] = tmp
        from zocr_eye_stoard import (
            load_doctrine,
            stoard_status,
            verify_stoard_chain,
            witness_compiler,
        )

        doc = load_doctrine()
        assert doc.get("schema") == "zocr-eye-stoard/v1"
        st = stoard_status()
        assert st.get("cap_bytes", 0) > 0
        assert Path(st["root"]).is_dir()

        w = witness_compiler(reason="test")
        assert w.get("ok") is True, w
        assert Path(w["path"]).is_file()

        chain = verify_stoard_chain()
        assert chain.get("ok") is True, chain

        st2 = stoard_status()
        assert int(st2.get("witness_count") or 0) >= 1
        assert st2.get("head_hash")


def test_field_compiler_includes_stoard():
    from zocr_field_compiler import field_compiler_status

    fc = field_compiler_status()
    assert "stoard" in fc
    assert fc["stoard"].get("cap_bytes", 0) > 0


def test_grok16_witness_includes_stoard():
    from zocr_grok16 import grok16_eye_witness

    w = grok16_eye_witness(mode="patrol", eye_profile="bird")
    assert "stoard" in w
    assert w["stoard"].get("free_bytes") is not None


def main() -> int:
    tests = [
        test_stoard_status_and_witness,
        test_field_compiler_includes_stoard,
        test_grok16_witness_includes_stoard,
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