# Final_Eye v0.9.6

**The Final Eyeball** — robotics field vision by [Zachary Geurts](https://github.com/ZacharyGeurts).

Proprietary stack: **ZOCRSM1** field vision + **GRKMF1/GVC1** media (not MPEG). Built for scientific robotics review — silent capture, AI-tunable fps/resolution, sealed integrity.

> We never presume vision loss. Confidence always in Vision.

## Quick start

```bash
pip install -r requirements.txt
./start.sh --no-open          # vision server http://127.0.0.1:9479
./tests/run_tests.sh          # smoke tests (run before field deploy)
python3 zocr_watch.py look    # on-demand capture — no auto flash
```

## Robotics modes

| Mode | Use | Video | FPS |
|------|-----|-------|-----|
| `dishes` | Domestic / low load | media | AI tunable |
| `war` | Field combat | combat | **3–20** AI on demand |

```bash
curl -X POST http://127.0.0.1:9479/api/robotics/arm \
  -H 'Content-Type: application/json' \
  -d '{"mode":"war","start_stream":false}'
```

## Stack

| Layer | ID | Role |
|-------|-----|------|
| Product | `Final_Eye` | Robotics vision product |
| Field video | `ZOCRSM1` | Silent capture, pattern, offense, WRDT |
| Media | `GRKMF1` | Proprietary cinema — legacy → **16K**, up to **240 fps** |
| Codec | `GVC1` | Grok Vision Codec — not MPEG |

See [docs/REVIEW_CHECKLIST.md](docs/REVIEW_CHECKLIST.md) for masters review protocol.

## License

Proprietary — Zachary Geurts / Grok / SG. Not MPEG.