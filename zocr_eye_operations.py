"""Final_Eye eye operations — enemy discernment, heaven/hell gate, disarmament."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from zocr_session import log_event

_ROOT = Path(__file__).resolve().parent
OPS_PATH = _ROOT / "data" / "eye-operations-doctrine.json"
STATE_PATH = _ROOT / "data" / "eye-operations-state.json"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_operations_doctrine() -> dict[str, Any]:
    try:
        return json.loads(OPS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema": "zocr-eye-operations/v1", "rule": "Enemy qualified before strike"}


def _load_state() -> dict[str, Any]:
    if STATE_PATH.is_file():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "schema": "zocr-eye-operations-state/v1",
        "disarmament_offers": 0,
        "disarmament_refusals": 0,
        "heaven_blocks": 0,
        "enemy_strikes": 0,
    }


def _save_state(st: dict[str, Any]) -> None:
    st["updated"] = _ts()
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(st, indent=2) + "\n", encoding="utf-8")


def _soul_map() -> dict[str, Any]:
    try:
        from zocr_heaven_hell import load_spec
        return load_spec().get("vision_threat_soul_map") or {}
    except ImportError:
        return {}


def soul_side_for_threat(threat: str) -> tuple[str, bool]:
    """Return (soul_side, hell_chosen) from heaven-hell vision map."""
    threat = str(threat or "").strip()
    entry = _soul_map().get(threat) or {}
    side = str(entry.get("soul_side") or "limbo").lower()
    hell = bool(entry.get("hell_chosen"))
    doc = load_operations_doctrine()
    if threat in (doc.get("enemy") or {}).get("markers") or []:
        if side == "limbo":
            side = "hell"
        hell = hell or True
    if threat in (doc.get("enemy") or {}).get("limbo_markers") or []:
        side = side if side != "hell" else "hell"
    return side, hell


def is_weapon_meta(wmeta: dict[str, Any]) -> bool:
    return bool(wmeta.get("strike") or wmeta.get("offense") or wmeta.get("handler"))


def qualify_enemy(threat: str) -> dict[str, Any]:
    """Enemy discernment — not people, lie/hostility on vision path."""
    threat = str(threat or "").strip()
    doc = load_operations_doctrine()
    enemy_doc = doc.get("enemy") or {}
    markers = set(enemy_doc.get("markers") or [])
    limbo = set(enemy_doc.get("limbo_markers") or [])
    truth = set(enemy_doc.get("truth_not_enemy") or [])
    side, hell_chosen = soul_side_for_threat(threat)
    is_enemy = threat in markers or side == "hell" or hell_chosen
    if threat in truth:
        is_enemy = False
        side = "heaven"
    return {
        "threat": threat,
        "enemy_qualified": is_enemy,
        "soul_side": side,
        "hell_chosen": hell_chosen,
        "limbo_watch": threat in limbo and side == "limbo",
        "definition": enemy_doc.get("definition"),
        "offense_allowed": is_enemy and side != "heaven",
    }


def disarmament_posture(threat: str, *, departed: bool | None = None) -> dict[str, Any]:
    doc = load_operations_doctrine()
    dis = doc.get("disarmament") or {}
    bearing = threat in set(dis.get("weapon_bearing_threats") or [])
    refused = bearing and departed is False
    return {
        "weapon_bearing": bearing,
        "offer": dis.get("offer"),
        "departed": departed,
        "refusal": refused,
        "escalation_weapon": dis.get("escalation_weapon") if refused else None,
        "lethal_weapon": dis.get("lethal_weapon") if refused else None,
        "rule": dis.get("rule"),
    }


def gate_eye_operation(
    weapon_id: str,
    threat: str | None,
    *,
    wmeta: dict[str, Any] | None = None,
    departed: bool | None = None,
) -> dict[str, Any]:
    """Heaven/Hell gate — qualify weapon, enemy, disarmament before offense."""
    threat = str(threat or "").strip()
    doc = load_operations_doctrine()
    wmeta = wmeta or {}
    enemy = qualify_enemy(threat) if threat else {"enemy_qualified": False, "soul_side": "limbo", "offense_allowed": False}
    disarm = disarmament_posture(threat, departed=departed) if threat else {}
    weapon_is_weapon = is_weapon_meta(wmeta) if wmeta else bool(weapon_id)

    offense_allowed = bool(enemy.get("offense_allowed"))
    heaven_block = enemy.get("soul_side") == "heaven" or threat in set(
        (doc.get("enemy") or {}).get("truth_not_enemy") or []
    )

    selected_weapon = weapon_id
    if disarm.get("refusal"):
        selected_weapon = str(disarm.get("lethal_weapon") or disarm.get("escalation_weapon") or weapon_id)

    st = _load_state()
    if heaven_block:
        st["heaven_blocks"] = int(st.get("heaven_blocks") or 0) + 1
    elif offense_allowed:
        st["enemy_strikes"] = int(st.get("enemy_strikes") or 0) + 1
    if disarm.get("weapon_bearing") and departed is None:
        st["disarmament_offers"] = int(st.get("disarmament_offers") or 0) + 1
    if disarm.get("refusal"):
        st["disarmament_refusals"] = int(st.get("disarmament_refusals") or 0) + 1
    _save_state(st)

    out = {
        "schema": "zocr-eye-operation-gate/v1",
        "ts": _ts(),
        "weapon_id": weapon_id,
        "weapon_discerned": weapon_is_weapon,
        "threat": threat,
        "enemy": enemy,
        "disarmament": disarm,
        "heaven_hell_gate": doc.get("heaven_hell_gate") or {},
        "offense_allowed": offense_allowed and not heaven_block,
        "heaven_block": heaven_block,
        "selected_weapon": selected_weapon,
        "action": "strike" if offense_allowed and not heaven_block else "heaven_pass",
    }
    log_event(
        "eye_operation_gate",
        ok=True,
        threat=threat,
        weapon=weapon_id,
        offense_allowed=out["offense_allowed"],
        soul_side=enemy.get("soul_side"),
    )
    return out


def eye_operations_status() -> dict[str, Any]:
    doc = load_operations_doctrine()
    st = _load_state()
    try:
        from zocr_heaven_hell import heaven_hell_status
        hh = heaven_hell_status()
    except ImportError:
        hh = {}
    return {
        "schema": "zocr-eye-operations-status/v1",
        "ts": _ts(),
        "version": doc.get("version", "1.2.0"),
        "codename": doc.get("codename", "heaven-hell-ops"),
        "rule": doc.get("rule"),
        "enemy": doc.get("enemy"),
        "discernment": doc.get("discernment"),
        "disarmament": doc.get("disarmament"),
        "heaven_hell": {
            "heaven_count": hh.get("heaven_count"),
            "hell_count": hh.get("hell_count"),
            "motto": (hh.get("motto") or "")[:200],
        },
        "counters": {
            "heaven_blocks": st.get("heaven_blocks"),
            "enemy_strikes": st.get("enemy_strikes"),
            "disarmament_offers": st.get("disarmament_offers"),
            "disarmament_refusals": st.get("disarmament_refusals"),
        },
    }


def main() -> int:
    import sys
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower()
    if cmd == "status":
        print(json.dumps(eye_operations_status(), indent=2))
        return 0
    if cmd == "doctrine":
        print(json.dumps(load_operations_doctrine(), indent=2))
        return 0
    if cmd == "gate" and len(sys.argv) > 3:
        print(json.dumps(gate_eye_operation(sys.argv[2], sys.argv[3]), indent=2))
        return 0
    if cmd == "qualify" and len(sys.argv) > 2:
        print(json.dumps(qualify_enemy(sys.argv[2]), indent=2))
        return 0
    print(json.dumps({"error": "usage: zocr_eye_operations.py [status|doctrine|qualify THREAT|gate WEAPON THREAT]"}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())