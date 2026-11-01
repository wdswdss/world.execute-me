"""Fixed logical grid for the whole MV.

The engine always draws into a 192 x 60 character grid.  Every renderer
(video at 1920x1080 via 10x18 px cells, terminal at any size by sub-sampling)
consumes the same grid, so scene code never worries about output resolution.

Zone map (rows):
   0      header bar            (program chrome, English only)
   1      header rule
   2..46  STAGE  (45 rows)      <- all scene animation happens here
   47     stage rule
   48..52 SUBTITLE strip (5 rows: EN line + CN line, fixed reading area)
   53     spectrum ruler
   54..59 SPECTRUM band (6 rows, thin strip at the bottom)
"""
COLS = 192
ROWS = 60

import os as _os

# 1 = 1920x1080, 2 = 3840x2160 (cells double, same 192x60 grid)
SCALE = int(_os.environ.get("MV_SCALE", "1") or 1)

CELL_W = 10 * SCALE
CELL_H = 18 * SCALE
PX_W = COLS * CELL_W   # 1920 / 3840
PX_H = ROWS * CELL_H   # 1080 / 2160

HEADER_Y = 0
HEADER_RULE_Y = 1
STAGE_X = 0
STAGE_Y = 2
STAGE_W = COLS
STAGE_H = 45            # rows 2..46 inclusive
STAGE_BOTTOM = STAGE_Y + STAGE_H - 1
STAGE_RULE_Y = 47
SUB_Y = 48
SUB_H = 8
SUB_EN_ROW = 50
SUB_CN_ROW = 53
SUB_RULE_Y = 48
FOOT_Y = 56
FOOT_H = 4

FPS = 60

# extra seconds held on the final sentence after the music has ended
TAIL_HOLD = 4.0
DURATION = 211.905 + TAIL_HOLD


def px_of_cell(col, row):
    return col * CELL_W, row * CELL_H


def cell_of_px(x, y):
    return int(x) // CELL_W, int(y) // CELL_H
