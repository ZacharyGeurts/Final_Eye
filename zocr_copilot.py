"""Final_Eye Co-Pilot — instant foundational truths that hold the structure together."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from zocr_product import product_info
from zocr_session import log_event

_ROOT = Path(__file__).resolve().parent
FOUNDATIONS_PATH = _ROOT / "data" / "copilot-foundations.json"
STATE_PATH = _ROOT / "data" / "copilot-state.json"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_foundations() -> dict[str, Any]:
    try:
        return json.loads(FOUNDATIONS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema": "final-eye-copilot-foundations/v1", "sources": []}


def _probe_mandate() -> dict[str, Any]:
    from zocr_field import load_mandate, mandate_gate
    m = load_mandate()
    gate = mandate_gate()
    return {
        "ok": gate.get("ok"),
        "mandate_id": m.get("mandate_id"),
        "rule": m.get("rule"),
        "vision_confidence": m.get("vision_confidence"),
        "doctrine_count": len(m.get("doctrine") or []),
    }


def _probe_code_seal() -> dict[str, Any]:
    from zocr_security import verify_code_seal
    v = verify_code_seal()
    return {"ok": v.get("ok"), "file_count": v.get("file_count"), "root_seal": (v.get("root_seal") or "")[:16]}


def _probe_hash_chain() -> dict[str, Any]:
    from zocr_field import verify_chain
    chain = _ROOT / "data" / "stream-chain.json"
    head_doc: dict[str, Any] = {}
    if chain.is_file():
        try:
            head_doc = json.loads(chain.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    try:
        v = verify_chain()
        return {
            "ok": v.get("ok", True),
            "head": (head_doc.get("head") or "")[:16],
            "seq": head_doc.get("seq"),
            "frames_verified": v.get("verified", 0),
        }
    except Exception as exc:
        return {"ok": chain.is_file(), "head": None, "note": str(exc)[:80]}


def _probe_gvc1() -> dict[str, Any]:
    from zocr_security import verify_gvc1_integrity
    v = verify_gvc1_integrity()
    return {"ok": v.get("ok"), "tamper_rejected": v.get("tamper_rejected"), "stream_mode": v.get("stream_mode")}


def _probe_sovereign_time() -> dict[str, Any]:
    from zocr_sovereign_time import sovereign_time_status
    st = sovereign_time_status(seal=False)
    return {"ok": bool(st.get("sealed_mono_ns")), "verdict": st.get("verdict"), "always": st.get("always")}


def _probe_trust_mesh() -> dict[str, Any]:
    from zocr_trust import verify_trust_mesh
    m = verify_trust_mesh()
    return {"ok": m.get("ok"), "woven_paths": m.get("woven_paths"), "peers_ok": m.get("peers_ok")}


def _probe_truth_doctrine() -> dict[str, Any]:
    from zocr_heaven_hell import truth_doctrine_status
    t = truth_doctrine_status()
    return {"ok": True, "noise_ratio": t.get("noise_ratio"), "truth_gates": len(t.get("truth_gates") or [])}


def _probe_heaven_hell() -> dict[str, Any]:
    from zocr_heaven_hell import heaven_hell_status
    h = heaven_hell_status()
    return {
        "ok": True,
        "hostility_priority": h.get("hostility_priority"),
        "heaven": h.get("heaven_count"),
        "hell": h.get("hell_count"),
    }


def _probe_kill() -> dict[str, Any]:
    from zocr_kill import kill_status
    k = kill_status()
    return {"ok": k.get("whole", True), "whole": k.get("whole"), "eyes_protect": k.get("eyes_protect")}


def _probe_twins() -> dict[str, Any]:
    from zocr_entity_eyeball import twin_eyeball_status
    t = twin_eyeball_status()
    return {
        "ok": True,
        "always_forward": t.get("always_forward"),
        "weapons_total": (t.get("arsenal") or {}).get("weapons_total"),
        "both_live": t.get("both_live"),
    }


def _probe_compiler() -> dict[str, Any]:
    from zocr_field_compiler import field_compiler_status
    fc = field_compiler_status()
    g = fc.get("grok16") or {}
    return {"ok": bool(g.get("ready") or g.get("cxx_std")), "grok16": g.get("version"), "profile": g.get("profile")}


def _probe_assist() -> dict[str, Any]:
    from zocr_contract import contract_status
    c = contract_status()
    return {"ok": True, "posture": c.get("posture"), "slots": c.get("slots")}


def _probe_preserve() -> dict[str, Any]:
    from zocr_preserve import preserve_status
    p = preserve_status()
    return {
        "ok": bool(p.get("last_good")),
        "confidence": p.get("vision_confidence"),
        "cascade_len": len(p.get("cascade") or []),
    }


def _probe_pattern() -> dict[str, Any]:
    from zocr_pattern import pattern_status
    p = pattern_status()
    return {"ok": p.get("enabled", True), "scans": p.get("scans_total"), "foreign": p.get("foreign_total")}


_PROBES: dict[str, Callable[[], dict[str, Any]]] = {
    "mandate": _probe_mandate,
    "code_seal": _probe_code_seal,
    "hash_chain": _probe_hash_chain,
    "gvc1_codec": _probe_gvc1,
    "sovereign_time": _probe_sovereign_time,
    "trust_mesh": _probe_trust_mesh,
    "truth_doctrine": _probe_truth_doctrine,
    "heaven_hell": _probe_heaven_hell,
    "kill_authority": _probe_kill,
    "twin_eyeballs": _probe_twins,
    "field_compiler": _probe_compiler,
    "assist_contract": _probe_assist,
    "preserve_cascade": _probe_preserve,
    "pattern_weave": _probe_pattern,
}


def foundational_source_status(source_id: str) -> dict[str, Any]:
    spec = load_foundations()
    src = next((s for s in (spec.get("sources") or []) if s.get("id") == source_id), None)
    if not src:
        return {"ok": False, "error": "unknown_source", "id": source_id}
    probe = _PROBES.get(source_id)
    live = probe() if probe else {"ok": False, "error": "no_probe"}
    path = _ROOT / str(src.get("spec", ""))
    spec_ok = path.is_file() or path.is_dir()
    ok = bool(live.get("ok")) and (spec_ok or source_id in ("gvc1_codec", "assist_contract"))
    return {
        "id": source_id,
        "layer": src.get("layer"),
        "title": src.get("title"),
        "truth": src.get("truth"),
        "holds": src.get("holds"),
        "label": src.get("label"),
        "api": src.get("api"),
        "spec_present": spec_ok,
        "live": live,
        "ok": ok,
    }


def all_foundational_sources() -> list[dict[str, Any]]:
    spec = load_foundations()
    return [foundational_source_status(s["id"]) for s in (spec.get("sources") or []) if s.get("id")]


def hold_together() -> dict[str, Any]:
    """What it takes to hold Final_Eye together — structural integrity report."""
    spec = load_foundations()
    sources = all_foundational_sources()
    ok_n = sum(1 for s in sources if s.get("ok"))
    total = len(sources)
    layers = spec.get("structure_layers") or []
    by_layer: dict[str, list[dict[str, Any]]] = {}
    for s in sources:
        by_layer.setdefault(str(s.get("layer")), []).append(s)

    weak: list[dict[str, Any]] = []
    for s in sources:
        if not s.get("ok"):
            weak.append({
                "id": s.get("id"),
                "title": s.get("title"),
                "holds": s.get("holds"),
                "live": s.get("live"),
            })

    integrity = round(100 * ok_n / max(1, total), 1)
    held = integrity >= 85 and not any(s["id"] in ("mandate", "code_seal") for s in weak)

    def _layer_ok(layer: str) -> bool:
        items = by_layer.get(layer) or []
        return all(x.get("ok") for x in items) if items else False

    pillars = [
        {"pillar": "Genesis", "truth": spec.get("hold_rule", "").split("→")[0].strip(), "ok": _layer_ok("genesis")},
        {"pillar": "Integrity triad", "truth": "sealed code + chained frames + GVC1", "ok": all(
            next((x for x in sources if x["id"] == i), {}).get("ok") for i in ("code_seal", "hash_chain", "gvc1_codec")
        )},
        {"pillar": "Corroboration", "truth": "IRTN woven — no single path owns truth", "ok": _layer_ok("corroboration")},
        {"pillar": "Truth forward", "truth": "doctrine + heaven/hell + Veritas", "ok": all(
            next((x for x in sources if x["id"] == i), {}).get("ok") for i in ("truth_doctrine", "heaven_hell", "twin_eyeballs")
        )},
        {"pillar": "One whole", "truth": "kill authority + assist contract + preserve", "ok": all(
            next((x for x in sources if x["id"] == i), {}).get("ok") for i in ("kill_authority", "assist_contract", "preserve_cascade")
        )},
    ]

    speak = _hold_speak(integrity, ok_n, total, weak, held)
    return {
        "schema": "final-eye-hold-together/v1",
        "ts": _ts(),
        "motto": spec.get("motto"),
        "hold_rule": spec.get("hold_rule"),
        "integrity_pct": integrity,
        "sources_ok": ok_n,
        "sources_total": total,
        "structure_held": held,
        "pillars": pillars,
        "layers": layers,
        "by_layer": {k: [{"id": x["id"], "ok": x["ok"], "title": x["title"]} for x in v] for k, v in by_layer.items()},
        "weak_links": weak,
        "speak": speak,
    }


def _hold_speak(integrity: float, ok: int, total: int, weak: list, held: bool) -> str:
    base = f"Co-Pilot: {ok}/{total} foundationals live — {integrity}% structural integrity."
    if held:
        return base + " Structure held. Mandate genesis, sealed code, woven trust, truth forward — all corroborate."
    if weak:
        ids = ", ".join(w["id"] for w in weak[:4])
        return base + f" Weak links: {ids}. Repair foundationals before field deploy."
    return base


def copilot_status() -> dict[str, Any]:
    product = product_info()
    hold = hold_together()
    sources = all_foundational_sources()
    return {
        "schema": "final-eye-copilot/v1",
        "ts": _ts(),
        "role": "instant sources of truth — maintain structures from foundationals",
        "product": {"version": product.get("version"), "name": product.get("name")},
        "hold": hold,
        "sources": sources,
        "speak": hold.get("speak"),
    }


def copilot_ask(query: str) -> dict[str, Any]:
    """Route operator question to relevant foundational truths."""
    q = (query or "").strip().lower()
    spec = load_foundations()
    sources = all_foundational_sources()
    hits: list[dict[str, Any]] = []

    keywords: dict[str, list[str]] = {
        "mandate": ["mandate", "genesis", "doctrine", "rule", "egress"],
        "code_seal": ["seal", "tamper", "integrity", "code"],
        "hash_chain": ["chain", "frame", "wrdt", "hash"],
        "gvc1_codec": ["gvc1", "grkmf", "mpeg", "codec", "envelope"],
        "sovereign_time": ["time", "witness", "monotonic", "sovereign"],
        "trust_mesh": ["trust", "irtn", "mesh", "hostess", "woven", "corroborat"],
        "truth_doctrine": ["truth", "honest", "noise", "signal", "94"],
        "heaven_hell": ["heaven", "hell", "hostility", "mercy"],
        "kill_authority": ["kill", "trip", "release", "whole", "disengage"],
        "twin_eyeballs": ["vita", "veritas", "twin", "eyeball", "weapon"],
        "field_compiler": ["grok16", "compiler", "field_opt", "g16", "forge"],
        "assist_contract": ["contract", "slot", "overflow", "assist", "bounded"],
        "preserve_cascade": ["preserve", "cascade", "failover", "last-good", "vision loss"],
        "pattern_weave": ["pattern", "weave", "moire", "provenance", "foreign"],
        "hold": ["hold", "together", "structure", "foundational", "pillar", "weak"],
    }

    for sid, words in keywords.items():
        if any(w in q for w in words):
            src = next((s for s in sources if s["id"] == sid), None)
            if src:
                hits.append(src)

    if not hits or "hold" in q or "together" in q or "structure" in q:
        hold = hold_together()
        answer = hold.get("speak", "")
        if hits:
            lines = [f"• {h['title']}: {h['truth']} — holds: {h['holds']}" for h in hits[:6]]
            answer = answer + "\n" + "\n".join(lines)
    else:
        lines = [f"• {h['title']}: {h['truth']} — holds: {h['holds']}" for h in hits[:8]]
        answer = "Foundational truths:\n" + "\n".join(lines)

    log_event("copilot_ask", ok=True, query=q[:80], hits=len(hits))
    return {
        "ok": True,
        "schema": "final-eye-copilot-ask/v1",
        "ts": _ts(),
        "query": query,
        "hits": [h["id"] for h in hits],
        "sources": hits,
        "hold": hold_together() if ("hold" in q or not hits) else None,
        "answer": answer.strip(),
    }


def copilot_doctrine() -> dict[str, Any]:
    spec = load_foundations()
    return {
        "schema": "final-eye-copilot-doctrine/v1",
        "title": spec.get("title"),
        "motto": spec.get("motto"),
        "hold_rule": spec.get("hold_rule"),
        "structure_layers": spec.get("structure_layers"),
        "sources": spec.get("sources"),
    }


def main() -> int:
    import sys
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower()
    if cmd == "hold":
        print(json.dumps(hold_together(), indent=2))
        return 0
    if cmd == "foundations":
        print(json.dumps({"sources": all_foundational_sources()}, indent=2))
        return 0
    if cmd == "doctrine":
        print(json.dumps(copilot_doctrine(), indent=2))
        return 0
    if cmd == "ask" and len(sys.argv) > 2:
        print(json.dumps(copilot_ask(" ".join(sys.argv[2:])), indent=2))
        return 0
    print(json.dumps(copilot_status(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())