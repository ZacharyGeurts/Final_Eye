"""Eye stoard — secure, safely expanding storage for field compiler witness."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent
DOCTRINE_PATH = _ROOT / "data" / "eye-stoard-doctrine.json"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def load_doctrine() -> dict[str, Any]:
    doc = _read_json(DOCTRINE_PATH)
    if doc.get("schema"):
        return doc
    return {
        "schema": "zocr-eye-stoard/v1",
        "rule": "Secure expanding eye storage for field compiler witness",
        "growth": {
            "initial_cap_bytes": 268435456,
            "max_cap_bytes": 8589934592,
            "expand_ratio": 1.25,
            "expand_threshold": 0.8,
            "min_witness_between_expand": 3,
            "max_blob_bytes": 33554432,
            "max_expand_per_day": 4,
        },
    }


def stoard_root() -> Path:
    env = os.environ.get("FINAL_EYE_STOARD_ROOT", "").strip()
    if env:
        return Path(env).resolve()
    return (_ROOT / "stoard").resolve()


def _paths() -> dict[str, Path]:
    root = stoard_root()
    return {
        "root": root,
        "manifest": root / "manifest.json",
        "ledger": root / "ledger.jsonl",
        "witness": root / "witness",
        "blobs": root / "blobs",
        "compile": root / "compile",
        "quarantine": root / "quarantine",
    }


def _ensure_layout() -> dict[str, Path]:
    p = _paths()
    for key in ("root", "witness", "blobs", "compile", "quarantine"):
        p[key].mkdir(parents=True, exist_ok=True)
    return p


def _growth_policy() -> dict[str, Any]:
    return load_doctrine().get("growth") or {}


def load_manifest() -> dict[str, Any]:
    p = _paths()
    doc = _read_json(p["manifest"])
    if doc.get("schema"):
        return doc
    pol = _growth_policy()
    return {
        "schema": "zocr-eye-stoard-manifest/v1",
        "cap_bytes": int(pol.get("initial_cap_bytes", 268435456)),
        "used_bytes": 0,
        "witness_count": 0,
        "expand_count": 0,
        "expands_today": 0,
        "last_expand_day": None,
        "last_witness": None,
        "head_hash": None,
    }


def _save_manifest(doc: dict[str, Any]) -> None:
    p = _ensure_layout()
    doc["updated"] = _ts()
    p["manifest"].write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def _dir_bytes(path: Path) -> int:
    if not path.is_dir():
        return 0
    total = 0
    try:
        for f in path.rglob("*"):
            if f.is_file():
                try:
                    total += f.stat().st_size
                except OSError:
                    pass
    except OSError:
        pass
    return total


def _refresh_usage(manifest: dict[str, Any]) -> dict[str, Any]:
    p = _paths()
    used = sum(_dir_bytes(p[k]) for k in ("witness", "blobs", "compile", "quarantine"))
    manifest["used_bytes"] = used
    cap = int(manifest.get("cap_bytes") or _growth_policy().get("initial_cap_bytes", 268435456))
    manifest["cap_bytes"] = cap
    manifest["free_bytes"] = max(0, cap - used)
    manifest["fill_ratio"] = round(used / cap, 4) if cap else 0.0
    return manifest


def _row_hash(row: dict[str, Any]) -> str:
    payload = json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _last_ledger_hash() -> str | None:
    p = _paths()
    if not p["ledger"].is_file():
        return None
    try:
        lines = p["ledger"].read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            doc = json.loads(line)
            return doc.get("hash") or _row_hash(doc)
        except json.JSONDecodeError:
            continue
    return None


def _append_ledger(row: dict[str, Any]) -> dict[str, Any]:
    p = _ensure_layout()
    prev = _last_ledger_hash()
    entry = {**row, "ts": row.get("ts") or _ts(), "prev_hash": prev}
    entry["hash"] = _row_hash(entry)
    with p["ledger"].open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def _seal_ok() -> dict[str, Any]:
    try:
        from zocr_security import verify_code_seal
        return verify_code_seal()
    except ImportError:
        return {"ok": True, "reason": "security_module_missing"}


def _maybe_expand(manifest: dict[str, Any], *, reason: str) -> dict[str, Any]:
    pol = _growth_policy()
    manifest = _refresh_usage(manifest)
    cap = int(manifest["cap_bytes"])
    max_cap = int(pol.get("max_cap_bytes", 8589934592))
    threshold = float(pol.get("expand_threshold", 0.8))
    min_wit = int(pol.get("min_witness_between_expand", 3))
    ratio = float(pol.get("expand_ratio", 1.25))
    max_day = int(pol.get("max_expand_per_day", 4))

    if manifest.get("fill_ratio", 0) < threshold:
        return manifest
    if int(manifest.get("witness_count") or 0) < min_wit:
        return manifest
    if cap >= max_cap:
        return manifest

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if manifest.get("last_expand_day") == today and int(manifest.get("expands_today") or 0) >= max_day:
        return manifest

    new_cap = min(max_cap, int(cap * ratio))
    if new_cap <= cap:
        return manifest

    manifest["cap_bytes"] = new_cap
    manifest["expand_count"] = int(manifest.get("expand_count") or 0) + 1
    if manifest.get("last_expand_day") == today:
        manifest["expands_today"] = int(manifest.get("expands_today") or 0) + 1
    else:
        manifest["last_expand_day"] = today
        manifest["expands_today"] = 1
    _append_ledger({
        "event": "expand",
        "reason": reason,
        "old_cap": cap,
        "new_cap": new_cap,
        "fill_ratio": manifest.get("fill_ratio"),
    })
    return _refresh_usage(manifest)


def _quarantine(row: dict[str, Any]) -> dict[str, Any]:
    p = _ensure_layout()
    name = f"reject-{_ts().replace(':', '').replace('.', '')}.json"
    path = p["quarantine"] / name
    path.write_text(json.dumps(row, indent=2) + "\n", encoding="utf-8")
    entry = _append_ledger({"event": "quarantine", **row})
    manifest = load_manifest()
    manifest = _refresh_usage(manifest)
    _save_manifest(manifest)
    return {"ok": False, "quarantined": str(path), "ledger": entry}


def stoard_status() -> dict[str, Any]:
    p = _ensure_layout()
    manifest = _refresh_usage(load_manifest())
    _save_manifest(manifest)
    pol = _growth_policy()
    return {
        "schema": "zocr-eye-stoard-status/v1",
        "ts": _ts(),
        "root": str(p["root"]),
        "rule": load_doctrine().get("rule"),
        "cap_bytes": manifest.get("cap_bytes"),
        "used_bytes": manifest.get("used_bytes"),
        "free_bytes": manifest.get("free_bytes"),
        "fill_ratio": manifest.get("fill_ratio"),
        "max_cap_bytes": pol.get("max_cap_bytes"),
        "witness_count": manifest.get("witness_count"),
        "expand_count": manifest.get("expand_count"),
        "head_hash": _last_ledger_hash(),
        "ledger_lines": (
            len(p["ledger"].read_text(encoding="utf-8", errors="replace").splitlines())
            if p["ledger"].is_file()
            else 0
        ),
        "zones": {k: str(p[k]) for k in ("witness", "blobs", "compile", "quarantine")},
        "can_expand": manifest.get("fill_ratio", 0) >= float(pol.get("expand_threshold", 0.8)),
    }


def stoard_doctrine() -> dict[str, Any]:
    return {**load_doctrine(), "ts": _ts(), "status": stoard_status()}


def read_ledger(*, n: int = 20) -> list[dict[str, Any]]:
    p = _paths()
    if not p["ledger"].is_file():
        return []
    try:
        lines = p["ledger"].read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    out: list[dict[str, Any]] = []
    for line in lines[-max(1, n) :]:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def verify_stoard_chain(*, n: int = 500) -> dict[str, Any]:
    rows = read_ledger(n=n)
    prev: str | None = None
    breaks: list[int] = []
    for i, row in enumerate(rows):
        if prev is not None and row.get("prev_hash") != prev:
            breaks.append(i)
        prev = row.get("hash")
    return {
        "ok": len(breaks) == 0,
        "checked": len(rows),
        "breaks": breaks,
        "head_hash": prev,
    }


def _fits(manifest: dict[str, Any], add_bytes: int) -> bool:
    manifest = _refresh_usage(manifest)
    return int(manifest.get("used_bytes", 0)) + add_bytes <= int(manifest.get("cap_bytes", 0))


def store_blob(
    data: bytes,
    *,
    kind: str = "blob",
    label: str = "",
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    seal = _seal_ok()
    if not seal.get("ok"):
        return _quarantine({"error": "seal_fail", "seal": seal, "kind": kind, "label": label})

    pol = _growth_policy()
    max_blob = int(pol.get("max_blob_bytes", 33554432))
    if len(data) > max_blob:
        return _quarantine({"error": "blob_oversize", "bytes": len(data), "max_blob_bytes": max_blob})

    manifest = load_manifest()
    if not _fits(manifest, len(data)):
        manifest = _maybe_expand(manifest, reason="store_blob")
        manifest = _refresh_usage(manifest)
        if not _fits(manifest, len(data)):
            return _quarantine({
                "error": "cap_exceeded",
                "bytes": len(data),
                "cap_bytes": manifest.get("cap_bytes"),
                "used_bytes": manifest.get("used_bytes"),
            })

    digest = hashlib.sha256(data).hexdigest()
    p = _ensure_layout()
    rel = Path(digest[:2]) / digest[2:4] / digest
    path = p["blobs"] / rel
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    entry = _append_ledger({
        "event": "store",
        "kind": kind,
        "label": label,
        "sha256": digest,
        "bytes": len(data),
        "path": str(path.relative_to(p["root"])),
        "meta": meta or {},
    })
    manifest = _refresh_usage(manifest)
    _save_manifest(manifest)
    return {
        "ok": True,
        "sha256": digest,
        "bytes": len(data),
        "path": str(path),
        "ledger": entry,
        "status": stoard_status(),
    }


def witness_compiler(*, reason: str = "compiler_witness") -> dict[str, Any]:
    seal = _seal_ok()
    if not seal.get("ok"):
        return _quarantine({"error": "seal_fail", "seal": seal, "reason": reason})

    from zocr_field_compiler import field_compiler_status
    from zocr_grok16 import grok16_eye_witness, grok16_status

    fc = field_compiler_status()
    g16 = grok16_status()
    witness = grok16_eye_witness()
    row = {
        "schema": "zocr-eye-stoard-witness/v1",
        "ts": _ts(),
        "reason": reason,
        "field_compiler": fc,
        "grok16": g16,
        "eye_witness": witness,
        "ready": bool(fc.get("ready")),
    }
    raw = json.dumps(row, indent=2, ensure_ascii=False).encode("utf-8")
    manifest = load_manifest()
    if not _fits(manifest, len(raw)):
        manifest = _maybe_expand(manifest, reason="witness_compiler")
        manifest = _refresh_usage(manifest)
        if not _fits(manifest, len(raw)):
            return _quarantine({
                "error": "cap_exceeded",
                "reason": reason,
                "bytes": len(raw),
            })

    p = _ensure_layout()
    stamp = _ts().replace(":", "").replace(".", "").replace("+", "")
    path = p["witness"] / f"witness-{stamp}.json"
    path.write_bytes(raw)
    entry = _append_ledger({
        "event": "witness",
        "reason": reason,
        "path": str(path.relative_to(p["root"])),
        "bytes": len(raw),
        "compiler_ready": fc.get("ready"),
        "grok16_ready": (fc.get("grok16") or {}).get("ready"),
    })
    manifest = _refresh_usage(manifest)
    manifest["witness_count"] = int(manifest.get("witness_count") or 0) + 1
    manifest["last_witness"] = _ts()
    manifest["head_hash"] = entry.get("hash")
    manifest = _maybe_expand(manifest, reason="post_witness")
    _save_manifest(manifest)
    return {
        "ok": True,
        "path": str(path),
        "ledger": entry,
        "witness": witness,
        "status": stoard_status(),
    }


def stoard_for_field_compiler() -> dict[str, Any]:
    """Compact block embedded in field_compiler_status."""
    st = stoard_status()
    return {
        "root": st.get("root"),
        "cap_bytes": st.get("cap_bytes"),
        "free_bytes": st.get("free_bytes"),
        "fill_ratio": st.get("fill_ratio"),
        "witness_count": st.get("witness_count"),
        "head_hash": st.get("head_hash"),
        "can_expand": st.get("can_expand"),
    }


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower()
    if cmd in ("status", "json"):
        print(json.dumps(stoard_status(), indent=2))
        return 0
    if cmd == "doctrine":
        print(json.dumps(stoard_doctrine(), indent=2))
        return 0
    if cmd == "witness":
        print(json.dumps(witness_compiler(reason="cli"), indent=2))
        return 0
    if cmd == "verify":
        print(json.dumps(verify_stoard_chain(), indent=2))
        return 0
    if cmd == "ledger":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        print(json.dumps(read_ledger(n=n), indent=2))
        return 0
    print(json.dumps({
        "error": "usage: zocr_eye_stoard.py [status|doctrine|witness|verify|ledger [n]]",
    }, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())