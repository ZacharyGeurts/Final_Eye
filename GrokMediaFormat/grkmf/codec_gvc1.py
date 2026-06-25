"""GVC1 — Grok Vision Codec v1. Proprietary inter-frame. Not MPEG."""
from __future__ import annotations

import io
import struct
import zlib
from dataclasses import dataclass
from typing import Any

_GVC_MAGIC = b"GVC1"
_K = 1
_P = 2


@dataclass
class GVC1Frame:
    kind: int
    index: int
    width: int
    height: int
    data: bytes


def _rgb_from_image(path: Any) -> tuple[bytes, int, int]:
    from PIL import Image
    img = Image.open(path)
    if img.mode != "RGB":
        img = img.convert("RGB")
    w, h = img.size
    return img.tobytes(), w, h


def _jpeg_bytes(rgb: bytes, w: int, h: int, quality: int) -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.frombytes("RGB", (w, h), rgb).save(buf, format="JPEG", quality=quality, optimize=True, subsampling=0)
    return buf.getvalue()


def _rgb_from_jpeg(jpeg: bytes) -> tuple[bytes, int, int]:
    from PIL import Image
    img = Image.open(io.BytesIO(jpeg))
    if img.mode != "RGB":
        img = img.convert("RGB")
    w, h = img.size
    return img.tobytes(), w, h


def _delta_pack(prev: bytes, cur: bytes) -> bytes:
    try:
        import numpy as np
        a = np.frombuffer(prev, dtype=np.uint8)
        b = np.frombuffer(cur, dtype=np.uint8)
        d = (b.astype(np.int16) - a.astype(np.int16)).astype(np.int8)
        return zlib.compress(d.tobytes(), level=6)
    except ImportError:
        out = bytearray(len(cur))
        for i, (p, c) in enumerate(zip(prev, cur)):
            out[i] = ((c - p) + 128) & 0xFF
        return zlib.compress(bytes(out), level=6)


def _delta_unpack(prev: bytes, packed: bytes, length: int) -> bytes:
    raw = zlib.decompress(packed)
    try:
        import numpy as np
        d = np.frombuffer(raw, dtype=np.int8)
        a = np.frombuffer(prev, dtype=np.uint8).astype(np.int16)
        b = (a + d.astype(np.int16)).clip(0, 255).astype(np.uint8)
        return b.tobytes()
    except ImportError:
        out = bytearray(length)
        for i, (p, d) in enumerate(zip(prev, raw)):
            out[i] = (p + (d - 128)) & 0xFF
        return bytes(out)


def encode_frame(
    *,
    index: int,
    source: Any,
    ref_rgb: bytes | None,
    width: int,
    height: int,
    gop: int,
    jpeg_quality: int,
) -> tuple[GVC1Frame, bytes]:
    rgb, w, h = _rgb_from_image(source) if not isinstance(source, (bytes, bytearray)) else (bytes(source), width, height)
    if w != width or h != height:
        from PIL import Image
        img = Image.frombytes("RGB", (w, h), rgb).resize((width, height))
        rgb = img.tobytes()
        w, h = width, height
    is_key = gop <= 1 or index % gop == 0 or ref_rgb is None
    if is_key:
        jpeg = _jpeg_bytes(rgb, w, h, jpeg_quality)
        blob = _GVC_MAGIC + struct.pack("<BIII", _K, index, w, h) + jpeg
        return GVC1Frame(_K, index, w, h, blob), rgb
    assert ref_rgb is not None
    delta = _delta_pack(ref_rgb, rgb)
    blob = _GVC_MAGIC + struct.pack("<BIII", _P, index, w, h) + delta
    return GVC1Frame(_P, index, w, h, blob), rgb


def decode_frame(blob: bytes, ref_rgb: bytes | None) -> tuple[bytes, int, int]:
    if len(blob) < 14 or blob[:4] != _GVC_MAGIC:
        raise ValueError("invalid_gvc1")
    kind, index, w, h = struct.unpack("<BIII", blob[4:14])
    payload = blob[14:]
    if kind == _K:
        return _rgb_from_jpeg(payload)
    if ref_rgb is None:
        raise ValueError("missing_ref_for_predicted")
    rgb = _delta_unpack(ref_rgb, payload, w * h * 3)
    return rgb, w, h


def chunk_bitrate_mbps(chunks: list[bytes], fps: float) -> float:
    total = sum(len(c) for c in chunks)
    if fps <= 0:
        return 0.0
    return total * fps * 8 / 1_000_000