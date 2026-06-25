"""ZOCR multi-eye rig v2 — block-matching stereo, occlusion-aware views."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from zocr_eye import perceive
from zocr_session import log_event

_ROOT = Path(__file__).resolve().parent
RIG_PATH = _ROOT / "data" / "eye-rig.json"
RIG_STATE = _ROOT / "data" / "eye-rig-state.json"
STEREO_OUT = _ROOT / "out" / "stereo"
ENGINE = "bm_v2"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_rig_doctrine() -> dict[str, Any]:
    try:
        return json.loads(RIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema": "zocr-eye-rig/v1", "eyes": [], "presets": {}}


def comfort_doctrine() -> dict[str, Any]:
    """Queen eye comfort — unlimited eyes; stereo for faces; monocular for media."""
    doc = load_rig_doctrine()
    cd = doc.get("comfort_doctrine") or {}
    return {
        "schema": "zocr-eye-comfort/v1",
        "rule": cd.get("rule", "Permit any number of eyes"),
        "stereo_preference": cd.get("stereo_preference"),
        "person_present": cd.get("person_present") or {},
        "media_relaxed": cd.get("media_relaxed") or {},
        "operator_note": cd.get("operator_note"),
        "presets": {
            "person_present": (cd.get("person_present") or {}).get("preset", "stereo_human"),
            "media": (cd.get("media_relaxed") or {}).get("preset", "monocular"),
        },
    }


def preset_for_context(context: str | None) -> str | None:
    """Map comfort context to rig preset — None leaves current rig unchanged."""
    ctx = (context or "").strip().lower().replace("-", "_")
    if not ctx:
        return None
    cd = comfort_doctrine()
    if ctx in ("person", "person_present", "face", "faces", "local_comfort", "with_person"):
        return cd["presets"]["person_present"]
    if ctx in ("media", "browsing", "movies", "movie", "gallery", "streaming", "pictures"):
        return cd["presets"]["media"]
    return None


def _load_state() -> dict[str, Any]:
    if RIG_STATE.is_file():
        try:
            return json.loads(RIG_STATE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    doc = load_rig_doctrine()
    preset = doc.get("presets", {}).get("monocular", {})
    return {
        "schema": "zocr-eye-rig-state/v1",
        "mode": doc.get("default_mode", "monocular"),
        "stereoscopic": preset.get("stereoscopic", {"enabled": False}),
        "eyes": preset.get("eyes", [{"id": "primary", "role": "center", "profile": "human", "offset_x": 0, "enabled": True}]),
    }


def _save_state(st: dict[str, Any]) -> None:
    RIG_STATE.parent.mkdir(parents=True, exist_ok=True)
    st["updated"] = _ts()
    RIG_STATE.write_text(json.dumps(st, indent=2) + "\n", encoding="utf-8")


def list_presets() -> list[dict[str, Any]]:
    doc = load_rig_doctrine()
    out = []
    for pid, p in doc.get("presets", {}).items():
        eyes = p.get("eyes", [])
        out.append({
            "id": pid,
            "eyes": len(eyes),
            "stereoscopic": bool(p.get("stereoscopic", {}).get("enabled")),
            "eye_ids": [e.get("id") for e in eyes],
        })
    return out


def configure_rig(
    *,
    preset: str | None = None,
    eyes: list[dict[str, Any]] | None = None,
    stereoscopic: dict[str, Any] | None = None,
    source: str = "api",
) -> dict[str, Any]:
    doc = load_rig_doctrine()
    st = _load_state()

    if preset:
        if preset not in doc.get("presets", {}):
            return {"ok": False, "error": "unknown_preset", "preset": preset}
        p = doc["presets"][preset]
        st["mode"] = preset
        st["eyes"] = p.get("eyes", [])
        st["stereoscopic"] = p.get("stereoscopic", {"enabled": False})
    else:
        if eyes is not None:
            st["eyes"] = eyes
            st["mode"] = "custom"
        if stereoscopic is not None:
            st["stereoscopic"] = stereoscopic

    _save_state(st)
    log_event("eye_rig_configure", ok=True, mode=st["mode"], eyes=len(st.get("eyes", [])), source=source)
    return {"ok": True, **rig_status()}


def active_eyes() -> list[dict[str, Any]]:
    st = _load_state()
    return [e for e in st.get("eyes", []) if e.get("enabled", True)]


def _block_match_disparity(gray_px: Any, w: int, h: int, *, max_disp: int, block: int = 9, scale: int = 8) -> list[list[int]]:
    """SSD block matching at reduced resolution — fast enough for field look."""
    sw, sh = max(1, w // scale), max(1, h // scale)
    md = max(2, max_disp // scale)
    blk = max(3, block // scale)
    step = max(1, blk)

    def sample(sx: int, sy: int) -> int:
        return int(gray_px[min(w - 1, sx * scale), min(h - 1, sy * scale)])

    disp = [[0] * sw for _ in range(sh)]
    for y in range(0, sh - blk, step):
        for x in range(0, sw - blk - md, step):
            best_d, best_sad = 0, 1 << 30
            for d in range(0, md + 1, max(1, md // 8)):
                sad = 0
                for by in range(0, blk, 2):
                    for bx in range(0, blk, 2):
                        sad += abs(sample(x + bx, y + by) - sample(x + bx + d, y + by))
                if sad < best_sad:
                    best_sad, best_d = sad, d
            for by in range(blk):
                for bx in range(blk):
                    yy, xx = y + by, x + bx
                    if yy < sh and xx < sw:
                        disp[yy][xx] = best_d * scale
    return disp


def _upscale_disp(disp: list[list[int]], w: int, h: int) -> list[list[int]]:
    sh, sw = len(disp), len(disp[0]) if disp else 0
    if sw <= 0 or sh <= 0:
        return [[0] * w for _ in range(h)]
    out = [[0] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            sy = min(sh - 1, int(y * sh / h))
            sx = min(sw - 1, int(x * sw / w))
            out[y][x] = disp[sy][sx]
    return out


def _shift_occlusion_aware(img: Any, disp: list[list[int]], sign: int) -> Any:
    from PIL import Image
    w, h = img.size
    src = img.load()
    out = Image.new("RGB", (w, h), (0, 0, 0))
    dst = out.load()
    filled = [[False] * w for _ in range(h)]
    for y in range(h):
        order = range(w) if sign < 0 else range(w - 1, -1, -1)
        for x in order:
            d = int(disp[y][x] / 255.0 * (sign * 16)) if disp[y][x] else 0
            sx = max(0, min(w - 1, x - d))
            dst[x, y] = src[sx, y]
            filled[y][x] = True
    for y in range(h):
        for x in range(w):
            if not filled[y][x]:
                for dx in range(1, 8):
                    sx = max(0, min(w - 1, x - sign * dx))
                    if filled[y][sx]:
                        dst[x, y] = dst[sx, y]
                        break
    return out


def _anaglyph_cyan_red(left: Any, right: Any) -> Any:
    from PIL import Image
    w, h = left.size
    right = right.resize((w, h))
    out = Image.new("RGB", (w, h))
    lp, rp, op = left.load(), right.load(), out.load()
    for y in range(h):
        for x in range(w):
            lr, lg, lb = lp[x, y]
            rr, rg, rb = rp[x, y]
            op[x, y] = (lr, rg, rb)
    return out


def _depth_colormap(disp: list[list[int]]) -> Any:
    from PIL import Image
    h, w = len(disp), len(disp[0])
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            v = disp[y][x]
            if v < 85:
                px[x, y] = (0, 0, min(255, v * 3))
            elif v < 170:
                px[x, y] = (0, min(255, (v - 85) * 3), 255)
            else:
                px[x, y] = (min(255, (v - 170) * 3), max(0, 255 - (v - 170)), 0)
    return img


def stereoscopic_compose(path: Path, *, stereo_cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        from PIL import Image, ImageFilter
    except ImportError:
        return {"ok": False, "error": "pil_missing"}

    if not path.is_file():
        return {"ok": False, "error": "no_frame"}

    cfg = stereo_cfg or _load_state().get("stereoscopic", {})
    if not cfg.get("enabled"):
        return {"ok": False, "error": "stereo_disabled"}

    max_disp = int(cfg.get("max_disparity_px", 32))
    img_full = Image.open(path).convert("RGB")
    w, h = img_full.size
    proc = img_full
    max_w = int(cfg.get("process_max_width", 1280))
    if w > max_w:
        scale = max_w / w
        proc = img_full.resize((int(w * scale), int(h * scale)))
    pw, ph = proc.size
    gray = proc.convert("L").filter(ImageFilter.GaussianBlur(radius=0.6))
    gpx = gray.load()

    disp_lo = _block_match_disparity(gpx, pw, ph, max_disp=max_disp)
    disp = _upscale_disp(disp_lo, pw, ph)

    edges = gray.filter(ImageFilter.FIND_EDGES).convert("L")
    epx = edges.load()
    for y in range(ph):
        for x in range(pw):
            disp[y][x] = max(0, min(255, int(disp[y][x] * 0.55 + epx[x, y] * 0.45)))
    vals = [disp[y][x] for y in range(ph) for x in range(pw)]
    hi = max(vals) or 1
    if hi < 80:
        for y in range(ph):
            for x in range(pw):
                disp[y][x] = min(255, int(disp[y][x] * (180 / hi)))

    if (pw, ph) != (w, h):
        disp = _upscale_disp(disp, w, h)
        img = img_full
    else:
        img = proc

    left = _shift_occlusion_aware(img, disp, sign=-1)
    right = _shift_occlusion_aware(img, disp, sign=1)

    STEREO_OUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    left_p = STEREO_OUT / f"{stamp}_left.png"
    right_p = STEREO_OUT / f"{stamp}_right.png"
    sbs_p = STEREO_OUT / f"{stamp}_sbs.png"
    ana_p = STEREO_OUT / f"{stamp}_anaglyph.png"
    dep_p = STEREO_OUT / f"{stamp}_depth.png"

    left.save(left_p)
    right.save(right_p)
    sbs = Image.new("RGB", (w * 2, h))
    sbs.paste(left, (0, 0))
    sbs.paste(right, (w, 0))
    sbs.save(sbs_p)
    _anaglyph_cyan_red(left, right).save(ana_p)
    _depth_colormap(disp).save(dep_p)

    vals = [disp[y][x] for y in range(h) for x in range(w)]
    disp_mean = sum(vals) / max(len(vals), 1)
    disp_max = max(vals) if vals else 0
    confidence = min(1.0, disp_max / 255.0)

    return {
        "ok": True,
        "engine": ENGINE,
        "baseline_mm": cfg.get("baseline_mm"),
        "ipd_mm": cfg.get("ipd_mm"),
        "max_disparity_px": max_disp,
        "disparity_mean": round(disp_mean, 2),
        "disparity_max": disp_max,
        "confidence": round(confidence, 3),
        "left": str(left_p),
        "right": str(right_p),
        "side_by_side": str(sbs_p),
        "anaglyph": str(ana_p),
        "depth_map": str(dep_p),
    }


def perceive_rig(path: Path | str) -> dict[str, Any]:
    path = Path(path)
    if not path.is_file():
        return {"ok": False, "error": "no_frame", "eyes": []}

    st = _load_state()
    results: list[dict[str, Any]] = []
    for eye in active_eyes():
        eid = eye.get("id", "eye")
        prof = eye.get("profile", "human")
        out, meta = perceive(path, profile_id=prof)
        results.append({
            "id": eid,
            "role": eye.get("role", "center"),
            "offset_x": eye.get("offset_x", 0),
            "profile": prof,
            "label": meta.get("label"),
            "engine": meta.get("engine"),
            "path": str(out) if out else None,
            "perceived": meta.get("perceived", False),
        })

    stereo: dict[str, Any] = {"enabled": False}
    if st.get("stereoscopic", {}).get("enabled"):
        primary = path
        for r in results:
            if r.get("role") == "left" and r.get("path"):
                primary = Path(r["path"])
                break
        stereo = stereoscopic_compose(primary, stereo_cfg=st.get("stereoscopic"))
        stereo["enabled"] = stereo.get("ok", False)

    return {
        "ok": True,
        "engine": ENGINE,
        "mode": st.get("mode"),
        "eye_count": len(results),
        "eyes": results,
        "stereoscopic": stereo,
    }


def rig_status() -> dict[str, Any]:
    st = _load_state()
    eyes = active_eyes()
    return {
        "schema": "zocr-eye-rig-status/v2",
        "ts": _ts(),
        "engine": ENGINE,
        "mode": st.get("mode"),
        "eye_count": len(eyes),
        "eyes": eyes,
        "stereoscopic": st.get("stereoscopic", {}),
        "presets": list_presets(),
        "doctrine": load_rig_doctrine().get("doctrine"),
        "comfort": comfort_doctrine(),
        "rule": "BM v2 block-matching disparity, occlusion fill, proper anaglyph",
    }


def main() -> int:
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        print(json.dumps(rig_status(), indent=2))
        return 0
    if cmd == "presets":
        print(json.dumps({"presets": list_presets()}, indent=2))
        return 0
    if cmd == "configure" and len(sys.argv) > 2:
        print(json.dumps(configure_rig(preset=sys.argv[2], source="cli"), indent=2))
        return 0
    print(json.dumps({"error": "usage: zocr_stereo.py [status|presets|configure PRESET]"}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())