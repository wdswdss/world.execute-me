#!/usr/bin/env python
"""Composite the subtitle layer (qtrle RGBA .mov) over the subtitle-free base.

Usage:
  python tools/compose_subs.py --base out/full_v28_base.mp4 \
      --subs out/subs_v28.mov --out out/full_v28_subbed.mp4
"""
import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from outpath import ensure_parent, ensure_dir  # noqa: E402
from ffbin import ffmpeg_bin  # noqa: E402

FFMPEG = ffmpeg_bin()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--subs", required=True,
                    help="PNG sequence pattern, e.g. out/subs_v28/%%05d.png")
    ap.add_argument("--out", required=True)
    ap.add_argument("--start-frame", type=int, default=0,
                    help="first frame number encoded in the PNG file names")
    ap.add_argument("--crf", type=int, default=21)
    ap.add_argument("--preset", default="faster")
    ap.add_argument("--encoder", default="libx264",
                    choices=["libx264", "nvenc"],
                    help="libx264 = software (slow, best quality); nvenc = GPU")
    ap.add_argument("--bitrate", default="20M",
                    help="target bitrate for nvenc (ignored by libx264)")
    ap.add_argument("--maxrate", default="28M", help="nvenc max bitrate")
    args = ap.parse_args()

    if args.encoder == "nvenc":
        enc = ["-c:v", "h264_nvenc", "-preset", "p7", "-tune", "hq",
               "-rc", "vbr", "-cq", str(args.crf),
               "-b:v", args.bitrate, "-maxrate", args.maxrate,
               "-bufsize", "56M", "-profile:v", "high", "-level", "5.2"]
    else:
        enc = ["-c:v", "libx264", "-preset", args.preset, "-crf", str(args.crf),
               "-profile:v", "high", "-level", "4.1"]

    ensure_parent(args.out)
    cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "warning",
           "-i", args.base,
           "-framerate", "60", "-start_number", str(args.start_frame),
           "-i", args.subs,
           "-filter_complex",
           "[0:v]format=rgb24[bg];[bg][1:v]overlay=0:0:shortest=1,format=yuv420p[v]",
           "-map", "[v]", "-an"] + enc + [
           "-pix_fmt", "yuv420p", "-r", "60", "-movflags", "+faststart", args.out]
    print("+", " ".join(cmd))
    r = subprocess.run(cmd)
    if r.returncode != 0:
        raise SystemExit(r.returncode)
    print("wrote", args.out, os.path.getsize(args.out))


if __name__ == "__main__":
    main()
