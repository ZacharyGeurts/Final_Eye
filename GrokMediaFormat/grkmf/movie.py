"""GRKMF 4K movie encode / decode — cinema tier."""
from __future__ import annotations

import io
import tempfile
from pathlib import Path
from typing import Any

from grkmf.codec_gvc1 import chunk_bitrate_mbps, decode_frame, encode_frame
from grkmf.container import read_grkm, verify_grkm, write_grkm
from grkmf.envelope import unpack_envelope
from grkmf.spec import CODEC_ID, FORMAT_ID
from grkmf.tune import resolve


def encode_movie(
    sources: list[Path | str],
    out: Path | str,
    *,
    profile_name: str = "cinema_4k",
    title: str = "",
    creator: str = "GrokMediaFormat",
    tune: dict[str, Any] | None = None,
    width: int | None = None,
    height: int | None = None,
    fps: float | None = None,
) -> dict[str, Any]:
    """Encode frame sequence to sealed .grkm — proprietary GVC1 inter."""
    overrides = dict(tune or {})
    if width is not None:
        overrides["width"] = width
    if height is not None:
        overrides["height"] = height
    if fps is not None:
        overrides["fps"] = fps
    prof = resolve(profile_name, overrides)
    w = int(prof.get("width", 3840))
    h = int(prof.get("height", 2160))
    gop = int(prof.get("gop", 24))
    q = int(prof.get("jpeg_quality", 94))
    fps = float(prof.get("fps", 24))
    mode = prof.get("mode", "inter")
    if mode == "intra":
        gop = 1

    chunks: list[bytes] = []
    ref: bytes | None = None
    for i, src in enumerate(sources):
        frame, ref = encode_frame(
            index=i,
            source=Path(src),
            ref_rgb=ref,
            width=w,
            height=h,
            gop=gop,
            jpeg_quality=q,
        )
        chunks.append(frame.data)

    meta = {
        "schema": "grkmf-movie/v1",
        "format": FORMAT_ID,
        "codec": CODEC_ID,
        "profile": profile_name,
        "title": title or Path(str(out)).stem,
        "creator": creator,
        "proprietary": True,
        "not_mpeg": True,
        "gop": gop,
        "jpeg_quality": q,
    }
    result = write_grkm(Path(out), width=w, height=h, fps=fps, meta=meta, chunks=chunks)
    result["profile"] = profile_name
    result["gvc1_chunks"] = len(chunks)
    result["measured_mbps"] = round(chunk_bitrate_mbps(chunks, fps), 2)
    result["target_mbps"] = prof.get("target_mbps")
    result["compression_vs_intra"] = _intra_ratio(sources[: min(24, len(sources))], chunks[: min(24, len(chunks))], w, h, q)
    return result


def decode_movie(grkm: Path | str, out_dir: Path | str) -> dict[str, Any]:
    """Decode .grkm to PNG frame sequence."""
    from PIL import Image
    doc = read_grkm(Path(grkm))
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    ref: bytes | None = None
    written: list[str] = []
    frame_i = 0
    for seg in sorted(doc.segments, key=lambda s: s.frame_start):
        if seg.kind == 3:
            continue
        payload, _meta = unpack_envelope(seg.payload) or (b"", {})
        if not payload:
            continue
        rgb, w, h = decode_frame(payload, ref)
        if payload[4:5] == b"\x01":
            ref = rgb
        fp = out_path / f"frame_{frame_i:06d}.png"
        Image.frombytes("RGB", (w, h), rgb).save(fp)
        written.append(str(fp))
        frame_i += 1
    return {
        "ok": True,
        "format": FORMAT_ID,
        "frames": len(written),
        "out_dir": str(out_path),
        "paths": written[:5],
        "meta": doc.meta,
    }


def export_from_png_dir(
    src_dir: Path | str,
    out: Path | str,
    *,
    profile_name: str = "cinema_4k",
    max_frames: int = 0,
    **kwargs: Any,
) -> dict[str, Any]:
    paths = sorted(Path(src_dir).glob("*.png")) + sorted(Path(src_dir).glob("*.jpg"))
    if max_frames > 0:
        paths = paths[:max_frames]
    if not paths:
        return {"ok": False, "error": "no_sources", "src_dir": str(src_dir)}
    return encode_movie(paths, out, profile_name=profile_name, **kwargs)


def _intra_ratio(sources: list[Path | str], chunks: list[bytes], w: int, h: int, q: int) -> float:
    from grkmf.codec_gvc1 import _jpeg_bytes, _rgb_from_image
    try:
        intra = 0
        for src in sources:
            rgb, sw, sh = _rgb_from_image(Path(src))
            if sw != w or sh != h:
                from PIL import Image
                rgb = Image.frombytes("RGB", (sw, sh), rgb).resize((w, h)).tobytes()
            intra += len(_jpeg_bytes(rgb, w, h, q))
        inter = sum(len(c) for c in chunks)
        return round(intra / max(inter, 1), 2)
    except Exception:
        return 0.0


def benchmark_profiles(
    sample: Path | str,
    *,
    frame_count: int = 48,
    profiles_to_test: list[str] | None = None,
) -> dict[str, Any]:
    """Benchmark GVC1 profiles from one source frame."""
    sample = Path(sample)
    targets = profiles_to_test or ["cinema_4k", "stream_4k", "dodge_4k", "archive_4k"]
    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="grkmf-bench-") as td:
        for name in targets:
            out = Path(td) / f"{name}.grkm"
            sources = [sample] * frame_count
            try:
                r = encode_movie(sources, out, profile_name=name, title=f"bench_{name}")
                v = verify_grkm(out)
                results.append({
                    "profile": name,
                    "ok": v.get("ok"),
                    "mbps": r.get("measured_mbps"),
                    "target_mbps": r.get("target_mbps"),
                    "bytes": r.get("bytes"),
                    "compression_vs_intra": r.get("compression_vs_intra"),
                    "frames": frame_count,
                })
            except Exception as exc:
                results.append({"profile": name, "ok": False, "error": str(exc)})
    return {
        "schema": "grkmf-benchmark/v1",
        "format": FORMAT_ID,
        "codec": CODEC_ID,
        "profiles": results,
        "summary": {
            "cinema_ready": any(r.get("profile") == "cinema_4k" and r.get("ok") for r in results),
            "best_compression": max((r.get("compression_vs_intra") or 0 for r in results), default=0),
        },
    }