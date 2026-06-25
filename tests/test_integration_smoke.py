#!/usr/bin/env python3
"""Final_Eye 1.0 — Queen/Hostess/ZAC co-deployment integration smoke."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("FINAL_EYE_LOW_END", "1")
os.environ.setdefault("FINAL_EYE_COOL", "1")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SG = ROOT.parent


def test_queen_hostess_paths():
    queen = Path(os.environ.get("QUEEN_ROOT", str(SG / "NewLatest" / "Queen")))
    hostess = Path(os.environ.get("HOSTESS7_ROOT", str(SG / "Hostess7")))
    assert (queen / "lib" / "queen-forge.py").is_file()
    assert (hostess / "Hostess7.sh").is_file()


def test_hostess7_bridge():
    from zocr_trust import hostess7_bridge

    b = hostess7_bridge()
    assert b.get("present") is True
    assert b.get("schema") == "zocr-hostess7-bridge/v1"


def test_zac_verify():
    from zocr_zac import zac_self_test, zac_status

    z = zac_self_test()
    assert z.get("ok") is True, z
    st = zac_status()
    assert st.get("schema") == "zac-status/v1"


def test_grok16_linkage():
    from zocr_grok16 import grok16_status
    from zocr_field_compiler import field_compiler_status

    g = grok16_status()
    fc = field_compiler_status()
    assert g.get("root")
    assert g.get("ready") is True
    assert (fc.get("grok16") or {}).get("product") == "Grok16"
    assert fc.get("ready") is True


def test_docker_compose_artifacts():
    compose = ROOT / "docker-compose.yml"
    dockerfile = ROOT / "Dockerfile"
    assert compose.is_file()
    assert dockerfile.is_file()
    text = compose.read_text(encoding="utf-8")
    assert "QUEEN_ROOT" in text
    assert "HOSTESS7_ROOT" in text
    assert "GROK16_ROOT" in text


def main() -> int:
    tests = [
        test_queen_hostess_paths,
        test_hostess7_bridge,
        test_zac_verify,
        test_grok16_linkage,
        test_docker_compose_artifacts,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"ok {t.__name__}")
        except Exception as exc:
            failed += 1
            print(f"FAIL {t.__name__}: {exc}", file=sys.stderr)
    print(json.dumps({"tests": len(tests), "failed": failed, "release": (ROOT / "VERSION").read_text(encoding="utf-8").strip()}))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())