# Final_Eye v1.0.0

**The Final Eyeball** — sovereign field robotics vision by [Zachary Geurts](https://github.com/ZacharyGeurts).

Proprietary stack: **ZOCRSM1** field vision + **GRKMF1/GVC1** media (**not MPEG**). Silent capture, AI-tunable fps/resolution, sealed integrity, Grok16 field compiler, Queen/Hostess integration.

> We never presume vision loss. Confidence always in Vision.

## Quick start

```bash
pip install -r requirements.txt
python3 zocr_security.py seal
./tests/run_tests.sh
./start.sh --no-open          # http://127.0.0.1:9479
```

**Field Ops UI (1.0):** http://127.0.0.1:9479/ops — live factual panels, release matrix, honesty labels.

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

Source: `data/zocrsm1-benchmark.json` · label **Measured** on this host.

| Profile | Mode | Target FPS | Measured emit FPS | Resolution |
|---------|------|------------|-------------------|------------|
| bullet_240 | bullet_train | 480 | **465.5** | 4K (3840px) |
| watch | capture | 2 | host-dependent | balanced |
| cinema_16k | AI tunable | 240 (doctrine) | host-dependent | 15360×8640 max |

**Grok16 field compiler** (`field_opt` profile): C + vision kernel run **~2 ms** · compile ~590 ms (see `GET /api/field/compile/optimize`).

## AI tuning

| Endpoint | Purpose |
|----------|---------|
| `POST /api/video/tune` | Set fps / width / height without restart when possible |
| `POST /api/video/ai-tune` | Contract-bounded assist path (`FINAL_EYE_ASSIST=1`) |
| `POST /api/robotics/arm` | Arm war/dishes mode + optional stream |
| Grok16 `field_opt` | Default compiler profile for patrol/war vision kernels |

```bash
curl -s -X POST http://127.0.0.1:9479/api/video/ai-tune -H 'Content-Type: application/json' -d '{}'
curl -s http://127.0.0.1:9479/api/grok16 | jq '.profiles'
```

## Stack integration

| Layer | Path |
|-------|------|
| Grok16 compiler | `SG/Grok16` — field_opt, gnu++26 |
| Queen forge | `SG/NewLatest/Queen` |
| Hostess7 truth | `SG/Hostess7` |
| Field_Primer docs | [Ch 11 — Final_Eye vision layer](https://github.com/ZacharyGeurts/Field_Primer) |
| ZAC artifacts | `POST /api/zac/pack` |

## Docker (Queen/Hostess co-deployment)

```bash
docker compose up --build
docker compose --profile test run tester_check
```

Mounts: `Hostess7`, `Queen`, `Grok16` under `/sg/` — same paths as bare-metal `SG/` layout.

## Docs

- [ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [API.md](docs/API.md)
- [SECURITY.md](docs/SECURITY.md)
- [PERFORMANCE.md](docs/PERFORMANCE.md)
- [REVIEW_CHECKLIST.md](docs/REVIEW_CHECKLIST.md)

## License

Proprietary — see [LICENSE](LICENSE). Scientific robotics review permitted at tagged releases.