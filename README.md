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

**Internal tester UI (1.0):** http://127.0.0.1:9479/tester — live factual panels, release matrix, honesty labels.

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

## Stack integration

| Layer | Path |
|-------|------|
| Grok16 compiler | `SG/Grok16` — field_opt, gnu++26 |
| Queen forge | `SG/NewLatest/Queen` |
| Hostess7 truth | `SG/Hostess7` |
| Field_Primer docs | [Field_Primer](https://github.com/ZacharyGeurts/Field_Primer) |
| ZAC artifacts | `POST /api/zac/pack` |

## Docker

```bash
docker compose up --build
docker compose --profile test run tester_check
```

## Docs

- [ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [API.md](docs/API.md)
- [SECURITY.md](docs/SECURITY.md)
- [PERFORMANCE.md](docs/PERFORMANCE.md)
- [REVIEW_CHECKLIST.md](docs/REVIEW_CHECKLIST.md)

## License

Proprietary — see [LICENSE](LICENSE). Scientific robotics review permitted at tagged releases.