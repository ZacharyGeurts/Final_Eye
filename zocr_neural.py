"""ZOCR protected neural networks — sealed local assistance for vision analysis."""
from __future__ import annotations

import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from zocr_field import load_mandate
from zocr_session import log_event

_ROOT = Path(__file__).resolve().parent
NET_PATH = _ROOT / "data" / "neural-protected.json"
NET_SEAL = _ROOT / "data" / "neural-seal.json"
ANALYSIS_LOG = _ROOT / "data" / "neural-analysis.jsonl"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_network() -> dict[str, Any]:
    try:
        return json.loads(NET_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema": "zocr-neural-protected/v1", "layers": []}


def seal_network() -> dict[str, Any]:
    """Seal protected NN weights under mandate."""
    net = load_network()
    mid = net.get("mandate_id", load_mandate().get("mandate_id"))
    payload = json.dumps(net, sort_keys=True, separators=(",", ":")).encode()
    seal = hashlib.sha256(f"{mid}|{payload.decode()}".encode()).hexdigest()
    doc = {
        "schema": "zocr-neural-seal/v1",
        "mandate_id": mid,
        "network_id": net.get("network_id"),
        "ts": _ts(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "root_seal": seal,
    }
    NET_SEAL.parent.mkdir(parents=True, exist_ok=True)
    NET_SEAL.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return doc


def verify_network_seal() -> dict[str, Any]:
    if not NET_SEAL.is_file():
        return {"ok": False, "reason": "neural_seal_missing", "hint": "python3 zocr_neural.py seal"}
    try:
        doc = json.loads(NET_SEAL.read_text(encoding="utf-8"))
        net = load_network()
        payload = json.dumps(net, sort_keys=True, separators=(",", ":")).encode()
        expect = hashlib.sha256(payload).hexdigest()
        mid = net.get("mandate_id", "")
        root = hashlib.sha256(f"{mid}|{payload.decode()}".encode()).hexdigest()
        ok = doc.get("sha256") == expect and doc.get("root_seal") == root
        return {
            "ok": ok,
            "network_id": doc.get("network_id"),
            "mandate_id": doc.get("mandate_id"),
            "sha256": doc.get("sha256"),
            "ts": doc.get("ts"),
        }
    except (OSError, json.JSONDecodeError):
        return {"ok": False, "reason": "neural_seal_corrupt"}


def _relu(x: float) -> float:
    return max(0.0, x)


def _softmax(vals: list[float]) -> list[float]:
    m = max(vals) if vals else 0.0
    ex = [math.exp(v - m) for v in vals]
    s = sum(ex) or 1.0
    return [e / s for e in ex]


def _mat_vec(weights: list[list[float]], bias: list[float], x: list[float], activation: str) -> list[float]:
    out: list[float] = []
    for row, b in zip(weights, bias):
        v = sum(w * xi for w, xi in zip(row, x)) + b
        if activation == "relu":
            v = _relu(v)
        out.append(v)
    if activation == "softmax":
        return _softmax(out)
    return out


def _image_features(path: Path) -> list[float]:
    try:
        from PIL import Image, ImageStat
        img = Image.open(path).convert("RGB")
        gray = img.convert("L")
        stat = ImageStat.Stat(gray)
        cstat = ImageStat.Stat(img)
        w, h = gray.size
        mean = float(stat.mean[0]) / 255.0
        var = min(1.0, float(stat.var[0]) / 5000.0)
        px = gray.load()
        edge = 0.0
        n = 0
        step = max(1, min(w, h) // 48)
        for y in range(0, h - step, step):
            for x in range(0, w - step, step):
                edge += abs(int(px[x, y]) - int(px[x + step, y]))
                n += 1
        edge = min(1.0, (edge / max(n, 1)) / 64.0)
        hist = gray.histogram()
        dark = sum(hist[:64]) / max(sum(hist), 1)
        bright = sum(hist[192:]) / max(sum(hist), 1)
        aspect = min(1.0, w / max(h, 1) / 3.0)
        color_var = min(1.0, sum(cstat.var) / 15000.0)
        mid = sum(hist[64:192]) / max(sum(hist), 1)
        q = w // 2
        tl = sum(px[x, y] for y in range(0, h // 2, step) for x in range(0, q, step)) / max(1, (h // 2 // step) * (q // step))
        br = sum(px[x, y] for y in range(h // 2, h, step) for x in range(q, w, step)) / max(1, (h // 2 // step) * ((w - q) // step))
        quadrant_delta = min(1.0, abs(tl - br) / 255.0)
        return [
            mean, var, edge, dark, bright, aspect,
            1.0 - mean, color_var, min(1.0, w / 1920.0), min(1.0, h / 1080.0),
            (mean + edge) / 2, dark * bright, var * edge, quadrant_delta,
            min(1.0, (w * h) / (1920 * 1080)), mid,
        ]
    except Exception:
        return [0.5] * 16


def _heuristic_scores(feats: list[float], ctx: dict[str, Any]) -> dict[str, float]:
    """Ground-truth-ish rules from metrics — fused with sealed NN."""
    mean, var, edge, dark, bright = feats[0], feats[1], feats[2], feats[3], feats[4]
    color_var, qdelta, mid = feats[7], feats[13], feats[15]
    scores = {
        "clear_field": 0.15,
        "ui_dense": 0.10,
        "motion_hint": 0.10,
        "low_light": 0.10,
        "threat_pattern": 0.10,
        "stereo_depth": 0.10,
    }
    if edge > 0.35 and bright > 0.25:
        scores["ui_dense"] += 0.45
    if var > 0.4 and edge > 0.25:
        scores["motion_hint"] += 0.35
    if mean < 0.28 or dark > 0.45:
        scores["low_light"] += 0.50
    if var > 0.55 and (bright > 0.35 or mean > 0.75):
        scores["threat_pattern"] += 0.40
    if mean > 0.3 and mean < 0.7 and edge < 0.3:
        scores["clear_field"] += 0.45
    stereo = ctx.get("stereo", {})
    if stereo.get("enabled") and float(stereo.get("confidence", 0) or 0) > 0.15:
        scores["stereo_depth"] += 0.35 + float(stereo.get("confidence", 0)) * 0.3
    if stereo.get("disparity_max", 0) > 40:
        scores["stereo_depth"] += 0.20
    if ctx.get("preserve", {}).get("threats"):
        scores["threat_pattern"] += 0.35
    if color_var > 0.35 and qdelta > 0.2:
        scores["ui_dense"] += 0.15
    if mid > 0.5 and edge < 0.2:
        scores["clear_field"] += 0.15
    total = sum(scores.values()) or 1.0
    return {k: v / total for k, v in scores.items()}


def _forward(features: list[float], net: dict[str, Any]) -> tuple[list[float], list[str]]:
    layers = net.get("layers", [])
    labels = ["unknown"]
    x = features[:16]
    while len(x) < 16:
        x.append(0.0)
    x = x[:16]
    for layer in layers:
        lid = layer.get("id")
        if lid == "features":
            continue
        w = layer.get("weights", [])
        b = layer.get("bias", [0.0] * len(w))
        act = layer.get("activation", "identity")
        if w:
            x = _mat_vec(w, b, x, act)
        if layer.get("labels"):
            labels = layer["labels"]
    return x, labels


def analyze(
    path: Path | str | None,
    *,
    context: dict[str, Any] | None = None,
    client_host: str | None = None,
) -> dict[str, Any]:
    """Protected NN assistance — sealed weights, mandate + kill gate, localhost default."""
    from zocr_kill import check as kill_check
    from zocr_security import mandate_enforce

    gate = mandate_enforce("nn_analyze", client_host=client_host)
    if not gate.get("ok"):
        return {"ok": False, "error": gate.get("error"), **gate}
    kill = kill_check("nn_analyze")
    if not kill.get("ok"):
        return {"ok": False, "error": kill.get("error"), **kill}

    net = load_network()
    if net.get("egress", False) and os.environ.get("ZOCR_STREAM_EGRESS", "127.0.0.1") == "127.0.0.1":
        host = (client_host or "127.0.0.1").split(":")[0]
        if host not in ("127.0.0.1", "localhost", "::1", ""):
            return {"ok": False, "error": "neural_egress_denied"}

    seal = verify_network_seal()
    if not seal.get("ok") and not os.environ.get("ZOCR_MANDATE_OFF"):
        return {"ok": False, "error": "neural_seal", **seal}

    ctx = context or {}
    feats = _image_features(Path(path)) if path else [0.5] * 16

    if ctx.get("stereo", {}).get("disparity_mean") is not None:
        feats[15] = min(1.0, float(ctx["stereo"]["disparity_mean"]) / 255.0)
    if ctx.get("preserve", {}).get("threats"):
        feats[14] = min(1.0, len(ctx["preserve"]["threats"]) / 5.0)
    if ctx.get("eye", {}).get("perceived"):
        feats[13] = 1.0

    nn_probs, labels = _forward(feats, net)
    heur = _heuristic_scores(feats, ctx)
    fused: dict[str, float] = {}
    for lb in labels:
        fused[lb] = 0.55 * heur.get(lb, 0.0) + 0.45 * (nn_probs[labels.index(lb)] if lb in labels else 0.0)
    total = sum(fused.values()) or 1.0
    fused = {k: v / total for k, v in fused.items()}
    ranked = sorted(fused.items(), key=lambda t: t[1], reverse=True)
    top_label, top_p = ranked[0] if ranked else ("unknown", 0.0)

    narrative = _narrative(top_label, ctx, ranked[:3])

    row = {
        "schema": "zocr-neural-analysis/v2",
        "ts": _ts(),
        "ok": True,
        "engine": "hybrid_v2",
        "network_id": net.get("network_id"),
        "seal_ok": seal.get("ok"),
        "top": {"label": top_label, "confidence": round(top_p, 4)},
        "classes": [{"label": lb, "p": round(p, 4)} for lb, p in ranked],
        "heuristic": [{"label": lb, "p": round(heur.get(lb, 0), 4)} for lb in labels],
        "features_dim": 16,
        "narrative": narrative,
        "protected": True,
        "local_only": net.get("assist", {}).get("local_only", True),
    }
    ANALYSIS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with ANALYSIS_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    log_event("nn_analyze", ok=True, top=top_label, confidence=top_p)
    return row


def _narrative(label: str, ctx: dict[str, Any], top3: list[tuple[str, float]]) -> str:
    eye = ctx.get("eye", {})
    rig = ctx.get("rig", {})
    stereo = ctx.get("stereo", {})
    lines = [
        f"Protected NN assist: {label.replace('_', ' ')}.",
        f"Eye: {eye.get('label', eye.get('profile', 'human'))} · rig {rig.get('eye_count', 1)} eye(s).",
    ]
    if stereo.get("enabled"):
        lines.append(
            f"Stereo BM v2 · disparity {stereo.get('disparity_mean', '—')} "
            f"conf {stereo.get('confidence', '—')}."
        )
    if ctx.get("preserve", {}).get("threats"):
        lines.append(f"Preserve threats: {', '.join(ctx['preserve']['threats'][:4])}.")
    lines.append("Top: " + ", ".join(f"{lb} {p:.0%}" for lb, p in top3))
    return " ".join(lines)


def neural_status() -> dict[str, Any]:
    net = load_network()
    seal = verify_network_seal()
    return {
        "schema": "zocr-neural-status/v2",
        "engine": "hybrid_v2",
        "ts": _ts(),
        "network_id": net.get("network_id"),
        "mandate_id": net.get("mandate_id"),
        "rule": net.get("rule"),
        "egress": net.get("egress", False),
        "seal": seal,
        "labels": net.get("layers", [{}])[-1].get("labels", []) if net.get("layers") else [],
        "assist": net.get("assist", {}),
        "api": {
            "analyze": "POST /api/neural/analyze",
            "seal": "POST /api/neural/seal",
            "verify": "GET /api/neural/verify",
        },
    }


def main() -> int:
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        print(json.dumps(neural_status(), indent=2))
        return 0
    if cmd == "seal":
        print(json.dumps(seal_network(), indent=2))
        return 0
    if cmd == "verify":
        print(json.dumps(verify_network_seal(), indent=2))
        return 0
    if cmd == "analyze" and len(sys.argv) > 2:
        print(json.dumps(analyze(sys.argv[2]), indent=2))
        return 0
    print(json.dumps({"error": "usage: zocr_neural.py [status|seal|verify|analyze IMAGE]"}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())