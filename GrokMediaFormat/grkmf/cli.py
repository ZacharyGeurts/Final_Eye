#!/usr/bin/env python3
"""GRKMF CLI — encode, verify, benchmark, compare."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from grkmf.compare import compare_summary
from grkmf.container import verify_grkm
from grkmf.movie import benchmark_profiles, decode_movie, export_from_png_dir
from grkmf.spec import load_spec
from grkmf.tune import ai_tune, tune_apply, tune_doctrine, tune_reset


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    cmd = args[0] if args else "spec"
    if cmd == "spec":
        print(json.dumps(load_spec(), indent=2))
        return 0
    if cmd == "compare":
        print(json.dumps(compare_summary(), indent=2))
        return 0
    if cmd == "encode":
        src = args[1] if len(args) > 1 else ""
        out = args[2] if len(args) > 2 else "out.grkm"
        prof = args[3] if len(args) > 3 else "cinema_4k"
        p = Path(src)
        if p.is_dir():
            print(json.dumps(export_from_png_dir(p, out, profile_name=prof), indent=2))
        else:
            from grkmf.movie import encode_movie
            print(json.dumps(encode_movie([p], out, profile_name=prof), indent=2))
        return 0
    if cmd == "decode":
        grkm = args[1] if len(args) > 1 else ""
        out_dir = args[2] if len(args) > 2 else "frames_out"
        print(json.dumps(decode_movie(grkm, out_dir), indent=2))
        return 0
    if cmd == "verify":
        path = args[1] if len(args) > 1 else ""
        print(json.dumps(verify_grkm(Path(path)), indent=2))
        return 0
    if cmd == "tune":
        if len(args) > 1 and args[1] == "reset":
            print(json.dumps(tune_reset(), indent=2))
            return 0
        if len(args) > 1 and args[1] == "doctrine":
            print(json.dumps(tune_doctrine(), indent=2))
            return 0
        body = {}
        for kv in args[1:]:
            if "=" in kv:
                k, v = kv.split("=", 1)
                body[k] = float(v) if "." in v else int(v)
        print(json.dumps(tune_apply(**body), indent=2))
        return 0
    if cmd == "ai-tune":
        load_ms = float(args[1]) if len(args) > 1 else None
        mode = args[2] if len(args) > 2 else None
        print(json.dumps(ai_tune(load_ms=load_ms, mode=mode), indent=2))
        return 0
    if cmd == "benchmark":
        sample = args[1] if len(args) > 1 else ""
        print(json.dumps(benchmark_profiles(sample), indent=2))
        return 0
    print(json.dumps({
        "usage": "python3 -m grkmf.cli [spec|compare|tune|ai-tune|encode|decode|verify|benchmark]",
        "format": "GRKMF1",
        "extension": ".grkm",
    }, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())