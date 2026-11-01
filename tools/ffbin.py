"""Locate the ffmpeg / ffprobe binaries.

Order:
    1. $FFMPEG / $FFPROBE
    2. the bundled copy next to this repo (../world-execute-her/tools/ffmpeg/), if any
    3. PATH

Every tool imports `ffmpeg_bin()` instead of hard-coding a path, so the repo runs
on Windows / Linux / macOS without edits.
"""
from __future__ import annotations

import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BUNDLED_DIR = os.path.join(os.path.dirname(ROOT), "world-execute-her", "tools", "ffmpeg")

_HINT = (
    "ffmpeg not found. Install it on PATH (Windows: winget install ffmpeg / "
    "choco install ffmpeg; macOS: brew install ffmpeg; Debian/Ubuntu: apt install ffmpeg) "
    "or set FFMPEG=/path/to/ffmpeg. See docs/RENDERING.md, Troubleshooting."
)


def _pick(env_key: str, names: tuple[str, ...], fallback: str) -> str:
    env = os.environ.get(env_key)
    if env:
        return env
    for name in names:
        for cand in (os.path.join(_BUNDLED_DIR, name), os.path.join(_BUNDLED_DIR, name + ".exe")):
            if os.path.exists(cand):
                return cand
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    # 不在这里退出：--help / 只出静帧都不需要 ffmpeg。
    # 真要用的时候 subprocess 会报 FileNotFoundError，提示见 docs/RENDERING.md 故障排查。
    print("warning: " + _HINT, file=sys.stderr)
    return fallback


def ffmpeg_bin() -> str:
    return _pick("FFMPEG", ("ffmpeg",), "ffmpeg")


def ffprobe_bin() -> str:
    return _pick("FFPROBE", ("ffprobe",), "ffprobe")


if __name__ == "__main__":
    print("ffmpeg :", ffmpeg_bin())
    print("ffprobe:", ffprobe_bin())
