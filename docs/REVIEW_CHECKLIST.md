# Final_Eye v0.9 — Review Checklist

## Reproduce

```bash
git clone https://github.com/ZacharyGeurts/Final_Eye.git
cd Final_Eye
pip install -r requirements.txt
./tests/run_tests.sh
./start.sh --no-open
curl -s http://127.0.0.1:9479/api/version
curl -s -X POST http://127.0.0.1:9479/api/robotics/arm -d '{"mode":"war"}'
python3 zocr_watch.py verify
```

## Verify

1. Silent capture — no flash tools on live path
2. On-demand look — no auto frame loop by default
3. War vs dishes modes — `POST /api/robotics/arm`
4. AI tune — `POST /api/video/tune` fps 3–20 combat
5. Code seal — `./tests/run_tests.sh` + `zocr_watch.py verify`
6. 16K preset — `GET /api/grkmf/profiles` → `cinema_16k`

## Sign-off

| Reviewer | Institution | Date | Notes |
|----------|-------------|------|-------|
| Master 1 | | | |
| Master 2 | | | |