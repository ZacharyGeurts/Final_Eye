"""ZOCR display additives — modular, accessible capture extensions."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

_ROOT = Path(__file__).resolve().parent
ADDITIVES_PATH = _ROOT / "data" / "display-additives.json"
ADDONS_DIR = _ROOT / "addons"

CaptureFn = Callable[[Path], Path | None]
AvailFn = Callable[[], bool]

_registry: dict[str, dict[str, Any]] = {}
_loaded = False


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_config() -> dict[str, Any]:
    if ADDITIVES_PATH.is_file():
        try:
            return json.loads(ADDITIVES_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {"schema": "zocr-display-additives/v1", "additives": []}


def register_additive(
    additive_id: str,
    *,
    capture: CaptureFn,
    available: AvailFn | None = None,
    label: str = "",
    kind: str = "builtin",
    accessibility: dict[str, Any] | None = None,
    priority: int = 50,
    silent: bool = True,
    approved: bool = True,
) -> None:
    """Register a display capture additive into the modular registry."""
    _registry[additive_id] = {
        "id": additive_id,
        "label": label or additive_id,
        "kind": kind,
        "priority": priority,
        "silent": silent,
        "approved": approved,
        "accessibility": accessibility or {},
        "_capture": capture,
        "_available": available or (lambda: True),
    }


def _register_builtins() -> None:
    from zocr_capture import capture_grim, capture_mss, capture_xwd_silent

    register_additive(
        "xwd_silent",
        capture=capture_xwd_silent,
        available=lambda: bool(shutil.which("xwd") and os.environ.get("DISPLAY")),
        label="X11 silent root grab",
        kind="builtin",
        priority=20,
        accessibility={"aria_label": "Silent X11 framebuffer capture", "flash_free": True},
    )
    register_additive(
        "grim",
        capture=capture_grim,
        available=lambda: bool(shutil.which("grim") and os.environ.get("WAYLAND_DISPLAY")),
        label="Wayland grim capture",
        kind="builtin",
        priority=25,
        accessibility={"aria_label": "Wayland screen capture", "flash_free": True},
    )
    register_additive(
        "mss",
        capture=capture_mss,
        available=lambda: _mss_ok(),
        label="Python MSS framebuffer",
        kind="builtin",
        priority=30,
        accessibility={"aria_label": "Cross-platform silent capture", "flash_free": True},
    )

    def _rtx_capture(out: Path) -> Path | None:
        from zocr_vision import _latest_ppm, _ppm_to_png
        ppm = _latest_ppm()
        if ppm:
            return _ppm_to_png(ppm)
        return None

    register_additive(
        "rtx",
        capture=_rtx_capture,
        available=lambda: True,
        label="Queen RTX engine grab",
        kind="builtin",
        priority=10,
        accessibility={"aria_label": "Engine framebuffer — survives display RF jam", "flash_free": True},
    )

    def _hold_capture(out: Path) -> Path | None:
        hold = _ROOT / "data" / "preserve" / "last-good.png"
        if hold.is_file() and hold.stat().st_size > 500:
            try:
                import shutil as sh
                sh.copy2(hold, out)
                return out
            except OSError:
                pass
        return None

    register_additive(
        "hold",
        capture=_hold_capture,
        available=lambda: (_ROOT / "data" / "preserve" / "last-good.png").is_file(),
        label="Last-good vault hold",
        kind="preserve",
        priority=90,
        accessibility={"aria_label": "Preserved last-good frame", "flash_free": True},
    )

    def _synthetic_capture(out: Path) -> Path | None:
        try:
            from PIL import Image, ImageDraw
            img = Image.new("RGB", (640, 360), (8, 12, 20))
            draw = ImageDraw.Draw(img)
            draw.text((20, 20), "ZOCR PRESERVE", fill=(94, 234, 212))
            draw.text((20, 50), _ts(), fill=(139, 156, 179))
            img.save(out)
            return out
        except Exception:
            return None

    register_additive(
        "synthetic",
        capture=_synthetic_capture,
        available=lambda: True,
        label="Synthetic field plate",
        kind="preserve",
        priority=99,
        accessibility={"aria_label": "Synthetic never-blank display plate", "flash_free": True},
    )


def _mss_ok() -> bool:
    try:
        import mss  # noqa: F401
        return True
    except ImportError:
        return False


def _capture_shell(cmd: list[str], out: Path, *, timeout: int = 10) -> Path | None:
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout, check=False)
        if proc.returncode == 0 and out.is_file() and out.stat().st_size > 500:
            return out
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def _load_plugin_module(path: Path) -> Any | None:
    try:
        spec = importlib.util.spec_from_file_location(f"zocr_addon_{path.stem}", path)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _register_config_additives() -> None:
    cfg = _load_config()
    mandate = cfg.get("mandate_id", "")
    for entry in cfg.get("additives", []):
        aid = str(entry.get("id", "")).strip()
        if not aid or aid in _registry:
            continue
        if not entry.get("enabled", True):
            continue
        if entry.get("require_approval", True) and not entry.get("approved", False):
            continue

        kind = entry.get("kind", "config")
        priority = int(entry.get("priority", 40))
        accessibility = entry.get("accessibility", {})

        if kind == "shell" and entry.get("command"):
            cmd_template = entry["command"]

            def _shell_cap(out: Path, _cmd=cmd_template) -> Path | None:
                cmd = [str(c).replace("{out}", str(out)) for c in _cmd]
                return _capture_shell(cmd, out, timeout=int(entry.get("timeout", 10)))

            def _shell_avail(_entry=entry) -> bool:
                for dep in _entry.get("requires", []):
                    if dep == "DISPLAY" and not os.environ.get("DISPLAY"):
                        return False
                    if dep == "WAYLAND_DISPLAY" and not os.environ.get("WAYLAND_DISPLAY"):
                        return False
                    if not shutil.which(dep) and dep not in ("DISPLAY", "WAYLAND_DISPLAY"):
                        return False
                return True

            register_additive(
                aid,
                capture=_shell_cap,
                available=_shell_avail,
                label=entry.get("label", aid),
                kind="shell",
                priority=priority,
                accessibility=accessibility,
                approved=entry.get("approved", False),
            )
            continue

        if kind == "plugin" and entry.get("module"):
            mod_path = (_ROOT / entry["module"]).resolve()
            if not str(mod_path).startswith(str(ADDONS_DIR.resolve())):
                continue
            mod = _load_plugin_module(mod_path)
            if not mod:
                continue
            cap_fn = getattr(mod, "capture", None)
            avail_fn = getattr(mod, "available", None)
            if not callable(cap_fn):
                continue
            register_additive(
                aid,
                capture=cap_fn,
                available=avail_fn if callable(avail_fn) else (lambda: True),
                label=entry.get("label", aid),
                kind="plugin",
                priority=priority,
                accessibility=accessibility,
                approved=entry.get("approved", False),
            )


def ensure_registry() -> None:
    global _loaded
    if _loaded:
        return
    _registry.clear()
    _register_builtins()
    _register_config_additives()
    _loaded = True


def list_additives(*, available_only: bool = False) -> list[dict[str, Any]]:
    ensure_registry()
    out: list[dict[str, Any]] = []
    for aid, rec in sorted(_registry.items(), key=lambda x: x[1].get("priority", 50)):
        avail = bool(rec["_available"]())
        if available_only and not avail:
            continue
        out.append({
            "id": aid,
            "label": rec.get("label"),
            "kind": rec.get("kind"),
            "priority": rec.get("priority"),
            "silent": rec.get("silent", True),
            "approved": rec.get("approved", True),
            "available": avail,
            "accessibility": rec.get("accessibility", {}),
        })
    return out


def cascade_for_prefer(prefer: str, *, extra: list[str] | None = None) -> list[str]:
    """Build ordered additive cascade — core + optional extras + preserve tail."""
    ensure_registry()
    core: list[str]
    if prefer == "rtx":
        core = ["rtx", "xwd_silent", "grim", "mss"]
    elif prefer == "screen":
        core = ["xwd_silent", "grim", "mss", "rtx"]
    else:
        core = ["rtx", "xwd_silent", "grim", "mss"]

    # Insert approved config additives by priority between core and preserve
    extras = []
    for rec in sorted(_registry.values(), key=lambda r: r.get("priority", 50)):
        aid = rec["id"]
        if aid in core or aid in ("hold", "synthetic"):
            continue
        if rec.get("kind") in ("shell", "plugin") and rec.get("approved"):
            extras.append(aid)

    if extra:
        for e in extra:
            if e in _registry and e not in core:
                extras.insert(0, e)

    seen: set[str] = set()
    ordered: list[str] = []
    for group in (core, extras, ["hold", "synthetic"]):
        for aid in group:
            if aid not in seen and aid in _registry:
                seen.add(aid)
                ordered.append(aid)
    return ordered


def capture_additive(additive_id: str, out_png: Path | None = None) -> tuple[Path | None, str]:
    from zocr_kill import check as kill_check, eyes_protect, is_tripped

    if is_tripped("capture") and additive_id not in ("hold", "synthetic"):
        return None, "none"
    gate = kill_check("additive_capture")
    if not gate.get("ok") and additive_id not in ("hold", "synthetic"):
        return None, "none"

    ensure_registry()
    rec = _registry.get(additive_id)
    if not rec:
        return None, "none"
    if not rec.get("approved", True):
        return None, "none"
    if eyes_protect() and not rec.get("silent", True):
        return None, "none"
    if not rec["_available"]():
        return None, "none"
    out = out_png or Path(tempfile.gettempdir()) / f"zocr-additive-{additive_id}.png"
    path = rec["_capture"](out)
    if path and Path(path).is_file():
        return Path(path), additive_id
    return None, "none"


def additives_status() -> dict[str, Any]:
    cfg = _load_config()
    items = list_additives()
    return {
        "schema": "zocr-additives-status/v1",
        "ts": _ts(),
        "mandate_id": cfg.get("mandate_id"),
        "config": str(ADDITIVES_PATH),
        "addons_dir": str(ADDONS_DIR),
        "count": len(items),
        "available": sum(1 for i in items if i.get("available")),
        "additives": items,
        "accessibility": {
            "modular": True,
            "aria_export": "/api/vigilance/additives",
            "register": "data/display-additives.json + addons/*.py",
        },
    }