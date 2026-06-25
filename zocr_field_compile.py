"""ZOCR field compile — Grok16 C/C++ probes, field_opt optimization bench."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from zocr_session import log_event

_ROOT = Path(__file__).resolve().parent
SG = _ROOT.parent
GROK16 = Path(os.environ.get("GROK16_ROOT", str(SG / "Grok16")))
OUT = _ROOT / "out" / "field-compile"
CACHE_PATH = _ROOT / "data" / "field-compiler-bench.json"
PROFILE_SCRIPT = GROK16 / "scripts" / "grok16-profile-flags.py"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _g16() -> Path:
    g = GROK16 / "bin" / "g16"
    if g.is_file() and os.access(g, os.X_OK):
        return g
    env = os.environ.get("G16_PREFIX", "").strip()
    if env:
        g = Path(env) / "bin" / "g16"
        if g.is_file():
            return g
    return GROK16 / "bin" / "g16"


def _gxx16() -> Path:
    for name in ("x86_64-pc-linux-gnu-g++16", "g++16"):
        p = GROK16 / "bin" / name
        if p.is_file() and os.access(p, os.X_OK):
            return p
    return GROK16 / "bin" / "x86_64-pc-linux-gnu-g++16"


def _profile_flags(profile: str, kind: str) -> list[str]:
    if not PROFILE_SCRIPT.is_file():
        return []
    env = {**os.environ, "GROK16_ROOT": str(GROK16)}
    try:
        proc = subprocess.run(
            [sys.executable, str(PROFILE_SCRIPT), profile, kind],
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        if proc.returncode != 0:
            return []
        return [x for x in (proc.stdout or "").split() if x]
    except (OSError, subprocess.TimeoutExpired):
        return []


def _run(cmd: list[str], *, cwd: Path | None = None, timeout: int = 120) -> dict[str, Any]:
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd) if cwd else None,
            env={**os.environ, "GROK16_ROOT": str(GROK16)},
        )
        elapsed = round(time.perf_counter() - t0, 3)
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "elapsed_sec": elapsed,
            "stdout": (proc.stdout or "").strip()[-2000:],
            "stderr": (proc.stderr or "").strip()[-800:] or None,
            "cmd": " ".join(cmd[:12]),
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "elapsed_sec": timeout, "cmd": " ".join(cmd[:12])}
    except OSError as exc:
        return {"ok": False, "error": str(exc)[:200], "cmd": " ".join(cmd[:12])}


def compile_c_smoke(*, profile: str = "field_opt") -> dict[str, Any]:
    """Compile Final_Eye vision_probe.c with Grok16 g16 (gnu17)."""
    src = _ROOT / "field" / "vision_probe.c"
    if not src.is_file():
        src = GROK16 / "examples" / "minimal-c-project" / "hello.c"
    g16 = _g16()
    if not g16.is_file():
        return {"ok": False, "error": "g16_missing", "path": str(g16)}
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "vision_probe_c"
    flags = _profile_flags(profile, "c") or ["-std=gnu17", "-O3", "-march=native"]
    defs = _profile_flags(profile, "defs")
    compile_r = _run([str(g16), *flags, *defs, "-o", str(out), str(src)])
    if not compile_r.get("ok"):
        return {"ok": False, "schema": "zocr-field-compile-c/v1", "compile": compile_r, "profile": profile}
    run_r = _run([str(out)])
    return {
        "ok": run_r.get("ok"),
        "schema": "zocr-field-compile-c/v1",
        "source": str(src),
        "binary": str(out),
        "compiler": str(g16),
        "profile": profile,
        "flags": flags[:8],
        "compile": compile_r,
        "run": run_r,
    }


def compile_vision_kernel(*, profile: str = "field_opt") -> dict[str, Any]:
    """Compile field_dispatch.cpp — Grok16 g++16 field_opt vision kernel."""
    src = GROK16 / "examples" / "field-canvas-kernel" / "field_dispatch.cpp"
    if not src.is_file():
        return {"ok": False, "error": "kernel_source_missing", "path": str(src)}
    gxx = _gxx16()
    if not gxx.is_file():
        return {"ok": False, "error": "g++16_missing", "path": str(gxx)}
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "field_canvas_kernel"
    flags = _profile_flags(profile, "cxx") or ["-std=gnu++26", "-O3", "-march=native"]
    defs = _profile_flags(profile, "defs")
    link = _profile_flags(profile, "link")
    compile_r = _run([str(gxx), *flags, *defs, "-o", str(out), str(src), *link])
    if not compile_r.get("ok"):
        return {"ok": False, "schema": "zocr-field-compile-kernel/v1", "compile": compile_r, "profile": profile}
    run_r = _run([str(out)])
    metrics: dict[str, Any] = {}
    if run_r.get("stdout"):
        for key in ("entropy_micro", "phi_micro", "wave_speed_micro"):
            m = re.search(rf"{key}=(\d+)", run_r["stdout"])
            if m:
                metrics[key] = int(m.group(1))
    return {
        "ok": run_r.get("ok"),
        "schema": "zocr-field-compile-kernel/v1",
        "source": str(src),
        "binary": str(out),
        "compiler": str(gxx),
        "profile": profile,
        "cxx_std": "gnu++26",
        "flags_count": len(flags) + len(defs),
        "compile": compile_r,
        "run": run_r,
        "metrics": metrics,
    }


def field_compiler_optimize(*, profiles: list[str] | None = None) -> dict[str, Any]:
    """Bench C + C++ kernels across profiles — pick fastest runtime."""
    targets = profiles or ["field_opt", "field_compute", "ai"]
    results: list[dict[str, Any]] = []
    for prof in targets:
        c = compile_c_smoke(profile=prof)
        k = compile_vision_kernel(profile=prof)
        run_ms = 0.0
        if c.get("run", {}).get("elapsed_sec"):
            run_ms += float(c["run"]["elapsed_sec"]) * 1000
        if k.get("run", {}).get("elapsed_sec"):
            run_ms += float(k["run"]["elapsed_sec"]) * 1000
        compile_ms = float(c.get("compile", {}).get("elapsed_sec") or 0) * 1000
        compile_ms += float(k.get("compile", {}).get("elapsed_sec") or 0) * 1000
        results.append({
            "profile": prof,
            "c_ok": c.get("ok"),
            "kernel_ok": k.get("ok"),
            "compile_ms": round(compile_ms, 1),
            "run_ms": round(run_ms, 2),
            "total_ms": round(compile_ms + run_ms, 1),
            "c_stdout": (c.get("run") or {}).get("stdout", "")[:80],
            "kernel_stdout": (k.get("run") or {}).get("stdout", "")[:80],
        })
    ok_rows = [r for r in results if r.get("c_ok") and r.get("kernel_ok")]
    best = min(ok_rows, key=lambda x: x["run_ms"]) if ok_rows else (results[0] if results else {})
    doc = {
        "schema": "zocr-field-compiler-bench/v1",
        "ts": _ts(),
        "g16": str(_g16()),
        "g++16": str(_gxx16()),
        "profiles_tested": targets,
        "results": results,
        "best_profile": best.get("profile"),
        "best_run_ms": best.get("run_ms"),
        "recommendation": f"Use profile '{best.get('profile')}' for vision kernels (field_opt default).",
    }
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    log_event("field_compiler_optimize", ok=bool(best.get("profile")), profile=best.get("profile"))
    return doc


def field_compile_status() -> dict[str, Any]:
    bench: dict[str, Any] = {}
    if CACHE_PATH.is_file():
        try:
            bench = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    g16 = _g16()
    gxx = _gxx16()
    return {
        "schema": "zocr-field-compile-status/v1",
        "ts": _ts(),
        "g16_ready": g16.is_file(),
        "g++16_ready": gxx.is_file(),
        "g16_dumpversion": _run([str(g16), "-dumpversion"]).get("stdout") if g16.is_file() else None,
        "out_dir": str(OUT),
        "last_bench": bench.get("best_profile"),
        "last_bench_ms": bench.get("best_run_ms"),
        "cache": str(CACHE_PATH),
    }


def field_compile_full_test() -> dict[str, Any]:
    """Full C + kernel + optimize — for release 0.9.9 review."""
    from zocr_field_compiler import field_compiler_status, probe_compilers

    c = compile_c_smoke()
    kernel = compile_vision_kernel()
    opt = field_compiler_optimize(profiles=["field_opt", "field_compute"])
    compiler = field_compiler_status()
    probe: dict[str, Any] = {"skipped": True, "reason": "FINAL_EYE_LOW_END"}
    if os.environ.get("FINAL_EYE_LOW_END", "").strip().lower() not in ("1", "true", "yes"):
        probe = probe_compilers(timeout=30)
    ok = c.get("ok") and kernel.get("ok")
    return {
        "ok": ok,
        "schema": "zocr-field-compile-full/v1",
        "ts": _ts(),
        "c_smoke": c,
        "vision_kernel": kernel,
        "optimize": opt,
        "compiler_status": compiler,
        "forge_probe": probe,
        "speak": (
            f"Grok16 C {'OK' if c.get('ok') else 'FAIL'} · "
            f"kernel {'OK' if kernel.get('ok') else 'FAIL'} · "
            f"best profile {opt.get('best_profile')} ({opt.get('best_run_ms')}ms run)"
        ),
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower()
    if cmd == "c":
        print(json.dumps(compile_c_smoke(), indent=2))
        return 0
    if cmd == "kernel":
        print(json.dumps(compile_vision_kernel(), indent=2))
        return 0
    if cmd == "optimize":
        print(json.dumps(field_compiler_optimize(), indent=2))
        return 0
    if cmd == "full":
        print(json.dumps(field_compile_full_test(), indent=2))
        return 0
    print(json.dumps(field_compile_status(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())