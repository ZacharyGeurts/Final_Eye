"""ZOCR Heaven/Hell + Truth parameters — wired from SG Hostess7, NEXUS-Shield, Queen panel."""
from __future__ import annotations

import importlib.util
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from zocr_session import log_event

_ROOT = Path(__file__).resolve().parent
_SG = _ROOT.parent
SPEC_PATH = _ROOT / "data" / "heaven-hell-truth.json"
STATE_PATH = _ROOT / "data" / "heaven-hell-state.json"
QUEEN_PANEL = _ROOT / "data" / "sovereign-time-state" / "field-queen-browser-panel.json"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_spec() -> dict[str, Any]:
    try:
        return json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema": "zocr-heaven-hell-truth/v1", "truth": {}, "heaven_hell": {}}


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save_state(st: dict[str, Any]) -> None:
    st["updated"] = _ts()
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(st, indent=2) + "\n", encoding="utf-8")


def _nexus_sg_root() -> Path:
    env = os.environ.get("NEXUS_SG_ROOT", "").strip()
    if env:
        return Path(env).resolve()
    return (_SG / "Latest" / "NEXUS-Shield").resolve()


def _nexus_install() -> Path:
    env = os.environ.get("NEXUS_INSTALL_ROOT", "").strip()
    if env:
        return Path(env).resolve()
    sg = _nexus_sg_root()
    if (sg / "lib" / "heaven-hell.py").is_file():
        return sg
    return Path("/usr/local/lib/nexus-shield")


def _nexus_state() -> Path:
    return Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))


def _import_nexus_mod(name: str, filename: str) -> Any | None:
    install = _nexus_install()
    path = install / "lib" / filename
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _classify_soul_side(
    *,
    verdict: str = "",
    trust_rank: int = 5,
    scores: dict[str, Any] | None = None,
    hell_chosen: bool = False,
    kill_eligible: bool = False,
) -> tuple[str, bool]:
    hh = _import_nexus_mod("nexus_heaven_hell", "heaven-hell.py")
    if hh and hasattr(hh, "classify_row"):
        return hh.classify_row({
            "verdict": verdict,
            "trust_rank": trust_rank,
            "scores": scores or {},
            "hell_chosen": hell_chosen,
            "kill_eligible": kill_eligible,
        })
    spec = load_spec()
    hh_spec = spec.get("heaven_hell") or {}
    scores = scores or {}
    heaven_v = set(hh_spec.get("heaven_verdicts") or [])
    hell_v = set(hh_spec.get("hell_verdicts") or [])
    op_floor = int(hh_spec.get("operator_auth_heaven_floor") or 10)
    min_trust = int(hh_spec.get("min_accept_trust_rank") or 2)
    if int(scores.get("operator_auth") or 0) >= op_floor:
        return "heaven", False
    if trust_rank <= min_trust and verdict in heaven_v:
        return "heaven", False
    if hell_chosen or kill_eligible or verdict == "HARM_CANDIDATE":
        return "hell", True
    if verdict in hell_v and int(scores.get("process_trust") or 0) <= 3:
        return "hell", bool(kill_eligible)
    return "limbo", False


def threat_soul_map(threat: str) -> dict[str, Any]:
    spec = load_spec()
    entry = (spec.get("vision_threat_soul_map") or {}).get(threat)
    if entry:
        return dict(entry)
    return {"soul_side": "limbo", "hell_chosen": False}


def _vision_heaven_hell_counts() -> dict[str, Any]:
    threats: list[str] = []
    meta_path = _ROOT / "data" / "preserve" / "last-good.json"
    if meta_path.is_file():
        meta = _load_json(meta_path, {})
        threats.extend(meta.get("threats") or [])

    heaven = 0
    hell = 0
    limbo = 0
    hell_chosen = 0
    mapped: list[dict[str, Any]] = []
    for t in threats:
        m = threat_soul_map(t)
        side = str(m.get("soul_side") or "limbo")
        chosen = bool(m.get("hell_chosen"))
        if side == "heaven":
            heaven += 1
        elif side == "hell":
            hell += 1
            if chosen:
                hell_chosen += 1
        else:
            limbo += 1
        mapped.append({"threat": t, "soul_side": side, "hell_chosen": chosen})

    return {
        "heaven_count": heaven,
        "hell_count": hell,
        "limbo_count": limbo,
        "hell_chosen_count": hell_chosen,
        "threats_mapped": mapped,
        "source": "vision_ingress",
    }


def _queen_panel_counts() -> dict[str, Any]:
    panel = _load_json(QUEEN_PANEL, {})
    slices = {s.get("id"): s for s in (panel.get("intel_digest") or []) if s.get("id")}
    heaven = int((slices.get("heaven") or {}).get("value") or 0)
    hell = int((slices.get("hell") or {}).get("value") or 0)
    field_ctx = panel.get("field_context") or ""
    truth_rating = panel.get("truth_rating") or {}
    return {
        "heaven_count": heaven,
        "hell_count": hell,
        "hell_chosen_count": hell,
        "field_context": field_ctx[:200],
        "truth_score": truth_rating.get("score"),
        "truth_signal": panel.get("truth_signal"),
        "correlation_score": panel.get("correlation_score"),
        "source": "queen_panel",
    }


def _nexus_live_counts() -> dict[str, Any] | None:
    state_file = _nexus_state() / "heaven-hell.json"
    if state_file.is_file():
        doc = _load_json(state_file, {})
        if doc:
            return {
                "heaven_count": int(doc.get("heaven_count") or 0),
                "hell_count": int(doc.get("hell_count") or 0),
                "hell_chosen_count": int(doc.get("hell_chosen_count") or 0),
                "limbo_count": int(doc.get("limbo_count") or 0),
                "hostile_registry": int(doc.get("hostile_registry") or 0),
                "source": "nexus_state",
                "updated": doc.get("updated"),
            }

    hh = _import_nexus_mod("nexus_heaven_hell", "heaven-hell.py")
    if hh and hasattr(hh, "build_status"):
        try:
            doc = hh.build_status()
            return {
                "heaven_count": int(doc.get("heaven_count") or 0),
                "hell_count": int(doc.get("hell_count") or 0),
                "hell_chosen_count": int(doc.get("hell_chosen_count") or 0),
                "limbo_count": int(doc.get("limbo_count") or 0),
                "hostile_registry": int(doc.get("hostile_registry") or 0),
                "source": "nexus_build_status",
                "updated": doc.get("updated"),
            }
        except Exception:
            pass
    return None


def truth_doctrine_status() -> dict[str, Any]:
    spec = load_spec()
    truth = spec.get("truth") or {}
    gates = truth.get("truth_gates") or []
    gate_weight = round(sum(float(g.get("weight") or 0) for g in gates), 2)
    return {
        "schema": "zocr-truth-doctrine/v1",
        "ts": _ts(),
        "motto": truth.get("motto"),
        "default_posture": truth.get("default_posture"),
        "never_deceive": truth.get("never_deceive"),
        "death_sentence_hell_exception": truth.get("death_sentence_hell_exception"),
        "noise_ratio": truth.get("noise_ratio"),
        "signal_ratio": truth.get("signal_ratio"),
        "truth_adapt_floor": truth.get("truth_adapt_floor"),
        "truth_genius_floor": truth.get("truth_genius_floor"),
        "truth_gates": gates,
        "truth_gate_weight_sum": gate_weight,
        "corpus_ids": [c.get("id") for c in (truth.get("corpus") or [])],
    }


def heaven_hell_status(*, prefer_live: bool = True) -> dict[str, Any]:
    spec = load_spec()
    hh_spec = spec.get("heaven_hell") or {}
    lethal = spec.get("lethal") or {}

    live: dict[str, Any] | None = None
    if prefer_live:
        live = _nexus_live_counts()
    queen = _queen_panel_counts()
    vision = _vision_heaven_hell_counts()

    counts = live or queen
    if vision.get("hell_chosen_count") or vision.get("hell_count"):
        counts = {
            **counts,
            "vision_overlay": vision,
            "heaven_count": max(int(counts.get("heaven_count") or 0), vision["heaven_count"]),
            "hell_count": max(int(counts.get("hell_count") or 0), vision["hell_count"]),
            "hell_chosen_count": max(
                int(counts.get("hell_chosen_count") or 0),
                vision["hell_chosen_count"],
            ),
        }

    st = _load_json(STATE_PATH, {})
    posture = str(st.get("posture") or "hell_first")
    if not st:
        st = {"schema": "zocr-heaven-hell-state/v1", "posture": posture, "rips": 0, "heaven_passes": 0}
        _save_state(st)

    return {
        "schema": "zocr-heaven-hell-status/v1",
        "ts": _ts(),
        "motto": hh_spec.get("motto"),
        "tagline": hh_spec.get("tagline"),
        "hostility_priority": hh_spec.get("hostility_priority", "hell_first"),
        "no_mercy": hh_spec.get("no_mercy"),
        "no_friendly_fire": hh_spec.get("no_friendly_fire"),
        "heaven_zero_cost": hh_spec.get("heaven_zero_cost"),
        "heaven_count": int(counts.get("heaven_count") or 0),
        "hell_count": int(counts.get("hell_count") or 0),
        "hell_chosen_count": int(counts.get("hell_chosen_count") or 0),
        "limbo_count": int(counts.get("limbo_count") or vision.get("limbo_count") or 0),
        "counts_source": counts.get("source", "queen_panel"),
        "queen_panel": queen,
        "vision": vision,
        "nexus_live": live,
        "lethal_gate": lethal.get("heaven_hell_gate"),
        "hostess7_corroborate": lethal.get("hostess7_corroborate"),
        "removal_levels": hh_spec.get("removal_levels"),
        "harm_thresholds": hh_spec.get("harm_thresholds"),
        "hell_kit_profiles": [p.get("id") for p in (hh_spec.get("hell_kit_profiles") or [])],
        "state": {
            "rips": int(st.get("rips") or 0),
            "heaven_passes": int(st.get("heaven_passes") or 0),
            "posture": posture,
        },
        "speak": _heaven_hell_speak(counts, vision),
    }


def _heaven_hell_speak(counts: dict[str, Any], vision: dict[str, Any]) -> str:
    h = int(counts.get("heaven_count") or 0)
    hell = int(counts.get("hell_count") or 0)
    rip = int(counts.get("hell_chosen_count") or 0)
    src = counts.get("source", "field")
    base = f"Heaven {h} · Hell {hell} · rip-ready {rip} — {src}."
    if vision.get("hell_chosen_count"):
        base += f" Vision marks {vision['hell_chosen_count']} hell-chosen on ingress."
    return base


def heaven_hell_truth_status() -> dict[str, Any]:
    """Combined Truth + Heaven/Hell posture for API and HUD."""
    spec = load_spec()
    hh = heaven_hell_status()
    doctrine = truth_doctrine_status()
    return {
        "schema": "zocr-heaven-hell-truth/v1",
        "ts": _ts(),
        "sources": [s.get("id") for s in (spec.get("sources") or [])],
        "truth": doctrine,
        "heaven_hell": hh,
        "speak": f"{doctrine.get('motto', '')} {hh.get('speak', '')}".strip(),
    }


def heaven_pass(*, reason: str = "heaven_zero_cost") -> dict[str, Any]:
    """Record heaven pass — zero cost, no friendly fire."""
    st = _load_json(STATE_PATH, {"schema": "zocr-heaven-hell-state/v1", "rips": 0, "heaven_passes": 0})
    st["heaven_passes"] = int(st.get("heaven_passes") or 0) + 1
    st["last_heaven_pass"] = {"ts": _ts(), "reason": reason}
    _save_state(st)
    log_event("heaven_pass", ok=True, reason=reason)
    return {"ok": True, "schema": "zocr-heaven-pass/v1", "reason": reason, "heaven_passes": st["heaven_passes"]}


def hell_rip(
    *,
    threat: str | None = None,
    target: dict[str, Any] | None = None,
    fire_offense: bool = True,
) -> dict[str, Any]:
    """Hell rip — hostility priority; heaven never bumped."""
    t = threat or "trust_breach"
    m = threat_soul_map(t)
    soul, chosen = _classify_soul_side(
        verdict="HARM_CANDIDATE" if m.get("soul_side") == "hell" else "MONITOR",
        trust_rank=4 if m.get("soul_side") == "hell" else 1,
        hell_chosen=bool(m.get("hell_chosen")),
        kill_eligible=bool(m.get("hell_chosen")),
    )
    if soul == "heaven":
        return {**heaven_pass(reason=f"refuse_rip:{t}"), "ripped": False, "threat": t}

    st = _load_json(STATE_PATH, {"schema": "zocr-heaven-hell-state/v1", "rips": 0, "heaven_passes": 0})
    offense_row: dict[str, Any] | None = None
    if fire_offense and soul == "hell":
        from zocr_offense import offense_strike
        offense_row = offense_strike(t, source="heaven_hell:hell_rip")
        st["rips"] = int(st.get("rips") or 0) + 1
        st["last_rip"] = {"ts": _ts(), "threat": t, "soul_side": soul, "hell_chosen": chosen}
        _save_state(st)

    log_event("hell_rip", ok=True, threat=t, soul=soul, hell_chosen=chosen)
    return {
        "ok": True,
        "schema": "zocr-hell-rip/v1",
        "ripped": soul == "hell",
        "threat": t,
        "soul_side": soul,
        "hell_chosen": chosen,
        "hostility_priority": "hell_first",
        "offense": offense_row,
        "rips_total": int(st.get("rips") or 0),
    }


def heaven_hell_doctrine() -> dict[str, Any]:
    spec = load_spec()
    return {
        "schema": "zocr-heaven-hell-doctrine/v1",
        "title": "Truth · Heaven · Hell",
        "sources": spec.get("sources"),
        "truth": spec.get("truth"),
        "heaven_hell": spec.get("heaven_hell"),
        "lethal": spec.get("lethal"),
        "vision_threat_soul_map": spec.get("vision_threat_soul_map"),
    }


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower()
    if cmd in ("status", "json"):
        print(json.dumps(heaven_hell_truth_status(), indent=2))
        return 0
    if cmd == "heaven":
        print(json.dumps(heaven_hell_status(), indent=2))
        return 0
    if cmd == "truth":
        print(json.dumps(truth_doctrine_status(), indent=2))
        return 0
    if cmd == "doctrine":
        print(json.dumps(heaven_hell_doctrine(), indent=2))
        return 0
    if cmd == "pass":
        print(json.dumps(heaven_pass(), indent=2))
        return 0
    if cmd == "rip":
        threat = sys.argv[2] if len(sys.argv) > 2 else "trust_breach"
        print(json.dumps(hell_rip(threat=threat), indent=2))
        return 0
    print(json.dumps({"error": "unknown_cmd", "cmds": ["status", "heaven", "truth", "doctrine", "pass", "rip"]}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())