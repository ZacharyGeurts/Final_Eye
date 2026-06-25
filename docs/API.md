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

## Internal tester (1.0)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/tester` | Internal tester UI |
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