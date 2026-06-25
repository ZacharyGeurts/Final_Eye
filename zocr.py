#!/usr/bin/env python3
"""ZOCR — live vision sink. Captures → SG/ZOCR/out/ + vision-session.jsonl."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
MANIFEST = ROOT / "manifest.jsonl"


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slug(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9._-]+", "-", name.strip())[:64]
    return s or "capture"


def tesseract_available() -> bool:
    return shutil.which("tesseract") is not None


def ocr_image(path: Path, *, psm: str = "6", whitelist: str = "") -> str:
    if not path.is_file():
        return ""
    if not tesseract_available():
        return ""
    cmd = ["tesseract", str(path), "stdout", "--psm", psm]
    if whitelist:
        cmd.extend(["-c", f"tessedit_char_whitelist={whitelist}"])
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return (proc.stdout or "").strip()


def write_capture(
    *,
    label: str,
    image: Path | None = None,
    ocr_text: str = "",
    meta: dict[str, Any] | None = None,
    copy_image: bool = True,
) -> dict[str, Any]:
    OUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = f"{stamp}_{_slug(label)}"
    row: dict[str, Any] = {
        "ts": _ts(),
        "label": label,
        "zocr_root": str(ROOT),
        "meta": meta or {},
    }
    if image and image.is_file():
        if copy_image:
            ext = image.suffix or ".png"
            dst = OUT / f"{base}{ext}"
            shutil.copy2(image, dst)
            row["image"] = str(dst)
        else:
            row["image"] = str(image)
        if not ocr_text:
            ocr_text = ocr_image(image)
    row["ocr"] = ocr_text
    row["ocr_len"] = len(ocr_text)
    txt = OUT / f"{base}.txt"
    txt.write_text(ocr_text + "\n", encoding="utf-8")
    row["ocr_file"] = str(txt)
    with MANIFEST.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    try:
        from zocr_session import log_event
        log_event("manifest", ok=True, label=label, image=row.get("image"), ocr_len=row["ocr_len"])
    except ImportError:
        pass
    return row


def latest(n: int = 5) -> list[dict[str, Any]]:
    if not MANIFEST.is_file():
        return []
    lines = MANIFEST.read_text(encoding="utf-8").strip().splitlines()
    out: list[dict[str, Any]] = []
    for line in lines[-n:]:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return out


def status() -> dict[str, Any]:
    captures = sum(1 for _ in MANIFEST.open(encoding="utf-8")) if MANIFEST.is_file() else 0
    return {
        "schema": "zocr/v2",
        "root": str(ROOT),
        "out": str(OUT),
        "manifest": str(MANIFEST),
        "tesseract": tesseract_available(),
        "captures": captures,
        "latest": latest(3),
    }


def main() -> int:
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        print(json.dumps(status(), indent=2))
        return 0
    if cmd == "live":
        from zocr_status import live_status
        print(json.dumps(live_status(), indent=2))
        return 0
    if cmd in ("poll", "look"):
        from zocr_vision import look
        prefer = sys.argv[2] if len(sys.argv) > 2 else "auto"
        print(json.dumps(look(prefer=prefer), indent=2))
        return 0
    if cmd == "observe":
        from zocr_ai import robotics_context
        from zocr_vision import look
        cap = look(prefer=sys.argv[2] if len(sys.argv) > 2 else "auto")
        print(json.dumps({"ok": True, "look": cap, "robotics": robotics_context(capture=cap)}, indent=2))
        return 0
    if cmd == "capabilities":
        from zocr_ai import capabilities
        print(json.dumps(capabilities(), indent=2))
        return 0
    if cmd == "ocr" and len(sys.argv) >= 3:
        img = Path(sys.argv[2])
        text = ocr_image(img)
        row = write_capture(label=img.stem, image=img, ocr_text=text, copy_image=True)
        print(json.dumps(row, indent=2))
        return 0
    print(json.dumps({
        "error": "usage: zocr.py [status|live|look|observe|capabilities|ocr IMAGE]",
    }, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())