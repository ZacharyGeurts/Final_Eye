# Final_Eye 1.0 Security Model

## Codec integrity (GVC1 / GRKMF1)

- **Implemented:** `grkmf.envelope.seal_payload` — 52-byte header + SHA-256 digest.
- **Implemented:** `zocr_security.verify_gvc1_integrity()` — round-trip + tamper rejection.
- **Implemented:** `encrypt_stream_payload` / `decrypt_stream_payload` — AES-GCM when `cryptography` installed; HMAC-sealed fallback.

## Code seal

- All `zocr*.py` and `gui/*.py` hashed into `data/code-seal.json`.
- Protected operations require seal verify unless `ZOCR_MANDATE_OFF=1`.

## Authentication

- HMAC operator tokens: `POST /api/security/token`, verify via `verify_operator_token()`.
- Key derived from `ZOCR_STREAM_KEY` or sovereign-time key material.

## Silent capture policy

- Default: **silent** — no auto stream, no flash.
- On-demand: `look`, `observe`, robotics arm with explicit operator action.
- Documented in `silent_capture_policy()`.

## Honesty covenant

All tester UI and API claims carry labels:

| Label | Meaning |
|-------|---------|
| implemented | Code exists and responds |
| measured | Numeric benchmark or live probe |
| doctrine | Manifest / Field stack policy |
| metaphor | NEXUS/Queen metaphor — not literal hardware |

## Tampering detection

1. GVC1 envelope digest mismatch → reject unpack.
2. Code seal file hash mismatch → `mandate_enforce` blocks protected ops.
3. Stream HMAC / AES-GCM failure → decrypt error.