"""ZOCR silent capture — no flash, robotics-safe framebuffer read."""
from __future__ import annotations

import os
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path
from typing import Any

# Flashy tools — never use for live viewing
_FLASH_TOOLS = frozenset({"gnome-screenshot", "scrot", "spectacle", "ksnip"})


def capture_backends() -> dict[str, Any]:
    return {
        "xwd_silent": bool(shutil.which("xwd") and os.environ.get("DISPLAY")),
        "grim": bool(shutil.which("grim") and os.environ.get("WAYLAND_DISPLAY")),
        "import_silent": bool(shutil.which("import")),
        "mss": _mss_available(),
        "rtx_ppm": True,
        "flash_blocked": sorted(_FLASH_TOOLS),
    }


def _mss_available() -> bool:
    try:
        import mss  # noqa: F401
        return True
    except ImportError:
        return False


def _xwd_header(data: bytes) -> dict[str, int]:
    u = lambda o: struct.unpack_from(">I", data, o)[0]
    return {
        "header_size": u(0),
        "width": u(16),
        "height": u(20),
        "depth": u(12),
        "ncolors": u(76),
    }


def xwd_to_png(xwd_path: Path, png_path: Path) -> Path | None:
    """Parse XWD ZPixmap (silent root grab) → PNG. No screen flash."""
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        data = xwd_path.read_bytes()
        hdr = _xwd_header(data)
        w, h = hdr["width"], hdr["height"]
        if w <= 0 or h <= 0 or w > 16384 or h > 16384:
            return None
        pixel_off = hdr["header_size"] + hdr["ncolors"] * 12
        bpl = w * 4
        need = pixel_off + bpl * h
        if len(data) < need:
            return None
        px = data[pixel_off : pixel_off + bpl * h]
        try:
            import numpy as np
            bgra = np.frombuffer(px, dtype=np.uint8).reshape(h, w, 4)
            rgb = np.ascontiguousarray(bgra[:, :, [2, 1, 0]])
            img = Image.frombytes("RGB", (w, h), rgb.tobytes())
        except ImportError:
            raw = bytearray(w * h * 3)
            di = 0
            for y in range(h):
                row = px[y * bpl : y * bpl + w * 4]
                for x in range(w):
                    b, g, r, _a = row[x * 4 : x * 4 + 4]
                    raw[di], raw[di + 1], raw[di + 2] = r, g, b
                    di += 3
            img = Image.frombytes("RGB", (w, h), bytes(raw))
        png_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(png_path, optimize=True)
        return png_path if png_path.is_file() else None
    except (OSError, struct.error, ValueError):
        return None


def capture_xwd_silent(out_png: Path) -> Path | None:
    """xwd -silent — no white flash."""
    if not shutil.which("xwd") or not os.environ.get("DISPLAY"):
        return None
    xwd_tmp = Path(tempfile.gettempdir()) / f"zocr-silent-{os.getpid()}.xwd"
    try:
        proc = subprocess.run(
            ["xwd", "-root", "-silent", "-out", str(xwd_tmp)],
            capture_output=True,
            timeout=12,
        )
        if proc.returncode != 0 or not xwd_tmp.is_file() or xwd_tmp.stat().st_size < 1000:
            return None
        return xwd_to_png(xwd_tmp, out_png)
    except (OSError, subprocess.TimeoutExpired):
        return None
    finally:
        xwd_tmp.unlink(missing_ok=True)


def capture_mss(out_png: Path) -> Path | None:
    try:
        import mss
        from PIL import Image
    except ImportError:
        return None
    try:
        with mss.mss() as sct:
            shot = sct.grab(sct.monitors[0])
            img = Image.frombytes("RGB", shot.size, shot.rgb)
            img.save(out_png)
            return out_png if out_png.is_file() else None
    except Exception:
        return None


def capture_grim(out_png: Path) -> Path | None:
    if not shutil.which("grim"):
        return None
    try:
        subprocess.run(["grim", str(out_png)], capture_output=True, timeout=8, check=False)
        return out_png if out_png.is_file() and out_png.stat().st_size > 500 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def capture_screen_silent(out_png: Path | None = None) -> tuple[Path | None, str]:
    """Silent screen capture — robotics/AI safe, no flash."""
    out = out_png or Path(tempfile.gettempdir()) / f"zocr-screen-silent.png"
    for fn, label in (
        (capture_xwd_silent, "xwd_silent"),
        (capture_grim, "grim"),
        (capture_mss, "mss"),
    ):
        if fn(out):
            return out, label
    return None, "none"