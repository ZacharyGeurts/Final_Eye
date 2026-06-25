#!/usr/bin/env python3
"""Build Final_Eye release artifacts for all major platforms."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PACKAGING = ROOT / "packaging"
RELEASES = ROOT / "releases"

EXCLUDE_DIRS = {
    ".git", ".venv", "venv", "__pycache__", "out", "releases", ".grok",
}
EXCLUDE_FILES = {
    ".DS_Store", "manifest.jsonl",
}
EXCLUDE_GLOBS = (
    "*.pyc", "*.pyo", "*.grkm", "*.pid",
    "data/*-ledger.jsonl", "data/vision-session.jsonl",
    "data/server.log", "data/poll.log",
    "data/operator-auth.json", "data/field-compiler-bench.json",
    "data/release-test-matrix.json", "data/stream-chain.json",
    "data/sovereign-time-state/sovereign-time-key.bin",
)


def _version() -> str:
    v = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if not v:
        raise SystemExit("VERSION file missing")
    return v


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _should_skip(rel: str) -> bool:
    parts = Path(rel).parts
    if parts and parts[0] in EXCLUDE_DIRS:
        return True
    if any(part in EXCLUDE_DIRS for part in parts):
        return True
    name = Path(rel).name
    if name in EXCLUDE_FILES:
        return True
    for pat in EXCLUDE_GLOBS:
        if Path(rel).match(pat):
            return True
    return False


def _copy_tree(src: Path, dst: Path) -> int:
    n = 0
    for p in sorted(src.rglob("*")):
        if not p.is_file():
            continue
        rel = str(p.relative_to(src))
        if _should_skip(rel):
            continue
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)
        n += 1
    return n


def _stage(name: str) -> Path:
    stage = RELEASES / f"stage-{name}"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    _copy_tree(ROOT, stage)
    (stage / "data").mkdir(exist_ok=True)
    (stage / "out").mkdir(exist_ok=True)
    return stage


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _tar_gz(stage: Path, out: Path, arc_root: str) -> None:
    with tarfile.open(out, "w:gz") as tar:
        tar.add(stage, arcname=arc_root)


def _zip_dir(stage: Path, out: Path, arc_root: str) -> None:
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(stage.rglob("*")):
            if p.is_file():
                zf.write(p, Path(arc_root) / p.relative_to(stage))


def _inject_launchers(stage: Path, platform: str) -> None:
    if platform == "linux":
        shutil.copy2(PACKAGING / "linux" / "install.sh", stage / "install.sh")
        os.chmod(stage / "install.sh", 0o755)
    elif platform == "windows":
        for name in ("Start-FinalEye.bat", "Start-FinalEye.ps1", "Install-FinalEye.ps1"):
            shutil.copy2(PACKAGING / "windows" / name, stage / name)
    elif platform == "macos":
        cmd = stage / "Start Final Eye.command"
        shutil.copy2(PACKAGING / "macos" / "Start Final Eye.command", cmd)
        os.chmod(cmd, 0o755)


def build_linux_tar(version: str) -> Path:
    stage = _stage("linux")
    _inject_launchers(stage, "linux")
    out = RELEASES / f"Final_Eye-{version}-linux-x86_64.tar.gz"
    _tar_gz(stage, out, f"Final_Eye-{version}-linux-x86_64")
    shutil.rmtree(stage)
    return out


def build_macos_tar(version: str) -> Path:
    stage = _stage("macos")
    _inject_launchers(stage, "macos")
    out = RELEASES / f"Final_Eye-{version}-macos-universal.tar.gz"
    _tar_gz(stage, out, f"Final_Eye-{version}-macos")
    shutil.rmtree(stage)
    return out


def build_windows_zip(version: str) -> Path:
    stage = _stage("windows")
    _inject_launchers(stage, "windows")
    out = RELEASES / f"Final_Eye-{version}-windows-x64.zip"
    _zip_dir(stage, out, f"Final_Eye-{version}-windows-x64")
    shutil.rmtree(stage)
    return out


def build_source_tar(version: str) -> Path:
    stage = _stage("source")
    out = RELEASES / f"Final_Eye-{version}-source.tar.gz"
    _tar_gz(stage, out, f"Final_Eye-{version}-source")
    shutil.rmtree(stage)
    return out


def build_deb(version: str) -> Path | None:
    if not shutil.which("dpkg-deb"):
        return None
    stage = _stage("deb")
    _inject_launchers(stage, "linux")
    deb_root = RELEASES / "deb-root"
    if deb_root.exists():
        shutil.rmtree(deb_root)
    app = deb_root / "opt" / "final-eye"
    shutil.copytree(stage, app)
    debian = PACKAGING / "debian" / "DEBIAN"
    shutil.copytree(debian, deb_root / "DEBIAN")
    control = deb_root / "DEBIAN" / "control"
    text = control.read_text(encoding="utf-8").replace("@VERSION@", version).rstrip() + "\n"
    control.write_text(text, encoding="utf-8")
    for script in ("postinst", "prerm"):
        p = deb_root / "DEBIAN" / script
        if p.is_file():
            os.chmod(p, 0o755)
    out = RELEASES / f"final-eye_{version}_amd64.deb"
    try:
        subprocess.run(["dpkg-deb", "--build", str(deb_root), str(out)], check=True)
    except subprocess.CalledProcessError as exc:
        print(f"  deb: FAILED ({exc})", file=sys.stderr)
        shutil.rmtree(stage, ignore_errors=True)
        shutil.rmtree(deb_root, ignore_errors=True)
        return None
    shutil.rmtree(stage)
    shutil.rmtree(deb_root)
    return out


def write_checksums(artifacts: list[Path]) -> Path:
    lines = []
    for p in artifacts:
        if p and p.is_file():
            lines.append(f"{_sha256(p)}  {p.name}")
    out = RELEASES / "SHA256SUMS"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def _codename() -> str:
    try:
        sys.path.insert(0, str(ROOT))
        from zocr_product import product_info
        return str(product_info().get("codename") or "teach-authority")
    except Exception:
        return "teach-authority"


def write_manifest(version: str, artifacts: list[Path]) -> Path:
    doc = {
        "schema": "final-eye-release-manifest/v1",
        "product": "Final_Eye",
        "version": version,
        "codename": _codename(),
        "ts": _ts(),
        "platforms": {
            "linux": f"Final_Eye-{version}-linux-x86_64.tar.gz",
            "linux_deb": f"final-eye_{version}_amd64.deb",
            "windows": f"Final_Eye-{version}-windows-x64.zip",
            "macos": f"Final_Eye-{version}-macos-universal.tar.gz",
            "source": f"Final_Eye-{version}-source.tar.gz",
            "docker": f"ghcr.io/zacharygeurts/final-eye:{version}",
        },
        "artifacts": [
            {"name": p.name, "bytes": p.stat().st_size, "sha256": _sha256(p)}
            for p in artifacts if p and p.is_file()
        ],
        "requirements": {
            "python": ">=3.10",
            "optional": ["tesseract-ocr", "scrot", "imagemagick"],
            "integration": ["Grok16", "Queen", "Hostess7 (optional SG layout)"],
        },
    }
    out = RELEASES / f"Final_Eye-{version}-manifest.json"
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return out


def write_release_notes(version: str) -> Path:
    codename = _codename()
    body = f"""# Final_Eye v{version} — {codename}

**The Final Eyeball** — sovereign field robotics vision for Linux, Windows, macOS, and source.

## Highlights (v1.1)
- **Teach doctrine** — the eye speaks; independent weapon authority over 37 weapons
- API: `/api/eye/authority`, `/api/eye/targets`, `/api/eye/teach/doctrine`, `/api/eye/understand`
- Threat-only fire: `POST /api/eye/weapons/fire {{"threat":"provenance_mismatch"}}` — eye selects salvo
- Silent capture · GVC1/GRKMF1 proprietary codec (not MPEG)
- Field Ops UI at `:9479/ops` · **34 automated tests**
- Grok16 field_opt + Queen/Hostess/ZAC integration
- Illustrated textbook: https://zacharygeurts.github.io/Final_Eye/

## Install by platform

### Linux (tarball)
```bash
tar -xzf Final_Eye-{version}-linux-x86_64.tar.gz
cd Final_Eye-{version}-linux-x86_64
./install.sh
./start.sh --no-open
```

### Linux (Debian/Ubuntu .deb)
```bash
sudo dpkg -i final-eye_{version}_amd64.deb
final-eye-start
```

### Windows
1. Extract `Final_Eye-{version}-windows-x64.zip`
2. Install Python 3.12+ from python.org
3. Double-click `Start-FinalEye.bat` or run `Install-FinalEye.ps1`

### macOS
```bash
tar -xzf Final_Eye-{version}-macos-universal.tar.gz
cd Final_Eye-{version}-macos
./Start\\ Final\\ Eye.command
```

### Docker (build locally)
GHCR image for v{version} builds from the included `Dockerfile` when CI workflow is enabled. Until then:
```bash
docker build -t final-eye:{version} .
docker run -p 9479:9479 final-eye:{version}
```

### Source (all platforms)
```bash
tar -xzf Final_Eye-{version}-source.tar.gz
pip install -r requirements.txt
python3 zocr_security.py seal
./start.sh --no-open
```

## Verify
```bash
sha256sum -c SHA256SUMS
```

## License
Proprietary — scientific robotics review permitted at tagged releases.
"""
    out = RELEASES / f"Final_Eye-{version}-RELEASE_NOTES.md"
    out.write_text(body, encoding="utf-8")
    return out


def verify_linux_tarball(path: Path, version: str) -> dict[str, Any]:
    """Smoke-verify release tarball: VERSION, teach doctrine, product version."""
    import tarfile
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        with tarfile.open(path, "r:gz") as tar:
            tar.extractall(tmp)
        root_name = f"Final_Eye-{version}-linux-x86_64"
        stage = Path(tmp) / root_name
        if not stage.is_dir():
            raise SystemExit(f"release verify failed: missing {root_name}/ in tarball")
        ver = (stage / "VERSION").read_text(encoding="utf-8").strip()
        if ver != version:
            raise SystemExit(f"release verify failed: VERSION={ver!r} expected {version!r}")
        teach = stage / "data" / "eye-teach-doctrine.json"
        if not teach.is_file():
            raise SystemExit("release verify failed: missing data/eye-teach-doctrine.json")
        sys.path.insert(0, str(stage))
        try:
            from zocr_product import product_info
            pinfo = product_info()
        finally:
            if str(stage) in sys.path:
                sys.path.remove(str(stage))
        if pinfo.get("version") != version:
            raise SystemExit(
                f"release verify failed: product version {pinfo.get('version')!r}"
            )
        return {"ok": True, "version": ver, "codename": pinfo.get("codename")}


def main() -> int:
    version = _version()
    RELEASES.mkdir(parents=True, exist_ok=True)
    print(f"Building Final_Eye v{version} releases…", flush=True)

    artifacts: list[Path] = []
    linux_tar = build_linux_tar(version)
    verify_linux_tarball(linux_tar, version)
    print(f"  verify: linux tar ok (VERSION, teach doctrine, product)", flush=True)
    artifacts.append(linux_tar)
    print(f"  linux tar: {artifacts[-1].name} ({artifacts[-1].stat().st_size // 1024} KB)")
    artifacts.append(build_macos_tar(version))
    print(f"  macos tar: {artifacts[-1].name}")
    artifacts.append(build_windows_zip(version))
    print(f"  windows zip: {artifacts[-1].name}")
    artifacts.append(build_source_tar(version))
    print(f"  source tar: {artifacts[-1].name}")
    deb = build_deb(version)
    if deb:
        artifacts.append(deb)
        print(f"  deb: {deb.name}")
    else:
        print("  deb: skipped (dpkg-deb missing)")

    notes = write_release_notes(version)
    manifest = write_manifest(version, artifacts)
    artifacts.extend([notes, manifest])
    sums = write_checksums(artifacts)
    artifacts.append(sums)

    print(json.dumps({
        "version": version,
        "artifacts": [p.name for p in artifacts if p.is_file()],
        "dir": str(RELEASES),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())