# Final_Eye 1.0 API — Port 9479

Base: `http://127.0.0.1:9479` · OpenAPI-style reference · **Not MPEG**

## Errors

| Code | error | Meaning |
|------|-------|---------|
| 403 | code_seal | Tampered or unsealed code |
| 403 | mandate_gate | Egress/host blocked |
| 403 | kill_switch | Operation tripped |
| 400 | path_required | Missing body field |

## Product

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/version` | Product metadata 1.0.0 |
| GET | `/api/health` | Liveness |
| GET | `/api/status` | Live session status |

## Co-Pilot — foundational truths

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/copilot` | Full status + hold-together report |
| GET | `/api/copilot/hold` | Structural integrity — what holds it together |
| GET | `/api/copilot/foundations` | All 14 foundational sources + live probe |
| GET | `/api/copilot/doctrine` | Foundations manifest |
| GET | `/api/copilot/ask?q=…` | Route query to foundational truths |
| POST | `/api/copilot/ask` | `{"query":"what holds trust together?"}` |

## Field Ops dashboard (single UI)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/ops` | Unified Field Ops UI — AI/robotics first, all weapons |
| GET | `/api/ops/full` | Full ops payload (8 sections + matrix + co-pilot) |
| GET | `/tester` | Alias → Field Ops UI |

## Internal tester (1.0)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/tester` | Field Ops UI (same as `/ops`) |
| GET | `/api/tester/snapshot` | Live subsystem snapshot |
| GET | `/api/tester/matrix` | Release test matrix |
| GET | `/api/tester/full?matrix=1` | Snapshot + matrix |

## Robotics & vision

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/robotics` | Robotics context |
| POST | `/api/robotics/arm` | `{"mode":"war\|dishes","start_stream":false}` |
| POST | `/api/look` | Silent capture |
| POST | `/api/observe` | Observe frame |
| GET | `/api/eye` | Eye status |
| GET | `/api/eye/final` | Final Eyeball prescription |
| POST | `/api/eye/final/mode` | Set war/dishes/patrol |
| GET | `/api/eye/twins` | Vita + Veritas twins |
| GET | `/api/eye/truth` | Truth eyeball |
| GET | `/api/eye/heaven-hell` | Truth + Heaven/Hell posture |

## Video & stream

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/video` | ZOCRSM1 status |
| POST | `/api/video/tune` | AI fps/resolution |
| POST | `/api/video/ai-tune` | AI assist tune |
| GET | `/api/video/benchmark` | FPS benchmark |
| GET | `/api/stream/mjpeg?profile=watch` | MJPEG view |
| POST | `/api/stream/start` | Start seal |
| POST | `/api/stream/stop` | Stop seal |

## Security

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/security` | Security status v2 |
| GET | `/api/security/verify` | Code seal verify |
| GET | `/api/security/model` | Documented security model |
| GET | `/api/security/gvc1` | GVC1 integrity probe |
| POST | `/api/security/seal` | Reseal codebase |
| POST | `/api/security/token` | Issue operator HMAC token |
| POST | `/api/security/encrypt` | Stream encrypt probe |

## Grok16 & compiler

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/grok16` | Grok16 status |
| GET | `/api/field/compiler` | Field compiler stack |
| POST | `/api/field/compiler/probe` | Compile probe |
| GET | `/api/field/compile` | Grok16 compile status (g16/g++16 ready, last bench) |
| GET | `/api/field/compile?mode=c` | Compile + run `field/vision_probe.c` (gnu17) |
| GET | `/api/field/compile?mode=kernel` | Compile + run `field_dispatch.cpp` kernel |
| GET | `/api/field/compile/optimize` | Bench profiles (`field_opt`, `field_compute`, `ai`) |
| GET | `/api/field/compile/full` | Full C + kernel + optimize (+ Queen forge probe) |

## ZAC integration

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/zac/status` | ZAC store status |
| GET | `/api/zac/test` | Self-test round-trip |
| POST | `/api/zac/pack` | Pack vision artifacts |
| POST | `/api/zac/restore` | `{"path":"/path/to/file.zac"}` |

## HUD

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/hud/modules` | Closed manifest |
| GET | `/api/hud/status` | Active tiles |
| POST | `/api/hud/request` | Whitelist toggle |

See `docs/ARCHITECTURE.md` for stack diagram.