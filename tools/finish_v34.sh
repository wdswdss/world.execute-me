#!/usr/bin/env bash
# finish v34: swap scene s03 (infinity -> fixed size symbol) into the 4K60 cut.
# v34 = v33_subbed[0:1782] + new s03 segment (888 f = 29.7-44.5s) + v33_subbed[2670:]
# Safe to re-run: only reads v33 finished files + out/_seg_inf_4k.mp4.
set -euo pipefail
cd "$(dirname "$0")/.."

FF="${FFMPEG:-ffmpeg}"
PY="${PYTHON:-python}"
SEG="out/_seg_inf_4k.mp4"
SEGSUB="out/_seg_inf_4k_subbed.mp4"
BASE="out/full_v33_4k60_subbed.mp4"
NEWBASE="out/full_v34_4k60_subbed.mp4"
FINAL="out/world_execute_me_phone_4k60_v34.mp4"

echo "[1/4] subtitles on the new s03 segment (starts at frame 1782)"
PYTHONIOENCODING=utf-8 "$PY" tools/compose_subs.py --base "$SEG" \
  --subs "out/subs_v29_4k/%05d.png" --start-frame 1782 --encoder nvenc \
  --crf 21 --bitrate 18M --maxrate 28M --out "$SEGSUB"
ls -l "$SEGSUB"

echo "[2/4] splice"
"$FF" -y -hide_banner -loglevel warning -i "$BASE" -i "$SEGSUB" \
  -filter_complex "[0:v]trim=start_frame=0:end_frame=1782,setpts=PTS-STARTPTS[a];[1:v]format=yuv420p,setpts=PTS-STARTPTS[b];[0:v]trim=start_frame=2670,setpts=PTS-STARTPTS[c];[a][b][c]concat=n=3:v=1:a=0[out]" \
  -map "[out]" -an -c:v h264_nvenc -preset p7 -tune hq -rc vbr -cq 20 \
  -b:v 18M -maxrate 28M -bufsize 56M -profile:v high -level 5.2 \
  -pix_fmt yuv420p -r 60 -movflags +faststart "$NEWBASE"
ls -l "$NEWBASE"

echo "[3/4] audio"
PYTHONIOENCODING=utf-8 "$PY" tools/mux_sfx.py --video "$NEWBASE" --out "$FINAL"
ls -l "$FINAL"

echo "[4/4] proof frames"
for t in 40.60 40.90 41.20 41.80 43.00 44.40 44.60; do
  "$FF" -y -hide_banner -loglevel error -ss "$t" -i "$FINAL" -frames:v 1 \
    -vf scale=1920:-1 "qa/f34_${t}.png"
done
echo done
