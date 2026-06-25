# Final_Eye 1.0 Performance

Labels: **Measured** = benchmark run; **Doctrine** = declared capability.

## Cached benchmarks (`data/zocrsm1-benchmark.json`)

| Profile | Mode | Target FPS | Measured emit FPS | Resolution | Label |
|---------|------|------------|-------------------|------------|-------|
| bullet_240 | bullet_train | 480 | **465.5** | 4K (3840px) | Measured |
| watch | capture | 2 | varies by host | balanced | Measured on demand |
| cinema_16k | AI tunable | 240 doctrine | host-dependent | 15360×8640 max | Doctrine |

## War vs dishes

| Mode | FPS range | Video profile | Label |
|------|-----------|---------------|-------|
| **war** | 3–20 | combat | Implemented |
| **dishes** | AI tunable up to 240 | media / cinema_16k | Implemented |

## Latency (low-end smoke host)

- Single frame capture (`_capture_video_frame`): ~50–200ms typical (Measured, env-dependent).
- Tester subsystem poll: &lt;500ms for full snapshot (Measured).

## AI tuning response

- `POST /api/video/tune` applies fps/width/height without restart when possible.
- `POST /api/video/ai-tune` uses contract-bounded assist path.

## Power / thermodynamics

- Entity weapons: `joule_throttle`, `cool_gate`, `entropy_fold` — thermo rack (Metaphor for field power doctrine).
- Assist contract (`zocr_contract.py`) prevents slot overflow on shared systems.

## Reproduce

```bash
cd Final_Eye
python3 zocr_security.py seal
FINAL_EYE_LOW_END=1 ./tests/run_tests.sh
curl -s http://127.0.0.1:9479/api/video/benchmark | jq .summary
```

Update `data/zocrsm1-benchmark.json` after hardware runs on target RTX field host.