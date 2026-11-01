"""Mux a (possibly longer) video with the song, padding audio with silence.

Usage:
    python tools/mux_pad.py --video out/full_v25_4k60.mp4 --audio audio/song.wav \
        --out out/world_execute_me_phone_4k60.mp4
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ffbin import ffmpeg_bin  # noqa: E402

FFMPEG = ffmpeg_bin()


def probe_duration(path: str) -> float:
    r = subprocess.run([FFMPEG, "-hide_banner", "-i", path],
                       capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", r.stderr or "")
    if not m:
        raise SystemExit("cannot read duration of " + path)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    vdur = probe_duration(args.video)
    adur = probe_duration(args.audio)
    total = max(vdur, adur)
    cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "warning",
           "-i", args.video, "-i", args.audio,
           "-map", "0:v:0", "-map", "1:a:0",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
           "-ar", "48000", "-ac", "2", "-af", "apad",
           "-t", f"{total:.3f}", "-movflags", "+faststart", args.out]
    print(f"video {vdur:.3f}s audio {adur:.3f}s -> {total:.3f}s")
    print("+", " ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-4000:])
        raise SystemExit(r.returncode)
    print("wrote", args.out, os.path.getsize(args.out))


if __name__ == "__main__":
    main()
