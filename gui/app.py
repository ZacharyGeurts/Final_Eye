#!/usr/bin/env python3
"""ZOCR vision server — stream, look, robotics/AI, field protection."""
from __future__ import annotations

import json
import mimetypes
import os
import subprocess
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote

ZOCR_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ZOCR_ROOT))
os.environ.setdefault("ZOCR_VISION_SESSION", str(ZOCR_ROOT / "data" / "vision-session.jsonl"))

from zocr import latest  # noqa: E402
from zocr_product import product_info  # noqa: E402
from zocr_robotics import arm_robotics, robotics_doctrine  # noqa: E402
from zocr_ai import ai_context, capabilities, robotics_context  # noqa: E402
from zocr_additives import additives_status, list_additives  # noqa: E402
from zocr_field import load_mandate, verify_chain  # noqa: E402
from zocr_security import mandate_enforce, security_status, seal_codebase, verify_code_seal  # noqa: E402
from zocr_status import live_status  # noqa: E402
from zocr_preserve import preserve_status, threat_doctrine  # noqa: E402
from zocr_stream import fps_profiles, mjpeg_generator, stream_start, stream_status, stream_stop  # noqa: E402
from zocr_video import (  # noqa: E402
    export_grkm_movie,
    format_doctrine,
    grkmf_market_compare,
    video_ai_tune,
    video_benchmark,
    video_enhance,
    video_status,
    video_tune,
    video_tune_reset,
    verify_grkm_movie,
    verify_video_index,
)
from zocr_grkmf import grkmf  # noqa: E402
from zocr_pattern import pattern_doctrine, pattern_status, scan_frame, stamp_frame  # noqa: E402
from zocr_offense import offense_doctrine, offense_status  # noqa: E402
from zocr_trust import hostess7_bridge, trust_doctrine, trust_network_status, verify_trust_mesh  # noqa: E402
from zocr_eye import (  # noqa: E402
    eye_status,
    final_eyeball_doctrine,
    final_eyeball_status,
    list_final_modes,
    list_profiles,
    set_final_mode,
    speak_final,
    spectrum_doctrine,
    teach,
)
from zocr_entity_eyeball import (  # noqa: E402
    entity_doctrine,
    entity_weapon_racks,
    entity_weapons,
    fire_entity_weapon,
    living_eyeball_status,
    make_living_live,
    truth_eyeball_status,
    truth_forward,
    twin_eyeball_status,
    weaponize_eyeball,
)
from zocr_neural import analyze as nn_analyze  # noqa: E402
from zocr_neural import neural_status, seal_network, verify_network_seal  # noqa: E402
from zocr_stereo import configure_rig, list_presets, perceive_rig, rig_status  # noqa: E402
from zocr_kill import kill_all, kill_status, release, trip  # noqa: E402
from zocr_vigilance import vigilance_start, vigilance_status, vigilance_stop  # noqa: E402
from zocr_vision import look  # noqa: E402
from zocr_field_compiler import (  # noqa: E402
    field_compiler_doctrine,
    field_compiler_status,
    probe_compilers,
)
from zocr_grok16 import grok16_status  # noqa: E402
from zocr_tester import tester_full, tester_matrix, tester_snapshot  # noqa: E402
from zocr_copilot import copilot_ask, copilot_doctrine, copilot_status, hold_together  # noqa: E402
from zocr_zac import pack_vision_artifacts, restore_vision_artifacts, zac_self_test, zac_status  # noqa: E402
from zocr_security import (  # noqa: E402
    decrypt_stream_payload,
    encrypt_stream_payload,
    issue_operator_token,
    security_model,
    verify_gvc1_integrity,
    verify_operator_token,
)
from zocr_heaven_hell import (  # noqa: E402
    heaven_hell_doctrine,
    heaven_hell_status,
    heaven_hell_truth_status,
    heaven_pass,
    hell_rip,
    truth_doctrine_status,
)
from zocr_hud import (  # noqa: E402
    fetch_module_data,
    hud_posture,
    hud_status,
    list_modules,
    module_analyze,
    request_hud,
)

WEB = Path(__file__).resolve().parent
HUD_STATIC = frozenset({"hud-modules.js", "hud.css"})
TESTER_STATIC = frozenset({"tester.js", "tester.css"})
OUT = ZOCR_ROOT / "out"
QUEEN_BUILD = Path(
    os.environ.get("QUEEN_ROOT", str(ZOCR_ROOT.parent / "NewLatest" / "Queen")),
) / "lib" / "queen-build.py"
HOST = os.environ.get("ZOCR_HOST", "127.0.0.1")
PORT = int(os.environ.get("ZOCR_PORT", "9479"))


def _queen_build_dispatch(body: dict) -> dict:
    if not QUEEN_BUILD.is_file():
        return {"ok": False, "error": "queen_build_missing", "path": str(QUEEN_BUILD)}
    env = {
        **os.environ,
        "SG_ROOT": str(ZOCR_ROOT.parent),
        "QUEEN_ROOT": str(QUEEN_BUILD.parent.parent),
        "HOSTESS7_ROOT": os.environ.get("HOSTESS7_ROOT", str(ZOCR_ROOT.parent / "Hostess7")),
        "NEXUS_INSTALL_ROOT": os.environ.get(
            "NEXUS_INSTALL_ROOT", str(ZOCR_ROOT.parent / "NewLatest" / "Queen"),
        ),
    }
    try:
        proc = subprocess.run(
            [sys.executable, str(QUEEN_BUILD), "dispatch"],
            input=json.dumps(body),
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
        return json.loads(proc.stdout or "{}")
    except (json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc)[:200]}


class Handler(BaseHTTPRequestHandler):
    server_version = "ZOCR/4"

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write(f"[zocr] {self.address_string()} - {fmt % args}\n")

    def _client_host(self) -> str:
        return (self.client_address[0] if self.client_address else "127.0.0.1")

    def _send_json(self, code: int, obj: dict) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, data: bytes, *, mime: str, cache: str = "public, max-age=3600") -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", cache)
        self.end_headers()
        self.wfile.write(data)

    def _enforce(self, operation: str) -> dict | None:
        gate = mandate_enforce(operation, client_host=self._client_host())
        if not gate.get("ok"):
            self._send_json(HTTPStatus.FORBIDDEN, {"ok": False, "error": gate.get("error"), **gate})
            return gate
        return None

    def _read_json_body(self) -> dict:
        n = int(self.headers.get("Content-Length", "0") or "0")
        if n <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return {}

    def _qs(self) -> dict[str, list[str]]:
        return parse_qs(self.path.split("?", 1)[1] if "?" in self.path else "")

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        path = unquote(self.path.split("?", 1)[0])
        qs = self._qs()

        if path in ("/", "/index.html", "/live", "/stream"):
            self._send_bytes((WEB / "index.html").read_bytes(), mime="text/html; charset=utf-8", cache="no-store")
            return
        if path in ("/tester", "/tester.html"):
            self._send_bytes((WEB / "tester.html").read_bytes(), mime="text/html; charset=utf-8", cache="no-store")
            return
        if path.startswith("/") and path.lstrip("/") in TESTER_STATIC:
            asset = WEB / path.lstrip("/")
            if asset.is_file():
                mime = mimetypes.guess_type(asset.name)[0] or "application/octet-stream"
                self._send_bytes(asset.read_bytes(), mime=mime, cache="no-store")
                return
        if path.startswith("/") and path.lstrip("/") in HUD_STATIC:
            asset = WEB / path.lstrip("/")
            if asset.is_file():
                mime = mimetypes.guess_type(asset.name)[0] or "application/octet-stream"
                self._send_bytes(asset.read_bytes(), mime=mime, cache="no-store")
                return
        if path == "/api/hud/modules":
            self._send_json(HTTPStatus.OK, {"ok": True, "modules": list_modules(), "posture": hud_posture()})
            return
        if path == "/api/hud/status":
            self._send_json(HTTPStatus.OK, hud_status())
            return
        if path.startswith("/api/hud/module/"):
            mid = path[len("/api/hud/module/") :].strip("/")
            self._send_json(HTTPStatus.OK, fetch_module_data(mid))
            return
        if path.startswith("/queen-build/"):
            rel = path[len("/queen-build/") :]
            target = (WEB / "queen-build" / rel).resolve()
            base = (WEB / "queen-build").resolve()
            if not str(target).startswith(str(base)) or not target.is_file():
                self.send_response(HTTPStatus.NOT_FOUND)
                self.end_headers()
                return
            mime = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            self._send_bytes(target.read_bytes(), mime=mime, cache="no-store")
            return
        if path == "/api/queen-build":
            self._send_json(HTTPStatus.OK, _queen_build_dispatch({"action": "json"}))
            return
        if path == "/api/health":
            self._send_json(HTTPStatus.OK, {"ok": True, "service": "zocr-vision", **product_info()})
            return
        if path == "/api/version":
            self._send_json(HTTPStatus.OK, product_info())
            return
        if path == "/api/robotics":
            from zocr_ai import robotics_context
            self._send_json(HTTPStatus.OK, {"ok": True, **robotics_context()})
            return
        if path == "/api/robotics/doctrine":
            self._send_json(HTTPStatus.OK, robotics_doctrine())
            return
        if path == "/api/status":
            self._send_json(HTTPStatus.OK, live_status())
            return
        if path == "/api/capabilities":
            self._send_json(HTTPStatus.OK, capabilities())
            return
        if path == "/api/mandate":
            self._send_json(HTTPStatus.OK, {"ok": True, **load_mandate()})
            return
        if path == "/api/grok16":
            self._send_json(HTTPStatus.OK, grok16_status())
            return
        if path == "/api/field/compiler":
            self._send_json(HTTPStatus.OK, field_compiler_status())
            return
        if path == "/api/field/compiler/doctrine":
            self._send_json(HTTPStatus.OK, field_compiler_doctrine())
            return
        if path == "/api/security":
            self._send_json(HTTPStatus.OK, security_status())
            return
        if path == "/api/security/verify":
            self._send_json(HTTPStatus.OK, verify_code_seal())
            return
        if path == "/api/security/model":
            self._send_json(HTTPStatus.OK, security_model())
            return
        if path == "/api/security/gvc1":
            self._send_json(HTTPStatus.OK, verify_gvc1_integrity())
            return
        if path == "/api/tester/snapshot":
            self._send_json(HTTPStatus.OK, tester_snapshot())
            return
        if path == "/api/tester/matrix":
            self._send_json(HTTPStatus.OK, tester_matrix())
            return
        if path == "/api/tester/full":
            run_matrix = (qs.get("matrix", ["1"])[0] or "1").strip().lower() not in ("0", "false", "no")
            self._send_json(HTTPStatus.OK, tester_full(run_matrix=run_matrix))
            return
        if path == "/api/copilot":
            self._send_json(HTTPStatus.OK, copilot_status())
            return
        if path == "/api/copilot/hold":
            self._send_json(HTTPStatus.OK, hold_together())
            return
        if path == "/api/copilot/foundations":
            from zocr_copilot import all_foundational_sources
            self._send_json(HTTPStatus.OK, {"ok": True, "sources": all_foundational_sources()})
            return
        if path == "/api/copilot/doctrine":
            self._send_json(HTTPStatus.OK, copilot_doctrine())
            return
        if path == "/api/copilot/ask":
            q = (qs.get("q", [""])[0] or qs.get("query", [""])[0] or "").strip()
            self._send_json(HTTPStatus.OK, copilot_ask(q or "what holds it together"))
            return
        if path == "/api/zac/status":
            self._send_json(HTTPStatus.OK, zac_status())
            return
        if path == "/api/zac/test":
            self._send_json(HTTPStatus.OK, zac_self_test())
            return
        if path == "/api/vigilance/status":
            self._send_json(HTTPStatus.OK, vigilance_status())
            return
        if path == "/api/vigilance/additives":
            self._send_json(HTTPStatus.OK, additives_status())
            return
        if path == "/api/additives":
            self._send_json(HTTPStatus.OK, {"ok": True, "additives": list_additives()})
            return
        if path == "/api/kill":
            self._send_json(HTTPStatus.OK, kill_status())
            return
        if path == "/api/eye":
            self._send_json(HTTPStatus.OK, eye_status())
            return
        if path == "/api/eye/profiles":
            self._send_json(HTTPStatus.OK, {"ok": True, "profiles": list_profiles()})
            return
        if path == "/api/eye/doctrine":
            self._send_json(HTTPStatus.OK, spectrum_doctrine())
            return
        if path == "/api/eye/final":
            self._send_json(HTTPStatus.OK, final_eyeball_status())
            return
        if path == "/api/eye/final/doctrine":
            self._send_json(HTTPStatus.OK, final_eyeball_doctrine())
            return
        if path == "/api/eye/final/modes":
            self._send_json(HTTPStatus.OK, {"ok": True, "modes": list_final_modes()})
            return
        if path == "/api/eye/twins":
            self._send_json(HTTPStatus.OK, twin_eyeball_status())
            return
        if path == "/api/eye/living":
            self._send_json(HTTPStatus.OK, living_eyeball_status())
            return
        if path == "/api/eye/truth":
            self._send_json(HTTPStatus.OK, truth_eyeball_status())
            return
        if path == "/api/eye/heaven-hell":
            self._send_json(HTTPStatus.OK, heaven_hell_truth_status())
            return
        if path == "/api/eye/heaven-hell/doctrine":
            self._send_json(HTTPStatus.OK, heaven_hell_doctrine())
            return
        if path == "/api/eye/truth/doctrine":
            self._send_json(HTTPStatus.OK, truth_doctrine_status())
            return
        if path == "/api/eye/entity/doctrine":
            self._send_json(HTTPStatus.OK, entity_doctrine())
            return
        if path == "/api/eye/weapons":
            rack = (qs.get("rack", [""])[0] or "").strip() or None
            self._send_json(HTTPStatus.OK, {
                "ok": True,
                "weapons": entity_weapons(rack=rack),
                "racks": entity_weapon_racks(),
            })
            return
        if path == "/api/eye/weapons/racks":
            self._send_json(HTTPStatus.OK, entity_weapon_racks())
            return
        if path == "/api/eye/final/speak":
            mode = (qs.get("mode", [""])[0] or "").strip() or None
            voice = (qs.get("voice", [""])[0] or "").strip() or None
            self._send_json(HTTPStatus.OK, speak_final(mode=mode, voice=voice))
            return
        if path == "/api/rig":
            self._send_json(HTTPStatus.OK, rig_status())
            return
        if path == "/api/rig/presets":
            self._send_json(HTTPStatus.OK, {"ok": True, "presets": list_presets()})
            return
        if path == "/api/neural":
            self._send_json(HTTPStatus.OK, neural_status())
            return
        if path == "/api/neural/verify":
            self._send_json(HTTPStatus.OK, verify_network_seal())
            return
        if path == "/api/stream/status":
            self._send_json(HTTPStatus.OK, stream_status())
            return
        if path == "/api/stream/profiles":
            self._send_json(HTTPStatus.OK, {"ok": True, "profiles": fps_profiles()})
            return
        if path == "/api/video":
            self._send_json(HTTPStatus.OK, video_status())
            return
        if path == "/api/video/format":
            self._send_json(HTTPStatus.OK, format_doctrine())
            return
        if path == "/api/video/verify":
            tail = int(qs.get("tail", ["20"])[0] or "20")
            self._send_json(HTTPStatus.OK, verify_video_index(tail=tail))
            return
        if path == "/api/video/benchmark":
            low_end = (qs.get("low_end", ["1"])[0] or "1").strip().lower() not in ("0", "false", "no")
            if low_end and not qs.get("profiles", [""])[0]:
                from zocr_bench import benchmark_low_end
                self._send_json(HTTPStatus.OK, benchmark_low_end())
                return
            profiles = [p.strip() for p in (qs.get("profiles", [""])[0] or "").split(",") if p.strip()]
            duration = float(qs.get("duration", ["0.5"])[0] or "0.5")
            self._send_json(HTTPStatus.OK, video_benchmark(
                profiles=profiles or None,
                duration_sec=duration,
                low_end=low_end,
            ))
            return
        if path == "/api/grkmf":
            self._send_json(HTTPStatus.OK, {
                "ok": True,
                "format": grkmf.FORMAT_ID,
                "codec": grkmf.CODEC_ID,
                "proprietary": True,
                "not_mpeg": True,
                "spec": grkmf.load_spec(),
            })
            return
        if path == "/api/grkmf/compare":
            self._send_json(HTTPStatus.OK, grkmf_market_compare())
            return
        if path == "/api/grkmf/profiles":
            self._send_json(HTTPStatus.OK, {"ok": True, "profiles": grkmf.profiles()})
            return
        if path == "/api/grkmf/tune":
            self._send_json(HTTPStatus.OK, grkmf.tune_doctrine())
            return
        if path == "/api/pattern":
            self._send_json(HTTPStatus.OK, pattern_status())
            return
        if path == "/api/pattern/doctrine":
            self._send_json(HTTPStatus.OK, pattern_doctrine())
            return
        if path == "/api/offense":
            self._send_json(HTTPStatus.OK, offense_status())
            return
        if path == "/api/offense/doctrine":
            self._send_json(HTTPStatus.OK, offense_doctrine())
            return
        if path == "/api/trust":
            self._send_json(HTTPStatus.OK, trust_network_status())
            return
        if path == "/api/trust/mesh":
            self._send_json(HTTPStatus.OK, verify_trust_mesh())
            return
        if path == "/api/trust/doctrine":
            self._send_json(HTTPStatus.OK, trust_doctrine())
            return
        if path == "/api/trust/hostess7":
            self._send_json(HTTPStatus.OK, hostess7_bridge())
            return
        if path == "/api/stream/verify":
            if self._enforce("verify"):
                return
            self._send_json(HTTPStatus.OK, verify_chain(tail=int(qs.get("tail", ["50"])[0] or 50)))
            return
        if path == "/api/preserve/status":
            self._send_json(HTTPStatus.OK, preserve_status())
            return
        if path == "/api/preserve/doctrine":
            self._send_json(HTTPStatus.OK, threat_doctrine())
            return
        if path == "/api/preserve/hold":
            hold = ZOCR_ROOT / "data" / "preserve" / "last-good.png"
            if hold.is_file():
                self._send_bytes(hold.read_bytes(), mime="image/png", cache="no-store")
            else:
                self.send_response(HTTPStatus.NOT_FOUND)
                self.end_headers()
            return
        if path == "/api/stream/mjpeg":
            if self._enforce("mjpeg"):
                return
            profile = (qs.get("profile", ["watch"])[0] or "watch").strip()
            prefer = (qs.get("prefer", ["auto"])[0] or "auto").strip()
            max_f = int(qs.get("max_frames", ["0"])[0] or "0")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Cache-Control", "no-store, no-cache")
            self.send_header("Connection", "close")
            self.send_header("X-ZOCR-Profile", profile)
            self.send_header("X-ZOCR-Field-Power", profile)
            self.end_headers()
            try:
                for chunk in mjpeg_generator(
                    profile=profile,
                    prefer=prefer,
                    client_host=self._client_host(),
                    max_frames=max_f,
                ):
                    self.wfile.write(chunk)
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            return
        if path == "/api/ai":
            include = (qs.get("look", ["0"])[0] or "0").lower() in ("1", "true", "yes")
            prefer = qs.get("prefer", ["auto"])[0] or "auto"
            self._send_json(HTTPStatus.OK, ai_context(include_look=include, prefer=prefer))
            return
        if path == "/api/captures":
            self._send_json(HTTPStatus.OK, {"ok": True, "captures": latest(24)})
            return
        if path.startswith("/out/"):
            rel = path[len("/out/"):]
            target = (OUT / unquote(rel)).resolve()
            if not str(target).startswith(str(OUT.resolve())) or not target.is_file():
                self.send_response(HTTPStatus.NOT_FOUND)
                self.end_headers()
                return
            mime = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            self._send_bytes(target.read_bytes(), mime=mime)
            return
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", "/#live")
        self.end_headers()

    def do_POST(self) -> None:
        path = unquote(self.path.split("?", 1)[0])
        body = self._read_json_body()
        prefer = str(body.get("prefer") or "auto").strip().lower()
        label = str(body.get("label") or "api_look").strip()[:64]
        host = self._client_host()

        if path == "/api/security/seal":
            self._send_json(HTTPStatus.OK, {"ok": True, **seal_codebase()})
            return
        if path == "/api/security/token":
            sub = str(body.get("subject") or "operator").strip()
            self._send_json(HTTPStatus.OK, issue_operator_token(subject=sub))
            return
        if path == "/api/security/encrypt":
            payload = body.get("payload", "probe").encode() if isinstance(body.get("payload"), str) else b"probe"
            self._send_json(HTTPStatus.OK, encrypt_stream_payload(payload))
            return
        if path == "/api/zac/pack":
            label = str(body.get("label") or "api-pack").strip()
            self._send_json(HTTPStatus.OK, pack_vision_artifacts(label=label))
            return
        if path == "/api/zac/restore":
            zpath = str(body.get("path") or "").strip()
            if not zpath:
                self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "path_required"})
                return
            self._send_json(HTTPStatus.OK, restore_vision_artifacts(zpath))
            return
        if path == "/api/copilot/ask":
            q = str(body.get("query") or body.get("q") or "what holds it together").strip()
            self._send_json(HTTPStatus.OK, copilot_ask(q))
            return
        if path == "/api/vigilance/start":
            if self._enforce("vigilance_start"):
                return
            profile = str(body.get("profile") or "sentinel").strip()
            interval = body.get("interval_sec")
            try:
                self._send_json(HTTPStatus.OK, vigilance_start(
                    profile=profile,
                    prefer=prefer,
                    interval_sec=float(interval) if interval is not None else None,
                ))
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": str(exc)})
            return
        if path == "/api/vigilance/stop":
            if self._enforce("vigilance_stop"):
                return
            self._send_json(HTTPStatus.OK, vigilance_stop())
            return
        if path in ("/api/look", "/api/vision/poll", "/api/vision/look"):
            if self._enforce("look"):
                return
            try:
                self._send_json(HTTPStatus.OK, look(label=label, prefer=prefer))
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": str(exc)})
            return
        if path == "/api/observe":
            if self._enforce("observe"):
                return
            try:
                cap = look(label=label or "observe", prefer=prefer)
                self._send_json(HTTPStatus.OK, {
                    "ok": True,
                    "look": cap,
                    "robotics": robotics_context(capture=cap),
                })
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": str(exc)})
            return
        if path == "/api/stream/start":
            if self._enforce("stream_start"):
                return
            profile = str(body.get("profile") or "watch").strip()
            try:
                self._send_json(HTTPStatus.OK, stream_start(
                    profile=profile, prefer=prefer, client_host=host,
                ))
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": str(exc)})
            return
        if path == "/api/stream/stop":
            self._send_json(HTTPStatus.OK, stream_stop())
            return
        if path == "/api/pattern/scan":
            if self._enforce("pattern_scan"):
                return
            img = body.get("image")
            if not img:
                self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "image_required"})
                return
            target = Path(str(img))
            if not target.is_file():
                self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "image_not_found"})
                return
            self._send_json(HTTPStatus.OK, scan_frame(
                target,
                session_id=body.get("session_id"),
                seq=int(body["seq"]) if body.get("seq") is not None else None,
                expect_stamp=bool(body.get("expect_stamp")),
            ))
            return
        if path == "/api/pattern/stamp":
            if self._enforce("pattern_stamp"):
                return
            img = body.get("image")
            if not img:
                self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "image_required"})
                return
            target = Path(str(img))
            if not target.is_file():
                self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "image_not_found"})
                return
            sid = str(body.get("session_id") or "manual")
            seq = int(body.get("seq") or 1)
            self._send_json(HTTPStatus.OK, stamp_frame(target, session_id=sid, seq=seq))
            return
        if path == "/api/grkmf/tune":
            body = self._read_json()
            if body.get("reset"):
                self._send_json(HTTPStatus.OK, {"ok": True, "resolved": grkmf.tune_reset()})
                return
            self._send_json(HTTPStatus.OK, {
                "ok": True,
                "resolved": grkmf.tune_apply(
                    mode=body.get("mode"),
                    width=body.get("width"),
                    height=body.get("height"),
                    fps=body.get("fps"),
                    refresh_hz=body.get("refresh_hz"),
                    gop=body.get("gop"),
                    jpeg_quality=body.get("jpeg_quality"),
                    preset=body.get("preset"),
                    ai_locked=body.get("ai_locked"),
                    reason=str(body.get("reason") or "api"),
                ),
            })
            return
        if path == "/api/grkmf/ai-tune":
            body = self._read_json()
            self._send_json(HTTPStatus.OK, {
                "ok": True,
                "resolved": grkmf.ai_tune(
                    load_ms=body.get("load_ms"),
                    mode=body.get("mode"),
                    preset=body.get("preset"),
                    goal=body.get("goal"),
                ),
            })
            return
        if path == "/api/video/tune":
            body = self._read_json()
            if body.get("reset"):
                self._send_json(HTTPStatus.OK, {**video_tune_reset(), "status": video_status()})
                return
            self._send_json(HTTPStatus.OK, video_tune(
                mode=body.get("mode"),
                width=body.get("width"),
                height=body.get("height"),
                max_width=body.get("max_width"),
                fps=body.get("fps"),
                refresh_hz=body.get("refresh_hz"),
                gop=body.get("gop"),
                jpeg_quality=body.get("jpeg_quality"),
                ai_locked=body.get("ai_locked"),
                preset=body.get("preset"),
                reason=str(body.get("reason") or "api"),
            ))
            return
        if path == "/api/video/ai-tune":
            body = self._read_json()
            self._send_json(HTTPStatus.OK, video_ai_tune(
                load_ms=body.get("load_ms"),
                goal=body.get("goal"),
            ))
            return
        if path == "/api/grkmf/export":
            src = str(body.get("src") or body.get("dir") or "").strip()
            out = str(body.get("out") or (ZOCR_ROOT / "out" / "movie.grkm")).strip()
            prof = str(body.get("profile") or "cinema_4k").strip()
            title = str(body.get("title") or "").strip()
            if not src:
                self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "src_required"})
                return
            src_path = Path(src)
            if not src_path.is_absolute():
                src_path = (ZOCR_ROOT / src).resolve()
            out_path = Path(out)
            if not out_path.is_absolute():
                out_path = (ZOCR_ROOT / out).resolve()
            try:
                if src_path.is_dir():
                    result = grkmf.export_from_png_dir(src_path, out_path, profile_name=prof, title=title)
                elif src_path.is_file():
                    result = export_grkm_movie([src_path], out_path, profile=prof, title=title)
                else:
                    self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "src_not_found"})
                    return
                self._send_json(HTTPStatus.OK, result)
            except OSError as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": str(exc)})
            return
        if path == "/api/grkmf/verify":
            target = str(body.get("path") or body.get("file") or "").strip()
            if not target:
                self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "path_required"})
                return
            p = Path(target)
            if not p.is_absolute():
                p = (ZOCR_ROOT / target).resolve()
            self._send_json(HTTPStatus.OK, verify_grkm_movie(p))
            return
        if path == "/api/video/enhance":
            enable = body.get("enable")
            if enable is None:
                enable = body.get("on")
            if isinstance(enable, str):
                enable = enable.strip().lower() in ("1", "true", "yes", "on")
            elif enable is not None:
                enable = bool(enable)
            self._send_json(HTTPStatus.OK, video_enhance(enable=enable))
            return
        if path == "/api/eye/teach":
            profile = str(body.get("profile") or body.get("eye") or "human").strip()
            self._send_json(HTTPStatus.OK, teach(profile, source="api"))
            return
        if path == "/api/robotics/arm":
            mode = str(body.get("mode") or body.get("final") or "dishes").strip()
            voice = body.get("voice")
            if voice is not None:
                voice = str(voice).strip()
            self._send_json(HTTPStatus.OK, arm_robotics(
                mode,
                voice=voice,
                start_stream=bool(body.get("start_stream")),
                tune=body.get("tune") if isinstance(body.get("tune"), dict) else None,
                prefer=str(body.get("prefer") or "auto"),
            ))
            return
        if path == "/api/eye/final/mode":
            mode = str(body.get("mode") or body.get("final") or "dishes").strip()
            voice = body.get("voice")
            if voice is not None:
                voice = str(voice).strip()
            self._send_json(HTTPStatus.OK, set_final_mode(mode, voice=voice, source="api"))
            return
        if path == "/api/eye/live":
            mode = str(body.get("mode") or "dishes").strip()
            voice = body.get("voice")
            if voice is not None:
                voice = str(voice).strip()
            self._send_json(HTTPStatus.OK, make_living_live(
                mode,
                voice=voice,
                start_stream=bool(body.get("start_stream")),
                vigilance=bool(body.get("vigilance")),
            ))
            return
        if path == "/api/eye/truth/forward":
            self._send_json(HTTPStatus.OK, truth_forward(
                speak=body.get("speak", True) is not False,
                scan=body.get("scan", True) is not False,
                fire_weapons=body.get("fire_weapons", True) is not False,
            ))
            return
        if path == "/api/eye/weaponize":
            mode = str(body.get("mode") or "war").strip()
            self._send_json(HTTPStatus.OK, weaponize_eyeball(mode=mode))
            return
        if path == "/api/eye/weapons/fire":
            weapon = str(body.get("weapon") or body.get("id") or "forward_truth").strip()
            threat = body.get("threat")
            if threat is not None:
                threat = str(threat).strip()
            mode = str(body.get("mode") or "").strip() or None
            self._send_json(HTTPStatus.OK, fire_entity_weapon(
                weapon, threat=threat, source="api", mode=mode,
            ))
            return
        if path == "/api/rig/configure":
            preset = body.get("preset")
            eyes = body.get("eyes")
            stereo = body.get("stereoscopic")
            self._send_json(HTTPStatus.OK, configure_rig(
                preset=str(preset).strip() if preset else None,
                eyes=eyes if isinstance(eyes, list) else None,
                stereoscopic=stereo if isinstance(stereo, dict) else None,
                source="api",
            ))
            return
        if path == "/api/neural/seal":
            self._send_json(HTTPStatus.OK, {"ok": True, **seal_network()})
            return
        if path == "/api/neural/analyze":
            if self._enforce("nn_analyze"):
                return
            img = body.get("image")
            from zocr_preserve import acquire_preserved
            path = None
            if img:
                path = Path(str(img))
            elif body.get("look", True):
                acq = acquire_preserved(prefer=str(body.get("prefer") or "auto"), allow_hold=True)
                path = acq.get("path")
            self._send_json(HTTPStatus.OK, nn_analyze(
                path, context=body.get("context") or {}, client_host=host,
            ))
            return
        if path == "/api/kill/all":
            self._send_json(HTTPStatus.OK, kill_all(reason=str(body.get("reason") or "api")))
            return
        if path == "/api/kill/trip":
            switch = str(body.get("switch") or "vision").strip()
            self._send_json(HTTPStatus.OK, trip(switch, reason=str(body.get("reason") or "api")))
            return
        if path == "/api/kill/release":
            switch = str(body.get("switch") or "all").strip()
            self._send_json(HTTPStatus.OK, release(switch))
            return
        if path == "/api/field/compiler/probe":
            self._send_json(HTTPStatus.OK, probe_compilers())
            return
        if path == "/api/hud/request":
            self._send_json(HTTPStatus.OK, request_hud(body))
            return
        if path == "/api/hud/analyze":
            module = str(body.get("module") or "spectrum").strip()
            self._send_json(HTTPStatus.OK, module_analyze(module))
            return
        if path == "/api/queen-build":
            self._send_json(HTTPStatus.OK, _queen_build_dispatch(body or {"action": "json"}))
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"ZOCR field vision http://{HOST}:{PORT}/#stream", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()