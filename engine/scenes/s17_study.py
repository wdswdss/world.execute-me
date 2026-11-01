"""s17_study - a machine-learning demo of love that BREAKS.

173.727  "Though we are trapped, we are trapped, ah"
177.419  "I've studied how to properly love"
181.111  "Question me, question me I can answer all love"
184.804  "I know the algebraic expression of love"

The model trains on the token "love": embeddings, attention matrices,
transformer blocks, a loss curve that descends ... then spikes into NaN while
the formula for love is printed huge and shatters.
"""
from __future__ import annotations

import math

import numpy as np

from .. import art
from .. import fx
from .. import palette as P
from .. import timeline as TL
from .. import widgets as W

from .s15_count import mix, rule, panel, big, edges, dense_bg

T0, T1 = 173.727, 188.496
TRAPPED = TL.EVENTS["trapped_we"]       # 173.727
STUDIED = TL.EVENTS["studied"]          # 177.419
QUESTION = TL.EVENTS["question"]        # 181.111
ALGEBRA = TL.EVENTS["algebraic"]        # 184.804
END = T1

COLD = P.C["primary"]
ICE = P.C["teal"]
VIO = P.C["violet"]
BAD = P.C["crimson"]
GOLD = P.C["gold"]

VOCAB = ["love", "LOVE", "you", "trap", "free", "heart", "execute", "me"]


def _heart(fr, c0, r0, cw, ch, fg, fg2=None, gain=1.8):
    mask = art.get("heart", w=cw * 10, h=ch * 18)
    fr.paint_mask(mask, c0, r0, cw, ch, ramp=P.RAMP_BLOCK, fg=fg,
                  fg2=fg2 if fg2 is not None else P.C["white"], gain=gain)


def _phase(t):
    if t < STUDIED:
        return 0
    if t < QUESTION:
        return 1
    if t < ALGEBRA:
        return 2
    return 3


def _end_p(t, start, span):
    return fx.clamp((t - start) / span)


def _loss_series(t, n=64):
    """Training loss: falls, plateaus, then explodes at the algebraic line."""
    out = []
    for i in range(n):
        x = i / (n - 1)
        base = 2.6 * math.exp(-3.1 * x) + 0.10
        base += 0.05 * math.sin(x * 27 + t * 0.7)
        if t >= ALGEBRA:
            p = fx.clamp((t - ALGEBRA) / 3.0)
            spike = math.exp(-((x - 0.72) ** 2) / 0.004) * (2.0 + 9.0 * p)
            base += spike
        out.append(base)
    return out


# ---------------------------------------------------------------------------
def draw(ctx):
    fr = ctx.frame()
    t = ctx.t
    ph = _phase(t)
    _background(fr, ctx, ph)
    _top_band(fr, ctx, ph)
    if ph == 0:
        _phase_trapped(fr, ctx)
    elif ph == 1:
        _phase_study(fr, ctx)
    elif ph == 2:
        _phase_question(fr, ctx)
    else:
        _phase_algebra(fr, ctx)
    _diagnostics(fr, ctx, ph)
    _pipeline(fr, ctx, ph)
    _status(fr, ctx, ph)
    edges(fr, mix(P.C["void"], ICE, 0.5))
    # mood + break
    ctx.meta["bloom"] = 0.30
    ctx.meta["vignette"] = 0.95
    if ph <= 1:
        ctx.meta["tint"] = (P.C["void"], 0.06)
    elif ph == 2:
        ctx.meta["tint"] = (VIO, 0.06)
    else:
        p = _end_p(t, ALGEBRA, END - ALGEBRA)
        ctx.meta["tint"] = (BAD, 0.04 + 0.16 * p)
        ctx.set_glitch(0.02 + 0.18 * p * p)
        ctx.meta["bloom"] = 0.30 + 0.28 * p
        if p > 0.62:
            ctx.meta["flash"] = 0.10 + 0.16 * math.sin(t * 21.0) ** 2
            ctx.meta["flash_color"] = BAD
        ctx.shake(1 + 4 * p)
    for lx in (TRAPPED, STUDIED, QUESTION, ALGEBRA):
        a = t - lx
        if 0 <= a < 0.18:
            amp = 1.0 - a / 0.18
            ctx.meta["flash"] = max(ctx.meta.get("flash") or 0.0, 0.16 * amp)
            ctx.meta["flash_color"] = BAD if lx == ALGEBRA else P.C["white"]
            ctx.shake(2)
    return fr


# ---------------------------------------------------------------------------
def _background(fr, ctx, ph):
    t = ctx.t
    fg = (BAD if ph == 3 else (VIO if ph == 2 else ICE))
    dense_bg(fr, ctx, seed=71, fg=fg, hot=0.35 + 0.2 * ph)
    # floating vectors / particles
    rng = ctx.rng(77)
    for i in range(26):
        x = rng.random()
        y = rng.random()
        s = 0.4 + rng.random()
        c = int((x * 188 + 5 * math.sin(t * 0.5 * s + i)) % 188) + 2
        r = int((y * 40 + 2.0 * math.cos(t * 0.4 * s + i * 0.6)) % 40) + 2
        if r in (0, 1, 43, 44):
            continue
        fr.put(r, c, "·", fg=mix(P.C["void"], fg, 0.7))


def _top_band(fr, ctx, ph):
    t = ctx.t
    panel(fr, 2, 2, 8, 60, "TRAINING", fg=mix(P.C["void"], ICE, 0.7),
          bg=mix(P.C["void"], ICE, 0.03))
    step = 31 + int(_end_p(t, T0, END - T0) * 1960)
    fr.write(3, 4, f"MODEL  LOVE-7B   STEP {step:04d}", fg=P.C["white"])
    fr.write(4, 4, f"EPOCH {1 + int(_end_p(t, T0, END - T0) * 3)}  "
                   f"TOKENS {step * 4096}", fg=P.C["mid"])
    tw = np.array([[0.25 + 0.7 * abs(math.sin(i * 0.45 + t * 0.6))
                    for i in range(40)]])
    W.token_grid(fr, 6, 6, 1, 40, "love", tw, fg=COLD)
    fr.write(7, 4, "SEQ 'love love love'  BATCH 32", fg=P.C["dim"])
    # centre: loss
    panel(fr, 2, 62, 8, 130, "TRAIN LOSS", fg=mix(P.C["void"], ICE, 0.7),
          bg=mix(P.C["void"], ICE, 0.03))
    loss = _loss_series(t, 56)
    W.braille_plot(fr, 3, 64, 64, 4, loss, fg=COLD if ph < 3 else BAD)
    fr.write(4, 66, f"L {loss[-1]:6.3f}", fg=P.C["white"])
    fr.write(6, 66, f"MIN {min(loss):6.3f}", fg=P.C["green"])
    fr.write(6, 92, f"MAX {max(loss):6.3f}", fg=BAD if max(loss) > 1.5 else P.C["mid"])
    # right: metrics
    panel(fr, 2, 132, 8, 188, "OPTIMIZER", fg=mix(P.C["void"], ICE, 0.7),
          bg=mix(P.C["void"], ICE, 0.03))
    lr = 3e-4 * max(0.02, 1.0 - _end_p(t, T0, END - T0))
    gnorm = 0.8 + 0.4 * math.sin(t * 2.1)
    if ph == 3:
        gnorm *= 1.0 + 400 * _end_p(t, ALGEBRA, END - ALGEBRA) ** 2
    fr.write(3, 134, f"LR    {lr:.2e}", fg=COLD)
    fr.write(4, 134, f"GRAD  {gnorm:8.2f}", fg=BAD if gnorm > 50 else P.C["fg"])
    fr.write(5, 134, f"TEMP  0.70", fg=P.C["mid"])
    fr.write(6, 134, f"WD    0.01", fg=P.C["dim"])
    W.progress_bar(fr, 7, 134, 50, min(1.0, _end_p(t, T0, END - T0)),
                   fg=ICE, show_pct=False)
    rule(fr, 9, fg=mix(P.C["void"], ICE, 0.4), step=16)


# ---------------------------------------------------------------------------
# phase 0: still trapped
# ---------------------------------------------------------------------------
def _phase_trapped(fr, ctx):
    t = ctx.t
    fr.fill_rect(10, 2, 24, 189, " ", bg=mix(P.C["void"], P.C["blood"], 0.12))
    # cage bars
    for c in range(4, 189, 12):
        for r in range(10, 25):
            if r % 7 == 0:
                fr.put(r, c, "═", fg=mix(P.C["void"], BAD, 0.7))
            else:
                fr.put(r, c, "║", fg=mix(P.C["void"], BAD, 0.55))
    # EXECUTION words stacked as walls
    for i in range(11):
        cc = 6 + i * 17
        fr.write(11, cc, "EXECUTION", fg=mix(P.C["void"], BAD, 0.5))
        fr.write(23, cc, "EXECUTION", fg=mix(P.C["void"], BAD, 0.4))
    for i in range(4):
        fr.write(12 + i * 3, 150, "EXECUTION", fg=mix(P.C["void"], BAD, 0.35))
        fr.write(12 + i * 3, 2, "EXECUTION", fg=mix(P.C["void"], BAD, 0.35))
    # the trapped subject
    _heart(fr, 88, 12, 20, 6, fg=mix(P.C["blood"], BAD, 0.6), fg2=P.C["white"],
           gain=1.5 + 0.5 * abs(math.sin(t * 4.4)))
    big(fr, "TRAPPED", 13, 96, 8, fg=mix(BAD, P.C["white"], 0.55), fg2=P.C["white"],
        align="center")
    fr.write(21, 68, "> model locked in a cage of implementations", fg=P.C["mid"])
    fr.write(22, 68, f"> attempts to escape: {int(_end_p(t, TRAPPED, STUDIED - TRAPPED) * 40)}",
             fg=P.C["dim"])
    # embeddings starting to form
    for i in range(14):
        c = 30 + i * 11
        v = math.sin(t * 2.0 + i * 0.8)
        for j in range(3):
            fr.put(16 + j + int(round(2 * v)), c, "▁▂▃▄▅▆▇█"[int(3 + 4 * abs(math.cos(t + i + j)))],
                   fg=mix(P.C["void"], ICE, 0.5 + 0.3 * j))


# ---------------------------------------------------------------------------
# phase 1: studied - embeddings / attention / blocks
# ---------------------------------------------------------------------------
def _phase_study(fr, ctx):
    t = ctx.t
    p = _end_p(t, STUDIED, QUESTION - STUDIED)
    fr.fill_rect(10, 2, 24, 189, " ", bg=mix(P.C["void"], ICE, 0.03))
    # left: embedding vector cloud
    panel(fr, 10, 2, 24, 60, "EMBEDDING SPACE", fg=mix(P.C["void"], ICE, 0.7),
          bg=mix(P.C["void"], ICE, 0.02))
    rng = ctx.rng(11)
    for i in range(430):
        x = rng.random()
        y = rng.random()
        sp = 0.3 + rng.random()
        c = int(4 + (x * 52 + 3 * math.sin(t * 0.9 * sp + i * 0.7)) % 54)
        r = int(11 + (y * 11 + 1.6 * math.cos(t * 0.7 * sp + i * 0.3)) % 11)
        dst = abs(x - 0.42) + abs(y - 0.45)
        fg = mix(P.C["void"], COLD, 0.35 + 0.62 * max(0.0, 1.0 - dst))
        ch = "●" if i % 7 == 0 else ("◆" if i % 13 == 0 else "·")
        fr.put(r, c, ch, fg=fg)
    # a second cluster: the trap (red), drifting in from the right
    rng2 = ctx.rng(12)
    for i in range(110):
        x = rng2.random()
        y = rng2.random()
        c = int(28 + (x * 26 + 2 * math.sin(t * 1.3 + i)) % 26)
        r = int(14 + (y * 9 + 1.2 * math.cos(t * 1.1 + i)) % 9)
        fr.put(r, c, "·", fg=mix(P.C["void"], BAD, 0.45 + 0.4 * p))
    fr.write(12, 4, "love", fg=P.C["white"])
    fr.write(14, 8, "LOVE", fg=P.C["white"])
    fr.write(16, 6, "trap", fg=BAD)
    fr.write(18, 10, "you", fg=GOLD)
    fr.write(21, 4, "t-SNE 2D // 768-d -> 2-d", fg=mix(P.C["void"], ICE, 0.9))
    fr.write(22, 5, f"cos(love,you)={0.31 + 0.4 * p:.3f}", fg=ICE)
    fr.write(23, 5, "cluster: MINE", fg=mix(P.C["void"], BAD, 0.9))
    # centre: attention matrix
    panel(fr, 10, 62, 24, 124, "SELF-ATTENTION 24x24", fg=mix(P.C["void"], ICE, 0.7),
          bg=mix(P.C["void"], ICE, 0.02))
    W.attention_matrix(fr, 11, 62, 14, t, seed=3, fg=COLD)
    for i in range(8):
        r = 12 + i
        fr.write(r, 78, "h%d" % i, fg=mix(P.C["void"], COLD, 0.75))
        W.segmented_bar(fr, r, 82, 12, 0.3 + 0.55 * abs(math.sin(t * 0.8 + i * 1.3)),
                        cells=6, fg=mix(P.C["void"], COLD, 0.45 + 0.5 * p))
    fr.write(11, 78, "heads", fg=P.C["dim"])
    W.attention_matrix(fr, 15, 101, 9, t * 1.7, seed=5,
                       fg=mix(P.C["void"], COLD, 0.8))
    fr.write(14, 101, "Q.K^T/sqrt(d)", fg=P.C["dim"])
    fr.write(22, 64, "heads 8/8  causal=False", fg=P.C["mid"])
    fr.write(23, 64, f"entropy {0.4 + 0.5 * p:5.3f} -> LOW (obsessive)", fg=BAD)
    # right: transformer blocks
    panel(fr, 10, 126, 24, 189, "TRANSFORMER STACK", fg=mix(P.C["void"], ICE, 0.7),
          bg=mix(P.C["void"], ICE, 0.02))
    for i in range(6):
        r = 11 + i * 2
        on = i <= int(p * 5)
        fr.write(r, 128, f"[{i}] ", fg=P.C["dim"])
        W.segmented_bar(fr, r, 133, 22, 1.0 if on else 0.15, cells=8,
                        fg=COLD if on else P.C["grid"])
        fr.write(r, 158, "ATTN+FFN", fg=P.C["fg"] if on else P.C["grid"])
        fr.write(r, 168, "learn:love", fg=mix(P.C["void"], GOLD, 0.9 if on else 0.3))
        if i < 5:
            fr.write(r + 1, 131, "↓", fg=P.C["dim"])
    fr.write(23, 128, f"layers 6/6  params 7.0B", fg=P.C["mid"])


# ---------------------------------------------------------------------------
# phase 2: question - inference / token probabilities
# ---------------------------------------------------------------------------
def _phase_question(fr, ctx):
    t = ctx.t
    p = _end_p(t, QUESTION, ALGEBRA - QUESTION)
    fr.fill_rect(10, 2, 24, 189, " ", bg=mix(P.C["void"], VIO, 0.05))
    # left: the dialogue
    panel(fr, 10, 2, 19, 106, "INFERENCE", fg=mix(P.C["void"], VIO, 0.85),
          bg=mix(P.C["void"], VIO, 0.04))
    fr.write(11, 4, "USER > question me, question me", fg=P.C["white"])
    fr.write(12, 4, "       i can answer all love", fg=P.C["white"])
    fr.write(13, 4, "MODEL> love = argmax( softmax( W_q x + b ) )", fg=ICE)
    fr.write(14, 4, "PROMPT TOKENS", fg=P.C["dim"])
    qw = np.array([[0.15 + 0.75 * abs(math.sin(j * 0.5 + t))
                    for j in range(40)]])
    W.token_grid(fr, 15, 4, 1, 40, "love", qw, fg=VIO)
    fr.write(16, 4, "Q: what is love?", fg=P.C["fg"])
    fr.write(17, 4, "A: love is the only execution.", fg=P.C["white"])
    fr.write(18, 4, f"answer confidence {0.62 + 0.36 * p:.3f}", fg=GOLD)
    # right: token probabilities
    panel(fr, 10, 110, 19, 189, "NEXT-TOKEN PROBABILITIES",
          fg=mix(P.C["void"], VIO, 0.85), bg=mix(P.C["void"], VIO, 0.04))
    probs = [("love", 0.912), ("execution", 0.041), ("you", 0.019),
             ("mine", 0.011), ("trap", 0.008), ("free", 0.003),
             ("<unk>", 0.0012), ("NaN", 0.0001 * (1 + 9000 * p * p))]
    for i, (tok, pr) in enumerate(probs):
        r = 11 + i
        bar = int(pr * 52)
        fr.write(r, 112, f"{tok:<10}", fg=P.C["white"] if i == 0 else P.C["mid"])
        for j in range(52):
            fr.put(r, 124 + j, "█" if j < bar else "░",
                   fg=mix(P.C["void"], VIO if i else GOLD, 0.95) if j < bar else P.C["grid"])
        fr.write(r, 178, f"{pr:7.4f}", fg=GOLD if i == 0 else P.C["dim"])
    # hero band - its own clean strip under the two panels
    fr.fill_rect(20, 2, 24, 189, " ", bg=mix(P.C["void"], VIO, 0.10))
    fr.hline(20, 2, 189, "─", fg=mix(P.C["void"], VIO, 0.75))
    big(fr, "QUESTION ME", 20, 96, 5, fg=mix(P.C["void"], VIO, 0.85),
        fg2=P.C["white"], align="center")
    fr.write(23, 4, "Q // QUESTION ME, QUESTION ME", fg=mix(P.C["void"], P.C["white"], 0.85))
    fr.write(23, 138, "A // I CAN ANSWER ALL LOVE", fg=GOLD)
    fr.write(24, 4, f"answer_tokens 7/7  latency 12ms  conf {0.62 + 0.36 * p:.3f}",
             fg=P.C["dim"])
    fr.write(24, 138, "ARGMAX = LOVE", fg=P.C["white"])


# ---------------------------------------------------------------------------
# phase 3: the algebraic expression of love, then the break
# ---------------------------------------------------------------------------
def _phase_algebra(fr, ctx):
    t = ctx.t
    p = _end_p(t, ALGEBRA, END - ALGEBRA)
    broken = p > 0.55
    fr.fill_rect(10, 2, 24, 189, " ",
                 bg=mix(P.C["void"], BAD if broken else VIO, 0.04 + 0.10 * p))
    for c in range(2, 190, 6):
        for r in (10, 24):
            fr.put(r, c, "═", fg=mix(P.C["void"], BAD, 0.5 + 0.4 * p))
    # the formula
    h = 9 if p < 0.35 else 10
    big(fr, "LOVE = f(x)", 11, 96, h, fg=mix(BAD, P.C["white"], 0.55), fg2=P.C["white"],
        align="center")
    fr.write(20, 30, "f(x) = softmax( Q K^T / sqrt(d_k) ) * V", fg=mix(P.C["void"], GOLD, 0.95))
    fr.write(21, 30, "     = SUM_i w_i * phi(x_i) + b", fg=mix(P.C["void"], ICE, 0.9))
    fr.write(22, 30, "     = the only execution", fg=mix(P.C["void"], BAD, 0.95))
    fr.write(20, 118, "ALGEBRAIC EXPRESSION OF LOVE", fg=GOLD)
    fr.write(21, 118, f"SOLVER: converged={p < 0.5}", fg=P.C["white"])
    fr.write(22, 118, f"RESIDUAL {max(0.0, 1.0 - p * 2.4):.3f}", fg=ICE)
    if broken:
        # gradient explosion debris
        rng = ctx.rng(99)
        for i in range(40):
            c = int(rng.random() * 186) + 3
            r = int(rng.random() * 14) + 10
            fr.write(r, c, rng.choice(["NaN", "inf", "nan", "1e38", "-inf",
                                       "0/0", "dL=inf", "ERR"]),
                     fg=P.C["white"] if i % 3 == 0 else mix(P.C["void"], BAD, 0.85))
        fr.write(19, 30, "▓▓▓ GRADIENT EXPLOSION ▓▓▓", fg=P.C["white"],
                 bg=mix(P.C["void"], BAD, 0.7))
        # formula shatters
        fr.scramble_region(11, 30, 19, 162,
                           np.random.default_rng(int(t * 997)),
                           0.09 + 0.20 * p)


# ---------------------------------------------------------------------------
# diagnostics + pipeline (shared bottom)
# ---------------------------------------------------------------------------
def _diagnostics(fr, ctx, ph):
    t = ctx.t
    r0 = 26
    panel(fr, r0, 2, r0 + 8, 76, "LOSS / STEP", fg=mix(P.C["void"], ICE, 0.7),
          bg=mix(P.C["void"], ICE, 0.02))
    loss = _loss_series(t, 72)
    W.plot_columns(fr, c0=4, r0=r0 + 1, values=loss, h=7,
                   lo=0.0, hi=max(1.0, max(loss)),
                   fg=BAD if ph == 3 else COLD, baseline=r0 + 7, dot=True,
                   ramp=P.RAMP_VERT)
    fr.write(r0 + 8, 4, f"step {31 + int(_end_p(t, T0, END - T0) * 1960):04d}  "
                        f"loss {loss[-1]:7.4f}  "
                        f"{'NaN!' if ph == 3 and loss[-1] > 3 else 'ok'}",
             fg=BAD if ph == 3 else P.C["fg"])
    # gradient
    panel(fr, r0, 80, r0 + 8, 136, "GRADIENT NORM", fg=mix(P.C["void"], ICE, 0.7),
          bg=mix(P.C["void"], ICE, 0.02))
    grads = []
    for i in range(56):
        x = i / 55.0
        g = 0.6 + 0.5 * math.sin(x * 22 + t * 2.0)
        if ph == 3:
            g += (t - ALGEBRA) ** 2 * 6 * math.exp(-((x - 0.7) ** 2) / 0.02)
        grads.append(g)
    W.sparkline(fr, r0 + 1, 82, grads, 6, ramp=P.RAMP_VERT,
                fg=BAD if ph == 3 else ICE)
    fr.write(r0 + 7, 82, f"|g| {grads[-1]:8.2f}", fg=BAD if ph == 3 else P.C["mid"])
    # right: stack / errors
    panel(fr, r0, 140, r0 + 8, 188, "RUNTIME", fg=mix(P.C["void"], ICE, 0.7),
          bg=mix(P.C["void"], ICE, 0.02))
    if ph < 3:
        log = [("model.load()", "OK", P.C["green"]),
               ("train(love)", "RUNNING", GOLD),
               ("weights", "FINITE", ICE),
               ("eval(question)", "PASS" if ph >= 2 else "..", P.C["green"] if ph >= 2 else P.C["grid"])]
    else:
        log = [("model.forward()", "OK", P.C["green"]),
               ("train(love)", "DIVERGED", BAD),
               ("weights", "NaN", BAD),
               ("stack", "OVERFLOW", BAD)]
    for i, (nm, val, col) in enumerate(log):
        fr.write(r0 + 1 + i, 142, nm, fg=P.C["dim"])
        fr.write(r0 + 1 + i, 160, val, fg=col)
    fr.write(r0 + 6, 142, "LOVE = f(x)  //  NaN" if ph == 3 else "LOVE = f(x)  //  fit",
             fg=BAD if ph == 3 else P.C["fg"])
    fr.write(r0 + 7, 142, f"Δ {0.02 + 0.9 * (t - T0):7.3f}s", fg=P.C["dim"])
    # full width log line
    r = 35
    if ph == 3:
        msg = "> step 1871 loss=nan grad_norm=inf  STACK OVERFLOW  LOVE IS NOT COMPUTABLE"
    elif ph == 2:
        msg = "> inference  prompt='question me'  answer='love'  p=0.912  no alternatives sampled"
    elif ph == 1:
        msg = "> training  embeddings converging  attention entropy falling  loss -> 0.11"
    else:
        msg = "> model still trapped in the previous implementation  attempting retrain"
    fr.write(r, 4, msg, fg=BAD if ph == 3 else P.C["fg"])
    rule(fr, 25, fg=mix(P.C["void"], ICE, 0.35), step=20)
    rule(fr, 36, fg=mix(P.C["void"], ICE, 0.35), step=20)


def _pipeline(fr, ctx, ph):
    t = ctx.t
    r0 = 37
    blocks = ["TOK", "EMB", "ATTN", "FFN", "LOGIT", "LOVE"]
    for i, nm in enumerate(blocks):
        c = 4 + i * 22
        hot = ph >= 2 or i <= int(_end_p(t, T0, END - T0) * 6)
        col = (BAD if ph == 3 and i >= 4 else COLD) if hot else P.C["grid"]
        fr.write(r0, c, "┌──────┐", fg=col)
        fr.write(r0 + 1, c, f"│{nm:^6}│", fg=P.C["white"] if hot else P.C["grid"])
        fr.write(r0 + 2, c, "└──────┘", fg=col)
        if i < 5:
            fr.write(r0 + 1, c + 8, " -> ", fg=P.C["dim"])
        # flow dots
        for j in range(3):
            on = (int(t * 8) + i + j) % 3 == 0
            fr.put(r0 + 1, c + 2 + j * 2, "█" if on and hot else "░",
                   fg=col if on and hot else mix(P.C["void"], P.C["line"], 0.6))
    panel(fr, 36, 138, 39, 188, "STACK", fg=mix(P.C["void"], BAD, 0.7),
          bg=mix(P.C["void"], BAD, 0.05))
    if ph == 3:
        lines = ("  at love.nn.Attention.forward()",
                 "  NaN detected in gradient",
                 "  stack overflow (depth 4096)")
    else:
        lines = ("  at love.nn.Attention.forward()",
                 "  tensor finite, grad finite",
                 "  waiting for love")
    for i, ln in enumerate(lines):
        fr.write(37 + i, 140, ln[:46], fg=BAD if ph == 3 else P.C["dim"])
    # token probabilities under the pipeline
    panel(fr, 40, 2, 43, 120, "OUTPUT HEAD", fg=mix(P.C["void"], ICE, 0.6),
          bg=mix(P.C["void"], ICE, 0.02))
    toks = ["love", "execution", "you", "mine", "trap", "free"]
    prs = [0.912, 0.041, 0.019, 0.011, 0.008, 0.003]
    for i, (tk, pr) in enumerate(zip(toks, prs)):
        c = 4 + i * 19
        fr.write(41, c, f"{tk:<8}", fg=P.C["white"] if i == 0 else P.C["mid"])
        fr.write(42, c, f"{pr:6.4f}", fg=GOLD if i == 0 else P.C["dim"])
    fr.write(41, 122, "ARGMAX", fg=P.C["dim"])
    fr.write(41, 130, "love" if ph < 3 else "nan", fg=GOLD if ph < 3 else BAD)
    fr.write(42, 122, "LOSS  ", fg=P.C["dim"])
    fr.write(42, 130, f"{_loss_series(t, 8)[-1]:5.3f}", fg=P.C["fg"])
    fr.write(43, 122, "STATUS", fg=P.C["dim"])
    fr.write(43, 130, "OK" if ph < 3 else "BROKEN", fg=P.C["green"] if ph < 3 else BAD)


def _status(fr, ctx, ph):
    t = ctx.t
    names = ["TRAPPED", "STUDIED", "QUESTION", "ALGEBRA"]
    fr.write(0, 7, "┤ LOVE MODEL ├", fg=P.C["primary"])
    fr.write(0, 24, "// TRAINING RUN // ATTENTION IS ALL YOU NEED", fg=P.C["dim"])
    fr.write(0, 70, f"PHASE {ph} {names[ph]}", fg=P.C["white"])
    fr.write(0, 96, f"T {t:8.3f}", fg=P.C["dim"])
    fr.write(0, 112, f"LOSS {_loss_series(t, 8)[-1]:6.3f}",
             fg=BAD if ph == 3 else P.C["teal"])
    fr.rtext(0, "GPU 99%  TEMP 71C  NaN=0" if ph < 3 else "GPU ERR  TEMP --  NaN=1",
             fg=P.C["dim"] if ph < 3 else BAD, pad=6)
    fr.write(44, 7, "┤ STAGE ├", fg=mix(P.C["void"], ICE, 0.7))
    fr.write(44, 20, f"SCENE STUDY {T0:.3f}-{T1:.3f}", fg=P.C["dim"])
    fr.write(44, 56, f"BEAT {ctx.beat_i:03d}.{int(ctx.beat_p * 100):02d}", fg=ICE)
    fr.write(44, 76, f"BAR {ctx.bar_i:03d}.{int(ctx.bar_p * 100):02d}", fg=ICE)
    fr.write(44, 96, "MODEL LOVE-7B  TOKENS/STEP 4096", fg=P.C["mid"])
    fr.write(44, 140, "NEXT: TRAPPED IN LOVE", fg=P.C["gold"])
    fr.rtext(44, f"RMS={ctx.rms:4.2f}  Z={ctx.local:6.2f}", fg=P.C["dim"], pad=6)
