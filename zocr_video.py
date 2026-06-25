"""ZOCRSM1 — field vision on GRKMF1 proprietary cinema (GVC1). Not MPEG."""
from __future__ import annotations

import hashlib
import io
import json
import os
import struct
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

from zocr_field import load_mandate, seal_frame
from zocr_grkmf import grkmf
from zocr_security import mandate_enforce
from zocr_session import log_event

_ROOT = Path(__file__).resolve().parent
FORMAT_PATH = _ROOT / "data" / "zocr-video-format.json"
VIDEO_DIR = _ROOT / "out" / "video"
INDEX_PATH = _ROOT / "data" / "video-index.jsonl"
ACTIVE_PATH = _ROOT / "data" / "video-active.json"
MAGIC = b"ZOCR"

_lock = threading.Lock()
_state: dict[str, Any] = {
    "running": False,
    "profile": "idle",
    "prefer": "auto",
    "session_id": None,
    "seq": 0,
    "started": None,
    "adaptive_scale": 1.0,
    "fabric_nm_per_px": 250.0,
    "thread": None,
    "stop_event": None,
    "ai_tune": None,
}
_load_ema: float = 0.0
_enhance_override: bool | None = None
_bullet_rail: Any = None


def bullet_train_profile(profile: str | None = None, prof: dict[str, Any] | None = None) -> bool:
    if os.environ.get("ZOCR_BULLET_TRAIN", "").strip().lower() in ("1", "true", "yes"):
        return True
    spec = prof or profile_spec(profile or "watch")
    if spec.get("bullet_train"):
        return True
    fmt = load_format()
    return bool(fmt.get("bullet_train", {}).get("enabled", True)) and str(profile or "").startswith("bullet")


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_format() -> dict[str, Any]:
    try:
        return json.loads(FORMAT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"format_id": "ZOCRSM1", "profiles": {}}


def fast_path_enabled() -> bool:
    global _enhance_override
    if os.environ.get("ZOCR_VIDEO_ENHANCE", "").strip().lower() in ("1", "true", "yes"):
        return False
    if _enhance_override is True:
        return False
    if _enhance_override is False:
        return True
    fmt = load_format()
    return bool(fmt.get("fast_path", {}).get("default", True))


def video_enhance(*, enable: bool | None = None) -> dict[str, Any]:
    """Toggle on-demand eye/stereo rig on video frames (disables fast path)."""
    global _enhance_override
    if enable is not None:
        _enhance_override = enable
    return {
        "ok": True,
        "enhance": not fast_path_enabled(),
        "fast_path": fast_path_enabled(),
        "format": "ZOCRSM1",
    }


def unpack_envelope(data: bytes) -> tuple[bytes, dict[str, Any]] | None:
    """WRDT-inspired verify — magic, sizes, sha256 must match payload."""
    if len(data) < 52:
        return None
    magic, ver, method, flags, orig_size, payload_len, digest = struct.unpack(
        "<4sBBHQI32s", data[:52],
    )
    if magic != MAGIC:
        return None
    payload = data[52 : 52 + payload_len]
    if len(payload) != payload_len or len(payload) != orig_size:
        return None
    if hashlib.sha256(payload).digest() != digest:
        return None
    return payload, {
        "version": ver,
        "method": method,
        "flags": flags,
        "original_size": orig_size,
        "payload_length": payload_len,
        "sha256": digest.hex(),
    }


def verify_envelope(path: Path) -> dict[str, Any]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        return {"ok": False, "path": str(path), "error": str(exc)}
    unpacked = unpack_envelope(data)
    if not unpacked:
        return {"ok": False, "path": str(path), "error": "envelope_invalid"}
    _payload, meta = unpacked
    return {"ok": True, "path": str(path), "format": "ZOCRSM1", **meta}


def verify_video_index(*, tail: int = 20) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    if INDEX_PATH.is_file():
        for line in INDEX_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    rows = rows[-max(1, tail) :]
    checks: list[dict[str, Any]] = []
    ok_count = 0
    for row in rows:
        env = row.get("envelope")
        if not env:
            checks.append({"seq": row.get("seq"), "ok": False, "error": "no_envelope"})
            continue
        v = verify_envelope(Path(env))
        checks.append({"seq": row.get("seq"), "session_id": row.get("session_id"), **v})
        if v.get("ok"):
            ok_count += 1
    return {
        "ok": ok_count == len(checks) and len(checks) > 0,
        "format": "ZOCRSM1",
        "checked": len(checks),
        "ok_count": ok_count,
        "frames": checks,
    }


def video_profiles() -> dict[str, Any]:
    fmt = load_format()
    return fmt.get("profiles", load_mandate().get("fps_profiles", {}))


def _zocr_tune_overrides() -> dict[str, Any]:
    with _lock:
        t = dict(_state.get("ai_tune") or {})
    if t:
        return t
    return {}


def profile_spec(name: str) -> dict[str, Any]:
    zocr = video_profiles().get(name, video_profiles().get("watch", {"fps": 2, "max_width": 1280}))
    preset = _grkmf_profile_name(name)
    resolved = grkmf.resolve(preset, {**zocr, **_zocr_tune_overrides()})
    return {**zocr, **resolved, "profile": name}


def video_tune_reset() -> dict[str, Any]:
    grkmf.tune_reset()
    with _lock:
        _state["ai_tune"] = None
    _persist()
    return {"ok": True, "format": "ZOCRSM1", "grkmf": grkmf.FORMAT_ID, "resolved": grkmf.resolve()}


def video_tune(
    *,
    mode: str | None = None,
    width: int | float | None = None,
    height: int | float | None = None,
    max_width: int | float | None = None,
    fps: float | None = None,
    refresh_hz: float | None = None,
    gop: int | None = None,
    jpeg_quality: int | None = None,
    ai_locked: bool | None = None,
    preset: str | None = None,
    reason: str = "zocr_api",
) -> dict[str, Any]:
    """AI-tunable fps + resolution — whatever, on demand."""
    with _lock:
        cur = dict(_state.get("ai_tune") or {})
    if preset:
        cur["preset"] = preset
    result = grkmf.tune_apply(
        mode=mode,
        width=width,
        height=height,
        max_width=max_width,
        fps=fps,
        refresh_hz=refresh_hz,
        gop=gop,
        jpeg_quality=jpeg_quality,
        ai_locked=ai_locked,
        preset=preset or _grkmf_profile_name(_state.get("profile", "watch")),
        reason=reason,
    )
    with _lock:
        _state["ai_tune"] = {
            k: result.get(k)
            for k in ("mode", "width", "height", "max_width", "fps", "refresh_hz", "gop", "jpeg_quality", "ai_locked")
            if result.get(k) is not None
        }
    _persist()
    return {"ok": True, "format": "ZOCRSM1", "grkmf": grkmf.FORMAT_ID, "resolved": result, "doctrine": grkmf.tune_doctrine()}


def video_ai_tune(*, load_ms: float | None = None, goal: str | None = None) -> dict[str, Any]:
    with _lock:
        prof = _state.get("profile", "watch")
    result = grkmf.ai_tune(
        load_ms=load_ms,
        preset=_grkmf_profile_name(prof),
        goal=goal,
    )
    with _lock:
        _state["ai_tune"] = {
            k: result.get(k)
            for k in ("mode", "width", "height", "max_width", "fps", "refresh_hz", "gop", "jpeg_quality")
            if result.get(k) is not None
        }
    _persist()
    return {"ok": True, "resolved": result}


def _fabric_nm(scale: float, profile: str) -> float:
    fmt = load_format()
    ad = fmt.get("adaptive", {})
    floor = float(ad.get("fabric_nm_floor", 250.0))
    ceil = float(ad.get("fabric_nm_ceiling", 50.0))
    prof = profile_spec(profile)
    if prof.get("fabric_nm_per_px"):
        base = float(prof["fabric_nm_per_px"])
    else:
        base = floor - (floor - ceil) * min(1.0, scale / 2.0)
    return round(base / max(scale, 0.25), 2)


def _ride_adaptive(capture_ms: float, profile: str) -> float:
    """AMOURANTHRTX-style tide — scale rides smoothed capture load."""
    global _load_ema
    _load_ema = _load_ema * 0.85 + capture_ms * 0.15
    fmt = load_format()
    tiers = fmt.get("adaptive", {}).get("scale_tiers", [0.5, 0.75, 1.0, 1.25, 1.5])
    prof = profile_spec(profile)
    target_ms = 1000.0 / max(float(prof.get("fps", 2)), 0.1)
    ratio = _load_ema / target_ms
    with _lock:
        cur = float(_state.get("adaptive_scale", 1.0))
    if ratio > 1.15 and cur > tiers[0]:
        nxt = max(tiers[0], cur - 0.25)
    elif ratio < 0.6 and cur < tiers[-1]:
        nxt = min(tiers[-1], cur + 0.25)
    else:
        nxt = cur
    with _lock:
        _state["adaptive_scale"] = nxt
        _state["fabric_nm_per_px"] = _fabric_nm(nxt, profile)
    try:
        video_ai_tune(load_ms=_load_ema, goal="min_latency" if ratio > 1.15 else "max_quality" if ratio < 0.55 else None)
    except Exception:
        pass
    return nxt


def _wrdt_seal_frame(png: Path, *, meta: dict[str, Any]) -> bytes | None:
    """WRDT-inspired ZOCR frame envelope — magic + sha256 + payload."""
    try:
        raw = png.read_bytes()
    except OSError:
        return None
    digest = hashlib.sha256(raw).digest()
    header = struct.pack(
        "<4sBBHQI32s",
        MAGIC,
        1,
        1,
        0,
        len(raw),
        len(raw),
        digest,
    )
    return header + raw


def _resize_for_tide(path: Path, max_width: int, scale: float, *, fast: bool = False) -> Path:
    if max_width <= 0 or scale >= 1.5:
        return path
    try:
        from PIL import Image
        img = Image.open(path)
        w, h = img.size
        target_w = min(max_width, int(w * scale))
        if target_w >= w:
            return path
        target_h = max(1, int(h * target_w / w))
        out = path.parent / f"{path.stem}_tide{target_w}.png"
        resample = Image.Resampling.BILINEAR if fast else Image.Resampling.LANCZOS
        img.resize((target_w, target_h), resample).save(out, optimize=not fast)
        return out if out.is_file() else path
    except Exception:
        return path


def _capture_bullet_direct(max_width: int = 3840) -> Path | None:
    """Bullet train ingest — direct silent grab, no preserve/pattern/offense stack."""
    import tempfile
    from zocr_capture import capture_grim, capture_mss, capture_xwd_silent
    from zocr_kill import check as kill_check

    if not kill_check("capture").get("ok"):
        return None
    out = Path(tempfile.gettempdir()) / f"zocr-bullet-{os.getpid()}.png"
    path = None
    if os.environ.get("WAYLAND_DISPLAY"):
        path = capture_grim(out)
    if not path:
        path = capture_mss(out)
    if not path:
        path = capture_xwd_silent(out)
    if not path:
        hold = _ROOT / "data" / "preserve" / "last-good.png"
        if hold.is_file():
            return hold
        return None
    return grkmf.resize_max(path, max_width, 1.0, fast=True)


def _png_to_jpeg_fast(png: Path, *, quality: int | None = None) -> bytes:
    fmt = load_format()
    q = quality if quality is not None else int(fmt.get("bullet_train", {}).get("jpeg_quality", 72))
    return grkmf.png_to_jpeg(png, quality=q, fast=True)


def _capture_video_frame(
    session_id: str,
    seq: int,
    prefer: str,
    profile: str,
    *,
    enhance: bool = False,
) -> dict[str, Any]:
    prof = profile_spec(profile)
    if bullet_train_profile(profile, prof) and not enhance:
        t0 = time.monotonic()
        max_w = int(prof.get("max_width", 3840))
        path = _capture_bullet_direct(max_w)
        if not path:
            return {"ok": False, "path": None, "source": "none", "video": {}}
        scale = _ride_adaptive((time.monotonic() - t0) * 1000.0, profile)
        fabric = _fabric_nm(scale, profile)
        fmt = load_format()
        seal_n = int(fmt.get("bullet_train", {}).get("seal_every_n", 120))
        row = {
            "schema": "zocrsm-frame/v1",
            "ts": _ts(),
            "format": "ZOCRSM1",
            "seq": seq,
            "session_id": session_id,
            "image": str(path),
            "profile": profile,
            "resolution": prof.get("resolution", "4K"),
            "adaptive_scale": scale,
            "fabric_nm_per_px": fabric,
            "fast_path": True,
            "bullet_train": True,
            "source": "bullet_direct",
            "preserved": False,
        }
        if seq == 1 or seq % seal_n == 0:
            VIDEO_DIR.mkdir(parents=True, exist_ok=True)
            sess = VIDEO_DIR / session_id
            sess.mkdir(parents=True, exist_ok=True)
            from shutil import copy2
            dst = sess / f"frame_{seq:06d}.png"
            try:
                copy2(path, dst)
                row["image"] = str(dst)
                envelope = _wrdt_seal_frame(dst, meta={"seq": seq, "profile": profile})
                if envelope:
                    env_path = sess / f"frame_{seq:06d}.zocrsm"
                    env_path.write_bytes(envelope)
                    row["envelope"] = str(env_path)
                with INDEX_PATH.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
            except OSError:
                pass
        return {"ok": True, "path": path, "source": "bullet_direct", "preserved": False, "video": row}

    from shutil import copy2
    from zocr_preserve import acquire_preserved

    t0 = time.monotonic()
    acq = acquire_preserved(prefer=prefer, allow_hold=True, profile=profile)
    image = acq.get("path")
    if not image:
        return acq

    scale = _ride_adaptive((time.monotonic() - t0) * 1000.0, profile)
    max_w = int(prof.get("max_width", 1280))
    path = Path(image)
    path = _resize_for_tide(path, max_w, scale, fast=bullet_train_profile(profile, prof))

    if enhance and not fast_path_enabled():
        from zocr_stereo import perceive_rig
        rig = perceive_rig(path)
        for e in rig.get("eyes", []):
            if e.get("path"):
                path = Path(e["path"])
                break
        acq["rig"] = rig

    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    sess = VIDEO_DIR / session_id
    sess.mkdir(parents=True, exist_ok=True)
    dst = sess / f"frame_{seq:06d}.png"
    try:
        copy2(path, dst)
    except OSError:
        return {**acq, "path": None}

    from zocr_pattern import secure_frame
    src = acq.get("source") or "internal"
    pat = secure_frame(
        dst, session_id=session_id, seq=seq, source=src,
        skip_foreign=bool(acq.get("preserved")) or "hold" in src or "synthetic" in src,
    )

    envelope = _wrdt_seal_frame(dst, meta={"seq": seq, "profile": profile})
    env_path = sess / f"frame_{seq:06d}.zocrsm"
    if envelope:
        env_path.write_bytes(envelope)

    fabric = _fabric_nm(scale, profile)
    row = {
        "schema": "zocrsm-frame/v1",
        "ts": _ts(),
        "format": "ZOCRSM1",
        "seq": seq,
        "session_id": session_id,
        "image": str(dst),
        "envelope": str(env_path) if env_path.is_file() else None,
        "profile": profile,
        "adaptive_scale": scale,
        "fabric_nm_per_px": fabric,
        "fast_path": not enhance,
        "source": acq.get("source"),
        "preserved": acq.get("preserved", False),
        "pattern": {
            "stamped": pat.get("stamped"),
            "weave": pat.get("weave"),
            "threats": pat.get("threats", []),
            "foreign": pat.get("foreign", []),
        },
    }
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    with INDEX_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

    return {**acq, "path": dst, "video": row}


def _png_to_jpeg(png: Path, quality: int = 82) -> bytes:
    from PIL import Image
    img = Image.open(png)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


def video_status() -> dict[str, Any]:
    fmt = load_format()
    with _lock:
        st = dict(_state)
    st.pop("thread", None)
    st.pop("stop_event", None)
    prof = profile_spec(st.get("profile", "idle"))
    return {
        "schema": "zocr-video-status/v1",
        "ts": _ts(),
        "format": fmt.get("format_id", "ZOCRSM1"),
        "grkmf": grkmf.FORMAT_ID,
        "codec": grkmf.CODEC_ID,
        "whole_new": True,
        "running": st.get("running", False),
        "profile": st.get("profile", "idle"),
        "fps": float(prof.get("fps", 0)),
        "field_power": prof.get("power", "minimal"),
        "prefer": st.get("prefer", "auto"),
        "session_id": st.get("session_id"),
        "seq": st.get("seq", 0),
        "adaptive_scale": st.get("adaptive_scale", 1.0),
        "fabric_nm_per_px": st.get("fabric_nm_per_px", 250.0),
        "fast_path": fast_path_enabled(),
        "bullet_train": bullet_train_profile(st.get("profile", "idle")),
        "ai_tune": _state.get("ai_tune") or grkmf.active_tune(),
        "ai_tunable": True,
        "resolved": profile_spec(st.get("profile", "idle")),
        "profiles": video_profiles(),
        "transports": fmt.get("transports", {}),
        "mandate": load_mandate().get("mandate_id"),
    }


def _persist() -> None:
    ACTIVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        doc = {k: v for k, v in _state.items() if k not in ("thread", "stop_event")}
    ACTIVE_PATH.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def _video_loop(session_id: str, profile: str, prefer: str, stop: threading.Event) -> None:
    prof = profile_spec(profile)
    interval = 1.0 / float(prof.get("fps", 1)) if prof.get("fps", 0) > 0 else 3600.0
    enhance = not fast_path_enabled()
    while not stop.is_set():
        from zocr_kill import is_tripped
        if is_tripped("stream") or is_tripped("vision") or is_tripped("mjpeg"):
            break
        with _lock:
            if not _state.get("running"):
                break
            _state["seq"] = int(_state.get("seq", 0)) + 1
            seq = _state["seq"]
        t0 = time.monotonic()
        try:
            acq = _capture_video_frame(session_id, seq, prefer, profile, enhance=enhance)
            path = acq.get("path")
            if path and Path(path).is_file() and not acq.get("preserved"):
                seal_frame(
                    Path(path), seq=seq,
                    fps_profile=profile,
                    power_mode=str(prof.get("power", "balanced")),
                )
            v = acq.get("video", {})
            log_event(
                "video_frame",
                ok=True,
                format="ZOCRSM1",
                seq=seq,
                profile=profile,
                fabric_nm=v.get("fabric_nm_per_px"),
                scale=v.get("adaptive_scale"),
                fast_path=v.get("fast_path"),
                image=str(path),
            )
        except Exception as exc:
            log_event("video_frame", ok=False, error=str(exc), seq=seq)
        elapsed = time.monotonic() - t0
        if stop.wait(max(0.02, interval - elapsed)):
            break
    _persist()


def video_start(
    *,
    profile: str = "watch",
    prefer: str = "auto",
    client_host: str | None = None,
    tune: dict[str, Any] | None = None,
) -> dict[str, Any]:
    gate = mandate_enforce("stream_start", client_host=client_host)
    if not gate.get("ok"):
        return {"ok": False, "error": gate.get("error", "mandate_gate"), **gate}
    if tune:
        video_tune(**{k: v for k, v in tune.items() if v is not None}, reason="stream_start")
    prof = profile_spec(profile)
    if float(prof.get("fps", 0)) <= 0:
        return {"ok": False, "error": "profile_idle", "hint": "Pick patrol/watch/tactical/engage/burst/submicron"}
    video_stop()
    session_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stop = threading.Event()
    scale = 1.0
    with _lock:
        _state.update({
            "running": True,
            "profile": profile,
            "prefer": prefer,
            "session_id": session_id,
            "seq": 0,
            "started": _ts(),
            "adaptive_scale": scale,
            "fabric_nm_per_px": _fabric_nm(scale, profile),
            "stop_event": stop,
        })
        th = threading.Thread(
            target=_video_loop,
            args=(session_id, profile, prefer, stop),
            name=f"zocrsm-{profile}",
            daemon=True,
        )
        _state["thread"] = th
        th.start()
    _persist()
    log_event("video_start", ok=True, format="ZOCRSM1", profile=profile, session_id=session_id)
    st = video_status()
    st["ok"] = True
    st["gate"] = gate
    return st


def video_stop() -> dict[str, Any]:
    with _lock:
        stop = _state.get("stop_event")
        if stop:
            stop.set()
        _state["running"] = False
        th = _state.get("thread")
    if th and th.is_alive():
        th.join(timeout=3.0)
    with _lock:
        _state["profile"] = "idle"
        _state["thread"] = None
        _state["stop_event"] = None
    _persist()
    log_event("video_stop", ok=True, format="ZOCRSM1")
    st = video_status()
    st["ok"] = True
    return st


def _mjpeg_bullet_generator(
    *,
    profile: str,
    max_frames: int = 0,
    ingest_while_emit: bool = False,
) -> Generator[bytes, None, None]:
    global _bullet_rail
    fabric = _fabric_nm(1.0, profile)

    def _tripped() -> bool:
        from zocr_kill import is_tripped
        return bool(is_tripped("mjpeg") or is_tripped("vision") or is_tripped("stream"))

    gen = grkmf.bullet_mjpeg_generator(
        profile_name=_grkmf_profile_name(profile),
        max_frames=max_frames,
        capture_fn=_capture_bullet_direct,
        ingest_while_emit=ingest_while_emit,
        fabric_nm=fabric,
        trip_check=_tripped,
        tune={**profile_spec(profile), **_zocr_tune_overrides()},
    )
    _bullet_rail = True
    try:
        yield from gen
    finally:
        _bullet_rail = None


def _grkmf_profile_name(zocr_profile: str) -> str:
    """Map ZOCR profiles → GRKMF preset hints (AI tune overrides actual values)."""
    mapping = {
        "idle": "legacy_vga",
        "sentinel": "legacy_vga",
        "patrol": "legacy_hd",
        "watch": "combat",
        "tactical": "combat_tactical",
        "engage": "combat_engage",
        "burst": "stream_4k",
        "submicron": "cinema_4k",
        "ultra_4k": "stream_4k_240",
        "bullet_120": "dodge_240",
        "bullet_240": "dodge_240",
        "bullet_480": "dodge_240",
        "combat": "combat",
        "cinema_16k": "cinema_16k",
        "cinema_8k": "cinema_8k",
    }
    if zocr_profile in mapping:
        return mapping[zocr_profile]
    if bullet_train_profile(zocr_profile):
        return "dodge_240"
    if zocr_profile.startswith("combat"):
        return "combat"
    return "stream_4k"


def mjpeg_generator(
    *,
    profile: str = "watch",
    prefer: str = "auto",
    client_host: str | None = None,
    max_frames: int = 0,
    enhance: bool | None = None,
) -> Generator[bytes, None, None]:
    """ZOCRSM_MJPEG — fast path default, whole new transport."""
    gate = mandate_enforce("mjpeg", client_host=client_host)
    if not gate.get("ok"):
        yield b"--frame\r\nContent-Type: application/json\r\n\r\n"
        yield json.dumps({"error": gate.get("error"), **gate}).encode()
        yield b"\r\n"
        return

    if bullet_train_profile(profile) and not enhance:
        yield from _mjpeg_bullet_generator(profile=profile, max_frames=max_frames)
        return

    prof = profile_spec(profile)
    fps = float(prof.get("fps", 0)) or float(os.environ.get("ZOCR_MJPEG_FPS", "2"))
    interval = 1.0 / fps
    enhance = (not fast_path_enabled()) if enhance is None else enhance
    boundary = b"--frame"
    session_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    seq = 0

    while True:
        from zocr_kill import is_tripped
        if is_tripped("mjpeg") or is_tripped("vision") or is_tripped("stream"):
            break
        if max_frames > 0 and seq >= max_frames:
            break
        seq += 1
        t0 = time.monotonic()
        acq = _capture_video_frame(session_id, seq, prefer, profile, enhance=enhance)
        path = acq.get("path")
        v = acq.get("video", {})
        if path and Path(path).is_file():
            if not acq.get("preserved") and not acq.get("video", {}).get("bullet_train"):
                seal_frame(
                    Path(path), seq=seq,
                    fps_profile=profile,
                    power_mode=str(prof.get("power", "balanced")),
                )
            try:
                jpeg = _png_to_jpeg_fast(Path(path)) if bullet_train_profile(profile) else _png_to_jpeg(Path(path))
                yield boundary + b"\r\nContent-Type: image/jpeg\r\n"
                yield b"X-ZOCR-Format: ZOCRSM1\r\n"
                yield b"X-ZOCR-Fabric-nm: " + str(v.get("fabric_nm_per_px", "")).encode() + b"\r\n"
                yield b"X-ZOCR-Scale: " + str(v.get("adaptive_scale", 1.0)).encode() + b"\r\n"
                yield b"X-ZOCR-Preserved: " + str(acq.get("preserved", False)).encode() + b"\r\n"
                yield b"X-ZOCR-Fast-Path: " + str(v.get("fast_path", True)).encode() + b"\r\n"
                yield b"Content-Length: " + str(len(jpeg)).encode() + b"\r\n\r\n"
                yield jpeg
                yield b"\r\n"
            except Exception:
                pass
        elapsed = time.monotonic() - t0
        time.sleep(max(0.02, interval - elapsed))


def video_benchmark(
    *,
    profiles: list[str] | None = None,
    frames: int = 0,
    duration_sec: float = 2.0,
) -> dict[str, Any]:
    """Benchmark ZOCRSM1 — bullet dodge 240/480/4K emit vs ingest."""
    import statistics

    targets = profiles or ["watch", "bullet_120", "bullet_240", "ultra_4k"]
    results: list[dict[str, Any]] = []

    for profile in targets:
        prof = profile_spec(profile)
        if float(prof.get("fps", 0)) <= 0 and not bullet_train_profile(profile, prof):
            continue
        is_bullet = bullet_train_profile(profile, prof)
        target_fps = float(prof.get("fps", 0))
        max_f = frames or max(1, int(target_fps * duration_sec))

        if is_bullet:
            t0 = time.perf_counter()
            t_emit: float | None = None
            gen = _mjpeg_bullet_generator(profile=profile, max_frames=max_f)
            nbytes = 0
            nframes = 0
            widths: list[int] = []
            for chunk in gen:
                nbytes += len(chunk)
                if b"X-ZOCR-Width: " in chunk or b"X-GRKMF-Width: " in chunk:
                    for line in chunk.split(b"\r\n"):
                        if line.startswith(b"X-ZOCR-Width: ") or line.startswith(b"X-GRKMF-Width: "):
                            try:
                                widths.append(int(line.split(b": ", 1)[1]))
                            except (ValueError, IndexError):
                                pass
                if b"Content-Type: image/jpeg" in chunk:
                    nframes += 1
                    if nframes == 1:
                        t_emit = time.perf_counter()
            elapsed = time.perf_counter() - t0
            emit_elapsed = (time.perf_counter() - t_emit) if t_emit and nframes > 1 else 0.0
            emit_frames = max(0, nframes - 1)
            achieved = emit_frames / emit_elapsed if emit_elapsed > 0 else 0
            results.append({
                "profile": profile,
                "mode": "bullet_train",
                "resolution": prof.get("resolution", "4K"),
                "max_width": prof.get("max_width"),
                "target_fps": target_fps,
                "refresh_hz": prof.get("refresh_hz", target_fps),
                "frames": nframes,
                "target_frames": max_f,
                "elapsed_sec": round(elapsed, 3),
                "emit_elapsed_sec": round(emit_elapsed, 3),
                "emit_fps": round(achieved, 1),
                "emit_headroom": round(achieved / target_fps, 2) if target_fps > 0 else None,
                "bytes_total": nbytes,
                "max_width_seen": max(widths) if widths else 0,
                "4k_ok": (max(widths) if widths else 0) >= 3840,
                "fabric_nm_per_px": prof.get("fabric_nm_per_px"),
            })
        else:
            times: list[float] = []
            ok = 0
            sid = f"bench_{profile}"
            n = min(3, max_f)
            for seq in range(1, n + 1):
                t1 = time.perf_counter()
                acq = _capture_video_frame(sid, seq, "auto", profile, enhance=False)
                times.append(time.perf_counter() - t1)
                if acq.get("path"):
                    ok += 1
            mean_ms = statistics.mean(times) * 1000 if times else 0
            results.append({
                "profile": profile,
                "mode": "field",
                "target_fps": target_fps,
                "frames": n,
                "ok_frames": ok,
                "mean_ms": round(mean_ms, 1),
                "achieved_fps": round(1000.0 / mean_ms, 2) if mean_ms > 0 else 0,
            })

    bullet_hits = [r for r in results if r.get("mode") == "bullet_train"]
    best_emit = max((r.get("emit_fps", 0) for r in bullet_hits), default=0)
    report = {
        "schema": "zocrsm1-benchmark/v2",
        "ts": _ts(),
        "format": "ZOCRSM1",
        "bullet_train": load_format().get("bullet_train", {}),
        "profiles": results,
        "summary": {
            "best_emit_fps": best_emit,
            "dodge_rule": "double fps — dodge the bullet",
            "target_240_met": any(
                r.get("profile") in ("bullet_120", "ultra_4k")
                and (r.get("emit_fps") or 0) >= (r.get("target_fps") or 0) * 0.92
                for r in bullet_hits
            ),
            "target_480_met": any(
                r.get("profile") in ("bullet_240", "bullet_480")
                and (r.get("emit_fps") or 0) >= (r.get("target_fps") or 0) * 0.92
                for r in bullet_hits
            ),
            "4k_emit_ok": any(r.get("4k_ok") for r in bullet_hits),
        },
    }
    out = _ROOT / "data" / "zocrsm1-benchmark.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def export_grkm_movie(
    sources: list[str | Path],
    out: str | Path,
    *,
    profile: str = "cinema_4k",
    title: str = "",
) -> dict[str, Any]:
    """Export sealed .grkm — proprietary 4K cinema, not MPEG."""
    return grkmf.encode_movie(
        [Path(s) for s in sources],
        Path(out),
        profile_name=profile,
        title=title,
        creator="ZOCR/GRKMF1",
    )


def verify_grkm_movie(path: str | Path) -> dict[str, Any]:
    return grkmf.verify_grkm(Path(path))


def grkmf_market_compare() -> dict[str, Any]:
    return grkmf.compare_summary()


def format_doctrine() -> dict[str, Any]:
    fmt = load_format()
    return {
        "schema": "zocr-video-doctrine/v1",
        "format_id": fmt.get("format_id"),
        "grkmf": grkmf.FORMAT_ID,
        "codec": grkmf.CODEC_ID,
        "proprietary": True,
        "not_mpeg": True,
        "title": fmt.get("title"),
        "rule": fmt.get("rule"),
        "lineage": fmt.get("lineage"),
        "adaptive": fmt.get("adaptive"),
        "fast_path": fmt.get("fast_path"),
        "grkmf_profiles": list(grkmf.profiles().keys()),
        "profiles": list(video_profiles().keys()),
    }


def main() -> int:
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        print(json.dumps(video_status(), indent=2))
        return 0
    if cmd == "doctrine":
        print(json.dumps(format_doctrine(), indent=2))
        return 0
    if cmd == "verify":
        tail = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        print(json.dumps(verify_video_index(tail=tail), indent=2))
        return 0
    if cmd == "benchmark":
        profs = sys.argv[2:] if len(sys.argv) > 2 else None
        print(json.dumps(video_benchmark(profiles=profs), indent=2))
        return 0
    if cmd == "compare":
        print(json.dumps(grkmf_market_compare(), indent=2))
        return 0
    if cmd == "export-grkm":
        src = Path(sys.argv[2]) if len(sys.argv) > 2 else None
        out = Path(sys.argv[3]) if len(sys.argv) > 3 else _ROOT / "out" / "movie.grkm"
        prof = sys.argv[4] if len(sys.argv) > 4 else "cinema_4k"
        if not src:
            print(json.dumps({"error": "usage: export-grkm <png|dir> <out.grkm> [profile]"}, indent=2))
            return 1
        if src.is_dir():
            print(json.dumps(grkmf.export_from_png_dir(src, out, profile_name=prof), indent=2))
        else:
            frames = sorted(src.parent.glob(src.name)) if "*" in src.name else [src]
            print(json.dumps(export_grkm_movie(frames, out, profile=prof), indent=2))
        return 0
    print(json.dumps({"error": "usage: zocr_video.py [status|doctrine|verify|benchmark|compare|export-grkm]"}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())