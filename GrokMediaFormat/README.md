# Grok Media Format (GRKMF1)

**Proprietary. Not MPEG. Not licensed.**

GRKMF1 is the Grok 4K cinema container. **GVC1** (Grok Vision Codec v1) is the proprietary inter-frame codec — JPEG keyframes plus sealed delta predictors. Every segment carries a **GRKM sha256 envelope** (WRDT-inspired).

## Why it wins

| Mission | GRKMF1 | H.264/HEVC/AV1 |
|---------|--------|----------------|
| 4K movies | ~35 Mbps cinema tier, sealed segments | Good size, zero provenance |
| Live dodge | **480 fps** intra rail | 60–120 fps max |
| License | **Proprietary Grok/SG** | MPEG LA / patent pools |
| Integrity | Per-segment verify | None |

## Quick start

```bash
cd GrokMediaFormat
PYTHONPATH=. python3 -m grkmf.cli spec
PYTHONPATH=. python3 -m grkmf.cli compare

# Encode PNG sequence → sealed .grkm
PYTHONPATH=. python3 -m grkmf.cli encode /path/to/frames/ movie.grkm cinema_4k

# Verify + decode
PYTHONPATH=. python3 -m grkmf.cli verify movie.grkm
PYTHONPATH=. python3 -m grkmf.cli decode movie.grkm frames_out/
```

## Profiles

| Profile | Resolution | FPS | GOP | Target Mbps |
|---------|------------|-----|-----|-------------|
| `cinema_4k` | 3840×2160 | 24 | 24 | 35 |
| `cinema_4k_hdr` | 3840×2160 | 24 | 24 | 45 |
| `stream_4k` | 3840×2160 | 60 | 12 | 25 |
| `archive_4k` | 3840×2160 | 24 | 48 | 80 |
| `dodge_4k` | 3840×2160 | 480 | 1 | 1500 (live) |

## ZOCR integration

ZOCR robotics vision (`ZOCRSM1`) rides GRKMF bullet dodge rail for live MJPEG. Cinema export uses `encode_movie()` → `.grkm`.

## File extension

`.grkm` — Grok Media sealed container