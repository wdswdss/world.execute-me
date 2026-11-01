# 常用命令。Windows 上没装 make 的话，直接照抄下面每行的命令。
PY      ?= python
WORKERS ?= 8
SCALE   ?= 1
CRF     ?= 17
FFMPEG  ?= ffmpeg

.PHONY: help setup assets still sheet render subs final cover check clean

help:
	@echo "make setup     # pip install -r requirements.txt"
	@echo "make still     # 单帧 1080p（T=41.8）"
	@echo "make sheet     # 21 场景拼图"
	@echo "make render    # 1080p 无声整片 -> out/video.mp4"
	@echo "make subs      # 字幕 PNG 序列 -> out/subs/"
	@echo "make final     # 烧字幕 + 混音 -> out/final.mp4"
	@echo "make cover     # 16:9 + 4:3 封面 -> out/"
	@echo "make check     # 全片抽样冒烟检查"
	@echo "make clean     # 清掉产物（保留 out/ 里的成片）"

setup:
	$(PY) -m pip install -r requirements.txt

assets:
	$(PY) tools/build_assets.py

still:
	MV_SCALE=$(SCALE) $(PY) tools/still.py --t 41.8 --out out/still.png

sheet:
	MV_SCALE=1 $(PY) tools/still.py --scene all --n 1 --sheet out/sheet.png --cols 4 --scale 0.30

render:
	MV_SCALE=$(SCALE) $(PY) tools/render.py --workers $(WORKERS) --crf $(CRF) --out out/video.mp4

subs:
	MV_SCALE=$(SCALE) $(PY) tools/render_subs.py --outdir out/subs

final:
	MV_SCALE=$(SCALE) $(PY) tools/compose_subs.py --base out/video.mp4 \
	  --subs "out/subs/%05d.png" --start-frame 0 --out out/video_subbed.mp4
	$(PY) tools/mux_sfx.py --video out/video_subbed.mp4 --out out/final.mp4

cover:
	MV_SCALE=1 $(PY) tools/cover_aspect.py --aspect 16x9 --out out/cover_16x9
	MV_SCALE=1 $(PY) tools/cover_aspect.py --aspect 4x3  --out out/cover_4x3

check:
	$(PY) tools/check_timeline.py --stride 97

clean:
	rm -rf out/subs out/_seg_*.mp4 out/*.png out/sheet.png out/still*.png
	rm -rf engine/__pycache__ engine/scenes/__pycache__ tools/__pycache__
