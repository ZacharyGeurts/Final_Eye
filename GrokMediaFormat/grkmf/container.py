"""GRKMF .grkm container — proprietary 4K movie file."""
from __future__ import annotations

import hashlib
import json
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from grkmf.envelope import seal_payload, unpack_envelope
from grkmf.spec import CODEC_ID, FORMAT_ID, MAGIC

_HDR = struct.Struct("<4sBBHIIIIIIQI12s")
_IDX = struct.Struct("<IBBHHI I32s")


@dataclass
class Segment:
    segment_id: int
    kind: int  # 1=key 2=delta 3=meta
    frame_start: int
    frame_count: int
    offset: int
    length: int
    digest: bytes
    payload: bytes = field(repr=False)


@dataclass
class GRKMFile:
    width: int
    height: int
    fps_num: int
    fps_den: int
    frame_count: int
    meta: dict[str, Any]
    segments: list[Segment]

    @property
    def fps(self) -> float:
        return self.fps_num / max(self.fps_den, 1)


def write_grkm(
    path: Path,
    *,
    width: int,
    height: int,
    fps: float,
    meta: dict[str, Any],
    chunks: list[bytes],
    frame_indices: list[int] | None = None,
) -> dict[str, Any]:
    """Write sealed .grkm from GVC1 chunk blobs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fps_num = int(round(fps * 1000))
    fps_den = 1000
    frame_count = len(chunks)
    meta_blob = json.dumps(meta, ensure_ascii=False).encode("utf-8")
    segments: list[Segment] = []

    # meta segment
    sealed_meta = seal_payload(meta_blob, codec=1, flags=1)
    segments.append(Segment(0, 3, 0, 0, 0, len(sealed_meta), hashlib.sha256(sealed_meta).digest(), sealed_meta))

    for i, chunk in enumerate(chunks):
        sealed = seal_payload(chunk, codec=1, flags=0)
        fi = frame_indices[i] if frame_indices else i
        kind = 1 if chunk[4:5] == b"\x01" else 2
        segments.append(Segment(i + 1, kind, fi, 1, 0, len(sealed), hashlib.sha256(sealed).digest(), sealed))

    header_size = _HDR.size
    index_size = _IDX.size * len(segments)
    payload_offset = header_size + index_size
    offset = payload_offset
    for seg in segments:
        seg.offset = offset
        offset += seg.length

    index = bytearray()
    for seg in segments:
        index.extend(
            _IDX.pack(
                seg.segment_id,
                seg.kind,
                0,
                seg.frame_start,
                seg.frame_count,
                seg.offset,
                seg.length,
                seg.digest,
            )
        )

    header = _HDR.pack(
        MAGIC,
        1,
        1,
        0,
        width,
        height,
        fps_num,
        fps_den,
        frame_count,
        len(meta_blob),
        payload_offset,
        len(segments),
        b"\x00" * 12,
    )

    with path.open("wb") as f:
        f.write(header)
        f.write(index)
        for seg in segments:
            f.write(seg.payload)

    total_bytes = offset
    duration = frame_count / (fps or 1)
    mbps = total_bytes * 8 / max(duration, 0.001) / 1_000_000
    return {
        "ok": True,
        "path": str(path),
        "format": FORMAT_ID,
        "codec": CODEC_ID,
        "width": width,
        "height": height,
        "fps": fps,
        "frames": frame_count,
        "bytes": total_bytes,
        "mbps": round(mbps, 2),
        "segments": len(segments),
        "meta": meta,
    }


def read_grkm(path: Path) -> GRKMFile:
    data = path.read_bytes()
    if len(data) < _HDR.size:
        raise ValueError("grkm_truncated")
    magic, ver, codec, flags, w, h, fps_num, fps_den, frame_count, meta_len, payload_off, seg_count, _rsv = _HDR.unpack(
        data[: _HDR.size],
    )
    if magic != MAGIC:
        raise ValueError("not_grkm")
    index_off = _HDR.size
    segments: list[Segment] = []
    meta: dict[str, Any] = {}
    for i in range(seg_count):
        off = index_off + i * _IDX.size
        seg_id, kind, _r, fstart, fcount, byte_off, byte_len, digest = _IDX.unpack(data[off : off + _IDX.size])
        payload = data[byte_off : byte_off + byte_len]
        segments.append(Segment(seg_id, kind, fstart, fcount, byte_off, byte_len, digest, payload))
        if kind == 3:
            unpacked = unpack_envelope(payload)
            if unpacked:
                meta = json.loads(unpacked[0].decode("utf-8"))
    return GRKMFile(w, h, fps_num, fps_den, frame_count, meta, segments)


def verify_grkm(path: Path) -> dict[str, Any]:
    try:
        doc = read_grkm(path)
    except (OSError, ValueError) as exc:
        return {"ok": False, "path": str(path), "error": str(exc)}
    ok = 0
    checks: list[dict[str, Any]] = []
    for seg in doc.segments:
        if hashlib.sha256(seg.payload).digest() != seg.digest:
            checks.append({"segment": seg.segment_id, "ok": False, "error": "index_digest_mismatch"})
            continue
        unpacked = unpack_envelope(seg.payload)
        if not unpacked:
            checks.append({"segment": seg.segment_id, "ok": False, "error": "seal_invalid"})
            continue
        checks.append({"segment": seg.segment_id, "ok": True, "kind": seg.kind, "frames": seg.frame_count})
        ok += 1
    return {
        "ok": ok == len(doc.segments) and len(doc.segments) > 0,
        "format": FORMAT_ID,
        "codec": CODEC_ID,
        "path": str(path),
        "frames": doc.frame_count,
        "fps": doc.fps,
        "resolution": f"{doc.width}x{doc.height}",
        "segments_ok": ok,
        "segments_total": len(doc.segments),
        "meta": doc.meta,
        "checks": checks,
    }