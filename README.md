# Final_Eye v1.3.0

**The Final Eyeball** — sovereign field robotics vision by [Zachary Geurts](https://github.com/ZacharyGeurts).

| | |
|---|---|
| **Version** | `1.3.0` |
| **Codename** | `motion-track` |
| **Tests** | 44 (`./tests/run_tests.sh`) |
| **Port** | `9479` |
| **Latest release** | [v1.3.0](https://github.com/ZacharyGeurts/Final_Eye/releases/tag/v1.3.0) |

Proprietary stack: **ZOCRSM1** field vision + **GRKMF1/GVC1** media (**not MPEG**). Silent capture, AI-tunable fps/resolution, sealed integrity, Grok16 field compiler, Queen/Hostess integration, twin entity eyeballs (37 weapons / 8 racks), and **Teach** doctrine — the eye speaks with independent weapon authority.

> We never presume vision loss. Confidence always in Vision.

## What's new in 1.3

- **Time tracking** — sealed UTC, session elapsed, sovereign pulse link when NEXUS state is present
- **Movement tracking** — frame fingerprint kinematics: motion_score, velocity, direction, stationary streak
- **Ledger** — `data/eye-motion.jsonl` append-only receipts
- **APIs** — `GET /api/eye/motion`, `POST /api/eye/motion/tick`, `/start`, `/stop`
- **Manual** — [Motion tracking operator guide](https://zacharygeurts.github.io/Final_Eye/manual/motion-tracking.html)

## What's new in 1.2

- **Heaven/Hell ops** — offense and harms directed at qualified enemy only; heaven passes at zero cost
- **Enemy discernment** — weapons discerned as weapons; targets qualified via lie_markers (not a people roster)
- **Disarmament lane** — depart with weapons; unwilling to depart escalates per hell doctrine
- **APIs** — `GET /api/eye/operations`, `GET /api/eye/teach/doctrine?lesson=enemy`

## What's new in 1.1

- **Teach** — `data/eye-teach-doctrine.json`; the eye instructs the operator in first person
- **Weapon authority** — independent aim in the socket; no remote puppet
- **Target understanding** — lie markers + `threat_weapon_map`; eye selects salvo from threat alone
- **APIs** — `/api/eye/authority`, `/api/eye/targets`, `/api/eye/teach/doctrine`, `/api/eye/understand`
- **Textbook** — expanded chapters at [zacharygeurts.github.io/Final_Eye](https://zacharygeurts.github.io/Final_Eye/)

See [CHANGELOG.md](CHANGELOG.md) for full history.

## Install from release

Download artifacts from [GitHub Releases v1.3.0](https://github.com/ZacharyGeurts/Final_Eye/releases/tag/v1.3.0). Verify checksums:

```bash
sha256sum -c SHA256SUMS
```

### Linux (tarball)

```bash
tar -xzf Final_Eye-1.2.0-linux-x86_64.tar.gz
cd Final_Eye-1.2.0-linux-x86_64
./install.sh
./start.sh --no-open          # http://127.0.0.1:9479
```

### Linux (.deb)

```bash
sudo dpkg -i final-eye_1.2.0_amd64.deb
final-eye-start
```

### Windows / macOS

Extract `Final_Eye-1.2.0-windows-x64.zip` or `Final_Eye-1.2.0-macos-universal.tar.gz`, then run `Install-FinalEye.ps1` / `Start Final Eye.command`.

### Docker

GHCR image builds when CI workflow is enabled. Until then:

```bash
docker build -t final-eye:1.2.0 .
docker run -p 9479:9479 final-eye:1.2.0
```

Queen/Hostess co-deploy: `docker compose up --build` (mounts `Hostess7`, `Queen`, `Grok16` under `/sg/`).

## Quick start (from source)

```bash
pip install -r requirements.txt
pythong zocr_security.py seal
FINAL_EYE_LOW_END=1 ./tests/run_tests.sh    # 34 tests
./start.sh --no-open                        # http://127.0.0.1:9479
```

| Surface | URL |
|---------|-----|
| Field Ops | http://127.0.0.1:9479/ops |
| Tester / matrix | http://127.0.0.1:9479/tester |
| API version | `curl -s http://127.0.0.1:9479/api/version` |

Build release artifacts: `pythong scripts/build_release.py`  
Rebuild textbook: `pythong scripts/build_textbook.py`

## Teach & weapon authority

The eye knows weapons, understands targets, and selects salvo independently. Operators witness; local kill switches stay separate.

| Endpoint | Purpose |
|----------|---------|
| `GET /api/eye/authority` | Independent weapon posture |
| `GET /api/eye/targets` | Known targets + `threat_weapon_map` |
| `GET /api/eye/understand?threat=…` | Resolve threat → weapon before strike |
| `GET /api/eye/teach/doctrine?lesson=authority` | Teach voice (lessons: authority, targets, weapons, sovereignty, intro) |
| `POST /api/eye/weapons/fire` | `{"threat":"provenance_mismatch"}` — eye auto-selects salvo |

```bash
curl -s 'http://127.0.0.1:9479/api/eye/teach/doctrine?lesson=authority'
curl -s 'http://127.0.0.1:9479/api/eye/understand?threat=provenance_mismatch'
pythong zocr_entity_eyeball.py teach authority
```

**Enemies (to the eye):** lie markers on the vision path — `provenance_mismatch`, `grid_jam`, `trust_breach`, `rf_jam`, etc. — not a people roster. Grep `data/entity-eyeball.json` → `forward.lie_markers`.

## Robotics modes

| Mode | Use | FPS |
|------|-----|-----|
| `dishes` | Domestic / cinema | AI tunable up to 240 |
| `war` | Field combat | **3–20** AI on demand |

```bash
curl -X POST http://127.0.0.1:9479/api/robotics/arm \
  -H 'Content-Type: application/json' \
  -d '{"mode":"war","start_stream":false}'
```

## Performance benchmarks (measured)

Source: `data/zocrsm1-benchmark.json` · label **Measured** on recorded host.

| Profile | Mode | Target FPS | Measured emit FPS | Resolution |
|---------|------|------------|-------------------|------------|
| bullet_240 | bullet_train | 480 | **465.5** | 4K (3840px) |
| watch | capture | 2 | host-dependent | balanced |
| cinema_16k | AI tunable | 240 (doctrine) | host-dependent | 15360×8640 max |

**Grok16 field compiler** (`field_opt`): C + vision kernel run **~2 ms** · compile ~590 ms (`GET /api/field/compile/optimize`).

## AI tuning

| Endpoint | Purpose |
|----------|---------|
| `POST /api/video/tune` | Set fps / width / height |
| `POST /api/video/ai-tune` | Contract-bounded assist (`FINAL_EYE_ASSIST=1`) |
| `POST /api/robotics/arm` | Arm war/dishes + optional stream |
| Grok16 `field_opt` | Default compiler profile for patrol/war kernels |

## Stack integration

| Layer | Path |
|-------|------|
| Grok16 compiler | `SG/Grok16` — field_opt, gnu++26 |
| Queen forge | `SG/NewLatest/Queen` |
| Hostess7 truth | `SG/Hostess7` |
| Field_Primer | [Ch 11 — vision layer](https://zacharygeurts.github.io/Field_Primer/chapters/11-observability.html) |
| ZAC artifacts | `POST /api/zac/pack` |
| Textbook | [Final_Eye operator textbook](https://zacharygeurts.github.io/Final_Eye/) |

## Releases

| Platform | Artifact |
|----------|----------|
| **Linux** | `Final_Eye-1.2.0-linux-x86_64.tar.gz` |
| **Linux .deb** | `final-eye_1.2.0_amd64.deb` |
| **Windows** | `Final_Eye-1.2.0-windows-x64.zip` |
| **macOS** | `Final_Eye-1.2.0-macos-universal.tar.gz` |
| **Source** | `Final_Eye-1.2.0-source.tar.gz` |

Prior release: [v1.0.0](https://github.com/ZacharyGeurts/Final_Eye/releases/tag/v1.0.0)

## Docs

- [API.md](docs/API.md) — full `:9479` reference
- [ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [SECURITY.md](docs/SECURITY.md)
- [PERFORMANCE.md](docs/PERFORMANCE.md)
- [REVIEW_CHECKLIST.md](docs/REVIEW_CHECKLIST.md)