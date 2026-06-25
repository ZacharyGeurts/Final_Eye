"""ZOCR vision preservation — confidence always in Vision; we never presume vision loss."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from zocr_session import log_event

_ROOT = Path(__file__).resolve().parent
VAULT_DIR = _ROOT / "data" / "preserve"
LAST_GOOD = VAULT_DIR / "last-good.png"
LAST_META = VAULT_DIR / "last-good.json"
STATE_PATH = VAULT_DIR / "preserve-state.json"
THREAT_LOG = VAULT_DIR / "threat-log.jsonl"

# Cascade order — modular additives; engine grab survives display RF jam; hold never blanks
SOURCE_CASCADE = ("rtx", "xwd_silent", "grim", "mss", "hold", "synthetic")
VISION_CONFIDENCE_RULE = "We never presume vision loss. Confidence always in Vision."

try:
    from zocr_offense import OFFENSE_RULE as _OFFENSE_RULE
except ImportError:
    _OFFENSE_RULE = "Defense of vision requires offense."
OFFENSE_RULE = _OFFENSE_RULE

_prev_hash: str = ""
_prev_hash_streak: int = 0
_last_acquire_mono: float = 0.0


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_state() -> dict[str, Any]:
    if STATE_PATH.is_file():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "threats_total": 0,
        "holds_total": 0,
        "failovers_total": 0,
        "last_threat": None,
        "vision_never_lost": True,
        "vision_confidence": 1.0,
        "confidence_rule": VISION_CONFIDENCE_RULE,
    }


def _affirm_confidence(st: dict[str, Any]) -> None:
    """Vision is never presumed lost — confidence stays at unity."""
    st["vision_never_lost"] = True
    st["vision_confidence"] = 1.0
    st["confidence_rule"] = VISION_CONFIDENCE_RULE


def _confidence_payload(*, via: str = "live") -> dict[str, Any]:
    return {
        "vision_confidence": 1.0,
        "vision_never_lost": True,
        "confidence_rule": VISION_CONFIDENCE_RULE,
        "confidence_via": via,
    }


def _save_state(st: dict[str, Any]) -> None:
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    st["updated"] = _ts()
    STATE_PATH.write_text(json.dumps(st, indent=2) + "\n", encoding="utf-8")


def _log_threat(kind: str, **fields: Any) -> None:
    row = {"ts": _ts(), "threat": kind, **fields}
    THREAT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with THREAT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    st = _load_state()
    st["threats_total"] = int(st.get("threats_total", 0)) + 1
    st["last_threat"] = row
    _save_state(st)
    log_event("threat", ok=True, threat=kind, **fields)
    try:
        from zocr_offense import offense_strike
        offense_strike(kind, **fields)
    except Exception:
        pass


def _image_metrics(path: Path) -> dict[str, float] | None:
    try:
        from PIL import Image, ImageStat
        import array

        img = Image.open(path).convert("L")
        w, h = img.size
        if w < 16 or h < 16:
            return None
        stat = ImageStat.Stat(img)
        mean = float(stat.mean[0])
        var = float(stat.var[0])
        # Laplacian-ish edge energy via pixel diffs (static/RF snow = high)
        px = img.load()
        diffs = 0.0
        samples = 0
        step = max(1, min(w, h) // 128)
        for y in range(0, h - step, step):
            for x in range(0, w - step, step):
                a = px[x, y]
                b = px[x + step, y]
                c = px[x, y + step]
                diffs += abs(int(a) - int(b)) + abs(int(a) - int(c))
                samples += 1
        edge = diffs / max(samples, 1)
        return {"mean": mean, "var": var, "edge": edge, "width": w, "height": h}
    except Exception:
        return None


def _file_hash(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def classify_threat(path: Path, *, source: str, elapsed_ms: float) -> list[str]:
    """Detect weaponized display interference patterns."""
    global _prev_hash, _prev_hash_streak
    threats: list[str] = []
    m = _image_metrics(path)
    if not m:
        threats.append("corrupt_frame")
        return threats

    if m["mean"] < 4.0 and m["var"] < 12.0:
        threats.append("blackout")
    if m["var"] > 4500.0 and m["edge"] > 40.0:
        threats.append("static_snow")
    if m["mean"] > 250.0 and m["var"] < 30.0:
        threats.append("whiteout")
    if elapsed_ms > float(os.environ.get("ZOCR_THREAT_GAP_MS", "8000")):
        threats.append("timing_gap")

    fh = _file_hash(path)
    if fh and fh == _prev_hash:
        _prev_hash_streak += 1
        if _prev_hash_streak >= 3 and source not in ("hold", "synthetic"):
            threats.append("frozen_display")
    else:
        _prev_hash = fh
        _prev_hash_streak = 1

    return threats


def _try_additive(src: str) -> tuple[Path | None, str]:
    from zocr_additives import capture_additive
    import tempfile
    out = Path(tempfile.gettempdir()) / f"zocr-preserve-{src}.png"
    path, label = capture_additive(src, out)
    if path:
        source = f"rtx_grab:{path.name}" if src == "rtx" else label
        return path, source
    return None, "none"


def _write_vault(path: Path, source: str, threats: list[str]) -> None:
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, LAST_GOOD)
    meta = {
        "ts": _ts(),
        "source": source,
        "image": str(LAST_GOOD),
        "sha256": _file_hash(LAST_GOOD),
        "threats_clear": len(threats) == 0,
        "threats": threats,
    }
    LAST_META.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def acquire_preserved(
    *,
    prefer: str = "auto",
    allow_hold: bool = True,
    profile: str = "watch",
) -> dict[str, Any]:
    """
    One whole cascade — additives registry is the single vision path.
    Threat detect + vault seal on live frames; confidence always in Vision via cascade.
    """
    from zocr_additives import cascade_for_prefer
    from zocr_kill import check as kill_check
    from zocr_offense import offense_cascade_bias, offense_clear_streak

    gate = kill_check("preserve")
    if not gate.get("ok"):
        return {"ok": False, "path": None, "source": "none", "threats": [], "tried": [], **gate}

    global _last_acquire_mono
    t0 = time.monotonic()
    st = _load_state()
    tried: list[str] = []
    threats: list[str] = []
    prefer, offense_front = offense_cascade_bias(prefer)
    cascade = cascade_for_prefer(prefer)
    if offense_front:
        seen = set(cascade)
        cascade = [s for s in offense_front if s in seen] + [s for s in cascade if s not in offense_front]
    if not allow_hold:
        cascade = [s for s in cascade if s not in ("hold", "synthetic")]

    for src in cascade:
        tried.append(src)
        path, source = _try_additive(src)
        if not path:
            continue
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        threats = classify_threat(path, source=source, elapsed_ms=elapsed_ms)
        if not threats and src not in ("hold", "synthetic"):
            from zocr_pattern import scan_frame
            pscan = scan_frame(path)
            pat_threats = [
                t for t in (pscan.get("threats") or [])
                if t not in ("provenance_missing", "provenance_mismatch")
            ]
            if pat_threats:
                threats = list(dict.fromkeys(threats + pat_threats))
        if threats:
            for th in threats:
                _log_threat(th, source=source, profile=profile, tried=tried)
            st["failovers_total"] = int(st.get("failovers_total", 0)) + 1
            continue

        preserved = src in ("hold", "synthetic")
        if preserved:
            if src == "hold":
                st["holds_total"] = int(st.get("holds_total", 0)) + 1
            _affirm_confidence(st)
            _save_state(st)
            offense_clear_streak(reason="hold_confidence")
            log_event("preserve_hold", ok=True, source=source, tried=tried, profile=profile)
            return {
                "ok": True,
                "path": path,
                "source": source,
                "preserved": True,
                "threats": threats or (["capture_fail"] if src == "synthetic" else []),
                "tried": tried,
                "vault": str(LAST_GOOD),
                "eyes_protect": gate.get("eyes_protect", True),
                **_confidence_payload(via=src),
            }

        _write_vault(path, source, [])
        _last_acquire_mono = time.monotonic()
        _affirm_confidence(st)
        _save_state(st)
        offense_clear_streak(reason="clean_live")
        return {
            "ok": True,
            "path": path,
            "source": source,
            "preserved": False,
            "threats": [],
            "tried": tried,
            "vault": str(LAST_GOOD),
            "eyes_protect": gate.get("eyes_protect", True),
            **_confidence_payload(via="live"),
        }

    # Cascade exhausted — confidence unchanged; vault or synthetic still serves Vision
    if LAST_GOOD.is_file():
        _affirm_confidence(st)
        st["holds_total"] = int(st.get("holds_total", 0)) + 1
        _save_state(st)
        log_event("preserve_vault", ok=True, tried=tried, profile=profile)
        return {
            "ok": True,
            "path": LAST_GOOD,
            "source": "vault_confidence",
            "preserved": True,
            "threats": threats,
            "tried": tried,
            "vault": str(LAST_GOOD),
            "eyes_protect": gate.get("eyes_protect", True),
            **_confidence_payload(via="vault"),
        }

    path, source = _try_additive("synthetic")
    if path:
        _affirm_confidence(st)
        _save_state(st)
        return {
            "ok": True,
            "path": path,
            "source": source,
            "preserved": True,
            "threats": threats or ["capture_fail"],
            "tried": tried + ["synthetic"],
            "vault": str(LAST_GOOD) if LAST_GOOD.is_file() else None,
            "eyes_protect": gate.get("eyes_protect", True),
            **_confidence_payload(via="synthetic"),
        }

    _affirm_confidence(st)
    _save_state(st)
    return {
        "ok": False,
        "path": None,
        "source": "none",
        "threats": threats,
        "tried": tried,
        **_confidence_payload(via="pending"),
    }


def preserve_status() -> dict[str, Any]:
    from zocr_additives import cascade_for_prefer
    st = _load_state()
    meta = {}
    if LAST_META.is_file():
        try:
            meta = json.loads(LAST_META.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    threats_recent: list[dict] = []
    if THREAT_LOG.is_file():
        try:
            for line in THREAT_LOG.read_text(encoding="utf-8").splitlines()[-8:]:
                if line.strip():
                    threats_recent.append(json.loads(line))
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "schema": "zocr-preserve-status/v1",
        "ts": _ts(),
        "doctrine": f"{VISION_CONFIDENCE_RULE} {OFFENSE_RULE}",
        "confidence_rule": VISION_CONFIDENCE_RULE,
        "offense_rule": OFFENSE_RULE,
        "vision_confidence": float(st.get("vision_confidence", 1.0)),
        "vision_never_lost": True,
        "last_good": str(LAST_GOOD) if LAST_GOOD.is_file() else None,
        "last_good_meta": meta,
        "cascade": cascade_for_prefer("auto"),
        "threats_total": int(st.get("threats_total", 0)),
        "holds_total": int(st.get("holds_total", 0)),
        "failovers_total": int(st.get("failovers_total", 0)),
        "last_threat": st.get("last_threat"),
        "threat_types": [
            "blackout", "whiteout", "static_snow", "frozen_display", "timing_gap",
            "corrupt_frame", "capture_fail", "grid_jam", "moire_weave",
            "injected_marker", "provenance_missing", "provenance_mismatch",
        ],
        "recent_threats": threats_recent,
        "countermeasures": {
            "multi_source": "modular additives — rtx → xwd → grim → mss → approved extensions",
            "hold_frame": "last-good vault on interference",
            "synthetic": "dark field plate if vault empty",
            "mjpeg_never_blank": "stream always emits JPEG — confidence in Vision, not fear of loss",
            "confidence_always": VISION_CONFIDENCE_RULE,
            "offense": OFFENSE_RULE,
        },
    }


def threat_doctrine() -> dict[str, Any]:
    return {
        "schema": "zocr-threat-doctrine/v1",
        "title": "Confidence and offense in Vision",
        "rule": f"{VISION_CONFIDENCE_RULE} {OFFENSE_RULE}",
        "offense_rule": OFFENSE_RULE,
        "threats": {
            "rf_jam": "timing_gap + capture_fail → failover + hold",
            "static_snow": "high variance + edge → reject frame, next source",
            "blackout": "display killed → rtx engine grab or hold",
            "whiteout": "weaponized full white → reject, hold",
            "frozen_display": "identical hash streak → failover",
            "weaponized_interference": "any threat → failover; Vision confidence unchanged",
        },
        "confidence_in_vision": [
            VISION_CONFIDENCE_RULE,
            OFFENSE_RULE,
            "We never presume vision loss — threats are rejected, not mourned",
            "Offense strikes on ingress — reject, preempt RTX, seal, trip when critical",
            "One whole additive cascade — confidence via live, hold, vault, synthetic",
            "Kill switch at choke points — trip hostile paths, not trust in Vision",
        ],
    }