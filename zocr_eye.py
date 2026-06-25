"""ZOCR ocular spectrum v2 — cone sensitivity, adaptation, foveal acuity; Grok16 field_opt tuned."""
from __future__ import annotations

import json
import math
import os
import tempfile
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from zocr_grok16 import grok16_eye_tune, grok16_eye_witness, grok16_profile_for_eye, grok16_profile_for_mode
from zocr_session import log_event

_ROOT = Path(__file__).resolve().parent
DOCTRINE_PATH = _ROOT / "data" / "ocular-spectrum.json"
FINAL_PATH = _ROOT / "data" / "final-eyeball.json"
FINAL_STATE_PATH = _ROOT / "data" / "final-eyeball-state.json"
STATE_PATH = _ROOT / "data" / "eye-state.json"
TEACH_LOG = _ROOT / "data" / "eye-teach.jsonl"
EYE_OUT = _ROOT / "out" / "eye"
ENGINE = "cone_v2"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clamp(v: float) -> int:
    return max(0, min(255, int(round(v))))


def _srgb_to_linear(c: float) -> float:
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(c: float) -> int:
    c = max(0.0, min(1.0, c))
    v = c * 12.92 if c <= 0.0031308 else 1.055 * (c ** (1.0 / 2.4)) - 0.055
    return _clamp(v * 255.0)


def load_doctrine() -> dict[str, Any]:
    try:
        return json.loads(DOCTRINE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema": "zocr-ocular-spectrum/v1", "default_profile": "human", "profiles": {}}


def _load_state() -> dict[str, Any]:
    if STATE_PATH.is_file():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    doc = load_doctrine()
    return {
        "schema": "zocr-eye-state/v1",
        "active_profile": doc.get("default_profile", "human"),
        "taught": [],
    }


def _save_state(st: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    st["updated"] = _ts()
    STATE_PATH.write_text(json.dumps(st, indent=2) + "\n", encoding="utf-8")


def list_profiles() -> list[dict[str, Any]]:
    doc = load_doctrine()
    profiles = doc.get("profiles", {})
    out: list[dict[str, Any]] = []
    for pid, p in profiles.items():
        out.append({
            "id": pid,
            "label": p.get("label", pid),
            "class": p.get("class", ""),
            "range_nm": p.get("range_nm", []),
            "receptors": p.get("receptors", []),
            "mode": p.get("mode", "matrix"),
            "engine": p.get("engine", ENGINE),
            "teach": p.get("teach", ""),
        })
    return sorted(out, key=lambda x: x["id"])


def active_profile() -> str:
    env = os.environ.get("ZOCR_EYE", "").strip()
    if env:
        return env
    return _load_state().get("active_profile", load_doctrine().get("default_profile", "human"))


def profile_spec(profile_id: str | None = None) -> dict[str, Any]:
    pid = profile_id or active_profile()
    profiles = load_doctrine().get("profiles", {})
    return profiles.get(pid, profiles.get("human", {"matrix": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]}))


def teach(profile_id: str, *, source: str = "api") -> dict[str, Any]:
    doc = load_doctrine()
    if profile_id not in doc.get("profiles", {}):
        return {"ok": False, "error": "unknown_profile", "profile": profile_id}

    st = _load_state()
    prev = st.get("active_profile")
    st["active_profile"] = profile_id
    taught = st.get("taught", [])
    if profile_id not in taught:
        taught.append(profile_id)
    st["taught"] = taught
    _save_state(st)

    row = {
        "ts": _ts(),
        "profile": profile_id,
        "previous": prev,
        "source": source,
        "label": doc["profiles"][profile_id].get("label"),
        "class": doc["profiles"][profile_id].get("class"),
    }
    TEACH_LOG.parent.mkdir(parents=True, exist_ok=True)
    with TEACH_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    log_event("eye_teach", ok=True, **row)

    spec = profile_spec(profile_id)
    return {
        "ok": True,
        "profile": profile_id,
        "label": spec.get("label"),
        "class": spec.get("class"),
        "range_nm": spec.get("range_nm"),
        "receptors": spec.get("receptors"),
        "teach": spec.get("teach"),
        "engine": spec.get("engine", ENGINE),
        "previous": prev,
    }


def _receptor_activations(r: float, g: float, b: float, spec: dict[str, Any]) -> list[float]:
    """Map linear RGB to photoreceptor activations (cone/pentachromat model)."""
    rl, gl, bl = _srgb_to_linear(r), _srgb_to_linear(g), _srgb_to_linear(b)
    cones = spec.get("cones")
    if cones:
        out = []
        for c in cones:
            w = c.get("weights", [0.33, 0.33, 0.34])
            out.append(rl * w[0] + gl * w[1] + bl * w[2])
        if spec.get("uv_sensitive"):
            uv = max(0.0, bl * 1.2 - rl * 0.35)
            out.append(uv)
        return out

    matrix = spec.get("matrix", [[1, 0, 0], [0, 1, 0], [0, 0, 1]])
    return [
        matrix[0][0] * r + matrix[0][1] * g + matrix[0][2] * b,
        matrix[1][0] * r + matrix[1][1] * g + matrix[1][2] * b,
        matrix[2][0] * r + matrix[2][1] * g + matrix[2][2] * b,
    ]


def _activations_to_display(acts: list[float], spec: dict[str, Any]) -> tuple[int, int, int]:
    """Project receptor space back to displayable RGB."""
    display = spec.get("display_matrix")
    if display and len(acts) >= len(display[0]):
        r = sum(display[0][i] * acts[i] for i in range(len(display[0])))
        g = sum(display[1][i] * acts[i] for i in range(len(display[1])))
        b = sum(display[2][i] * acts[i] for i in range(len(display[2])))
        return _clamp(r), _clamp(g), _clamp(b)

    if len(acts) >= 4:
        r = acts[0] * 0.9 + acts[3] * 0.15
        g = acts[1] * 0.95 + acts[3] * 0.05
        b = acts[2] * 1.1 + acts[3] * 0.45
        return _clamp(r), _clamp(g), _clamp(b)
    return _clamp(acts[0]), _clamp(acts[1]), _clamp(acts[2])


def _active_grok16_tune(*, profile_id: str | None = None) -> dict[str, Any]:
    mode = _load_final_state().get("active_mode", "dishes")
    return grok16_eye_tune(mode=mode, eye_profile=profile_id or active_profile())


@lru_cache(maxsize=32)
def _cone_kernel_cached(profile_id: str, adapt_key: int) -> tuple[Any, ...]:
    spec = profile_spec(profile_id)
    adapt = adapt_key / 1000.0
    cones = spec.get("cones")
    display = spec.get("display_matrix")
    uv = bool(spec.get("uv_sensitive"))
    return (cones, display, uv, adapt, spec.get("matrix"))


def _cone_perceive_bytes(
    rgb: bytes,
    spec: dict[str, Any],
    *,
    tune: dict[str, Any] | None = None,
    profile_id: str | None = None,
) -> bytes:
    pid = profile_id or spec.get("id") or active_profile()
    t = tune or _active_grok16_tune(profile_id=pid)
    adapt = float(spec.get("adaptation", 0.12)) * float(t.get("adaptation_scale", 1.0))
    adapt_key = int(round(adapt * 1000))
    cones, display, uv, _, matrix = _cone_kernel_cached(pid, adapt_key)

    try:
        import numpy as np
        arr = np.frombuffer(rgb, dtype=np.uint8).reshape(-1, 3).astype(np.float32)
        c = arr / 255.0
        lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
        if cones:
            w = np.array([c.get("weights", [0.33, 0.33, 0.34]) for c in cones], dtype=np.float32)
            acts = lin @ w.T
            if uv:
                uv_ch = np.maximum(0.0, lin[:, 2] * 1.2 - lin[:, 0] * 0.35)
                acts = np.column_stack([acts, uv_ch])
        else:
            m = np.array(matrix or [[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.float32)
            acts = arr @ m.T
        mean_a = acts.mean(axis=1) / 255.0
        gain = 1.0 / (1.0 + adapt * 10.0 * mean_a)
        acts = acts * gain[:, np.newaxis]
        if display is not None:
            d = np.array(display, dtype=np.float32)
            out_rgb = acts @ d.T
        elif acts.shape[1] >= 4:
            out_rgb = np.column_stack([
                acts[:, 0] * 0.9 + acts[:, 3] * 0.15,
                acts[:, 1] * 0.95 + acts[:, 3] * 0.05,
                acts[:, 2] * 1.1 + acts[:, 3] * 0.45,
            ])
        else:
            out_rgb = acts[:, :3]
        out_rgb = np.clip(np.round(out_rgb), 0, 255).astype(np.uint8)
        return out_rgb.tobytes()
    except ImportError:
        pass

    out = bytearray(len(rgb))
    adapt_gain_k = adapt * 10.0
    for i in range(0, len(rgb), 3):
        r, g, b = rgb[i], rgb[i + 1], rgb[i + 2]
        acts = _receptor_activations(r, g, b, spec)
        mean_a = sum(acts) / max(len(acts), 1) / 255.0
        gain = 1.0 / (1.0 + adapt_gain_k * mean_a)
        acts = [a * gain for a in acts]
        nr, ng, nb = _activations_to_display(acts, spec)
        out[i], out[i + 1], out[i + 2] = nr, ng, nb
    return bytes(out)


def _apply_matrix(rgb: bytes, matrix: list[list[float]]) -> bytes:
    out = bytearray(len(rgb))
    m = matrix
    for i in range(0, len(rgb), 3):
        r, g, b = rgb[i], rgb[i + 1], rgb[i + 2]
        out[i] = _clamp(m[0][0] * r + m[0][1] * g + m[0][2] * b)
        out[i + 1] = _clamp(m[1][0] * r + m[1][1] * g + m[1][2] * b)
        out[i + 2] = _clamp(m[2][0] * r + m[2][1] * g + m[2][2] * b)
    return bytes(out)


def _thermal_overlay(img: Any) -> Any:
    from PIL import Image, ImageChops, ImageFilter
    base = img.convert("RGB")
    gray = base.convert("L").filter(ImageFilter.GaussianBlur(radius=2))
    w, h = base.size
    heat = Image.new("RGB", (w, h))
    px = gray.load()
    hp = heat.load()
    for y in range(h):
        for x in range(w):
            v = px[x, y]
            t = v / 255.0
            if t < 0.33:
                hp[x, y] = (0, int(80 * t * 3), int(60 + 195 * t))
            elif t < 0.66:
                u = (t - 0.33) / 0.33
                hp[x, y] = (int(220 * u), int(255 * u), int(255 * (1 - u)))
            else:
                u = (t - 0.66) / 0.34
                hp[x, y] = (int(180 + 75 * u), int(255 * (1 - u * 0.7)), 0)
    return ImageChops.blend(base, heat, 0.5)


def _foveal_acuity(img: Any, *, strength: float = 0.65) -> Any:
    """Raptor-style fovea — sharp center, softer periphery."""
    from PIL import Image, ImageFilter, ImageChops
    w, h = img.size
    sharp = img.filter(ImageFilter.UnsharpMask(radius=2, percent=180, threshold=2))
    soft = img.filter(ImageFilter.GaussianBlur(radius=2.5))
    mask = Image.new("L", (w, h), 0)
    mx = mask.load()
    cx, cy = w / 2.0, h / 2.0
    rx, ry = w * 0.42, h * 0.38
    for y in range(h):
        for x in range(w):
            dx = (x - cx) / rx
            dy = (y - cy) / ry
            d = min(1.0, math.sqrt(dx * dx + dy * dy))
            mx[x, y] = _clamp(255 * (1.0 - d) ** 1.8 * strength + 255 * (1.0 - strength))
    return Image.composite(sharp, soft, mask)


def _rod_scotopic(img: Any) -> Any:
    from PIL import Image, ImageEnhance
    gray = img.convert("L")
    lum = ImageEnhance.Contrast(gray).enhance(1.35)
    lum = ImageEnhance.Brightness(lum).enhance(1.08)
    return lum.convert("RGB")


def perceive(
    path: Path,
    *,
    profile_id: str | None = None,
    out_path: Path | None = None,
    on_demand: bool = False,
) -> tuple[Path | None, dict[str, Any]]:
    pid = profile_id or active_profile()
    spec = profile_spec(pid)
    mode = _load_final_state().get("active_mode", "dishes")
    tune = grok16_eye_tune(mode=mode, eye_profile=pid)
    engine = tune.get("engine", spec.get("engine", ENGINE))
    meta: dict[str, Any] = {
        "profile": pid,
        "label": spec.get("label", pid),
        "class": spec.get("class", ""),
        "range_nm": spec.get("range_nm", []),
        "receptors": spec.get("receptors", []),
        "mode": spec.get("mode", "matrix"),
        "engine": engine,
        "teach": spec.get("teach", ""),
        "perceived": pid != "human",
        "grok16": tune,
        "field_compiler": grok16_eye_witness(mode=mode, eye_profile=pid),
    }

    if not path.is_file():
        return None, meta
    if pid == "human" and spec.get("mode", "matrix") == "matrix" and not spec.get("cones"):
        meta["perceived"] = False
        return path, meta

    try:
        from zocr_cool import cool_status, eye_budget, eye_may_run, prepare_eye_image, yield_share
        meta["cool"] = cool_status()
        if not eye_may_run(on_demand=on_demand):
            meta["perceived"] = False
            meta["cool_skip"] = True
            return path, meta
        budget = eye_budget(on_demand=on_demand)
        meta["eye_budget"] = budget
    except ImportError:
        budget = {}

    try:
        from PIL import Image
    except ImportError:
        return path, {**meta, "error": "pil_missing"}

    try:
        img = Image.open(path).convert("RGB")
        img, budget_meta = prepare_eye_image(img, on_demand=on_demand)
        if budget_meta:
            meta["eye_budget"] = budget_meta
        mode = spec.get("mode", "matrix")
        allow_thermal = budget.get("allow_thermal", True) if budget else True
        allow_foveal = budget.get("allow_foveal", True) if budget else True

        if mode == "luminance":
            img = _rod_scotopic(img)
        elif mode == "thermal_overlay":
            if allow_thermal:
                img = _thermal_overlay(img)
            if spec.get("cones") or spec.get("engine", ENGINE).startswith("cone_v2"):
                raw = _cone_perceive_bytes(img.tobytes(), spec, tune=tune, profile_id=pid)
                img = Image.frombytes("RGB", img.size, raw)
            elif spec.get("matrix"):
                raw = _apply_matrix(img.tobytes(), spec["matrix"])
                img = Image.frombytes("RGB", img.size, raw)
        elif spec.get("cones") or spec.get("engine", ENGINE).startswith("cone_v2"):
            raw = _cone_perceive_bytes(img.tobytes(), spec, tune=tune, profile_id=pid)
            img = Image.frombytes("RGB", img.size, raw)
        else:
            matrix = spec.get("matrix", [[1, 0, 0], [0, 1, 0], [0, 0, 1]])
            raw = _apply_matrix(img.tobytes(), matrix)
            img = Image.frombytes("RGB", img.size, raw)

        foveal_base = float(spec.get("foveal_strength", 0.65))
        foveal_strength = min(1.0, foveal_base * float(tune.get("foveal_scale", 1.0)))
        if allow_foveal and (spec.get("post") == "sharpen" or spec.get("foveal")):
            img = _foveal_acuity(img, strength=foveal_strength)

        EYE_OUT.mkdir(parents=True, exist_ok=True)
        dst = out_path or EYE_OUT / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{pid}.png"
        img.save(dst, optimize=True)
        meta["path"] = str(dst)
        try:
            yield_share(on_demand=on_demand)
        except Exception:
            pass
        return dst if dst.is_file() else path, meta
    except Exception as exc:
        return path, {**meta, "error": str(exc)}


def perceive_if_active(path: Path | str | None, *, on_demand: bool = False) -> tuple[Path | None, dict[str, Any]]:
    if not path:
        return None, {"profile": active_profile(), "perceived": False}
    path = Path(path)
    pid = active_profile()
    if pid == "human" and not profile_spec("human").get("cones"):
        spec = profile_spec("human")
        return path, {
            "profile": "human",
            "label": spec.get("label", "Human trichromat"),
            "perceived": False,
            "engine": ENGINE,
            "teach": spec.get("teach", ""),
        }
    out, meta = perceive(path, profile_id=pid, on_demand=on_demand)
    return out, meta


def load_final_eyeball() -> dict[str, Any]:
    try:
        return json.loads(FINAL_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema": "zocr-final-eyeball/v1", "modes": {}, "manners": {}}


def _load_final_state() -> dict[str, Any]:
    if FINAL_STATE_PATH.is_file():
        try:
            return json.loads(FINAL_STATE_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    doc = load_final_eyeball()
    return {
        "schema": "zocr-final-eyeball-state/v1",
        "active_mode": "dishes",
        "active_voice": "robotics_brief",
    }


def _save_final_state(st: dict[str, Any]) -> None:
    FINAL_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    st["updated"] = _ts()
    FINAL_STATE_PATH.write_text(json.dumps(st, indent=2) + "\n", encoding="utf-8")


def list_final_modes() -> list[dict[str, Any]]:
    doc = load_final_eyeball()
    modes = doc.get("modes", {})
    return [
        {
            "id": mid,
            "label": m.get("label", mid),
            "eye_profile": m.get("eye_profile"),
            "rig_preset": m.get("rig_preset"),
            "video_profile": m.get("video_profile"),
        }
        for mid, m in sorted(modes.items())
    ]


def speak_final(
    *,
    mode: str | None = None,
    voice: str | None = None,
) -> dict[str, Any]:
    """Return Final Eyeball doctrine in the chosen manner of speaking."""
    doc = load_final_eyeball()
    st = _load_final_state()
    mid = mode or st.get("active_mode", "dishes")
    voc = voice or st.get("active_voice", "robotics_brief")
    modes = doc.get("modes", {})
    if mid not in modes:
        return {"ok": False, "error": "unknown_mode", "mode": mid, "available": list(modes.keys())}
    m = modes[mid]
    speak = m.get("speak", {})
    manners = doc.get("manners", {})
    text = speak.get(voc) or manners.get(voc) or doc.get("rule", "")
    preservation = doc.get("preservation", {})
    return {
        "ok": True,
        "mode": mid,
        "label": m.get("label", mid),
        "voice": voc,
        "speak": text,
        "manner": manners.get(voc),
        "prescription": {
            "eye_profile": m.get("eye_profile"),
            "rig_preset": m.get("rig_preset"),
            "video_profile": m.get("video_profile"),
            "vigilance_profile": m.get("vigilance_profile"),
            "prefer": m.get("prefer", "auto"),
            "fast_path": m.get("fast_path", True),
        },
        "preservation_biological": preservation.get("biological", []),
        "preservation_field": preservation.get("field", []),
        "universal_law": preservation.get("universal_law"),
    }


def _eyeball_witness(*, seal: bool = True) -> dict[str, Any]:
    try:
        from zocr_sovereign_time import eyeball_time_and_redundancy
        return eyeball_time_and_redundancy(seal=seal)
    except ImportError:
        return {
            "sovereign_time": {"always": True, "ok": False, "error": "zocr_sovereign_time missing"},
            "redundancy": {"always": True, "ok": False, "error": "zocr_sovereign_time missing"},
        }


def set_final_mode(
    mode: str,
    *,
    voice: str | None = None,
    apply_rig: bool = True,
    source: str = "api",
) -> dict[str, Any]:
    """Arm Final Eyeball mode — teach eye, configure rig, return prescription."""
    doc = load_final_eyeball()
    modes = doc.get("modes", {})
    if mode not in modes:
        return {"ok": False, "error": "unknown_mode", "mode": mode, "available": list(modes.keys())}

    m = modes[mode]
    eye_result = teach(m.get("eye_profile", "human"), source=source)
    rig_result: dict[str, Any] = {"ok": True, "skipped": True}
    if apply_rig and m.get("rig_preset"):
        from zocr_stereo import configure_rig
        rig_result = configure_rig(preset=m["rig_preset"], source=source)

    st = _load_final_state()
    st["active_mode"] = mode
    if voice:
        st["active_voice"] = voice
    st["last_prescription"] = {
        "eye_profile": m.get("eye_profile"),
        "rig_preset": m.get("rig_preset"),
        "video_profile": m.get("video_profile"),
        "vigilance_profile": m.get("vigilance_profile"),
    }
    _save_final_state(st)

    spoken = speak_final(mode=mode, voice=voice or st.get("active_voice"))
    witness = _eyeball_witness(seal=True)
    g16_tune = grok16_eye_tune(mode=mode, eye_profile=m.get("eye_profile"))
    st["sovereign_time"] = witness.get("sovereign_time")
    st["redundancy"] = witness.get("redundancy")
    st["grok16_profile"] = g16_tune.get("grok16_profile")
    _save_final_state(st)

    log_event(
        "final_eyeball",
        ok=True,
        mode=mode,
        eye=m.get("eye_profile"),
        rig=m.get("rig_preset"),
        video=m.get("video_profile"),
        source=source,
        sovereign_verdict=(witness.get("sovereign_time") or {}).get("verdict"),
        redundancy_woven=(witness.get("redundancy") or {}).get("woven_paths"),
    )
    return {
        "ok": eye_result.get("ok", False) and rig_result.get("ok", False),
        "mode": mode,
        "label": m.get("label", mode),
        "eye": eye_result,
        "rig": rig_result,
        "prescription": spoken.get("prescription"),
        "speak": spoken.get("speak"),
        "voice": spoken.get("voice"),
        "sovereign_time": witness.get("sovereign_time"),
        "redundancy": witness.get("redundancy"),
        "grok16": g16_tune,
        "field_compiler": grok16_eye_witness(mode=mode, eye_profile=m.get("eye_profile")),
        "video_hint": (
            f"POST /api/stream/start {{\"profile\":\"{m.get('video_profile', 'idle')}\"}}"
            if m.get("video_profile") and m.get("video_profile") != "idle"
            else "Stream idle — POST /api/look on demand"
        ),
        "title": doc.get("title"),
        "rule": doc.get("rule"),
    }


def final_eyeball_doctrine() -> dict[str, Any]:
    doc = load_final_eyeball()
    st = _load_final_state()
    return {
        "schema": "zocr-final-eyeball-doctrine/v1",
        "title": doc.get("title"),
        "subtitle": doc.get("subtitle"),
        "rule": doc.get("rule"),
        "voices": doc.get("voices", []),
        "manners": doc.get("manners", {}),
        "preservation": doc.get("preservation", {}),
        "modes": list_final_modes(),
        "active_mode": st.get("active_mode"),
        "active_voice": st.get("active_voice"),
    }


def final_eyeball_status() -> dict[str, Any]:
    doc = load_final_eyeball()
    st = _load_final_state()
    mid = st.get("active_mode", "dishes")
    spoken = speak_final(mode=mid, voice=st.get("active_voice"))
    witness = _eyeball_witness(seal=True)
    sealed_mono = (witness.get("sovereign_time") or {}).get("sealed_mono_ns")
    return {
        "schema": "zocr-final-eyeball-status/v1",
        "ts": _ts(),
        "sealed_ts": sealed_mono,
        "title": doc.get("title"),
        "active_mode": mid,
        "active_voice": st.get("active_voice", "robotics_brief"),
        "modes": list_final_modes(),
        "voices": doc.get("voices", []),
        "speak": spoken.get("speak"),
        "prescription": spoken.get("prescription"),
        "preservation": doc.get("preservation", {}),
        "sovereign_time": witness.get("sovereign_time"),
        "redundancy": witness.get("redundancy"),
        "twins": _twin_eyeballs(),
        "eye": eye_status(),
        "grok16": grok16_eye_tune(mode=mid, eye_profile=(spoken.get("prescription") or {}).get("eye_profile")),
        "field_compiler": grok16_eye_witness(
            mode=mid,
            eye_profile=(spoken.get("prescription") or {}).get("eye_profile"),
        ),
        "path": str(FINAL_PATH),
    }


def _twin_eyeballs() -> dict[str, Any]:
    try:
        from zocr_entity_eyeball import (
            _load_state as entity_state,
            entity_weapons,
            living_eyeball_status,
            truth_eyeball_status,
        )
        st = entity_state()
        return {
            "schema": "zocr-twin-eyeball-summary/v1",
            "living": living_eyeball_status(),
            "truth": truth_eyeball_status(),
            "both_live": bool(st.get("living_live")),
            "always_forward": bool(st.get("truth_forward", True)),
            "weapons_armed": bool(st.get("weapons_armed", True)),
            "weapons": entity_weapons(),
        }
    except ImportError:
        return {"error": "zocr_entity_eyeball missing"}


def spectrum_doctrine() -> dict[str, Any]:
    doc = load_doctrine()
    mode = _load_final_state().get("active_mode", "dishes")
    pid = active_profile()
    return {
        "schema": "zocr-spectrum-doctrine/v2",
        "title": "Ocular spectrum — cone sensitivity engine",
        "engine": grok16_eye_tune(mode=mode, eye_profile=pid).get("engine", ENGINE),
        "doctrine": doc.get("doctrine"),
        "profiles": list_profiles(),
        "active": pid,
        "taught": _load_state().get("taught", []),
        "grok16_profile": grok16_profile_for_mode(mode),
        "eye_grok16_profile": grok16_profile_for_eye(pid),
        "field_compiler": grok16_eye_witness(mode=mode, eye_profile=pid),
    }


def _cool_summary() -> dict[str, Any]:
    try:
        from zocr_contract import contract_status
        return contract_status()
    except ImportError:
        return {"enabled": False, "posture": "assistive"}


def eye_status() -> dict[str, Any]:
    pid = active_profile()
    spec = profile_spec(pid)
    recent: list[dict] = []
    if TEACH_LOG.is_file():
        try:
            for line in TEACH_LOG.read_text(encoding="utf-8").splitlines()[-6:]:
                if line.strip():
                    recent.append(json.loads(line))
        except (OSError, json.JSONDecodeError):
            pass
    witness = _eyeball_witness(seal=False)
    st_doc = witness.get("sovereign_time") or {}
    mode = _load_final_state().get("active_mode", "dishes")
    tune = grok16_eye_tune(mode=mode, eye_profile=pid)
    return {
        "schema": "zocr-eye-status/v2",
        "ts": _ts(),
        "sealed_ts": st_doc.get("sealed_mono_ns"),
        "engine": tune.get("engine", ENGINE),
        "active_profile": pid,
        "label": spec.get("label"),
        "class": spec.get("class"),
        "range_nm": spec.get("range_nm"),
        "receptors": spec.get("receptors"),
        "mode": spec.get("mode", "matrix"),
        "teach": spec.get("teach"),
        "profiles": list_profiles(),
        "taught": _load_state().get("taught", []),
        "recent_teach": recent,
        "doctrine_path": str(DOCTRINE_PATH),
        "rule": "Cone v2 + Grok16 field_opt — entropy dispatch adaptation, wave-phase fovea",
        "grok16": tune,
        "field_compiler": grok16_eye_witness(mode=mode, eye_profile=pid),
        "cool": _cool_summary(),
        "sovereign_time": st_doc,
        "redundancy": witness.get("redundancy"),
        "final_eyeball": {
            "active_mode": _load_final_state().get("active_mode"),
            "title": load_final_eyeball().get("title"),
        },
    }


def main() -> int:
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        print(json.dumps(eye_status(), indent=2))
        return 0
    if cmd == "profiles":
        print(json.dumps({"profiles": list_profiles()}, indent=2))
        return 0
    if cmd == "teach" and len(sys.argv) > 2:
        print(json.dumps(teach(sys.argv[2], source="cli"), indent=2))
        return 0
    if cmd == "doctrine":
        print(json.dumps(spectrum_doctrine(), indent=2))
        return 0
    if cmd == "final":
        print(json.dumps(final_eyeball_status(), indent=2))
        return 0
    if cmd == "final-mode" and len(sys.argv) > 2:
        voice = sys.argv[3] if len(sys.argv) > 3 else None
        print(json.dumps(set_final_mode(sys.argv[2], voice=voice, source="cli"), indent=2))
        return 0
    if cmd == "speak":
        mode = sys.argv[2] if len(sys.argv) > 2 else None
        voice = sys.argv[3] if len(sys.argv) > 3 else None
        print(json.dumps(speak_final(mode=mode, voice=voice), indent=2))
        return 0
    print(json.dumps({
        "error": "usage: zocr_eye.py [status|profiles|teach PROFILE|doctrine|final|final-mode MODE|speak [MODE] [VOICE]]",
    }, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())