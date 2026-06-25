# Changelog

## 0.9.9 — 2026-06-25 (field-forge-opt)

### Release
- Review cycle **0.9.9** — Grok16 C/C++ field compiler harness (`zocr_field_compile.py`)
- `field/vision_probe.c` — gnu17 C smoke with `FIELD_ENTROPY_DISPATCH`
- Compile + run: `g16` C probe, `g++16` field_dispatch vision kernel
- Profile optimization bench: `field_opt` vs `field_compute` vs `ai` → `data/field-compiler-bench.json`
- API: `GET /api/field/compile`, `/api/field/compile/full`, `/api/field/compile/optimize`
- Ops dashboard: field compile status + last bench in AI section
- 28 automated tests (smoke + release + field compiler C)

## 1.0.0 — 2026-06-25 (sovereign-vision)

### Release
- DARPA-quality 1.0 sovereign robotics vision — tagged `v1.0.0`
- Internal tester UI at `/tester` — live factual panels, honesty labels, release matrix
- Security model: GVC1 integrity, stream AES-GCM/HMAC, operator tokens, silent capture policy
- ZAC vision artifact pack/restore (`zocr_zac.py`)
- Grok16 field_opt integration test; war/dishes cycle tests
- Docker + docker-compose for Queen/Hostess co-deployment
- Docs: ARCHITECTURE, API (full 9479), SECURITY, PERFORMANCE, expanded REVIEW_CHECKLIST

### Integration
- Truth + Heaven/Hell parameters (Hostess7, NEXUS, Queen panel)
- Twin entity eyeballs — 37 weapons, 8 racks
- Closed-manifest HUD + Grok16 primary field compiler
- 21 automated tests (smoke + release 1.0)

## 0.9.6 — 2026-06-25 (truth-heaven-hell)

- Truth + Heaven/Hell parameters from Hostess7, NEXUS-Shield, Queen panel (`heaven-hell-truth.json`, `zocr_heaven_hell.py`)
- Twin entity eyeballs — 37 weapons, 8 racks; `heaven_pass` + `hell_rip` handlers
- Closed-manifest HUD module system with Truth·H/H tile
- Grok16 field compiler primary; Queen forge + FIELDC RTX sub-layer
- API: `/api/eye/heaven-hell`, `/api/field/compiler`, `/api/grok16`
- 14 smoke tests pass

## 0.9.0 — 2026-06-25 (robotics-review)

- Final_Eye product packaging for scientific robotics masters review
- ZOCRSM1 + GRKMF1/GVC1, AI-tunable video, combat 3–20 fps
- Robotics arm API, smoke tests, review checklist