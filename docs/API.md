# API — Final_Eye 0.9

Base: `http://127.0.0.1:9479`

- `GET /api/version` — product metadata
- `GET /api/robotics` — robotics context
- `POST /api/robotics/arm` — `{"mode":"war|dishes"}`
- `POST /api/look` — silent capture
- `POST /api/video/tune` — AI fps/resolution
- `GET /api/stream/mjpeg?profile=watch`
- `GET /api/eye/final` — Final Eyeball status