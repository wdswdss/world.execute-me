#!/usr/bin/env bash
# finish v33: splice new title segment into the 4K base, composite subtitles,
# mux audio, then extract proof frames. Safe to re-run.
set -euo pipefail
cd "$(dirname "$0")/.."

FF="${FFMPEG:-ffmpeg}"
PY="${PYTHON:-python}"
SEG="out/_seg_title_4k7.mp4"
BASE="out/full_v29_4k60_base.mp4"
NEWBASE="out/full_v33_4k60_base.mp4"
SUBBED="out/full_v33_4k60_subbed.mp4"
FINAL="out/world_execute_me_phone_4k60_v33.mp4"

echo "[1/4] splice"
"$FF" -y -hide_banner -loglevel warning -i "$BASE" -i "$SEG" \
  -filter_complex "[0:v]trim=start_frame=0:end_frame=894,setpts=PTS-STARTPTS[a];[1:v]format=yuv420p,setpts=PTS-STARTPTS[b];[0:v]trim=start_frame=1788,setpts=PTS-STARTPTS[c];[a][b][c]concat=n=3:v=1:a=0[out]" \
  -map "[out]" -an -c:v h264_nvenc -preset p7 -tune hq -rc vbr -cq 20 \
  -b:v 18M -maxrate 28M -bufsize 56M -profile:v high -level 5.2 \
  -pix_fmt yuv420p -r 60 -movflags +faststart "$NEWBASE"
ls -l "$NEWBASE"

echo "[2/4] subtitles"
PYTHONIOENCODING=utf-8 "$PY" tools/compose_subs.py --base "$NEWBASE" \
  --subs "out/subs_v29_4k/%05d.png" --start-frame 0 --encoder nvenc \
  --crf 21 --bitrate 18M --maxrate 28M --out "$SUBBED"

echo "[3/4] audio"
PYTHONIOENCODING=utf-8 "$PY" tools/mux_sfx.py --video "$SUBBED" --out "$FINAL"
ls -l "$FINAL"

echo "[4/4] proof frames"
for t in 20.80 21.40 22.00 22.60 23.40 24.40 26.50; do
  "$FF" -y -hide_banner -loglevel error -ss "$t" -i "$FINAL" -frames:v 1 \
    -vf scale=1920:-1 "qa/f32_${t}.png"
done
echo "done"
