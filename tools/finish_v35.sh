#!/usr/bin/env bash
# v35: multilingual counting line in the subtitle strip (2:39-2:41)
#   only the affected 220 frames are re-rendered / re-subtitled, then spliced
#   back into the v34 master; audio is re-muxed unchanged.
set -euo pipefail
cd "$(dirname "$0")/.."

FF="${FFMPEG:-ffmpeg}"
PY="${PYTHON:-python}"

A=9530          # first re-made frame  (t = 158.8333)
B=9750          # first untouched frame after it (t = 162.5)
SRC="out/full_v34_4k60_subbed.mp4"
SEG="out/_seg_lyr_subbed.mp4"
OUT="out/full_v35_4k60_subbed.mp4"

echo "== 1/3 splice =="
"$FF" -y -hide_banner -loglevel warning \
  -i "$SRC" -i "$SEG" \
  -filter_complex "[0:v]trim=start_frame=0:end_frame=$A,setpts=PTS-STARTPTS[a];\
[1:v]format=yuv420p,setpts=PTS-STARTPTS[b];\
[0:v]trim=start_frame=$B,setpts=PTS-STARTPTS[c];\
[a][b][c]concat=n=3:v=1:a=0[out]" \
  -map "[out]" -an \
  -c:v h264_nvenc -preset p7 -tune hq -rc vbr -cq 20 \
  -b:v 18M -maxrate 28M -bufsize 56M -profile:v high -level 5.2 \
  -pix_fmt yuv420p -r 60 -movflags +faststart \
  "$OUT"
ls -l "$OUT"

echo "== 2/3 mux audio =="
"$PY" tools/mux_sfx.py --video "$OUT" --out out/world_execute_me_phone_4k60_v35.mp4
ls -l out/world_execute_me_phone_4k60_v35.mp4

echo "== 3/3 proof frames =="
for t in 158.70 159.60 161.50 162.40 163.50; do
  "$FF" -y -hide_banner -loglevel error -ss "$t" -i out/world_execute_me_phone_4k60_v35.mp4 \
    -frames:v 1 "qa/f35_$t.png"
done
echo "done"
