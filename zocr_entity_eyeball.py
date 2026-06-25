"""Twin entity eyeballs — Living (Vita) makes live; Truth (Veritas) guards lies, always forward."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from zocr_session import log_event

_ROOT = Path(__file__).resolve().parent
SPEC_PATH = _ROOT / "data" / "entity-eyeball.json"
STATE_PATH = _ROOT / "data" / "entity-eyeball-state.json"
FORWARD_LEDGER = _ROOT / "data" / "truth-forward-ledger.jsonl"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_entity_spec() -> dict[str, Any]:
    try:
        return json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema": "zocr-entity-eyeball/v1", "twins": {}, "weapons": {}}


def _load_state() -> dict[str, Any]:
    if STATE_PATH.is_file():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "schema": "zocr-entity-eyeball-state/v1",
        "living_live": False,
        "truth_forward": True,
        "weapons_armed": True,
        "forward_count": 0,
        "lies_rejected": 0,
        "last_weapon": None,
    }


def _save_state(st: dict[str, Any]) -> None:
    st["updated"] = _ts()
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(st, indent=2) + "\n", encoding="utf-8")


def _append_forward(row: dict[str, Any]) -> None:
    FORWARD_LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with FORWARD_LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def entity_weapons(*, rack: str | None = None) -> list[dict[str, Any]]:
    spec = load_entity_spec()
    out: list[dict[str, Any]] = []
    for wid, meta in sorted((spec.get("weapons") or {}).items()):
        if rack and meta.get("rack") != rack:
            continue
        out.append({"id": wid, **meta})
    return out


def entity_weapon_racks() -> dict[str, Any]:
    spec = load_entity_spec()
    racks = spec.get("racks") or {}
    weapons = spec.get("weapons") or {}
    by_rack: dict[str, list[dict[str, Any]]] = {rid: [] for rid in racks}
    for wid, meta in weapons.items():
        rid = meta.get("rack", "core")
        by_rack.setdefault(rid, []).append({"id": wid, **meta})
    return {
        "schema": "zocr-entity-weapon-racks/v1",
        "ts": _ts(),
        "socket_fit": spec.get("socket_fit"),
        "racks": racks,
        "weapons_total": len(weapons),
        "by_rack": {k: sorted(v, key=lambda x: x["id"]) for k, v in by_rack.items() if v},
    }


def _threat_weapon_map() -> dict[str, str]:
    spec = load_entity_spec()
    return dict(spec.get("forward", {}).get("threat_weapon_map") or {})


def auto_weapon_for_threat(threat: str) -> str:
    return _threat_weapon_map().get(threat, "reject_lie")


def _detect_lies() -> dict[str, Any]:
    """Scan ingress for lie markers — truth eyeball always forward."""
    spec = load_entity_spec()
    lie_markers = set(spec.get("forward", {}).get("lie_markers", []))
    threats: list[str] = []
    sources: list[str] = []

    meta_path = _ROOT / "data" / "preserve" / "last-good.json"
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            for t in meta.get("threats") or []:
                if t in lie_markers:
                    threats.append(t)
            if threats:
                sources.append("preserve_meta")
        except (OSError, json.JSONDecodeError):
            pass

    last_good = _ROOT / "data" / "preserve" / "last-good.png"
    if last_good.is_file():
        try:
            from zocr_pattern import scan_frame
            scan = scan_frame(last_good)
            for t in scan.get("threats") or []:
                if t in lie_markers and t not in threats:
                    threats.append(t)
            if scan.get("foreign"):
                sources.append("pattern_scan")
        except Exception:
            pass

    from zocr_security import verify_code_seal
    seal = verify_code_seal()
    if not seal.get("ok"):
        threats.append("corrupt_frame")
        sources.append("code_seal")

    try:
        from zocr_sovereign_time import sovereign_time_status
        st = sovereign_time_status(seal=False)
        if st.get("verdict") not in (None, "USER_OK"):
            threats.append("timing_gap")
            sources.append("sovereign_time")
            if st.get("verdict") == "ENTROPY_SPOOF":
                threats.append("entropy_spoof")
    except ImportError:
        pass

    try:
        from zocr_trust import verify_trust_mesh
        mesh = verify_trust_mesh()
        if not mesh.get("ok"):
            threats.append("trust_breach")
            sources.append("irtn")
    except ImportError:
        pass

    try:
        from zocr_grok16 import grok16_status
        g = grok16_status()
        if not g.get("ready"):
            threats.append("compiler_gap")
            sources.append("grok16")
    except ImportError:
        pass

    try:
        from zocr_stream import stream_status
        ss = stream_status()
        if ss.get("running") and float(ss.get("fps") or 0) > 20:
            threats.append("thermal_breach")
            sources.append("field_power")
    except ImportError:
        pass

    unique = list(dict.fromkeys(threats))
    return {
        "lies_detected": unique,
        "lie_count": len(unique),
        "sources": sources,
        "forward": True,
        "truth_ok": len(unique) == 0,
    }


def _weapon_threat(weapon_id: str) -> str:
    spec = load_entity_spec()
    w = (spec.get("weapons") or {}).get(weapon_id, {})
    targets = w.get("targets") or []
    return str(targets[0] if targets else "corrupt_frame")


def _trip_layers(wmeta: dict[str, Any], weapon_id: str, acted: list[str]) -> None:
    from zocr_kill import trip
    for layer in wmeta.get("trip") or []:
        trip(str(layer), reason=f"entity_weapon:{weapon_id}")
        acted.append(f"trip_{layer}")


def _offense_fire(
    weapon_id: str,
    wmeta: dict[str, Any],
    *,
    threat: str | None,
    acted: list[str],
) -> tuple[str, dict[str, Any] | None]:
    from zocr_offense import offense_strike
    t = threat or _weapon_threat(weapon_id)
    offense_row = offense_strike(t, source=f"entity:{weapon_id}")
    acted.append(f"offense_strike:{t}")
    _trip_layers(wmeta, weapon_id, acted)
    if weapon_id in ("reject_lie", "autokill_certain", "moire_kill", "grid_jam_sever"):
        st = _load_state()
        st["lies_rejected"] = int(st.get("lies_rejected", 0)) + 1
        _save_state(st)
    return t, offense_row


def _weapon_handlers() -> dict[str, Any]:
    return {
        "forward_truth": lambda **kw: _h_forward_truth(**kw),
        "vigilance_forward": lambda **kw: _h_vigilance_forward(**kw),
        "vigilance_swarm": lambda **kw: _h_vigilance_swarm(**kw),
        "queen_weaponize": lambda **kw: _h_queen_weaponize(**kw),
        "twin_salvo": lambda **kw: _h_twin_salvo(**kw),
        "joule_throttle": lambda **kw: _h_joule_throttle(**kw),
        "entropy_fold": lambda **kw: _h_entropy_fold(**kw),
        "cool_gate": lambda **kw: _h_cool_gate(**kw),
        "rod_snap": lambda **kw: _h_rod_snap(**kw),
        "spectrum_hard": lambda **kw: _h_spectrum_hard(**kw),
        "trust_strike": lambda **kw: _h_trust_strike(**kw),
        "irtn_woven": lambda **kw: _h_irtn_woven(**kw),
        "hostess_corroborate": lambda **kw: _h_hostess_corroborate(**kw),
        "mesh_sever": lambda **kw: _h_mesh_sever(**kw),
        "code_seal_maul": lambda **kw: _h_code_seal_maul(**kw),
        "moire_kill": lambda **kw: _h_moire_kill(**kw),
        "weave_purge": lambda **kw: _h_weave_purge(**kw),
        "provenance_seal": lambda **kw: _h_provenance_seal(**kw),
        "g16_preempt": lambda **kw: _h_g16_preempt(**kw),
        "field_opt_burst": lambda **kw: _h_field_opt_burst(**kw),
        "gnu26_strike": lambda **kw: _h_gnu26_strike(**kw),
        "forge_forward": lambda **kw: _h_forge_forward(**kw),
        "ai_beacon_reject": lambda **kw: _h_ai_beacon_reject(**kw),
        "streak_ignite": lambda **kw: _h_streak_ignite(**kw),
        "hell_rip": lambda **kw: _h_hell_rip(**kw),
        "heaven_pass": lambda **kw: _h_heaven_pass(**kw),
    }


def _h_forward_truth(**_: Any) -> dict[str, Any]:
    fwd = truth_forward(speak=True, scan=True, fire_weapons=False)
    return {"acted": ["forward_ledger"], "forward": fwd, "offense": None}


def _h_hell_rip(*, threat: str | None = None, **_: Any) -> dict[str, Any]:
    from zocr_heaven_hell import hell_rip
    rip = hell_rip(threat=threat, fire_offense=True)
    acted = ["hell_rip"]
    if rip.get("ripped"):
        acted.append(f"offense:{rip.get('threat')}")
    return {"acted": acted, "heaven_hell": rip, "offense": rip.get("offense")}


def _h_heaven_pass(**_: Any) -> dict[str, Any]:
    from zocr_heaven_hell import heaven_pass
    passed = heaven_pass(reason="entity_weapon:heaven_pass")
    return {"acted": ["heaven_pass"], "heaven_hell": passed, "offense": None}


def _h_vigilance_forward(**_: Any) -> dict[str, Any]:
    from zocr_vigilance import vigilance_start
    vig = vigilance_start(profile="sentinel", prefer="auto")
    return {"acted": ["vigilance_start"], "vigilance": vig, "offense": None}


def _h_vigilance_swarm(**_: Any) -> dict[str, Any]:
    from zocr_additives import additives_status
    from zocr_vigilance import vigilance_start
    vig = vigilance_start(profile="patrol", prefer="auto")
    add = additives_status()
    return {"acted": ["vigilance_swarm"], "vigilance": vig, "additives": add, "offense": None}


def _h_joule_throttle(**_: Any) -> dict[str, Any]:
    from zocr_video import video_tune
    tuned = video_tune(mode="media", fps=2, max_width=1280, reason="weapon:joule_throttle")
    t, off = _offense_fire("joule_throttle", {"offense": "joule_throttle"}, threat="thermal_breach", acted=[])
    return {"acted": ["joule_throttle", f"offense:{t}"], "video_tune": tuned, "offense": off, "threat": t}


def _h_entropy_fold(**_: Any) -> dict[str, Any]:
    from zocr_grok16 import grok16_eye_tune
    tune = grok16_eye_tune()
    t, off = _offense_fire("entropy_fold", {"offense": "entropy_fold"}, threat="entropy_spoof", acted=[])
    return {"acted": ["entropy_fold", f"offense:{t}"], "grok16": tune, "offense": off, "threat": t}


def _h_cool_gate(**_: Any) -> dict[str, Any]:
    try:
        from zocr_cool import cool_status
        cool = cool_status()
    except ImportError:
        cool = {"enabled": False}
    return {"acted": ["cool_gate"], "cool": cool, "offense": None}


def _h_rod_snap(**_: Any) -> dict[str, Any]:
    from zocr_eye import teach
    eye = teach("mammal_night", source="weapon:rod_snap")
    acted = ["rod_snap", "teach:mammal_night"]
    t, off = _offense_fire("rod_dominant_snap", {"offense": "preempt_rtx"}, threat="blackout", acted=[])
    acted.extend([f"offense:{t}"])
    return {"acted": acted, "eye": eye, "offense": off, "threat": t}


def _h_spectrum_hard(**_: Any) -> dict[str, Any]:
    from zocr_eye import teach
    eye = teach("raptor", source="weapon:spectrum_hard")
    acted = ["spectrum_hard", "teach:raptor"]
    t, off = _offense_fire("spectrum_hard_switch", {"offense": "preempt_rtx"}, threat="rf_jam", acted=[])
    acted.append(f"offense:{t}")
    return {"acted": acted, "eye": eye, "offense": off, "threat": t}


def _h_trust_strike(**kw: Any) -> dict[str, Any]:
    from zocr_trust import verify_trust_mesh
    mesh = verify_trust_mesh()
    acted: list[str] = [f"trust_strike:ok={mesh.get('ok')}"]
    off = None
    t = kw.get("threat") or "trust_breach"
    if not mesh.get("ok"):
        t, off = _offense_fire("trust_strike", {"offense": "trust_strike"}, threat=t, acted=acted)
    return {"acted": acted, "mesh": mesh, "offense": off, "threat": t}


def _h_irtn_woven(**_: Any) -> dict[str, Any]:
    from zocr_trust import verify_trust_mesh
    mesh = verify_trust_mesh()
    return {"acted": ["irtn_woven"], "mesh": mesh, "offense": None}


def _h_hostess_corroborate(**_: Any) -> dict[str, Any]:
    from zocr_trust import hostess7_bridge
    h7 = hostess7_bridge()
    return {"acted": ["hostess_corroborate"], "hostess7": h7, "offense": None}


def _h_mesh_sever(**kw: Any) -> dict[str, Any]:
    from zocr_trust import verify_trust_mesh
    mesh = verify_trust_mesh()
    acted = ["mesh_sever"]
    wmeta = {"offense": "trust_strike", "trip": ["vision"]}
    t, off = _offense_fire("mesh_sever", wmeta, threat=kw.get("threat") or "trust_breach", acted=acted)
    return {"acted": acted, "mesh": mesh, "offense": off, "threat": t}


def _h_code_seal_maul(**_: Any) -> dict[str, Any]:
    from zocr_security import seal_codebase, verify_code_seal
    v = verify_code_seal()
    seal = seal_codebase() if not v.get("ok") else v
    acted = ["code_seal_maul"]
    t, off = _offense_fire("code_seal_maul", {"offense": "seal_threat"}, threat="corrupt_frame", acted=acted)
    return {"acted": acted, "seal": seal, "offense": off, "threat": t}


def _scan_last_good() -> dict[str, Any]:
    last = _ROOT / "data" / "preserve" / "last-good.png"
    if not last.is_file():
        return {"ok": False, "error": "no_last_good"}
    from zocr_pattern import scan_frame
    return scan_frame(last)


def _h_moire_kill(**kw: Any) -> dict[str, Any]:
    scan = _scan_last_good()
    acted = ["moire_kill", "pattern_scan"]
    t, off = _offense_fire("moire_kill", {"offense": "pattern_strike"}, threat=kw.get("threat") or "moire_weave", acted=acted)
    return {"acted": acted, "scan": scan, "offense": off, "threat": t}


def _h_weave_purge(**kw: Any) -> dict[str, Any]:
    scan = _scan_last_good()
    acted = ["weave_purge", "pattern_scan"]
    t, off = _offense_fire("foreign_weave_purge", {"offense": "pattern_strike"}, threat=kw.get("threat") or "grid_jam", acted=acted)
    return {"acted": acted, "scan": scan, "offense": off, "threat": t}


def _h_ai_beacon_reject(**kw: Any) -> dict[str, Any]:
    scan = _scan_last_good()
    acted = ["ai_beacon_reject"]
    t, off = _offense_fire("ai_beacon_reject", {"offense": "pattern_strike"}, threat=kw.get("threat") or "injected_marker", acted=acted)
    return {"acted": acted, "scan": scan, "offense": off, "threat": t}


def _h_provenance_seal(**_: Any) -> dict[str, Any]:
    last = _ROOT / "data" / "preserve" / "last-good.png"
    if not last.is_file():
        return {"acted": ["provenance_seal_skip"], "offense": None}
    from zocr_pattern import stamp_frame
    stamped = stamp_frame(last, session_id="entity_weapon", seq=1)
    return {"acted": ["provenance_seal"], "stamp": stamped, "offense": None}


def _h_g16_preempt(**_: Any) -> dict[str, Any]:
    from zocr_field_compiler import field_compiler_status
    fc = field_compiler_status()
    acted = ["g16_preempt"]
    t, off = _offense_fire("g16_preempt", {"offense": "preempt_rtx"}, threat="compiler_gap", acted=acted)
    return {"acted": acted, "field_compiler": fc, "offense": off, "threat": t}


def _h_field_opt_burst(**_: Any) -> dict[str, Any]:
    from zocr_robotics import arm_robotics
    armed = arm_robotics("submicron", start_stream=False)
    acted = ["field_opt_burst"]
    t, off = _offense_fire("field_opt_burst", {"offense": "preempt_rtx"}, threat="rf_jam", acted=acted)
    return {"acted": acted, "armed": armed, "offense": off, "threat": t}


def _h_gnu26_strike(**_: Any) -> dict[str, Any]:
    from zocr_grok16 import grok16_eye_witness
    g = grok16_eye_witness()
    acted = ["gnu26_strike"]
    t, off = _offense_fire("gnu26_strike", {"offense": "seal_threat"}, threat="compiler_gap", acted=acted)
    return {"acted": acted, "grok16": g, "offense": off, "threat": t}


def _h_forge_forward(**_: Any) -> dict[str, Any]:
    from zocr_field_compiler import forge_posture
    forge = forge_posture()
    acted = ["forge_forward"]
    t, off = _offense_fire("forge_forward", {"offense": "preempt_rtx"}, threat="compiler_gap", acted=acted)
    return {"acted": acted, "forge": forge, "offense": off, "threat": t}


def _h_streak_ignite(**_: Any) -> dict[str, Any]:
    from zocr_offense import _load_state as off_state, _save_state as off_save
    st = off_state()
    st["preempt_armed"] = True
    st["threat_streak"] = max(int(st.get("threat_streak", 0)), 2)
    off_save(st)
    acted = ["streak_ignite"]
    t, off = _offense_fire("offense_streak_ignite", {"offense": "preempt_rtx"}, threat="rf_jam", acted=acted)
    return {"acted": acted, "offense": off, "threat": t}


def _h_queen_weaponize(**kw: Any) -> dict[str, Any]:
    mode = str(kw.get("mode") or "war")
    out = weaponize_eyeball(mode=mode)
    return {"acted": ["queen_weaponize"], "weaponize": out, "offense": None}


def _h_twin_salvo(**kw: Any) -> dict[str, Any]:
    mode = str(kw.get("mode") or "war")
    live = make_living_live(mode, start_stream=False, vigilance=True)
    return {"acted": ["twin_salvo"], "salvo": live, "offense": None}


def weaponize_eyeball(*, mode: str = "war") -> dict[str, Any]:
    """Queen-style full socket weaponize — arm, verify, offense mesh, twins hot."""
    from zocr_robotics import arm_robotics
    from zocr_security import verify_code_seal
    from zocr_trust import verify_trust_mesh

    armed = arm_robotics(mode, start_stream=False)
    mesh = verify_trust_mesh()
    seal = verify_code_seal()
    fwd = truth_forward(speak=True, scan=True, fire_weapons=True)
    racks = entity_weapon_racks()

    st = _load_state()
    st["weapons_armed"] = True
    st["weaponize_mode"] = mode
    st["living_live"] = bool(armed.get("ok"))
    st["truth_forward"] = True
    _save_state(st)

    log_event("eyeball_weaponize", ok=armed.get("ok"), mode=mode, weapons=racks.get("weapons_total"))

    return {
        "ok": bool(armed.get("ok")) and bool(seal.get("ok")),
        "schema": "zocr-eyeball-weaponize/v1",
        "mode": mode,
        "socket_fit": racks.get("socket_fit"),
        "weapons_total": racks.get("weapons_total"),
        "racks": len(racks.get("racks") or {}),
        "armed": armed,
        "trust_mesh": {"ok": mesh.get("ok"), "woven_paths": mesh.get("woven_paths")},
        "code_seal": {"ok": seal.get("ok")},
        "truth_forward": fwd,
        "offense_rule": "Defense of vision requires offense.",
        "posture": "monster_in_socket",
    }


def fire_entity_weapon(
    weapon_id: str,
    *,
    threat: str | None = None,
    source: str = "entity",
    mode: str | None = None,
) -> dict[str, Any]:
    """Entity eyeball fires a weapon — independent authority selects salvo from threat."""
    spec = load_entity_spec()
    weapons = spec.get("weapons") or {}
    understood: dict[str, Any] | None = None
    if threat and (weapon_id in ("auto", "") or weapon_id not in weapons):
        understood = eye_understand_target(threat)
        weapon_id = str(understood.get("weapon_selected") or auto_weapon_for_threat(threat))
    if weapon_id not in weapons:
        return {"ok": False, "error": "unknown_weapon", "weapon": weapon_id, "available": list(weapons.keys())}

    wmeta = weapons[weapon_id]
    entity = wmeta.get("entity", "truth")
    handler_name = wmeta.get("handler")
    handlers = _weapon_handlers()

    if handler_name and handler_name in handlers:
        payload = handlers[handler_name](threat=threat, mode=mode, wmeta=wmeta, weapon_id=weapon_id)
        if handler_name == "forward_truth":
            return {
                "ok": True,
                "schema": "zocr-entity-weapon/v1",
                "weapon": weapon_id,
                "entity": entity,
                "rack": wmeta.get("rack"),
                "label": wmeta.get("label"),
                **payload,
            }
        acted = payload.get("acted") or []
        offense_row = payload.get("offense")
        row = {"ts": _ts(), "weapon": weapon_id, "entity": entity, **payload}
    else:
        acted: list[str] = []
        t, offense_row = _offense_fire(weapon_id, wmeta, threat=threat, acted=acted)
        row = {"ts": _ts(), "weapon": weapon_id, "entity": entity, "threat": t, "offense": offense_row}

    st = _load_state()
    st["last_weapon"] = row
    st["weapons_armed"] = True
    _save_state(st)
    _append_forward({"event": "weapon", **row})
    log_event("entity_weapon", ok=True, weapon=weapon_id, entity=entity, rack=wmeta.get("rack"), source=source)

    out = {
        "ok": True,
        "schema": "zocr-entity-weapon/v1",
        "weapon": weapon_id,
        "entity": entity,
        "rack": wmeta.get("rack"),
        "label": wmeta.get("label"),
        "acted": acted,
        "offense": offense_row,
        "row": row,
        "authority": "entity_eyeball",
    }
    if understood:
        out["understood_target"] = understood
    return out


def living_eyeball_status() -> dict[str, Any]:
    from zocr_eye import eye_status, load_final_eyeball, _load_final_state, _eyeball_witness
    from zocr_preserve import preserve_status
    from zocr_stream import stream_status
    from zocr_video import video_status

    spec = load_entity_spec()
    twin = (spec.get("twins") or {}).get("living", {})
    st = _load_state()
    fstate = _load_final_state()
    witness = _eyeball_witness(seal=False)
    doc = load_final_eyeball()
    mid = fstate.get("active_mode", "dishes")
    mode = (doc.get("modes") or {}).get(mid, {})
    return {
        "schema": "zocr-living-eyeball/v1",
        "ts": _ts(),
        "entity": twin.get("entity", "Vita"),
        "title": twin.get("title", "The Eyeball That Lives"),
        "motto": twin.get("motto"),
        "live": bool(st.get("living_live")),
        "always": twin.get("always", []),
        "eye": eye_status(),
        "final_eyeball": {
            "active_mode": mid,
            "label": mode.get("label", mid),
            "prescription": fstate.get("last_prescription"),
        },
        "preserve": preserve_status(),
        "stream": stream_status(),
        "video": video_status(),
        "sovereign_time": witness.get("sovereign_time"),
        "redundancy": witness.get("redundancy"),
        "field_compiler": _grok16_witness_for_entity(mid, mode.get("eye_profile")),
    }


def _grok16_witness_for_entity(mode: str, eye_profile: str | None) -> dict[str, Any]:
    try:
        from zocr_grok16 import grok16_eye_witness
        return grok16_eye_witness(mode=mode, eye_profile=eye_profile)
    except ImportError:
        return {"field_compiler": "Grok16", "ready": False}


def truth_eyeball_status() -> dict[str, Any]:
    from zocr_offense import offense_status
    from zocr_pattern import pattern_status
    from zocr_security import verify_code_seal
    from zocr_trust import verify_trust_mesh

    from zocr_eye import _load_final_state as eye_final_state, load_final_eyeball

    spec = load_entity_spec()
    twin = (spec.get("twins") or {}).get("truth", {})
    st = _load_state()
    fstate = eye_final_state()
    mid = fstate.get("active_mode", "dishes")
    mode_doc = (load_final_eyeball().get("modes") or {}).get(mid, {})
    lies = _detect_lies()
    mesh = verify_trust_mesh()
    seal = verify_code_seal()

    recent_forward: list[dict] = []
    if FORWARD_LEDGER.is_file():
        try:
            for line in FORWARD_LEDGER.read_text(encoding="utf-8").splitlines()[-5:]:
                if line.strip():
                    recent_forward.append(json.loads(line))
        except (OSError, json.JSONDecodeError):
            pass

    try:
        from zocr_heaven_hell import heaven_hell_truth_status
        hh_truth = heaven_hell_truth_status()
    except ImportError:
        hh_truth = {}

    return {
        "schema": "zocr-truth-eyeball/v1",
        "ts": _ts(),
        "entity": twin.get("entity", "Veritas"),
        "title": twin.get("title", "The Eyeball That Talks Truth"),
        "motto": twin.get("motto"),
        "always_forward": bool(st.get("truth_forward", True)),
        "weapons_armed": bool(st.get("weapons_armed", True)),
        "forward_count": int(st.get("forward_count", 0)),
        "lies_rejected": int(st.get("lies_rejected", 0)),
        "always": twin.get("always", []),
        "lies": lies,
        "truth_ok": lies.get("truth_ok"),
        "offense": offense_status(),
        "pattern": pattern_status(),
        "code_seal": seal,
        "trust_mesh": {"ok": mesh.get("ok"), "woven_paths": mesh.get("woven_paths")},
        "weapons": entity_weapons(),
        "last_weapon": st.get("last_weapon"),
        "recent_forward": recent_forward,
        "speak": _truth_speak(lies, mesh, seal, hh_truth),
        "truth_doctrine": hh_truth.get("truth"),
        "heaven_hell": hh_truth.get("heaven_hell"),
        "field_compiler": _grok16_witness_for_entity(mid, mode_doc.get("eye_profile")),
    }


def _truth_speak(
    lies: dict[str, Any],
    mesh: dict[str, Any],
    seal: dict[str, Any],
    hh_truth: dict[str, Any] | None = None,
) -> str:
    if lies.get("lies_detected"):
        return (
            f"Lie guard active — rejected: {', '.join(lies['lies_detected'])}. "
            "Always forward. Weapons ready."
        )
    woven = mesh.get("woven_paths", 0)
    seal_ok = "sealed" if seal.get("ok") else "check seal"
    hh_line = ""
    if hh_truth:
        hh = hh_truth.get("heaven_hell") or {}
        if hh.get("speak"):
            hh_line = f" {hh['speak']}"
    return (
        f"Truth forward — no lies on ingress. Mesh woven {woven}. Code {seal_ok}."
        f"{hh_line}"
    ).strip()


def truth_forward(
    *,
    speak: bool = True,
    scan: bool = True,
    fire_weapons: bool = True,
) -> dict[str, Any]:
    """Truth eyeball advances — scan lies, speak truth, optionally fire weapons."""
    lies = _detect_lies() if scan else {"lies_detected": [], "truth_ok": True}
    spoken = _truth_speak(lies, {}, {"ok": True}) if speak else ""

    weapons_fired: list[dict[str, Any]] = []
    if fire_weapons and lies.get("lies_detected"):
        for threat in lies["lies_detected"]:
            wid = auto_weapon_for_threat(threat)
            weapons_fired.append(fire_entity_weapon(wid, threat=threat, source="truth_forward"))

    st = _load_state()
    st["truth_forward"] = True
    st["forward_count"] = int(st.get("forward_count", 0)) + 1
    if lies.get("lies_detected"):
        st["lies_rejected"] = int(st.get("lies_rejected", 0)) + len(lies["lies_detected"])
    _save_state(st)

    row = {
        "schema": "zocr-truth-forward/v1",
        "ts": _ts(),
        "forward": True,
        "speak": spoken,
        "lies": lies,
        "weapons_fired": len(weapons_fired),
    }
    _append_forward(row)
    log_event("truth_forward", ok=True, lies=len(lies.get("lies_detected", [])), weapons=len(weapons_fired))

    return {
        "ok": True,
        "schema": "zocr-truth-forward/v1",
        "always_forward": True,
        "speak": spoken,
        "lies": lies,
        "weapons_fired": weapons_fired,
        "forward_count": st["forward_count"],
    }


def make_living_live(
    mode: str = "dishes",
    *,
    voice: str | None = None,
    start_stream: bool = False,
    vigilance: bool = False,
) -> dict[str, Any]:
    """Living eyeball — arm perceive path and make the field live."""
    from zocr_robotics import arm_robotics

    armed = arm_robotics(mode, voice=voice, start_stream=start_stream)
    vig: dict[str, Any] | None = None
    if vigilance:
        from zocr_vigilance import vigilance_start
        vig = vigilance_start(profile="sentinel", prefer="auto")

    truth = truth_forward(speak=True, scan=True, fire_weapons=True)

    st = _load_state()
    st["living_live"] = bool(armed.get("ok"))
    st["truth_forward"] = True
    _save_state(st)

    log_event("living_live", ok=armed.get("ok"), mode=mode, stream=start_stream, vigilance=vigilance)

    return {
        "ok": bool(armed.get("ok")),
        "schema": "zocr-living-live/v1",
        "entity": "Vita",
        "title": "The Eyeball That Lives",
        "live": st["living_live"],
        "armed": armed,
        "vigilance": vig,
        "truth_forward": truth,
        "twins": twin_eyeball_status(),
    }


def twin_eyeball_status() -> dict[str, Any]:
    spec = load_entity_spec()
    living = living_eyeball_status()
    truth = truth_eyeball_status()
    st = _load_state()
    racks = entity_weapon_racks()
    return {
        "schema": "zocr-twin-eyeball/v1",
        "ts": _ts(),
        "title": spec.get("title"),
        "rule": spec.get("rule"),
        "socket_fit": spec.get("socket_fit"),
        "arsenal": {
            "weapons_total": racks.get("weapons_total"),
            "racks": len(racks.get("racks") or {}),
            "weaponize_mode": st.get("weaponize_mode"),
        },
        "living": living,
        "truth": truth,
        "both_live": bool(st.get("living_live")),
        "always_forward": bool(st.get("truth_forward", True)),
        "weapons_armed": bool(st.get("weapons_armed", True)),
        "weapons": entity_weapons(),
    }


def _load_teach_doctrine() -> dict[str, Any]:
    path = _ROOT / "data" / "eye-teach-doctrine.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema": "zocr-eye-teach-doctrine/v1", "lessons": {}}


def eye_targets_know() -> dict[str, Any]:
    """Catalog of targets the eye understands — per-weapon targets + lie markers + map."""
    spec = load_entity_spec()
    weapons = spec.get("weapons") or {}
    by_target: dict[str, list[str]] = {}
    all_targets: set[str] = set()
    for wid, meta in weapons.items():
        for t in meta.get("targets") or []:
            all_targets.add(t)
            by_target.setdefault(t, []).append(wid)
    forward = spec.get("forward") or {}
    lie_markers = list(forward.get("lie_markers") or [])
    threat_map = _threat_weapon_map()
    return {
        "schema": "zocr-eye-targets/v1",
        "ts": _ts(),
        "targets_known": sorted(all_targets),
        "target_count": len(all_targets),
        "weapons_per_target": {k: sorted(v) for k, v in sorted(by_target.items())},
        "lie_markers": lie_markers,
        "threat_weapon_map": threat_map,
        "truth_markers": forward.get("truth_markers") or [],
        "rule": "The eye understands targets before strike — grep entity-eyeball.json",
    }


def eye_understand_target(threat: str) -> dict[str, Any]:
    """Resolve threat → weapon, targets[], doctrine — independent aim."""
    threat = str(threat or "").strip()
    spec = load_entity_spec()
    weapons = spec.get("weapons") or {}
    weapon_id = auto_weapon_for_threat(threat)
    wmeta = weapons.get(weapon_id, {})
    lie = threat in set(spec.get("forward", {}).get("lie_markers") or [])
    return {
        "schema": "zocr-eye-understand-target/v1",
        "ts": _ts(),
        "threat": threat,
        "lie_marker": lie,
        "weapon_selected": weapon_id,
        "weapon_label": wmeta.get("label"),
        "rack": wmeta.get("rack"),
        "entity": wmeta.get("entity"),
        "targets": wmeta.get("targets") or [],
        "doctrine": wmeta.get("doctrine"),
        "strike": wmeta.get("strike"),
        "offense": wmeta.get("offense"),
        "authority": "entity_eyeball",
        "independent": True,
    }


def eye_weapon_authority() -> dict[str, Any]:
    """Independent weapon authority — the eye arms and selects, not remote puppet."""
    spec = load_entity_spec()
    st = _load_state()
    teach = _load_teach_doctrine()
    auth = spec.get("weapon_authority") or teach.get("authority") or {}
    racks = entity_weapon_racks()
    lies = _detect_lies()
    return {
        "schema": "zocr-eye-weapon-authority/v1",
        "ts": _ts(),
        "holder": auth.get("holder", "entity_eyeball"),
        "independent": bool(auth.get("independent", True)),
        "remote_puppet": bool(auth.get("remote_puppet", False)),
        "weapons_armed": bool(st.get("weapons_armed", True)),
        "weapons_total": racks.get("weapons_total", 0),
        "racks": len(racks.get("racks") or {}),
        "auto_threat_resolution": auth.get("auto_threat_resolution", "auto_weapon_for_threat"),
        "kill_separate": True,
        "lies_current": lies.get("lies_detected") or [],
        "rule": auth.get(
            "rule",
            "The eye holds independent authority over weapons — aim in socket, truth forward",
        ),
        "speak": teach.get("lessons", {}).get("authority", ""),
        "twins": list((spec.get("twins") or {}).values()),
    }


def eye_teach(*, lesson: str | None = None) -> dict[str, Any]:
    """Teach voice — the eye instructs the operator."""
    doc = _load_teach_doctrine()
    lessons = doc.get("lessons") or {}
    key = (lesson or "intro").strip().lower()
    if key not in lessons:
        key = "intro"
    posture = eye_weapon_authority()
    targets = eye_targets_know()
    return {
        "schema": "zocr-eye-teach/v1",
        "ts": _ts(),
        "voice": doc.get("voice", "Teach"),
        "lesson": key,
        "available_lessons": sorted(lessons.keys()),
        "speak": lessons[key],
        "authority": {
            "independent": posture.get("independent"),
            "weapons_total": posture.get("weapons_total"),
            "weapons_armed": posture.get("weapons_armed"),
        },
        "targets_known": targets.get("target_count"),
        "ok": True,
    }


def entity_doctrine() -> dict[str, Any]:
    spec = load_entity_spec()
    weapons = spec.get("weapons") or {}
    return {
        "schema": "zocr-entity-eyeball-doctrine/v2",
        "title": spec.get("title"),
        "rule": spec.get("rule"),
        "weapon_authority": spec.get("weapon_authority"),
        "socket_fit": spec.get("socket_fit"),
        "twins": spec.get("twins"),
        "racks": spec.get("racks"),
        "weapons_total": len(weapons),
        "weapons": list(weapons.keys()),
        "forward": spec.get("forward"),
        "weaponize": "weaponize_eyeball(mode='war')",
        "teach": "eye_teach() — GET /api/eye/teach/doctrine",
    }


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower()
    if cmd in ("status", "json", "twin"):
        print(json.dumps(twin_eyeball_status(), indent=2))
        return 0
    if cmd == "living":
        print(json.dumps(living_eyeball_status(), indent=2))
        return 0
    if cmd == "truth":
        print(json.dumps(truth_eyeball_status(), indent=2))
        return 0
    if cmd == "forward":
        print(json.dumps(truth_forward(), indent=2))
        return 0
    if cmd == "live":
        mode = sys.argv[2] if len(sys.argv) > 2 else "dishes"
        print(json.dumps(make_living_live(mode), indent=2))
        return 0
    if cmd == "weapons":
        print(json.dumps({"ok": True, "weapons": entity_weapons()}, indent=2))
        return 0
    if cmd == "racks":
        print(json.dumps(entity_weapon_racks(), indent=2))
        return 0
    if cmd == "weaponize":
        mode = sys.argv[2] if len(sys.argv) > 2 else "war"
        print(json.dumps(weaponize_eyeball(mode=mode), indent=2))
        return 0
    if cmd == "fire" and len(sys.argv) > 2:
        threat = sys.argv[3] if len(sys.argv) > 3 else None
        print(json.dumps(fire_entity_weapon(sys.argv[2], threat=threat), indent=2))
        return 0
    if cmd == "doctrine":
        print(json.dumps(entity_doctrine(), indent=2))
        return 0
    if cmd == "teach":
        lesson = sys.argv[2] if len(sys.argv) > 2 else None
        print(json.dumps(eye_teach(lesson=lesson), indent=2))
        return 0
    if cmd == "authority":
        print(json.dumps(eye_weapon_authority(), indent=2))
        return 0
    if cmd == "targets":
        print(json.dumps(eye_targets_know(), indent=2))
        return 0
    if cmd == "understand" and len(sys.argv) > 2:
        print(json.dumps(eye_understand_target(sys.argv[2]), indent=2))
        return 0
    print(json.dumps({
        "error": "usage: zocr_entity_eyeball.py [status|living|truth|teach [LESSON]|authority|targets|understand THREAT|fire WEAPON|auto THREAT|doctrine]",
    }, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())