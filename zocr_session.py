"""ZOCR vision session log — World_Redata web_session pattern."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def session_path() -> Path:
    return Path(os.environ.get("ZOCR_VISION_SESSION", str(_ROOT / "data" / "vision-session.jsonl")))


def log_event(action: str, **fields: Any) -> None:
    path = session_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"ts": _ts(), "action": action, **fields}
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def tail_session(*, limit: int = 40) -> list[dict[str, Any]]:
    path = session_path()
    if not path.is_file():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    rows: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def vision_status() -> dict[str, Any]:
    rows = tail_session(limit=80)
    captures = ocr_total = 0
    frames = text_only = errors = 0
    stream_frames = 0
    for r in rows:
        act = r.get("action", "")
        if act in ("capture", "look") and r.get("ok"):
            captures += 1
            ocr_total += int(r.get("ocr_len") or 0)
            if r.get("image"):
                frames += 1
            else:
                text_only += 1
        elif act == "stream_frame" and r.get("ok"):
            stream_frames += 1
            frames += 1
        elif act in ("capture", "look", "poll", "stream_frame") and not r.get("ok"):
            errors += 1
    return {
        "mode": "live_vision",
        "session_path": str(session_path()),
        "captures": captures,
        "frames": frames,
        "text_only": text_only,
        "errors": errors,
        "ocr_bytes_total": ocr_total,
        "stream_frames": stream_frames,
        "recent": list(reversed(rows[-20:])),
    }