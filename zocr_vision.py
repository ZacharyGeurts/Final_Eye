"""ZOCR vision — on-demand look, silent capture, robotics/AI safe."""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from zocr_capture import capture_backends, capture_screen_silent
from zocr_session import log_event

SG = Path(__file__).resolve().parents[1]
QUEEN = SG / "NewLatest" / "Queen"
FORGE_LOG = QUEEN / ".queen-forge.log"
RTX_BUILD = QUEEN / "build" / "rtx"
BIN_CANDIDATES = (
    RTX_BUILD / "bin" / "Linux" / "queen-browser",
    RTX_BUILD / "bin" / "queen-browser",
)

GRAB_DIRS = (
    RTX_BUILD / "grabs",
    SG / "NewLatest" / "AMOURANTHRTX" / "build" / "grabs",
    SG / "AMOURANTHRTX" / "build" / "grabs",
)


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_tail(path: Path, n: int = 15) -> str:
    if not path.is_file():
        return ""
    try:
        return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-n:])
    except OSError:
        return ""


def _find_binary() -> Path | None:
    for p in BIN_CANDIDATES:
        if p.is_file() and os.access(p, os.X_OK):
            return p
    return None


def _stage_from_tail(tail: str) -> str:
    if re.search(r"QUEEN BINARY READY", tail):
        return "binary_ready"
    if re.search(r"FORGE END rtx ok=True", tail):
        return "rtx_done"
    if re.search(r"FORGE END rtx ok=False|compile failed|CMake Error", tail):
        return "failed"
    if re.search(r"=== forge:rtx_build", tail):
        return "compiling"
    if re.search(r"rtx_configure|cmake -S", tail):
        return "cmake_configure"
    return "idle"


def _procs() -> list[str]:
    try:
        proc = subprocess.run(
            ["pgrep", "-af", "queen-forge|cmake.*rtx|cmake.*AMOURANTHRTX"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        return [ln.strip() for ln in (proc.stdout or "").splitlines() if ln.strip() and "pgrep" not in ln][:4]
    except (OSError, subprocess.TimeoutExpired):
        return []


def forge_snapshot() -> dict[str, Any]:
    from zocr_field_compiler import forge_posture
    return forge_posture()


def _latest_ppm() -> Path | None:
    best: Path | None = None
    best_mtime = 0.0
    for d in GRAB_DIRS:
        if not d.is_dir():
            continue
        for p in d.rglob("*.ppm"):
            try:
                m = p.stat().st_mtime
                if m > best_mtime:
                    best_mtime = m
                    best = p
            except OSError:
                pass
    return best


def _ppm_to_png(ppm: Path) -> Path | None:
    try:
        from PIL import Image
        png = Path(tempfile.gettempdir()) / f"zocr-frame-{ppm.stem}.png"
        Image.open(ppm).save(png)
        return png if png.is_file() else None
    except Exception:
        return None


def grab_frame(*, prefer: str = "auto", preserve: bool = True) -> tuple[Path | None, str]:
    """Return (image_path, source_label). Uses preserve cascade when enabled."""
    if preserve:
        from zocr_preserve import acquire_preserved
        acq = acquire_preserved(prefer=prefer, allow_hold=True)
        if acq.get("path"):
            return acq["path"], acq.get("source", "none")
        return None, "none"
    if prefer in ("auto", "rtx", "ppm"):
        ppm = _latest_ppm()
        if ppm:
            png = _ppm_to_png(ppm)
            if png:
                return png, f"rtx_grab:{ppm.name}"
    if prefer in ("auto", "screen"):
        out = Path(tempfile.gettempdir()) / f"zocr-look-{datetime.now(timezone.utc).strftime('%H%M%S%f')}.png"
        shot, label = capture_screen_silent(out)
        if shot:
            return shot, label
    return None, "none"


def look(*, label: str = "look", prefer: str = "auto", enhance_eye: bool | None = None) -> dict[str, Any]:
    """On-demand vision — one frame when you ask. Eye runs cool unless enhance_eye."""
    from zocr import ocr_image, write_capture, tesseract_available

    forge = forge_snapshot()
    image, source = None, "text"
    preserve_meta: dict[str, Any] = {}
    if prefer != "text":
        from zocr_preserve import acquire_preserved
        acq = acquire_preserved(prefer=prefer, allow_hold=True)
        preserve_meta = acq
        if acq.get("path"):
            from zocr_cool import cool_enabled, register_worker
            register_worker("preserve")
            run_eye = enhance_eye
            if run_eye is None:
                run_eye = os.environ.get("ZOCR_LOOK_EYE", "").strip().lower() in ("1", "true", "yes")
                if cool_enabled() and not run_eye:
                    run_eye = False
            image = Path(acq["path"])
            eye_meta: dict[str, Any] = {"rig": {}, "eyes": [], "stereo": {}, "cool_skip": not run_eye}
            if run_eye:
                from zocr_stereo import perceive_rig
                rig = perceive_rig(acq["path"], on_demand=True)
                eye_meta = {"rig": rig, "eyes": rig.get("eyes", []), "stereo": rig.get("stereoscopic", {})}
                for e in rig.get("eyes", []):
                    if e.get("role") in ("center", "left") and e.get("path"):
                        image = Path(e["path"])
                        break
                else:
                    for e in rig.get("eyes", []):
                        if e.get("path"):
                            image = Path(e["path"])
                            break
            source = acq.get("source", "none")
        else:
            image, source, eye_meta = None, "none", {}
    else:
        eye_meta = {}
    nn_meta: dict[str, Any] = {}
    ocr_text = ""
    if image:
        from zocr_neural import analyze as nn_analyze
        nn_meta = nn_analyze(
            image,
            context={
                "eye": eye_meta.get("eyes", [{}])[0] if eye_meta.get("eyes") else {},
                "rig": eye_meta.get("rig", {}),
                "stereo": eye_meta.get("stereo", {}),
                "preserve": preserve_meta,
            },
        )
        ocr_text = ocr_image(image)
        if nn_meta.get("narrative") and nn_meta.get("ok"):
            ocr_text = f"{nn_meta['narrative']}\n\n--- OCR ---\n{ocr_text}"
    if not ocr_text.strip():
        ocr_text = (
            f"ZOCR look @ {forge['ts']}\n"
            f"stage={forge['stage']} running={forge['running']} binary={forge['binary_ready']}\n"
            f"rtx_files={forge['rtx_file_count']} cmake_cache={forge['cmake_cache']}\n"
            f"source={source} prefer={prefer}\n"
            f"--- forge tail ---\n{forge['tail']}\n"
        )
    silent = source in ("xwd_silent", "grim", "mss", "rtx_grab") or source.startswith("rtx_grab:")
    row = write_capture(
        label=label,
        image=image,
        ocr_text=ocr_text,
        meta={
            "schema": "zocr-look/v1",
            "source": source,
            "prefer": prefer,
            "silent": silent,
            "on_demand": True,
            "backends": capture_backends(),
            "forge": {k: v for k, v in forge.items() if k != "tail"},
            "tesseract": tesseract_available(),
            "preserve": {
                "preserved": preserve_meta.get("preserved", False),
                "threats": preserve_meta.get("threats", []),
                "tried": preserve_meta.get("tried", []),
            },
            "eye": eye_meta,
            "neural": nn_meta,
        },
        copy_image=True,
    )
    log_event(
        "look",
        ok=True,
        label=label,
        source=source,
        prefer=prefer,
        silent=silent,
        image=row.get("image"),
        ocr_file=row.get("ocr_file"),
        ocr_len=row.get("ocr_len"),
        stage=forge["stage"],
        binary_ready=forge["binary_ready"],
    )
    return {
        "ok": True, "forge": forge, "source": source, "prefer": prefer,
        "eye": eye_meta, "neural": nn_meta, "capture": row,
    }


# Legacy alias
def poll_once(*, label: str = "look", prefer: str = "auto") -> dict[str, Any]:
    return look(label=label, prefer=prefer)