#!/usr/bin/env python3
"""Headless Queen/RTX smoke → OCR → SG/ZOCR/out/."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

SG = Path(__file__).resolve().parents[1]
ZOCR = Path(__file__).resolve().parent
sys.path.insert(0, str(ZOCR))
from zocr import write_capture, tesseract_available, status  # noqa: E402

QUEEN = SG / "NewLatest" / "Queen"
RTX_CANDIDATES = (
    QUEEN / "build/rtx/bin/Linux/queen-browser",
    QUEEN / "build/rtx/bin/queen-browser",
    SG / "AMOURANTHRTX/build/bin/Linux/AMOURANTHRTX",
    SG / "NewLatest/AMOURANTHRTX/build/bin/Linux/AMOURANTHRTX",
)


def _find_binary() -> Path | None:
    for p in RTX_CANDIDATES:
        if p.is_file() and os.access(p, os.X_OK):
            return p
    return None


def _browser_markers(log: str, ocr: str) -> dict[str, bool]:
    blob = (log + "\n" + ocr).lower()
    return {
        "queen": bool(re.search(r"queen|fieldqueen|queenboot", blob, re.I)),
        "vulkan": bool(re.search(r"vulkan|vkcmd|dispatch", blob, re.I)),
        "thermo": bool(re.search(r"thermo|entropy", blob, re.I)),
        "browser_ui": bool(re.search(r"start|field|browser|canvas|x86|navigat", blob, re.I)),
        "field_die": bool(re.search(r"field.?die|x86\.comp|hotswap", blob, re.I)),
    }


def _panel_json_capture() -> dict[str, Any]:
    """Queen gate posture when RTX binary not ready yet — still lands in ZOCR."""
    panel_py = QUEEN / "lib" / "field-queen-browser.py"
    if not panel_py.is_file():
        return {"ok": False, "error": "field-queen-browser missing"}
    proc = subprocess.run(
        [sys.executable, str(panel_py), "json"],
        capture_output=True,
        text=True,
        timeout=30,
        env={**os.environ, "NEXUS_INSTALL_ROOT": str(QUEEN)},
    )
    try:
        doc = json.loads(proc.stdout)
    except json.JSONDecodeError:
        doc = {"raw": (proc.stdout or "")[-1500:]}
    text = json.dumps(doc, indent=2)
    row = write_capture(
        label="queen_panel_json",
        ocr_text=text,
        meta={"source": "field-queen-browser.py json", "queen_verdict": doc.get("queen_verdict")},
        copy_image=False,
    )
    return {
        "ok": doc.get("queen_verdict") == "QUEEN_READY",
        "mode": "panel_json",
        "queen_verdict": doc.get("queen_verdict"),
        "gates_held": (doc.get("gates") or {}).get("held"),
        "zocr": row,
    }


def run_smoke(*, max_frames: int | None = None, timeout: int = 90) -> dict[str, Any]:
    binary = _find_binary()
    if not binary:
        panel = _panel_json_capture()
        panel["error"] = "no_rtx_binary_yet"
        panel["candidates"] = [str(p) for p in RTX_CANDIDATES]
        panel["zocr_status"] = status()
        return panel

    mf = max_frames
    if mf is None:
        env_mf = os.environ.get("AMOURANTHRTX_MAX_FRAMES", "").strip()
        mf = int(env_mf) if env_mf.isdigit() else 0  # 0 = no hard limit
    env = {
        **os.environ,
        "AMOURANTHRTX_HEADLESS": "1",
        "AMOURANTHRTX_MAX_FRAMES": str(mf),
        "NEXUS_INSTALL_ROOT": str(QUEEN),
        "QUEEN_ROOT": str(QUEEN),
    }
    args = [str(binary)]
    if "queen-browser" in binary.name:
        args.extend(["--sovereign", "--queen"])
    proc = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
        cwd=str(binary.parent),
    )
    log = (proc.stdout or "") + (proc.stderr or "")
    markers = _browser_markers(log, "")

    shot: Path | None = None
    for grab_dir in (
        binary.parents[2] / "grabs",
        SG / "AMOURANTHRTX/build/grabs",
        SG / "NewLatest/AMOURANTHRTX/build/grabs",
    ):
        if grab_dir.is_dir():
            ppms = sorted(grab_dir.rglob("*.ppm"), key=lambda p: p.stat().st_mtime, reverse=True)
            if ppms:
                shot = ppms[0]
                break

    ocr_text = ""
    if shot and shot.is_file():
        try:
            from PIL import Image
            png = shot.with_suffix(".png")
            Image.open(shot).save(png)
            shot = png
        except Exception:
            pass
        from zocr import ocr_image
        ocr_text = ocr_image(shot) if shot else ""

    markers = _browser_markers(log, ocr_text)
    looks_like_browser = markers["queen"] or markers["browser_ui"] or markers["field_die"]
    looks_like_engine = markers["vulkan"] or markers["thermo"]

    row = write_capture(
        label=f"queen_browser_smoke_{binary.name}",
        image=shot,
        ocr_text=ocr_text,
        meta={
            "binary": str(binary),
            "returncode": proc.returncode,
            "markers": markers,
            "log_tail": log[-2000:],
        },
    )
    return {
        "ok": proc.returncode == 0 and (looks_like_browser or looks_like_engine),
        "binary": str(binary),
        "returncode": proc.returncode,
        "markers": markers,
        "looks_like_browser": looks_like_browser,
        "looks_like_engine": looks_like_engine,
        "tesseract": tesseract_available(),
        "zocr": row,
        "zocr_status": status(),
    }


def main() -> int:
    out = run_smoke()
    print(json.dumps(out, indent=2))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())