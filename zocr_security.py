"""ZOCR mandate security — code seal, GVC1 integrity, stream auth, silent capture policy."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import struct
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from zocr_field import load_mandate, mandate_gate

_ROOT = Path(__file__).resolve().parent
SEAL_PATH = _ROOT / "data" / "code-seal.json"
_AUTH_PATH = _ROOT / "data" / "operator-auth.json"
_STREAM_KEY_ENV = "ZOCR_STREAM_KEY"

# Encrypted stream envelope — ZSE1 (ZOCR Stream Envelope v1)
_STREAM_MAGIC = b"ZSE1"
_STREAM_HDR = struct.Struct("<4sBBH16s12s")

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


def _stream_key() -> bytes:
    env = os.environ.get(_STREAM_KEY_ENV, "").strip()
    if env:
        return hashlib.sha256(env.encode()).digest()
    key_path = _ROOT / "data" / "sovereign-time-state" / "sovereign-time-key.bin"
    if key_path.is_file():
        return hashlib.sha256(key_path.read_bytes()).digest()
    return hashlib.sha256(b"ZOCR_FIELD_ROBOTICS_MANDATE_v1|local-dev").digest()


def _aes_gcm_encrypt(plaintext: bytes, *, aad: bytes = b"") -> bytes | None:
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        return None
    nonce = secrets.token_bytes(12)
    ct = AESGCM(_stream_key()).encrypt(nonce, plaintext, aad)
    return nonce + ct


def _aes_gcm_decrypt(blob: bytes, *, aad: bytes = b"") -> bytes | None:
    if len(blob) < 28:
        return None
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        return None
    nonce, ct = blob[:12], blob[12:]
    try:
        return AESGCM(_stream_key()).decrypt(nonce, ct, aad)
    except Exception:
        return None


def encrypt_stream_payload(payload: bytes, *, codec: str = "GVC1") -> dict[str, Any]:
    """Seal + optionally AES-GCM encrypt stream payload for egress."""
    from grkmf.envelope import seal_payload
    sealed = seal_payload(payload)
    encrypted = _aes_gcm_encrypt(sealed, aad=codec.encode())
    if encrypted is None:
        mac = hmac.new(_stream_key(), sealed, hashlib.sha256).digest()
        header = _STREAM_HDR.pack(_STREAM_MAGIC, 1, 0, len(sealed), mac[:16], mac[16:28])
        return {
            "ok": True,
            "schema": "zocr-stream-seal/v1",
            "mode": "hmac_sealed",
            "label": "metaphor",
            "bytes": len(header + sealed),
            "blob": header + sealed,
            "sha256": hashlib.sha256(sealed).hexdigest(),
        }
    header = _STREAM_HDR.pack(_STREAM_MAGIC, 1, 1, len(encrypted), b"\0" * 16, b"\0" * 12)
    blob = header + encrypted
    return {
        "ok": True,
        "schema": "zocr-stream-seal/v1",
        "mode": "aes_gcm",
        "label": "implemented",
        "bytes": len(blob),
        "blob": blob,
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def decrypt_stream_payload(blob: bytes, *, codec: str = "GVC1") -> dict[str, Any]:
    from grkmf.envelope import unpack_envelope
    if len(blob) < _STREAM_HDR.size:
        return {"ok": False, "error": "stream_too_short"}
    magic, ver, mode, payload_len, _mac16, _mac12 = _STREAM_HDR.unpack(blob[: _STREAM_HDR.size])
    if magic != _STREAM_MAGIC:
        return {"ok": False, "error": "stream_bad_magic"}
    body = blob[_STREAM_HDR.size : _STREAM_HDR.size + payload_len]
    if mode == 1:
        plain = _aes_gcm_decrypt(body, aad=codec.encode())
        if plain is None:
            return {"ok": False, "error": "stream_decrypt_failed"}
        sealed = plain
    else:
        sealed = body
        mac = hmac.new(_stream_key(), sealed, hashlib.sha256).digest()
        if _mac16 != mac[:16] or _mac12 != mac[16:28]:
            return {"ok": False, "error": "stream_hmac_mismatch"}
    unpacked = unpack_envelope(sealed)
    if not unpacked:
        return {"ok": False, "error": "gvc1_envelope_invalid"}
    payload, meta = unpacked
    return {"ok": True, "payload": payload, "meta": meta, "mode": "aes_gcm" if mode == 1 else "hmac_sealed"}


def verify_gvc1_integrity(*, sample: bytes | None = None) -> dict[str, Any]:
    """Round-trip GVC1 envelope integrity — tamper detection."""
    from grkmf.envelope import seal_payload, unpack_envelope
    payload = sample or b"final-eye-gvc1-integrity-probe"
    sealed = seal_payload(payload)
    unpacked = unpack_envelope(sealed)
    if not unpacked:
        return {"ok": False, "error": "envelope_roundtrip_failed"}
    recovered, meta = unpacked
    tampered = bytearray(sealed)
    if len(tampered) > 55:
        tampered[55] ^= 0xFF
    tamper_check = unpack_envelope(bytes(tampered))
    stream = encrypt_stream_payload(payload)
    stream_ok = stream.get("ok") and decrypt_stream_payload(stream["blob"]).get("ok")
    return {
        "ok": recovered == payload and tamper_check is None and stream_ok,
        "schema": "zocr-gvc1-integrity/v1",
        "format": meta.get("format"),
        "codec": meta.get("codec"),
        "tamper_rejected": tamper_check is None,
        "stream_seal_ok": bool(stream_ok),
        "stream_mode": stream.get("mode"),
        "label": "measured",
    }


def silent_capture_policy() -> dict[str, Any]:
    m = load_mandate()
    return {
        "schema": "zocr-silent-capture-policy/v1",
        "silent_by_default": True,
        "no_flash": True,
        "on_demand_only": True,
        "rule": "look/observe never auto-flash display — stream off until operator arms",
        "protected_ops": sorted(_PROTECTED_OPS),
        "mandate_id": m.get("mandate_id"),
        "label": "doctrine",
        "operator_covenant": "Claims tagged Implemented / Measured / Metaphor / Doctrine in tester UI",
    }


def issue_operator_token(*, subject: str = "operator", ttl_sec: int = 3600) -> dict[str, Any]:
    issued = _ts()
    nonce = secrets.token_hex(16)
    body = f"{subject}|{issued}|{ttl_sec}|{nonce}"
    sig = hmac.new(_stream_key(), body.encode(), hashlib.sha256).hexdigest()
    doc = {
        "schema": "zocr-operator-token/v1",
        "subject": subject,
        "issued": issued,
        "ttl_sec": ttl_sec,
        "nonce": nonce,
        "token": f"{body}|{sig}",
    }
    _AUTH_PATH.parent.mkdir(parents=True, exist_ok=True)
    _AUTH_PATH.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return {"ok": True, **doc}


def verify_operator_token(token: str) -> dict[str, Any]:
    parts = token.split("|")
    if len(parts) != 5:
        return {"ok": False, "error": "token_format"}
    subject, issued, ttl_s, nonce, sig = parts
    body = f"{subject}|{issued}|{ttl_s}|{nonce}"
    expect = hmac.new(_stream_key(), body.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expect, sig):
        return {"ok": False, "error": "token_sig"}
    return {"ok": True, "subject": subject, "issued": issued, "label": "implemented"}


def security_model() -> dict[str, Any]:
    """Documented security model for 1.0 — honesty labels on every claim."""
    return {
        "schema": "zocr-security-model/v1",
        "ts": _ts(),
        "codec": {
            "format": "GRKMF1",
            "codec": "GVC1",
            "not_mpeg": True,
            "integrity": "SHA-256 envelope per segment (Implemented)",
            "tamper_detection": "unpack_envelope rejects digest mismatch (Measured)",
            "label": "implemented",
        },
        "stream": {
            "encryption": "AES-GCM when cryptography installed; else HMAC-sealed (Implemented)",
            "authentication": "HMAC operator tokens (Implemented)",
            "silent_capture": silent_capture_policy(),
        },
        "code": {
            "seal": "SHA-256 manifest of all zocr*.py + gui/*.py (Implemented)",
            "mandate_gate": "Egress + kill switch on protected ops (Implemented)",
        },
        "storage": {
            "pattern": "Hostess7 brain pattern — artifacts under data/ and out/ (Doctrine)",
            "external_deps": "Pillow, numpy, optional cryptography — no MPEG (Implemented)",
        },
        "honesty_labels": ["implemented", "measured", "doctrine", "metaphor"],
    }


def security_status() -> dict[str, Any]:
    m = load_mandate()
    seal = verify_code_seal()
    gvc1 = verify_gvc1_integrity()
    return {
        "schema": "zocr-security-status/v2",
        "ts": _ts(),
        "mandate_id": m.get("mandate_id"),
        "protection": m.get("protection", {}),
        "code_seal": seal,
        "gvc1_integrity": gvc1,
        "silent_capture": silent_capture_policy(),
        "model": security_model(),
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
    if cmd == "gvc1":
        print(json.dumps(verify_gvc1_integrity(), indent=2))
        return 0
    if cmd == "model":
        print(json.dumps(security_model(), indent=2))
        return 0
    if cmd == "token":
        print(json.dumps(issue_operator_token(), indent=2))
        return 0
    print(json.dumps(security_status(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())