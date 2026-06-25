"""Grok Media Format — GRKMF1 proprietary 4K cinema. Not MPEG."""
from grkmf.compare import compare_summary, market_table
from grkmf.container import read_grkm, verify_grkm, write_grkm
from grkmf.envelope import seal_payload, unpack_envelope, verify_file
from grkmf.movie import benchmark_profiles, decode_movie, encode_movie, export_from_png_dir
from grkmf.spec import CODEC_ID, FORMAT_ID, MAGIC, bullet_profile, load_spec, profile, profiles
from grkmf.tune import active_tune, ai_tune, resolve, tune_apply, tune_doctrine, tune_reset
from grkmf.stream import (
    BulletRail,
    bullet_mjpeg_generator,
    bullet_pace,
    list_profiles,
    mjpeg_packet,
    png_to_jpeg,
    resize_max,
)

__all__ = [
    "FORMAT_ID",
    "CODEC_ID",
    "MAGIC",
    "load_spec",
    "profiles",
    "profile",
    "bullet_profile",
    "seal_payload",
    "unpack_envelope",
    "verify_file",
    "write_grkm",
    "read_grkm",
    "verify_grkm",
    "encode_movie",
    "decode_movie",
    "export_from_png_dir",
    "benchmark_profiles",
    "compare_summary",
    "market_table",
    "BulletRail",
    "bullet_mjpeg_generator",
    "bullet_pace",
    "mjpeg_packet",
    "png_to_jpeg",
    "resize_max",
    "list_profiles",
    "resolve",
    "tune_apply",
    "tune_reset",
    "active_tune",
    "ai_tune",
    "tune_doctrine",
]

__version__ = "1.0.0"