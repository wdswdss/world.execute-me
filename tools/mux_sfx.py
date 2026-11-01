"""Mux video + song + quiet SFX bed into the final phone cut.

Video length may exceed the song (tail hold); both audio inputs are padded.
Usage:
    python tools/mux_sfx.py --video out/full_v26_1080p60.mp4 \
        --out out/world_execute_me_phone_v26.mp4
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from outpath import ensure_parent, ensure_dir  # noqa: E402
from ffbin import ffmpeg_bin  # noqa: E402

FFMPEG = ffmpeg_bin()


def dur(path: str) -> float:
    r = subprocess.run([FFMPEG, "-hide_banner", "-i", path],
                       capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", r.stderr or "")
    if not m:
        raise SystemExit("cannot read duration of " + path)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--song", default=os.path.join(ROOT, "audio", "song.wav"))
    ap.add_argument("--sfx", default=os.path.join(ROOT, "audio", "sfx.wav"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--sfx-gain", type=float, default=1.0)
    args = ap.parse_args()

    total = max(dur(args.video), dur(args.song), dur(args.sfx))
    fc = (f"[1:a]apad[a1];[2:a]volume={args.sfx_gain:.3f},apad[a2];"
          f"[a1][a2]amix=inputs=2:duration=longest:normalize=0[a]")
    ensure_parent(args.out)
    cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "warning",
           "-i", args.video, "-i", args.song, "-i", args.sfx,
           "-filter_complex", fc,
           "-map", "0:v:0", "-map", "[a]",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
           "-ar", "48000", "-ac", "2",
           "-t", f"{total:.3f}", "-movflags", "+faststart", args.out]
    print(f"total {total:.3f}s -> {args.out}")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-4000:])
        raise SystemExit(r.returncode)
    print("wrote", args.out, os.path.getsize(args.out))


if __name__ == "__main__":
    main()
