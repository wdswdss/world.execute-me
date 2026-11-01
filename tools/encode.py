"""Encode / mux the final MV.

Usage (from world-execute-ascii/):
    python tools/encode.py --video out/full_video.mp4 --audio audio/song.wav \
        --out out/world_execute_me.mp4

    # phone-friendly master (default when --phone): re-encodes with x264 high/4.0,
    # yuv420p, crf 21, faststart, AAC 160k
    python tools/encode.py --video out/full_video.mp4 --audio audio/song.wav \
        --out out/world_execute_me_phone.mp4 --phone

    # fast stream-copy mux (no quality change)
    python tools/encode.py --video ... --audio ... --out ... --copy
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ffbin import ffmpeg_bin  # noqa: E402

FFMPEG = ffmpeg_bin()


def _run(cmd):
    print("+", " ".join(cmd))
    return subprocess.run(cmd, capture_output=True, text=True)


def probe(path: str) -> dict:
    """ffprobe is not shipped; parse `ffmpeg -i` stderr instead."""
    r = _run([FFMPEG, "-hide_banner", "-i", path])
    s = r.stderr or ""
    out = {"path": path, "size_mb": os.path.getsize(path) / 1e6 if os.path.exists(path) else 0}
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", s)
    if m:
        out["duration"] = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    m = re.search(r"Video: (\w+) [^,]*, (?:[^,]+, )*?(\d+x\d+)", s)
    if m:
        out["vcodec"], out["size"] = m.group(1), m.group(2)
    m = re.search(r"(\d+(?:\.\d+)?) fps", s)
    if m:
        out["fps"] = float(m.group(1))
    m = re.search(r"bitrate: (\d+) kb/s", s)
    if m:
        out["vbitrate"] = int(m.group(1))
    m = re.search(r"Audio: (\w+) [^,]*, (\d+) Hz, (\w+)", s)
    if m:
        out["acodec"], out["ar"], out["channels"] = m.group(1), int(m.group(2)), m.group(3)
    return out


def mux(video: str, audio: str, out: str, phone: bool, copy: bool,
        crf: int, preset: str, start: float = 0.0, dur: float | None = None) -> dict:
    os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
    cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "warning"]
    if start:
        cmd += ["-ss", f"{start:.3f}"]
    cmd += ["-i", video]
    if start:
        cmd += ["-ss", f"{start:.3f}"]
    cmd += ["-i", audio]
    if dur:
        cmd += ["-t", f"{dur:.3f}"]
    if copy:
        cmd += ["-c:v", "copy"]
    else:
        vf = "scale=1920:1080:flags=lanczos,format=yuv420p"
        cmd += ["-vf", vf, "-c:v", "libx264", "-preset", preset,
                "-crf", str(crf), "-profile:v", "high", "-level", "4.0",
                "-g", "60", "-keyint_min", "30", "-sc_threshold", "0"]
    cmd += ["-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
            "-shortest", "-movflags", "+faststart", out]
    r = _run(cmd)
    if r.returncode != 0:
        print(r.stderr[-4000:])
        raise SystemExit(f"ffmpeg failed ({r.returncode})")
    info = probe(out)
    print(json.dumps(info, indent=2))
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--audio", default=os.path.join(ROOT, "audio", "song.wav"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--phone", action="store_true", help="re-encode for phones (crf21 high/4.0)")
    ap.add_argument("--copy", action="store_true", help="stream copy video, only mux audio")
    ap.add_argument("--crf", type=int, default=21)
    ap.add_argument("--preset", default="medium")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--dur", type=float, default=None)
    args = ap.parse_args()
    if not os.path.exists(args.video):
        raise SystemExit(f"missing video: {args.video}")
    if not os.path.exists(FFMPEG):
        raise SystemExit(f"missing ffmpeg: {FFMPEG}")
    copy = args.copy or (not args.phone)
    mux(args.video, args.audio, args.out, args.phone, copy,
        args.crf, args.preset, args.start, args.dur)


if __name__ == "__main__":
    main()
