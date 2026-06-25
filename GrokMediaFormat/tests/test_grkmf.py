"""GRKMF1 smoke tests."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from grkmf.container import verify_grkm, write_grkm
from grkmf.envelope import seal_payload, unpack_envelope
from grkmf.movie import encode_movie
from grkmf.spec import FORMAT_ID, load_spec


def test_spec_loads():
    spec = load_spec()
    assert spec["format_id"] == FORMAT_ID
    assert "cinema_4k" in spec["profiles"]


def test_envelope_roundtrip():
    raw = b"grok-proprietary-not-mpeg"
    sealed = seal_payload(raw)
    out = unpack_envelope(sealed)
    assert out is not None
    payload, meta = out
    assert payload == raw
    assert meta["sha256"]


def test_encode_verify_roundtrip(tmp_path=None):
    from PIL import Image
    td = Path(tempfile.mkdtemp(prefix="grkmf-test-"))
    src = td / "frame.png"
    Image.new("RGB", (640, 360), (40, 120, 200)).save(src)
    out = td / "test.grkm"
    r = encode_movie([src] * 12, out, profile_name="stream_4k", title="smoke")
    assert r["ok"]
    v = verify_grkm(out)
    assert v["ok"]
    assert v["format"] == FORMAT_ID


if __name__ == "__main__":
    test_spec_loads()
    test_envelope_roundtrip()
    test_encode_verify_roundtrip()
    print("ok")