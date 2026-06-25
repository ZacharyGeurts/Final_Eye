"""ZOCR internal imaging patterning — provenance weave + foreign-pattern security."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from zocr_field import load_mandate
from zocr_session import log_event

_ROOT = Path(__file__).resolve().parent
REGISTRY_PATH = _ROOT / "data" / "zocr-pattern-registry.json"
LOG_PATH = _ROOT / "data" / "pattern-security.jsonl"
STATE_PATH = _ROOT / "data" / "pattern-state.json"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def patterning_enabled() -> bool:
    if os.environ.get("ZOCR_PATTERN_OFF", "").strip().lower() in ("1", "true", "yes"):
        return False
    reg = load_registry()
    return bool(reg.get("stamp", {}).get("enabled", True))


def load_registry() -> dict[str, Any]:
    try:
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"stamp": {"enabled": True, "grid": 8, "cell_px": 4}, "detect": {}}


def _load_state() -> dict[str, Any]:
    if STATE_PATH.is_file():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {"stamps_total": 0, "scans_total": 0, "foreign_total": 0, "last_scan": None}


def _save_state(st: dict[str, Any]) -> None:
    st["updated"] = _ts()
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(st, indent=2) + "\n", encoding="utf-8")


def _log_security(row: dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def digest_bits(*, session_id: str, seq: int, mandate_id: str) -> list[int]:
    raw = f"{mandate_id}|{session_id}|{seq}".encode()
    digest = hashlib.sha256(raw).digest()
    bits: list[int] = []
    for byte in digest[:8]:
        for shift in range(7, -1, -1):
            bits.append((byte >> shift) & 1)
    return bits[:64]


def _stamp_region(img: Any, *, bits: list[int], reg: dict[str, Any]) -> None:
    stamp = reg.get("stamp", {})
    grid = int(stamp.get("grid", 8))
    cell = int(stamp.get("cell_px", 4))
    mod = int(stamp.get("modulation", 6))
    w, h = img.size
    patch = grid * cell
    x0 = max(0, w - patch - 2)
    y0 = max(0, h - patch - 2)
    if img.mode != "RGB":
        img = img.convert("RGB")
    px = img.load()
    for gy in range(grid):
        for gx in range(grid):
            bit = bits[gy * grid + gx]
            cx = x0 + gx * cell
            cy = y0 + gy * cell
            v = 220 if bit else 35
            for yy in range(cy, min(cy + cell, h)):
                for xx in range(cx, min(cx + cell, w)):
                    px[xx, yy] = (v, v, v)


def _read_region_bits(img: Any, *, reg: dict[str, Any]) -> list[int]:
    stamp = reg.get("stamp", {})
    grid = int(stamp.get("grid", 8))
    cell = int(stamp.get("cell_px", 4))
    w, h = img.size
    patch = grid * cell
    x0 = max(0, w - patch - 2)
    y0 = max(0, h - patch - 2)
    gray = img.convert("L")
    px = gray.load()
    bits: list[int] = []
    for gy in range(grid):
        for gx in range(grid):
            cx = x0 + gx * cell
            cy = y0 + gy * cell
            vals = [
                px[xx, yy]
                for yy in range(cy, min(cy + cell, h))
                for xx in range(cx, min(cx + cell, w))
            ]
            if not vals:
                bits.append(0)
                continue
            mean = sum(vals) / len(vals)
            bits.append(1 if mean >= 128 else 0)
    return bits


def stamp_frame(
    path: Path,
    *,
    session_id: str,
    seq: int,
    mandate_id: str | None = None,
) -> dict[str, Any]:
    """Embed 64-bit provenance weave in frame corner — internal imaging mark."""
    if not patterning_enabled():
        return {"ok": True, "stamped": False, "reason": "patterning_off"}
    reg = load_registry()
    mid = mandate_id or load_mandate().get("mandate_id", "ZOCR_FIELD_ROBOTICS_MANDATE_v1")
    bits = digest_bits(session_id=session_id, seq=seq, mandate_id=mid)
    try:
        from PIL import Image

        img = Image.open(path)
        _stamp_region(img, bits=bits, reg=reg)
        img.save(path, optimize=True)
    except Exception as exc:
        return {"ok": False, "stamped": False, "error": str(exc)}
    weave = hashlib.sha256("".join(str(b) for b in bits).encode()).hexdigest()[:16]
    st = _load_state()
    st["stamps_total"] = int(st.get("stamps_total", 0)) + 1
    st["last_stamp"] = {"ts": _ts(), "path": str(path), "session_id": session_id, "seq": seq, "weave": weave}
    _save_state(st)
    row = {
        "schema": "zocr-pattern-stamp/v1",
        "ts": _ts(),
        "path": str(path),
        "session_id": session_id,
        "seq": seq,
        "weave": weave,
        "bits": 64,
    }
    _log_security(row)
    log_event("pattern_stamp", ok=True, session_id=session_id, seq=seq, weave=weave)
    return {"ok": True, "stamped": True, "weave": weave, "session_id": session_id, "seq": seq}


def _periodicity_score(samples: list[float]) -> float:
    if len(samples) < 8:
        return 0.0
    mean = sum(samples) / len(samples)
    var = sum((x - mean) ** 2 for x in samples) / len(samples)
    if var < 1e-6:
        return 0.0
    best = 0.0
    for period in range(2, min(16, len(samples) // 3)):
        acc = 0.0
        n = 0
        for i in range(period, len(samples)):
            acc += abs(samples[i] - samples[i - period])
            n += 1
        if not n:
            continue
        inv = 1.0 - min(1.0, (acc / n) / (var ** 0.5 + 1e-6))
        best = max(best, inv)
    return best


def _stamp_bounds(img: Any, *, reg: dict[str, Any]) -> tuple[int, int, int, int]:
    stamp = reg.get("stamp", {})
    grid = int(stamp.get("grid", 8))
    cell = int(stamp.get("cell_px", 4))
    w, h = img.size
    patch = grid * cell
    x0 = max(0, w - patch - 2)
    y0 = max(0, h - patch - 2)
    return x0, y0, x0 + patch, y0 + patch


def _detect_foreign(img: Any, *, reg: dict[str, Any]) -> list[dict[str, Any]]:
    from PIL import ImageStat

    det = reg.get("detect", {})
    hits: list[dict[str, Any]] = []
    gray = img.convert("L")
    w, h = gray.size
    if w < 32 or h < 32:
        return [{"id": "corrupt_frame", "severity": "high", "score": 1.0}]

    px = gray.load()
    sx0, sy0, sx1, sy1 = _stamp_bounds(img, reg=reg)
    step = max(1, min(w, h) // 128)

    def _in_stamp(x: int, y: int) -> bool:
        return sx0 <= x < sx1 and sy0 <= y < sy1

    row_means = []
    for y in range(0, h, step):
        vals = [px[x, y] for x in range(0, w, step) if not _in_stamp(x, y)]
        row_means.append(sum(vals) / max(1, len(vals)))
    col_means = []
    for x in range(0, w, step):
        vals = [px[x, y] for y in range(0, h, step) if not _in_stamp(x, y)]
        col_means.append(sum(vals) / max(1, len(vals)))

    grid_score = max(_periodicity_score(row_means), _periodicity_score(col_means))
    if grid_score >= float(det.get("grid_jam_threshold", 0.62)):
        hits.append({"id": "grid_jam", "severity": "high", "score": round(grid_score, 3)})

    stat = ImageStat.Stat(gray)
    edge = 0.0
    samples = 0
    for y in range(0, h - step, step):
        for x in range(0, w - step, step):
            if _in_stamp(x, y) or _in_stamp(x + step, y) or _in_stamp(x, y + step):
                continue
            a = px[x, y]
            b = px[x + step, y]
            c = px[x, y + step]
            edge += abs(int(a) - int(b)) + abs(int(a) - int(c))
            samples += 1
    edge_n = edge / max(samples, 1) / 255.0
    var_n = min(1.0, float(stat.var[0]) / 5000.0)
    moire = min(1.0, grid_score * 0.6 + var_n * 0.25 + edge_n * 0.15)
    if moire >= float(det.get("moire_threshold", 0.55)) and "grid_jam" not in {h["id"] for h in hits}:
        hits.append({"id": "moire_weave", "severity": "high", "score": round(moire, 3)})

    # High-contrast injection blocks (weaponized corner markers)
    blocks = 0
    bsize = max(8, min(w, h) // 16)
    for by in range(0, h - bsize, bsize):
        for bx in range(0, w - bsize, bsize):
            if bx >= sx0 and by >= sy0:
                continue
            vals = [px[x, y] for y in range(by, by + bsize, 2) for x in range(bx, bx + bsize, 2)]
            if not vals:
                continue
            vmin, vmax = min(vals), max(vals)
            if vmax - vmin > 180 and sum(1 for v in vals if v < 40 or v > 215) / len(vals) > 0.55:
                blocks += 1
    inject = min(1.0, blocks / max(1, ((w // bsize) * (h // bsize)) // 12))
    if inject >= float(det.get("injection_threshold", 0.48)):
        hits.append({"id": "injected_marker", "severity": "medium", "score": round(inject, 3)})

    return hits


def scan_frame(
    path: Path,
    *,
    session_id: str | None = None,
    seq: int | None = None,
    expect_stamp: bool = False,
    provenance_only: bool = False,
) -> dict[str, Any]:
    """Detect foreign interference patterns and verify provenance weave."""
    reg = load_registry()
    det = reg.get("detect", {})
    try:
        from PIL import Image

        img = Image.open(path)
    except Exception as exc:
        return {"ok": False, "path": str(path), "error": str(exc), "foreign": [], "threats": ["corrupt_frame"]}

    foreign: list[dict[str, Any]] = []
    if not provenance_only:
        foreign = _detect_foreign(img, reg=reg)
    threats = [h["id"] for h in foreign if h.get("severity") in ("high", "critical")]

    provenance: dict[str, Any] = {"checked": False}
    if det.get("verify_provenance", True) and expect_stamp and session_id and seq is not None:
        provenance["checked"] = True
        read_bits = _read_region_bits(img, reg=reg)
        if sum(read_bits) < 8:
            foreign.append({"id": "provenance_missing", "severity": "medium", "score": 1.0})
            threats.append("provenance_missing")
        else:
            mid = load_mandate().get("mandate_id", "ZOCR_FIELD_ROBOTICS_MANDATE_v1")
            expect = digest_bits(session_id=session_id, seq=seq, mandate_id=mid)
            mism = sum(1 for a, b in zip(read_bits, expect) if a != b)
            provenance.update({
                "mismatches": mism,
                "confidence": round(1.0 - mism / 64.0, 3),
            })
            if mism > 20:
                foreign.append({"id": "provenance_mismatch", "severity": "critical", "score": round(mism / 64.0, 3)})
                threats.append("provenance_mismatch")

    st = _load_state()
    st["scans_total"] = int(st.get("scans_total", 0)) + 1
    if foreign:
        st["foreign_total"] = int(st.get("foreign_total", 0)) + 1
    st["last_scan"] = {
        "ts": _ts(),
        "path": str(path),
        "foreign_count": len(foreign),
        "threats": threats,
    }
    _save_state(st)

    row = {
        "schema": "zocr-pattern-scan/v1",
        "ts": _ts(),
        "path": str(path),
        "session_id": session_id,
        "seq": seq,
        "foreign": foreign,
        "threats": threats,
        "provenance": provenance,
    }
    _log_security(row)
    if threats:
        log_event("pattern_threat", ok=False, path=str(path), threats=threats)
        try:
            from zocr_offense import offense_strike
            for th in threats:
                offense_strike(th, path=str(path), source="pattern_scan")
        except Exception:
            pass

    critical = any(h.get("severity") == "critical" for h in foreign)
    sec = reg.get("security", {})
    if critical and sec.get("trip_on_critical", True):
        from zocr_kill import trip
        trip("vision", reason="provenance_mismatch")

    return {
        "ok": len(threats) == 0,
        "path": str(path),
        "foreign": foreign,
        "threats": threats,
        "provenance": provenance,
        "patterning": patterning_enabled(),
    }


def secure_frame(
    path: Path,
    *,
    session_id: str,
    seq: int,
    source: str = "internal",
    skip_foreign: bool = False,
) -> dict[str, Any]:
    """Foreign scan → stamp → provenance verify — one whole internal imaging security pass."""
    pre: dict[str, Any] = {"ok": True, "threats": [], "foreign": []}
    if not skip_foreign:
        pre = scan_frame(path, provenance_only=False)
    pre_threats = pre.get("threats") or []
    stamp = stamp_frame(path, session_id=session_id, seq=seq)
    post = scan_frame(path, session_id=session_id, seq=seq, expect_stamp=True, provenance_only=True)
    threats = list(dict.fromkeys(pre_threats + (post.get("threats") or [])))
    foreign = (pre.get("foreign") or []) + (post.get("foreign") or [])
    return {
        "ok": stamp.get("ok", False) and len(threats) == 0,
        "stamped": stamp.get("stamped", False),
        "weave": stamp.get("weave"),
        "foreign": foreign,
        "threats": threats,
        "provenance": post.get("provenance", {}),
        "source": source,
    }


def pattern_status() -> dict[str, Any]:
    reg = load_registry()
    st = _load_state()
    recent: list[dict[str, Any]] = []
    if LOG_PATH.is_file():
        try:
            for line in LOG_PATH.read_text(encoding="utf-8").splitlines()[-6:]:
                if line.strip():
                    recent.append(json.loads(line))
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "schema": "zocr-pattern-status/v1",
        "ts": _ts(),
        "enabled": patterning_enabled(),
        "registry": str(REGISTRY_PATH),
        "stamp": reg.get("stamp", {}),
        "detect": reg.get("detect", {}),
        "foreign_catalog": reg.get("foreign_patterns", []),
        "stamps_total": int(st.get("stamps_total", 0)),
        "scans_total": int(st.get("scans_total", 0)),
        "foreign_total": int(st.get("foreign_total", 0)),
        "last_stamp": st.get("last_stamp"),
        "last_scan": st.get("last_scan"),
        "recent": recent,
        "doctrine": "Internal real imaging — provenance weave stamped, foreign patterns rejected",
    }


def pattern_doctrine() -> dict[str, Any]:
    reg = load_registry()
    return {
        "schema": "zocr-pattern-doctrine/v1",
        "title": reg.get("title"),
        "rule": reg.get("rule"),
        "lineage": reg.get("lineage", {}),
        "stamp": reg.get("stamp", {}),
        "foreign_patterns": reg.get("foreign_patterns", []),
        "security": reg.get("security", {}),
    }


def main() -> int:
    import sys

    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        print(json.dumps(pattern_status(), indent=2))
        return 0
    if cmd == "doctrine":
        print(json.dumps(pattern_doctrine(), indent=2))
        return 0
    if cmd == "scan" and len(sys.argv) > 2:
        print(json.dumps(scan_frame(Path(sys.argv[2])), indent=2))
        return 0
    print(json.dumps({"error": "usage: zocr_pattern.py [status|doctrine|scan PATH]"}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())