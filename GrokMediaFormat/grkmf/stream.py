"""GRKMF live stream — bullet dodge MJPEG rail."""
from __future__ import annotations

import io
import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Generator

from grkmf.spec import FORMAT_ID, bullet_profile, profiles
from grkmf.tune import resolve


def png_to_jpeg(png: Path, *, quality: int | None = None, fast: bool = False) -> bytes:
    from PIL import Image
    q = quality if quality is not None else 72
    img = Image.open(png)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=q, optimize=not fast, subsampling=2 if fast else 0)
    return buf.getvalue()


def resize_max(path: Path, max_width: int, scale: float = 1.0, *, fast: bool = False) -> Path:
    if max_width <= 0 or scale >= 1.5:
        return path
    try:
        from PIL import Image
        img = Image.open(path)
        w, h = img.size
        target_w = min(max_width, int(w * scale))
        if target_w >= w:
            return path
        target_h = max(1, int(h * target_w / w))
        out = path.parent / f"{path.stem}_tide{target_w}.png"
        resample = Image.Resampling.BILINEAR if fast else Image.Resampling.LANCZOS
        img.resize((target_w, target_h), resample).save(out, optimize=not fast)
        return out if out.is_file() else path
    except Exception:
        return path


def bullet_pace(interval: float, t0: float) -> None:
    deadline = t0 + interval
    slack = deadline - time.monotonic()
    if slack > 0.003:
        time.sleep(slack - 0.001)
    while time.monotonic() < deadline:
        pass


def mjpeg_packet(
    jpeg: bytes,
    *,
    width: int,
    height: int,
    profile_name: str,
    fabric: float = 0.0,
    ingest_fps: float = 0.0,
    emit_fps: float = 0.0,
    boundary: bytes = b"--frame",
    brand: str = FORMAT_ID,
) -> bytes:
    prof = resolve(profile_name)
    return (
        boundary + b"\r\nContent-Type: image/jpeg\r\n"
        b"X-GRKMF-Format: " + brand.encode() + b"\r\n"
        b"X-GRKMF-Codec: GVC1\r\n"
        b"X-GRKMF-Bullet-Train: 1\r\n"
        b"X-GRKMF-Resolution: " + str(prof.get("resolution", "4K")).encode() + b"\r\n"
        b"X-GRKMF-Width: " + str(width).encode() + b"\r\n"
        b"X-GRKMF-Height: " + str(height).encode() + b"\r\n"
        b"X-GRKMF-Fabric-nm: " + str(fabric).encode() + b"\r\n"
        b"X-GRKMF-Ingest-fps: " + f"{ingest_fps:.1f}".encode() + b"\r\n"
        b"X-GRKMF-Emit-fps: " + f"{emit_fps:.0f}".encode() + b"\r\n"
        b"Content-Length: " + str(len(jpeg)).encode() + b"\r\n\r\n"
        + jpeg
        + b"\r\n"
    )


class BulletRail:
    """Cache rail — prime once, emit at dodge fps; ingest optional subprocess."""

    def __init__(
        self,
        *,
        max_width: int,
        refresh_hz: float,
        capture_fn: Any,
        jpeg_quality: int = 72,
        ingest_while_emit: bool = False,
    ) -> None:
        self._max_width = max_width
        self._interval = 1.0 / max(float(refresh_hz), 1.0)
        self._capture_fn = capture_fn
        self._jpeg_quality = jpeg_quality
        self._ingest_while_emit = ingest_while_emit
        self._stop = threading.Event()
        self._jpeg: bytes | None = None
        self._size: tuple[int, int] = (0, 0)
        self._ingest_fps: float = 0.0
        self._thread: threading.Thread | None = None
        import tempfile
        self._ingest_jpeg = Path(tempfile.gettempdir()) / f"grkmf-ingest-{os.getpid()}.jpg"

    def start(self) -> None:
        self._prime()
        if self._ingest_while_emit:
            self._thread = threading.Thread(target=self._loop, name="grkmf-bullet-rail", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._ingest_jpeg.unlink(missing_ok=True)

    def _prime(self) -> None:
        path = self._capture_fn(self._max_width)
        if path and Path(path).is_file():
            try:
                from PIL import Image
                img = Image.open(path)
                self._size = img.size
                self._jpeg = png_to_jpeg(Path(path), quality=self._jpeg_quality, fast=True)
            except Exception:
                pass

    def _loop(self) -> None:
        while not self._stop.is_set():
            t0 = time.monotonic()
            path = self._capture_fn(self._max_width)
            if path and Path(path).is_file():
                try:
                    from PIL import Image
                    img = Image.open(path)
                    jpeg = png_to_jpeg(Path(path), quality=self._jpeg_quality, fast=True)
                    self._jpeg = jpeg
                    self._size = img.size
                except Exception:
                    pass
            elapsed = time.monotonic() - t0
            self._ingest_fps = 1.0 / elapsed if elapsed > 0 else 0.0
            slack = max(self._interval, 0.05) - elapsed
            if slack > 0 and self._stop.wait(slack):
                break

    def snapshot(self) -> tuple[bytes | None, tuple[int, int], float]:
        return self._jpeg, self._size, self._ingest_fps


def bullet_mjpeg_generator(
    *,
    profile_name: str,
    max_frames: int = 0,
    capture_fn: Any,
    ingest_while_emit: bool = False,
    fabric_nm: float = 0.0,
    trip_check: Any | None = None,
    tune: dict[str, Any] | None = None,
) -> Generator[bytes, None, None]:
    prof = resolve(profile_name, tune)
    fps = float(prof.get("fps", 120))
    interval = 1.0 / fps
    max_w = int(prof.get("width", prof.get("max_width", 3840)))
    refresh = float(prof.get("refresh_hz", fps))
    q = int(prof.get("jpeg_quality", 72))
    rail = BulletRail(
        max_width=max_w,
        refresh_hz=refresh,
        capture_fn=capture_fn,
        jpeg_quality=q,
        ingest_while_emit=ingest_while_emit,
    )
    rail.start()
    seq = 0
    packet: bytes | None = None

    def _refresh() -> bytes | None:
        jpeg, size, ingest_fps = rail.snapshot()
        if not jpeg:
            return None
        w, h = size
        return mjpeg_packet(
            jpeg, width=w, height=h, profile_name=profile_name,
            fabric=fabric_nm, ingest_fps=ingest_fps, emit_fps=fps,
        )

    packet = _refresh()
    try:
        while True:
            if trip_check and trip_check():
                break
            if max_frames > 0 and seq >= max_frames:
                break
            seq += 1
            t0 = time.monotonic()
            if ingest_while_emit and seq % max(1, int(fps // 30)) == 0:
                packet = _refresh() or packet
            if packet:
                yield packet
            bullet_pace(interval, t0)
    finally:
        rail.stop()


def list_profiles() -> dict[str, Any]:
    return profiles()