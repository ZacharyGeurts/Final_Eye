"""ZOCR interwoven redundancies trust network — Hostess7 integration."""
from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from zocr_session import log_event

_ROOT = Path(__file__).resolve().parent
_SG = _ROOT.parent
SPEC_PATH = _ROOT / "data" / "zocr-trust-network.json"
STATE_PATH = _ROOT / "data" / "trust-network-state.json"

TRUST_RULE = "Interwoven redundancies — no single path owns truth; Hostess7 corroborates ZOCR vision."

_queen_cache: dict[str, Any] = {"mono": 0.0, "peer": {}}
_QUEEN_CACHE_SEC = 45.0


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_spec() -> dict[str, Any]:
    try:
        return json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema": "zocr-trust-network/v1", "mesh": {}, "quorum": {}}


def _hostess7_root() -> Path:
    env = os.environ.get("HOSTESS7_ROOT", "").strip()
    if env:
        return Path(env).resolve()
    spec = load_spec()
    rel = spec.get("hostess7", {}).get("default_root", "../Hostess7")
    return (_ROOT / rel).resolve()


def _queen_root() -> Path:
    return Path(os.environ.get("QUEEN_ROOT", str(_SG / "NewLatest" / "Queen"))).resolve()


def _peer_code_seal() -> dict[str, Any]:
    from zocr_security import verify_code_seal
    v = verify_code_seal()
    return {"id": "code_seal", "ok": v.get("ok", False), "role": "integrity", **v}


def _peer_neural_seal() -> dict[str, Any]:
    from zocr_neural import verify_network_seal
    v = verify_network_seal()
    return {"id": "neural", "ok": v.get("ok", False), "role": "assist", **v}


def _peer_capture() -> dict[str, Any]:
    from zocr_preserve import preserve_status
    p = preserve_status()
    return {
        "id": "capture",
        "ok": bool(p.get("last_good")),
        "role": "ingress",
        "vision_confidence": p.get("vision_confidence", 1.0),
        "cascade": p.get("cascade", []),
    }


def _peer_video() -> dict[str, Any]:
    from zocr_video import video_status, verify_video_index
    v = video_status()
    chk = verify_video_index(tail=5)
    return {
        "id": "video",
        "ok": v.get("format") == "ZOCRSM1",
        "role": "transport",
        "envelopes_ok": chk.get("ok_count", 0),
        "format": v.get("format"),
    }


def _peer_offense() -> dict[str, Any]:
    from zocr_offense import offense_status
    o = offense_status()
    return {"id": "offense", "ok": True, "role": "ingress", "strikes": o.get("strikes_total", 0)}


def _peer_kill() -> dict[str, Any]:
    from zocr_kill import kill_status
    k = kill_status()
    return {"id": "kill", "ok": k.get("whole", True), "role": "authority", "whole": k.get("whole")}


def _peer_wrdt() -> dict[str, Any]:
    wrdt = _SG / "World_Redata" / "cpp" / "build" / "world-redata"
    return {
        "id": "wrdt",
        "ok": wrdt.is_file(),
        "role": "integrity",
        "binary": str(wrdt) if wrdt.is_file() else None,
    }


def _peer_hostess7_truth() -> dict[str, Any]:
    h7 = _hostess7_root()
    stack_path = h7 / "data" / "hostess7-neural-stack.json"
    peer: dict[str, Any] = {
        "id": "hostess7_truth",
        "ok": h7.is_dir(),
        "role": "corroboration",
        "root": str(h7),
    }
    if stack_path.is_file():
        try:
            stack = json.loads(stack_path.read_text(encoding="utf-8"))
            vision_nets = []
            for series in stack.get("series", []):
                if series.get("id") in ("perception", "truth_gates", "brain_imaging"):
                    for net in series.get("nets", []):
                        if "vision" in str(net.get("id", "")).lower() or net.get("corpus") == "field_vision_corpus":
                            vision_nets.append(net.get("id"))
            peer["neural_stack"] = stack.get("schema")
            peer["vision_nets"] = vision_nets
            peer["truth_philosophy"] = stack.get("philosophy", "")[:120]
            peer["ok"] = bool(vision_nets) or h7.is_dir()
        except (OSError, json.JSONDecodeError):
            peer["ok"] = h7.is_dir()
    return peer


def _peer_nexus_trust() -> dict[str, Any]:
    spec = load_spec()
    rel = spec.get("hostess7", {}).get("nexus_trusted", "")
    paths = [
        _hostess7_root() / rel,
        Path("/var/lib/nexus-shield/firewall-trusted.tsv"),
    ]
    entries = 0
    found: str | None = None
    for p in paths:
        if p.is_file():
            found = str(p)
            entries = sum(1 for line in p.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip())
            break
    return {
        "id": "nexus_trust",
        "ok": entries > 0 or any(p.is_file() for p in paths),
        "role": "egress",
        "path": found,
        "entries": entries,
    }


def _peer_sovereign_time() -> dict[str, Any]:
    try:
        from zocr_sovereign_time import sovereign_time_status
        st = sovereign_time_status(seal=False)
        return {
            "id": "sovereign_time",
            "ok": st.get("ok", st.get("verdict") == "USER_OK"),
            "role": "time",
            "verdict": st.get("verdict"),
            "always": st.get("always", True),
            "sealed_mono_ns": st.get("sealed_mono_ns"),
        }
    except ImportError:
        return {"id": "sovereign_time", "ok": False, "role": "time", "error": "zocr_sovereign_time missing"}


def _peer_queen_gates() -> dict[str, Any]:
    queen = _queen_root()
    panel_py = queen / "lib" / "field-queen-browser.py"
    spec = load_spec()
    ready = spec.get("queen", {}).get("verdict_ready", "QUEEN_READY")
    peer: dict[str, Any] = {
        "id": "queen_gates",
        "ok": panel_py.is_file(),
        "role": "mandate",
        "panel": str(panel_py) if panel_py.is_file() else None,
    }
    if not panel_py.is_file():
        return peer
    now = time.monotonic()
    if _queen_cache.get("peer") and now - float(_queen_cache.get("mono", 0)) < _QUEEN_CACHE_SEC:
        return dict(_queen_cache["peer"])
    try:
        proc = subprocess.run(
            ["python3", str(panel_py), "json"],
            capture_output=True,
            text=True,
            timeout=8,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(queen)},
        )
        doc = json.loads(proc.stdout or "{}")
        gates = doc.get("gates") or {}
        peer.update({
            "ok": doc.get("queen_verdict") == ready or gates.get("all_held"),
            "queen_verdict": doc.get("queen_verdict"),
            "gates_held": gates.get("held"),
            "gates_all_held": gates.get("all_held"),
            "hostess7_available": doc.get("hostess7_available") or (doc.get("hostess7_command") or {}).get("ok"),
        })
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
        peer["error"] = str(exc)[:200]
    _queen_cache["peer"] = dict(peer)
    _queen_cache["mono"] = now
    return peer


def trust_peers() -> list[dict[str, Any]]:
    return [
        _peer_code_seal(),
        _peer_neural_seal(),
        _peer_capture(),
        _peer_video(),
        _peer_offense(),
        _peer_kill(),
        _peer_wrdt(),
        _peer_hostess7_truth(),
        _peer_nexus_trust(),
        _peer_queen_gates(),
        _peer_sovereign_time(),
    ]


def redundancy_paths_status() -> list[dict[str, Any]]:
    spec = load_spec()
    peers = {p["id"]: p for p in trust_peers()}
    paths_out: list[dict[str, Any]] = []
    for rp in spec.get("redundancy_paths", []):
        pid = rp.get("id", "")
        nodes = rp.get("path", [])
        hop_ok = [bool(peers.get(n, {}).get("ok")) for n in nodes]
        paths_out.append({
            "id": pid,
            "path": nodes,
            "hops_ok": hop_ok,
            "ok": all(hop_ok) if hop_ok else False,
            "woven": sum(hop_ok) >= max(1, len(hop_ok) - 1),
        })
    return paths_out


def verify_trust_mesh() -> dict[str, Any]:
    spec = load_spec()
    peers = trust_peers()
    paths = redundancy_paths_status()
    quorum = spec.get("quorum", {})
    required = set(quorum.get("required", []))
    peer_map = {p["id"]: p for p in peers}
    required_ok = all(peer_map.get(r, {}).get("ok") for r in required)
    ok_peers = sum(1 for p in peers if p.get("ok"))
    woven_paths = sum(1 for p in paths if p.get("woven"))
    ok = required_ok and ok_peers >= int(quorum.get("min_peers", 4))
    return {
        "ok": ok,
        "schema": "zocr-trust-mesh-verify/v1",
        "ts": _ts(),
        "rule": spec.get("rule", TRUST_RULE),
        "peers_ok": ok_peers,
        "peers_total": len(peers),
        "required_ok": required_ok,
        "woven_paths": woven_paths,
        "paths_total": len(paths),
        "peers": peers,
        "paths": paths,
        "quorum": quorum,
    }


def hostess7_bridge() -> dict[str, Any]:
    h7 = _hostess7_root()
    spec = load_spec().get("hostess7", {})
    stack_file = h7 / spec.get("neural_stack", "data/hostess7-neural-stack.json")
    trusted_file = h7 / spec.get("nexus_trusted", "")
    bridge = {
        "schema": "zocr-hostess7-bridge/v1",
        "ts": _ts(),
        "hostess7_root": str(h7),
        "present": h7.is_dir(),
        "neural_stack": str(stack_file) if stack_file.is_file() else None,
        "nexus_trusted": str(trusted_file) if trusted_file.is_file() else None,
        "vision_lane": spec.get("vision_lane", "vision"),
        "integration": [
            "ZOCR capture → Hostess7 field_vision_corpus corroboration",
            "WRDT envelopes ↔ Hostess7 lossless redata discipline",
            "NEXUS trust list ↔ ZOCR egress mandate localhost default",
            "Queen gates ↔ ZOCR code seal + offense quorum",
        ],
    }
    if stack_file.is_file():
        try:
            stack = json.loads(stack_file.read_text(encoding="utf-8"))
            bridge["series_count"] = len(stack.get("series", []))
            bridge["philosophy"] = stack.get("philosophy", "")
        except (OSError, json.JSONDecodeError):
            pass
    bridge["queen"] = _peer_queen_gates()
    return bridge


def trust_network_status(*, full_mesh: bool = True) -> dict[str, Any]:
    spec = load_spec()
    mesh = verify_trust_mesh() if full_mesh else {"ok": None, "woven_paths": 0, "peers_ok": 0}
    bridge = hostess7_bridge()
    return {
        "schema": "zocr-trust-network-status/v1",
        "ts": _ts(),
        "title": spec.get("title", "Interwoven Redundancies Trust Network"),
        "abbrev": spec.get("abbrev", "IRTN"),
        "rule": spec.get("rule", TRUST_RULE),
        "paired": spec.get("paired", []),
        "interwoven": mesh.get("woven_paths", 0),
        "mesh_ok": mesh.get("ok", False),
        "peers_ok": mesh.get("peers_ok", 0),
        "hostess7_root": str(_hostess7_root()),
        "queen_root": str(_queen_root()),
        "mesh": mesh,
        "hostess7": bridge,
    }


def trust_doctrine() -> dict[str, Any]:
    spec = load_spec()
    return {
        "schema": "zocr-trust-doctrine/v1",
        "title": spec.get("title"),
        "abbrev": spec.get("abbrev"),
        "rule": spec.get("rule"),
        "paired": spec.get("paired"),
        "mesh_nodes": [n.get("id") for n in spec.get("mesh", {}).get("nodes", [])],
        "redundancy_paths": [p.get("id") for p in spec.get("redundancy_paths", [])],
        "hostess7": spec.get("hostess7", {}),
        "quorum": spec.get("quorum", {}),
        "doctrine": [
            TRUST_RULE,
            "Each node corroborates — capture, pattern, offense, video, eye, rig, neural",
            "Hostess7 truth gates + vision lane echo ZOCR frames",
            "NEXUS trust network + Queen gates = egress and mandate quorum",
            "WRDT + code seal + neural seal = interwoven integrity",
            "No single path owns truth — woven paths must agree",
        ],
    }


def main() -> int:
    import sys

    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        print(json.dumps(trust_network_status(), indent=2))
        return 0
    if cmd == "verify":
        print(json.dumps(verify_trust_mesh(), indent=2))
        return 0
    if cmd == "doctrine":
        print(json.dumps(trust_doctrine(), indent=2))
        return 0
    if cmd == "hostess7":
        print(json.dumps(hostess7_bridge(), indent=2))
        return 0
    print(json.dumps({"error": "usage: zocr_trust.py [status|verify|doctrine|hostess7]"}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())