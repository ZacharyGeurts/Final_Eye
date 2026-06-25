"""ZOCR HUD — closed manifest module system. No runtime plugins. No bullshit."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from zocr_session import log_event

_ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = _ROOT / "data" / "hud-modules.json"
STATE_PATH = _ROOT / "data" / "hud-state.json"

MODULE_ID_RE = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
ALLOWED_ACTIONS = frozenset({"enable", "disable", "toggle", "focus", "analyze"})
FORBIDDEN_REQUEST_KEYS = frozenset({
    "html", "script", "template", "module_code", "eval", "src", "url", "payload",
})


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_manifest() -> dict[str, Any]:
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema": "zocr-hud-modules/v1", "modules": {}, "max_active": 8}


def _load_state() -> dict[str, Any]:
    if STATE_PATH.is_file():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    manifest = load_manifest()
    defaults = [
        mid for mid, m in (manifest.get("modules") or {}).items()
        if m.get("default")
    ]
    return {
        "schema": "zocr-hud-state/v1",
        "active": defaults[: int(manifest.get("max_active", 8))],
        "focus": defaults[0] if defaults else None,
    }


def _save_state(st: dict[str, Any]) -> None:
    st["updated"] = _ts()
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(st, indent=2) + "\n", encoding="utf-8")


def _validate_module_id(module_id: str) -> str | None:
    if not module_id or not MODULE_ID_RE.match(module_id):
        return None
    if module_id not in (load_manifest().get("modules") or {}):
        return None
    return module_id


def list_modules() -> list[dict[str, Any]]:
    manifest = load_manifest()
    st = _load_state()
    active = set(st.get("active") or [])
    focus = st.get("focus")
    out: list[dict[str, Any]] = []
    for mid, meta in sorted((manifest.get("modules") or {}).items()):
        out.append({
            "id": mid,
            "label": meta.get("label", mid),
            "kind": meta.get("kind", "meter"),
            "group": meta.get("group", "field"),
            "api": meta.get("api"),
            "describe": meta.get("describe", ""),
            "actions": meta.get("actions", ["enable", "disable", "toggle"]),
            "default": bool(meta.get("default")),
            "active": mid in active,
            "focus": mid == focus,
        })
    return out


def hud_posture() -> dict[str, Any]:
    manifest = load_manifest()
    st = _load_state()
    return {
        "schema": "zocr-hud-posture/v1",
        "ts": _ts(),
        "rule": manifest.get("rule"),
        "max_active": int(manifest.get("max_active", 8)),
        "active": st.get("active") or [],
        "focus": st.get("focus"),
        "groups": manifest.get("groups", []),
        "modules": list_modules(),
    }


def request_hud(body: dict[str, Any]) -> dict[str, Any]:
    """Whitelist-only HUD request — rejects unknown modules and forbidden keys."""
    for key in body:
        if key in FORBIDDEN_REQUEST_KEYS:
            return {"ok": False, "error": "forbidden_key", "key": key}

    action = str(body.get("action") or "toggle").strip().lower()
    if action not in ALLOWED_ACTIONS:
        return {"ok": False, "error": "forbidden_action", "action": action}

    module_id = _validate_module_id(str(body.get("module") or body.get("id") or "").strip())
    if not module_id:
        return {"ok": False, "error": "unknown_module", "allowed": list((load_manifest().get("modules") or {}).keys())}

    manifest = load_manifest()
    mod = manifest["modules"][module_id]
    allowed = set(mod.get("actions") or ["enable", "disable", "toggle"])
    if action not in allowed:
        return {"ok": False, "error": "action_not_allowed", "module": module_id, "allowed": sorted(allowed)}

    st = _load_state()
    active = list(st.get("active") or [])
    max_active = int(manifest.get("max_active", 8))

    if action == "enable" and module_id not in active:
        if len(active) >= max_active:
            return {"ok": False, "error": "max_active", "max": max_active}
        active.append(module_id)
    elif action == "disable" and module_id in active:
        active.remove(module_id)
        if st.get("focus") == module_id:
            st["focus"] = active[0] if active else None
    elif action == "toggle":
        if module_id in active:
            active.remove(module_id)
            if st.get("focus") == module_id:
                st["focus"] = active[0] if active else None
        elif len(active) < max_active:
            active.append(module_id)
        else:
            return {"ok": False, "error": "max_active", "max": max_active}
    elif action == "focus":
        if module_id not in active:
            if len(active) >= max_active:
                return {"ok": False, "error": "max_active", "max": max_active}
            active.append(module_id)
        st["focus"] = module_id

    st["active"] = active
    _save_state(st)

    analyze_out: dict[str, Any] | None = None
    if action == "analyze":
        analyze_out = module_analyze(module_id)

    log_event("hud_request", ok=True, action=action, module=module_id)
    return {
        "ok": True,
        "schema": "zocr-hud-request/v1",
        "action": action,
        "module": module_id,
        "posture": hud_posture(),
        "analyze": analyze_out,
    }


def _module_spectrum() -> dict[str, Any]:
    from zocr_eye import eye_status, list_profiles, spectrum_doctrine
    eye = eye_status()
    doc = spectrum_doctrine()
    pid = eye.get("active_profile", "human")
    profiles = {p["id"]: p for p in list_profiles()}
    prof = profiles.get(pid, {})
    gamut: list[dict[str, Any]] = []
    for p in list_profiles():
        gamut.append({
            "id": p["id"],
            "label": p.get("label"),
            "range_nm": p.get("range_nm"),
            "active": p["id"] == pid,
        })
    return {
        "schema": "zocr-hud-spectrum/v1",
        "profile": pid,
        "label": prof.get("label") or eye.get("label"),
        "range_nm": prof.get("range_nm") or eye.get("range_nm"),
        "class": prof.get("class") or eye.get("class"),
        "engine": doc.get("engine"),
        "teach": prof.get("teach") or eye.get("teach"),
        "gamut": gamut,
        "taught": doc.get("taught", []),
    }


def _module_sovereign_clock() -> dict[str, Any]:
    try:
        from zocr_sovereign_time import sovereign_time_status
        st = sovereign_time_status(seal=False)
        return {
            "verdict": st.get("verdict"),
            "sealed_mono_ns": st.get("sealed_mono_ns"),
            "micron_witness": (st.get("micron_witness") or "")[:12],
        }
    except ImportError:
        return {"verdict": "—", "sealed_mono_ns": None}


def _module_ocr_hud() -> dict[str, Any]:
    from zocr_status import live_status
    d = live_status()
    recent = (d.get("session") or {}).get("recent") or []
    last = recent[-1] if recent else {}
    return {
        "last_action": last.get("action"),
        "last_ts": last.get("ts"),
        "snippet": str(last.get("ocr") or last.get("label") or "")[:120],
    }


def _module_contract_budget() -> dict[str, Any]:
    try:
        from zocr_contract import contract_status
        c = contract_status()
        return {
            "posture": c.get("posture"),
            "slots": c.get("slots") or c.get("budgets"),
            "overflow": c.get("overflow_blocked"),
        }
    except ImportError:
        return {"posture": "assistive"}


def _module_field_compiler() -> dict[str, Any]:
    from zocr_field_compiler import field_compiler_status
    fc = field_compiler_status()
    g = fc.get("grok16") or {}
    f = fc.get("fieldc") or {}
    fr = fc.get("forge") or {}
    return {
        "grok16": g.get("version") or g.get("dumpversion"),
        "g16_ready": g.get("ready") or g.get("ready_rtx"),
        "profile": g.get("profile", "field_opt"),
        "fieldc": f.get("version"),
        "rtx_ready": f.get("rtx_ready"),
        "forge_stage": fr.get("stage"),
    }


def _module_heaven_hell_truth() -> dict[str, Any]:
    from zocr_heaven_hell import heaven_hell_truth_status
    doc = heaven_hell_truth_status()
    truth = doc.get("truth") or {}
    hh = doc.get("heaven_hell") or {}
    return {
        "truth_floor": truth.get("truth_adapt_floor"),
        "noise_ratio": truth.get("noise_ratio"),
        "heaven": hh.get("heaven_count"),
        "hell": hh.get("hell_count"),
        "rip_ready": hh.get("hell_chosen_count"),
        "hostility": hh.get("hostility_priority"),
        "speak": (hh.get("speak") or "")[:100],
    }


def _module_look_radar() -> dict[str, Any]:
    from zocr_preserve import preserve_status
    p = preserve_status()
    return {
        "last_source": p.get("last_source"),
        "last_good": bool(p.get("last_good")),
        "cascade": p.get("cascade", [])[:4],
        "vision_confidence": p.get("vision_confidence"),
    }


def _module_stream_meter() -> dict[str, Any]:
    from zocr_video import video_status
    v = video_status()
    return {
        "format": v.get("format"),
        "running": v.get("running"),
        "fps": v.get("fps"),
        "profile": v.get("profile"),
        "fabric_nm_per_px": v.get("fabric_nm_per_px"),
        "adaptive_scale": v.get("adaptive_scale"),
    }


def _module_stereo_depth() -> dict[str, Any]:
    from zocr_stereo import rig_status
    r = rig_status()
    return {
        "mode": r.get("mode"),
        "eye_count": r.get("eye_count"),
        "stereo": (r.get("stereoscopic") or {}).get("enabled"),
        "preset": r.get("preset"),
    }


def _module_threat_overlay() -> dict[str, Any]:
    from zocr_preserve import preserve_status
    p = preserve_status()
    return {
        "confidence": p.get("vision_confidence"),
        "threats_total": p.get("threats_total"),
        "failovers": p.get("failovers_total"),
        "last_threats": (p.get("recent_threats") or [])[-3:],
    }


def _module_twin_entity() -> dict[str, Any]:
    from zocr_entity_eyeball import twin_eyeball_status
    t = twin_eyeball_status()
    living = t.get("living") or {}
    truth = t.get("truth") or {}
    return {
        "vita_live": living.get("live"),
        "veritas_forward": truth.get("always_forward"),
        "speak": (truth.get("speak") or "")[:100],
    }


def _module_final_mode() -> dict[str, Any]:
    from zocr_eye import final_eyeball_status
    f = final_eyeball_status()
    return {
        "mode": f.get("active_mode"),
        "voice": f.get("active_voice"),
        "speak": (f.get("speak") or "")[:80],
    }


def _module_pattern_weave() -> dict[str, Any]:
    from zocr_pattern import pattern_status
    p = pattern_status()
    return {
        "enabled": p.get("enabled"),
        "scans": p.get("scans_total"),
        "foreign": p.get("foreign_total"),
    }


def _module_entity_weapons() -> dict[str, Any]:
    from zocr_entity_eyeball import entity_weapon_racks, entity_weapons
    racks = entity_weapon_racks()
    w = entity_weapons()
    by_rack = racks.get("by_rack") or {}
    return {
        "count": len(w),
        "racks": len(by_rack),
        "socket": (racks.get("socket_fit") or {}).get("rule", "")[:80],
        "ids": [x.get("id") for x in w[:8]],
        "rack_labels": list((racks.get("racks") or {}).keys())[:6],
    }


def _module_offense_streak() -> dict[str, Any]:
    from zocr_offense import offense_status
    o = offense_status()
    return {
        "strikes": o.get("strikes_total"),
        "streak": o.get("threat_streak"),
        "preempt": o.get("preempt_armed"),
    }


def _module_kill_gate() -> dict[str, Any]:
    from zocr_kill import kill_status
    k = kill_status()
    return {"whole": k.get("whole"), "eyes": k.get("eyes_protect")}


def _module_trust_woven() -> dict[str, Any]:
    from zocr_trust import trust_network_status
    t = trust_network_status()
    return {"mesh_ok": t.get("mesh_ok"), "woven": t.get("interwoven"), "peers": t.get("peers_ok")}


def _module_neural_assist() -> dict[str, Any]:
    from zocr_neural import neural_status
    n = neural_status()
    seal = n.get("seal") or {}
    return {"network": n.get("network_id"), "seal_ok": seal.get("ok")}


def _module_vigilance_patrol() -> dict[str, Any]:
    from zocr_vigilance import vigilance_status
    v = vigilance_status()
    return {"running": v.get("running"), "checks": v.get("checks"), "alerts": v.get("alerts")}


def _module_video_tune() -> dict[str, Any]:
    from zocr_video import video_status
    v = video_status()
    tune = v.get("tune") or v.get("resolved") or {}
    return {
        "fps": v.get("fps"),
        "width": tune.get("width") or v.get("width"),
        "height": tune.get("height") or v.get("height"),
        "mode": tune.get("mode"),
    }


_FETCHERS: dict[str, Any] = {
    "spectrum": _module_spectrum,
    "stream_meter": _module_stream_meter,
    "stereo_depth": _module_stereo_depth,
    "threat_overlay": _module_threat_overlay,
    "sovereign_clock": _module_sovereign_clock,
    "trust_woven": _module_trust_woven,
    "twin_entity": _module_twin_entity,
    "final_mode": _module_final_mode,
    "neural_assist": _module_neural_assist,
    "pattern_weave": _module_pattern_weave,
    "kill_gate": _module_kill_gate,
    "offense_streak": _module_offense_streak,
    "capture_cascade": _module_look_radar,
    "ocr_hud": _module_ocr_hud,
    "contract_budget": _module_contract_budget,
    "entity_weapons": _module_entity_weapons,
    "vigilance_patrol": _module_vigilance_patrol,
    "video_tune": _module_video_tune,
    "look_radar": _module_look_radar,
    "field_compiler": _module_field_compiler,
    "heaven_hell_truth": _module_heaven_hell_truth,
}


def fetch_module_data(module_id: str) -> dict[str, Any]:
    mid = _validate_module_id(module_id)
    if not mid:
        return {"ok": False, "error": "unknown_module"}
    fn = _FETCHERS.get(mid)
    if not fn:
        return {"ok": False, "error": "no_fetcher", "module": mid}
    try:
        data = fn()
        return {"ok": True, "module": mid, "data": data}
    except Exception as exc:
        return {"ok": False, "module": mid, "error": str(exc)[:200]}


def module_analyze(module_id: str) -> dict[str, Any]:
    mid = _validate_module_id(module_id)
    if not mid:
        return {"ok": False, "error": "unknown_module"}
    manifest = load_manifest()
    if manifest["modules"][mid].get("kind") != "spectrum" and mid != "pattern_weave":
        if mid != "spectrum":
            return fetch_module_data(mid)
    if mid == "spectrum":
        data = _module_spectrum()
        return {"ok": True, "module": mid, "analysis": data, "summary": _spectrum_summary(data)}
    if mid == "pattern_weave":
        from zocr_pattern import pattern_status
        return {"ok": True, "module": mid, "analysis": pattern_status()}
    return fetch_module_data(mid)


def _spectrum_summary(data: dict[str, Any]) -> str:
    rng = data.get("range_nm") or []
    nm = f"{rng[0]}–{rng[1]}nm" if len(rng) >= 2 else "—"
    return f"{data.get('label', '—')} · {nm} · {data.get('engine', 'cone_v2')}"


def hud_status() -> dict[str, Any]:
    """Poll all active modules — templated data only."""
    st = _load_state()
    active = st.get("active") or []
    focus = st.get("focus")
    tiles: dict[str, Any] = {}
    for mid in active:
        if _validate_module_id(mid):
            tiles[mid] = fetch_module_data(mid)
    spectrum_focus = None
    if focus == "spectrum" or "spectrum" in active:
        spectrum_focus = module_analyze("spectrum")
    return {
        "schema": "zocr-hud-status/v1",
        "ts": _ts(),
        "posture": hud_posture(),
        "tiles": tiles,
        "spectrum": spectrum_focus,
        "focus": focus,
    }


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower()
    if cmd in ("status", "json"):
        print(json.dumps(hud_status(), indent=2))
        return 0
    if cmd == "modules":
        print(json.dumps({"ok": True, "modules": list_modules()}, indent=2))
        return 0
    if cmd == "request" and len(sys.argv) > 2:
        body = {"action": sys.argv[2], "module": sys.argv[3] if len(sys.argv) > 3 else ""}
        print(json.dumps(request_hud(body), indent=2))
        return 0
    if cmd == "analyze" and len(sys.argv) > 2:
        print(json.dumps(module_analyze(sys.argv[2]), indent=2))
        return 0
    print(json.dumps({
        "error": "usage: zocr_hud.py [status|modules|request ACTION MODULE|analyze MODULE]",
    }, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())