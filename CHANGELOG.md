# Changelog

## 1.2.0 — 2026-06-25 (heaven-hell-ops)

- **Eye operations doctrine** — enemy discernment, heaven/hell gate on every salvo, disarmament lane
- **Offense at enemy only** — weapons and targets qualified before strike; heaven blocks friendly fire
- **Disarmament** — weapon-bearing hostility must depart; refusal escalates when corroborated
- **APIs** — `/api/eye/operations`, `/api/eye/operations/doctrine`, Teach lessons `enemy`, `operations`, `disarmament`
- **Queen + Hostess7** — `final-eye-12-doctrine.json`, queen-brain-manifest `hostess7_final_eye`

## 1.1.0 — 2026-06-25 (teach-authority)

### Release
- **Final_Eye 1.1.0** — Teach doctrine: the eye speaks with independent weapon authority
- `data/eye-teach-doctrine.json` — Teach voice lessons (authority, targets, weapons, sovereignty, intro)
- API: `GET /api/eye/authority`, `/api/eye/targets`, `/api/eye/teach/doctrine`, `/api/eye/understand?threat=`
- Threat-only `POST /api/eye/weapons/fire {"threat":"…"}` — eye auto-selects salvo via `threat_weapon_map`
- Entity spec `weapon_authority` block — independent aim, no remote puppet
- **34 automated tests** (+ `test_eye_teach_weapon_authority`)
- Textbook Ch 1 Teach intro, Ch 7 enemies table, Ch 8 v1.1 release — expanded prose toward manuscript target

## 1.0.0 — 2026-06-25 (sovereign-vision) — FINAL

### Release (authorized sign-off)
- **Final_Eye 1.0.0** — sovereign robotics vision stack, production-aligned with Field Technology v5
- Silent capture integrity · proprietary **GVC1/GRKMF1** codec security (not MPEG) · field vision sovereignty
- Field Ops UI at `/ops` and `/tester` — 8 sections, 37+ weapons, release matrix
- Security: code seal, GVC1 tamper rejection, stream AES-GCM/HMAC, operator tokens, silent capture policy
- **ZAC** vision artifact pack/restore (`zocr_zac.py`) — World_Redata alignment
- **Grok16 + Queen/Hostess** integration layer complete — configurable paths, forge probe, co-deploy Docker
- **Field compiler C/C++** harness (`zocr_field_compile.py`) — g16 smoke, g++16 kernel, profile optimization bench
- Co-Pilot foundational truth sources · Heaven/Hell parameters · twin entity eyeballs
- **33 automated tests** (smoke + field compiler + integration + release)
- Docs: ARCHITECTURE, API (9479), SECURITY, PERFORMANCE, REVIEW_CHECKLIST

### Highlights (extra work incorporated)
- Forge integration strengthened · examples expanded · tests robust
- Performance metrics in README and `data/zocrsm1-benchmark.json`
- Field_Primer Ch 11 + glossary updated with Final_Eye 1.0 vision layer reference

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