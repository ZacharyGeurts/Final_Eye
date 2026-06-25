# Final_Eye 1.0 Architecture

**Product:** Final_Eye (ZOCRSM1 + GRKMF1/GVC1) · **Port:** 9479 · **Not MPEG**

## Layer stack

```
Operator / Tester UI (gui/)
    ↓ HTTP JSON
ZOCR API Server (gui/app.py)
    ↓ mandate_enforce + code seal
Vision Core
  zocr_vision · zocr_capture · zocr_preserve · zocr_stream
Video / Codec
  zocr_video (ZOCRSM1) · zocr_grkmf · GrokMediaFormat/GVC1
Entity / Truth
  zocr_entity_eyeball · zocr_heaven_hell · zocr_trust
Field Compiler
  zocr_grok16 (primary) · zocr_field_compiler · Queen forge
Security
  zocr_security · zocr_kill · zocr_sovereign_time
Integration
  zocr_zac · Hostess7 · Queen · NEXUS (read-only doctrine)
```

## Data flow — silent capture

1. Operator calls `POST /api/look` or arms robotics — **no display flash** (doctrine).
2. `zocr_preserve` cascade: RTX → XWD → hold failover.
3. `zocr_pattern` scans for foreign/weave threats.
4. `zocr_offense` records strikes; truth eyeball may fire entity weapons.
5. Optional `zocr_video` seals frames as ZOCRSM1; GRKMF envelope for transport.

## Grok16 alignment

- Profiles from `SG/Grok16/data/` — **field_opt** for patrol/submicron eyes.
- Mode map: `war → vulkan_rtx`, `dishes → ai`, `patrol → field_opt`.
- Queen `lib/queen-forge.py` provides RTX sub-layer compile probe.

## Field_Primer / redata / ZAC

- Vision artifacts pack via `zocr_zac.py` (ZAC1 format).
- Cross-reference: [Field_Primer](https://github.com/ZacharyGeurts/Field_Primer) redata chapter.
- World_Redata WRDT1 seals align with GRKMF envelope doctrine (SHA-256 proof).

## Internal tester (1.0)

- UI: `http://127.0.0.1:9479/tester`
- API: `GET /api/tester/full` — live subsystem snapshot + release matrix.
- Honesty labels: **implemented** · **measured** · **doctrine** · **metaphor**

## Storage pattern

All state under `data/` and `out/` — Hostess7 brain pattern routing. No external MPEG dependencies.