# Final_Eye 1.0 — Review Test Matrix

## Reproduce

```bash
git clone https://github.com/ZacharyGeurts/Final_Eye.git
cd Final_Eye
pip install -r requirements.txt
./tests/run_tests.sh
./start.sh --no-open
open http://127.0.0.1:9479/tester
```

## Automated matrix (`tests/test_release_1_0.py`)

| ID | Group | Check |
|----|-------|-------|
| product_0_9_9 | release | Version == 0.9.9 |
| code_seal | security | Seal verifies |
| gvc1_envelope | security | GVC1 round-trip + tamper reject |
| war_mode | robotics | War in final modes |
| dishes_mode | robotics | Dishes in final modes |
| silent_capture_policy | security | Silent by default |
| grok16_profile | compiler | field_opt profile present |
| twin_eyeballs | entity | Twin schema v1 |
| heaven_hell | truth | Heaven/Hell spec loaded |
| zac_pack | integration | ZAC round-trip |
| hud_manifest | ui | ≥16 HUD modules |
| grkmf_format | codec | GRKMF1 |
| not_mpeg | codec | GVC1 not MPEG |
| sovereign_witness | field | Monotonic witness |

## Manual verification

1. **Tester UI** — `http://127.0.0.1:9479/tester` — all subsystems green, matrix 14/14
2. **Silent capture** — `python3 zocr_watch.py look` — no display flash
3. **War arm** — `POST /api/robotics/arm {"mode":"war"}` — combat profile
4. **Dishes arm** — `POST /api/robotics/arm {"mode":"dishes"}` — media path
5. **AI tune** — `POST /api/video/tune {"fps":8,"width":1280}`
6. **Grok16** — `GET /api/grok16` — g16_version + field_opt
7. **Heaven/Hell** — `GET /api/eye/heaven-hell`
8. **ZAC pack** — `POST /api/zac/pack`
9. **Security model** — `GET /api/security/model`
10. **Code verify** — `python3 zocr_watch.py verify`

## Sign-off

| Reviewer | Institution | Date | Notes |
|----------|-------------|------|-------|
| Master 1 | | | |
| Master 2 | | | |