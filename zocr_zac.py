"""ZAC vision artifact pack/restore — Field Technology monolith alignment."""
from __future__ import annotations

import hashlib
import json
import struct
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from zocr_session import log_event

_ROOT = Path(__file__).resolve().parent
ZAC_MAGIC = b"ZAC1"
_HDR = struct.Struct("<4sBBII32s")
_STORE = _ROOT / "out" / "zac"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def pack_vision_artifacts(
    *,
    paths: list[str | Path] | None = None,
    label: str = "vision-pack",
) -> dict[str, Any]:
    """Pack preserve frames + state JSON into a ZAC1 blob."""
    _STORE.mkdir(parents=True, exist_ok=True)
    if paths is None:
        paths = []
        preserve = _ROOT / "data" / "preserve"
        for name in ("last-good.png", "last-good.json"):
            p = preserve / name
            if p.is_file():
                paths.append(p)
        for name in ("entity-eyeball-state.json", "final-eyeball-state.json", "video-active.json"):
            p = _ROOT / "data" / name
            if p.is_file():
                paths.append(p)

    manifest: list[dict[str, Any]] = []
    blobs: list[bytes] = []
    for raw in paths:
        p = Path(raw)
        if not p.is_file():
            continue
        data = p.read_bytes()
        rel = str(p.relative_to(_ROOT)) if p.is_relative_to(_ROOT) else p.name
        manifest.append({"path": rel, "size": len(data), "sha256": _sha256(data).hex()})
        blobs.append(data)

    manifest_json = json.dumps({"schema": "zac-vision-manifest/v1", "label": label, "files": manifest}, indent=2).encode()
    payload = manifest_json + b"\n---BLOB---\n" + b"".join(
        struct.pack("<I", len(b)) + b for b in blobs
    )
    compressed = zlib.compress(payload, 9)
    digest = _sha256(compressed)
    header = _HDR.pack(ZAC_MAGIC, 1, 0, len(compressed), len(manifest), digest)
    out_path = _STORE / f"{label}-{_ts().replace(':', '').replace('+00:00', 'Z')}.zac"
    out_path.write_bytes(header + compressed)

    log_event("zac_pack", ok=True, files=len(manifest), path=str(out_path))
    return {
        "ok": True,
        "schema": "zac-pack/v1",
        "path": str(out_path),
        "files": len(manifest),
        "bytes": out_path.stat().st_size,
        "manifest": manifest,
    }


def restore_vision_artifacts(path: str | Path, *, dest: Path | None = None) -> dict[str, Any]:
    """Restore ZAC1 pack into data/ tree."""
    dest = dest or (_ROOT / "data" / "zac-restore")
    dest.mkdir(parents=True, exist_ok=True)
    raw = Path(path).read_bytes()
    if len(raw) < _HDR.size:
        return {"ok": False, "error": "zac_too_short"}
    magic, ver, flags, comp_len, file_count, digest = _HDR.unpack(raw[: _HDR.size])
    if magic != ZAC_MAGIC:
        return {"ok": False, "error": "zac_bad_magic"}
    compressed = raw[_HDR.size : _HDR.size + comp_len]
    if _sha256(compressed) != digest:
        return {"ok": False, "error": "zac_digest_mismatch"}
    payload = zlib.decompress(compressed)
    parts = payload.split(b"\n---BLOB---\n", 1)
    if len(parts) != 2:
        return {"ok": False, "error": "zac_corrupt"}
    manifest = json.loads(parts[0].decode())
    blob_data = parts[1]
    restored: list[str] = []
    offset = 0
    for entry in manifest.get("files") or []:
        if offset + 4 > len(blob_data):
            break
        (blen,) = struct.unpack("<I", blob_data[offset : offset + 4])
        offset += 4
        chunk = blob_data[offset : offset + blen]
        offset += blen
        if _sha256(chunk).hex() != entry.get("sha256"):
            return {"ok": False, "error": "zac_blob_hash", "path": entry.get("path")}
        out = dest / Path(entry["path"]).name
        out.write_bytes(chunk)
        restored.append(str(out))

    log_event("zac_restore", ok=True, files=len(restored))
    return {"ok": True, "schema": "zac-restore/v1", "restored": restored, "dest": str(dest)}


def zac_self_test() -> dict[str, Any]:
    packed = pack_vision_artifacts(label="self-test")
    if not packed.get("ok"):
        return {"ok": False, "stage": "pack"}
    restored = restore_vision_artifacts(packed["path"])
    return {"ok": restored.get("ok"), "pack": packed, "restore": restored}


def zac_status() -> dict[str, Any]:
    packs = sorted(_STORE.glob("*.zac"), key=lambda p: p.stat().st_mtime, reverse=True) if _STORE.is_dir() else []
    return {
        "schema": "zac-status/v1",
        "ts": _ts(),
        "store": str(_STORE),
        "pack_count": len(packs),
        "latest": str(packs[0]) if packs else None,
        "label": _label_note(),
    }


def _label_note() -> str:
    return "ZAC1 — zlib manifest+blobs; Hostess7 brain pattern routing (Implemented)"


def main() -> int:
    import sys
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower()
    if cmd == "pack":
        print(json.dumps(pack_vision_artifacts(), indent=2))
        return 0
    if cmd == "restore" and len(sys.argv) > 2:
        print(json.dumps(restore_vision_artifacts(sys.argv[2]), indent=2))
        return 0
    if cmd == "test":
        print(json.dumps(zac_self_test(), indent=2))
        return 0
    print(json.dumps(zac_status(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())