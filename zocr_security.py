"""ZOCR mandate security — code seal, integrity gate on every operation."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from zocr_field import load_mandate, mandate_gate

_ROOT = Path(__file__).resolve().parent
SEAL_PATH = _ROOT / "data" / "code-seal.json"

# All ZOCR Python modules under mandate
_CODE_GLOB = ("zocr*.py", "gui/*.py", "addons/*.py")

# Operations requiring full mandate enforcement
_PROTECTED_OPS = frozenset({
    "look", "observe", "capture", "stream_start", "stream_stop",
    "mjpeg", "preserve", "verify", "vigilance_start", "vigilance_stop",
    "additive_register", "additive_capture", "nn_analyze",
    "pattern_stamp", "pattern_scan",
})


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _code_files() -> list[Path]:
    found: list[Path] = []
    for pattern in _CODE_GLOB:
        found.extend(_ROOT.glob(pattern))
    return sorted({p.resolve() for p in found if p.is_file()})


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def seal_codebase(*, mandate_id: str | None = None) -> dict[str, Any]:
    """Seal all ZOCR code modules under field mandate."""
    m = load_mandate()
    mid = mandate_id or m.get("mandate_id", "ZOCR_FIELD_ROBOTICS_MANDATE_v1")
    files: dict[str, str] = {}
    for p in _code_files():
        rel = str(p.relative_to(_ROOT))
        files[rel] = _hash_file(p)
    chain_input = "|".join(f"{k}:{v}" for k, v in sorted(files.items()))
    root_seal = hashlib.sha256(f"{mid}|{chain_input}".encode()).hexdigest()
    doc = {
        "schema": "zocr-code-seal/v1",
        "mandate_id": mid,
        "ts": _ts(),
        "files": files,
        "file_count": len(files),
        "root_seal": root_seal,
        "rule": "All ZOCR entry points verify this seal before protected operations",
    }
    SEAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    SEAL_PATH.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return doc


def verify_code_seal() -> dict[str, Any]:
    """Verify on-disk code matches sealed manifest."""
    if not SEAL_PATH.is_file():
        return {
            "ok": False,
            "reason": "seal_missing",
            "hint": "Run: python3 zocr_security.py seal",
        }
    try:
        doc = json.loads(SEAL_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"ok": False, "reason": "seal_corrupt"}
    sealed = doc.get("files", {})
    errors: list[str] = []
    missing: list[str] = []
    extra: list[str] = []
    current = {str(p.relative_to(_ROOT)): _hash_file(p) for p in _code_files()}
    for rel, expect in sealed.items():
        if rel not in current:
            missing.append(rel)
        elif current[rel] != expect:
            errors.append(rel)
    for rel in current:
        if rel not in sealed:
            extra.append(rel)
    ok = not errors and not missing and not extra
    return {
        "ok": ok,
        "mandate_id": doc.get("mandate_id"),
        "root_seal": doc.get("root_seal"),
        "file_count": len(sealed),
        "verified": len(sealed) - len(errors) - len(missing),
        "tampered": errors[:12],
        "missing": missing[:12],
        "unsealed_new": extra[:12],
        "ts": doc.get("ts"),
    }


def security_status() -> dict[str, Any]:
    m = load_mandate()
    seal = verify_code_seal()
    return {
        "schema": "zocr-security-status/v1",
        "ts": _ts(),
        "mandate_id": m.get("mandate_id"),
        "protection": m.get("protection", {}),
        "code_seal": seal,
        "seal_path": str(SEAL_PATH),
        "protected_operations": sorted(_PROTECTED_OPS),
        "override": os.environ.get("ZOCR_MANDATE_OFF", "").strip().lower() in ("1", "true", "yes"),
    }


def mandate_enforce(
    operation: str,
    *,
    client_host: str | None = None,
    require_seal: bool = True,
) -> dict[str, Any]:
    """
    Unified security gate — kill switch + egress mandate + code integrity.
    Returns {"ok": True, ...} or {"ok": False, "error": ..., ...}.
    """
    if os.environ.get("ZOCR_MANDATE_OFF", "").strip().lower() in ("1", "true", "yes"):
        return {"ok": True, "override": True, "operation": operation}

    from zocr_kill import check as kill_check
    kill = kill_check(operation)
    if not kill.get("ok"):
        return kill

    gate = mandate_gate(client_host=client_host)
    if not gate.get("ok"):
        return {"ok": False, "error": "mandate_gate", "operation": operation, **gate}

    m = load_mandate()
    sec = m.get("security", {})
    if require_seal and sec.get("code_seal_required", True):
        if operation in _PROTECTED_OPS or sec.get("enforce_all_ops", False):
            seal = verify_code_seal()
            if not seal.get("ok"):
                return {
                    "ok": False,
                    "error": "code_seal",
                    "operation": operation,
                    **seal,
                }

    return {
        "ok": True,
        "operation": operation,
        "mandate_id": m.get("mandate_id"),
        "client": gate.get("client"),
    }


def main() -> int:
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "seal":
        print(json.dumps(seal_codebase(), indent=2))
        return 0
    if cmd == "verify":
        print(json.dumps(verify_code_seal(), indent=2))
        return 0
    print(json.dumps(security_status(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())