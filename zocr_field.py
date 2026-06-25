"""ZOCR field protection — DARPA-style seal chain, mandate gate, egress control."""
from __future__ import annotations

import hashlib
import json
import os
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent
MANDATE_PATH = _ROOT / "data" / "zocr-field-mandate.json"
CHAIN_PATH = _ROOT / "data" / "stream-chain.json"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_mandate() -> dict[str, Any]:
    try:
        return json.loads(MANDATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"mandate_id": "ZOCR_FIELD_ROBOTICS_MANDATE_v1", "protection": {}}


def mandate_gate(*, client_host: str | None = None) -> dict[str, Any]:
    """Verify stream may run under field mandate."""
    m = load_mandate()
    bind = os.environ.get("ZOCR_STREAM_EGRESS", "127.0.0.1").strip()
    host = (client_host or "127.0.0.1").split(":")[0]
    local_ok = host in ("127.0.0.1", "localhost", "::1", "")
    if bind == "127.0.0.1" and not local_ok:
        return {
            "ok": False,
            "reason": "egress_denied",
            "mandate_id": m.get("mandate_id"),
            "client": host,
            "required_bind": bind,
        }
    if os.environ.get("ZOCR_MANDATE_OFF", "").strip().lower() in ("1", "true", "yes"):
        return {"ok": True, "mandate_id": m.get("mandate_id"), "override": True}
    return {
        "ok": True,
        "mandate_id": m.get("mandate_id"),
        "protection": m.get("protection", {}),
        "client": host,
    }


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_chain_head() -> str:
    if CHAIN_PATH.is_file():
        try:
            doc = json.loads(CHAIN_PATH.read_text(encoding="utf-8"))
            return str(doc.get("head") or "")
        except (OSError, json.JSONDecodeError):
            pass
    mandate = load_mandate()
    seed = mandate.get("mandate_id", "ZOCR_GENESIS")
    return hashlib.sha256(seed.encode()).hexdigest()


def _save_chain_head(head: str, seq: int) -> None:
    CHAIN_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHAIN_PATH.write_text(
        json.dumps({"head": head, "seq": seq, "updated": _ts()}, indent=2) + "\n",
        encoding="utf-8",
    )


def seal_frame(
    image_path: Path,
    *,
    seq: int,
    fps_profile: str,
    power_mode: str,
    ocr_excerpt: str = "",
) -> dict[str, Any]:
    """Seal one stream frame — hash chain + integrity record."""
    prev = _load_chain_head()
    img_hash = sha256_file(image_path) if image_path.is_file() else ""
    link_input = f"{prev}|{seq}|{img_hash}|{fps_profile}|{power_mode}"
    seal = hashlib.sha256(link_input.encode()).hexdigest()
    _save_chain_head(seal, seq)
    row = {
        "schema": "zocr-frame-seal/v1",
        "ts": _ts(),
        "seq": seq,
        "image": str(image_path),
        "image_sha256": img_hash,
        "prev_seal": prev,
        "seal": seal,
        "fps_profile": fps_profile,
        "power_mode": power_mode,
        "ocr_excerpt_len": len(ocr_excerpt),
        "mandate_id": load_mandate().get("mandate_id"),
    }
    index = _ROOT / "data" / "stream-index.jsonl"
    index.parent.mkdir(parents=True, exist_ok=True)
    with index.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def verify_chain(*, tail: int = 20) -> dict[str, Any]:
    index = _ROOT / "data" / "stream-index.jsonl"
    if not index.is_file():
        return {"ok": True, "frames": 0, "verified": 0}
    all_lines = index.read_text(encoding="utf-8").strip().splitlines()
    start = max(0, len(all_lines) - tail)
    lines = all_lines[start:]
    verified = 0
    mandate = load_mandate().get("mandate_id", "ZOCR_GENESIS")
    prev = hashlib.sha256(mandate.encode()).hexdigest()
    if start > 0:
        try:
            prior = json.loads(all_lines[start - 1])
            prev = str(prior.get("seal") or prev)
        except (json.JSONDecodeError, KeyError):
            pass
    errors: list[str] = []
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        img = Path(row.get("image", ""))
        img_hash = sha256_file(img) if img.is_file() else row.get("image_sha256", "")
        if img_hash != row.get("image_sha256"):
            errors.append(f"seq {row.get('seq')}: file hash mismatch")
            continue
        link = f"{prev}|{row.get('seq')}|{img_hash}|{row.get('fps_profile')}|{row.get('power_mode')}"
        expect = hashlib.sha256(link.encode()).hexdigest()
        if expect != row.get("seal"):
            errors.append(f"seq {row.get('seq')}: chain break")
            continue
        if row.get("prev_seal") != prev:
            errors.append(f"seq {row.get('seq')}: prev_seal mismatch")
            continue
        prev = row.get("seal", "")
        verified += 1
    return {
        "ok": len(errors) == 0,
        "frames": len(lines),
        "verified": verified,
        "errors": errors[:10],
        "head": prev,
    }


def field_power_for_profile(profile: str) -> dict[str, Any]:
    m = load_mandate()
    profiles = m.get("fps_profiles", {})
    p = profiles.get(profile, profiles.get("watch", {"fps": 2, "power": "balanced"}))
    return {
        "profile": profile,
        "fps": float(p.get("fps", 2)),
        "power": p.get("power", "balanced"),
        "use": p.get("use", ""),
    }


def hostname_bind_ok() -> bool:
    host = os.environ.get("ZOCR_HOST", "127.0.0.1")
    return host in ("127.0.0.1", "localhost", "::1")