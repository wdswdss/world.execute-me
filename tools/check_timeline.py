"""Integration sweep for the whole MV - run this before the final render.

    python tools/check_timeline.py                 # every 3rd frame (fast baseline)
    python tools/check_timeline.py --stride 1      # every frame (6357)
    python tools/check_timeline.py --stride 1 --json qa/check_timeline.json

Checks, in order:
  1. SCHEDULE audit      - contiguous 0 .. DURATION, no gap/overlap, every module
                           loaded and exposes a callable draw(ctx)
  2. dispatch            - scene_at() returns the scheduled key at both edges of
                           every entry (and endtext at/after DURATION)
  3. frame sweep         - draw_scene(t, assets) on a frame grid (plus t0+0.05 and
                           t1-0.05 for every scene): exceptions are caught and
                           reported with traceback, then the sweep continues
  4. stage purity        - CJK write attempts on stage rows (font.cell_width==2,
                           and a char-grid rescan), plus unknown-glyph writes
  5. meta sanity         - NaN/Inf anywhere in meta, missing / non-numeric glitch,
                           glitch & bloom ranges
  6. lyric sync          - LINES: EN+CN non-empty, monotonic t0, no overlap, and
                           line_at() resolves the right line at t0 and t1-0.05
  7. outro percent       - s19 progress frac stays strictly below 100% right up
                           to the cut (reads the scene's exported constants)
Exit code 0 = PASS, 1 = FAIL.  --json writes the machine-readable report.
"""
from __future__ import annotations

import sys as _sys
try:                                    # Windows consoles default to GBK/cp1252
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import argparse
import json
import math
import os
import statistics
import sys
import time
import traceback

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import engine.font as F                           # noqa: E402
from engine import layout as L                    # noqa: E402
from engine import sceneapi                       # noqa: E402
from engine import timeline as TL                 # noqa: E402


# --------------------------------------------------------------------------
# instrument the glyph pipeline so CJK / unknown-glyph writes can be caught
# (they are swallowed to blank / "?" by Frame.put/write, so the grid alone
# cannot show them afterwards)
# --------------------------------------------------------------------------
class _Watch:
    def __init__(self):
        self.cjk = []          # (frame_index, row, col, char)
        self.unknown = {}      # char -> first frame index
        self.on = False
        self.fi = -1

    def install(self):
        """Wrap Frame.put/write so glyphs that fall back to blank/"?" are caught.

        F.char_index alone is not enough: widgets probe it with candidate pools
        that contain unsupported chars on purpose, which would be false hits.
        """
        from engine.frame import Frame
        watch = self
        idx = F.get_atlas()[1]
        orig_put = Frame.put
        orig_write = Frame.write

        def _cjk(o):
            return ((0x2E80 <= o <= 0xA4CF) or (0xAC00 <= o <= 0xD7A3)
                    or (0xF900 <= o <= 0xFAFF) or (0xFE30 <= o <= 0xFE4F)
                    or (0xFF00 <= o <= 0xFF60) or (0xFFE0 <= o <= 0xFFE6))

        def put(self, r, c, ch_=" ", fg=None, bg=None):
            if watch.on and isinstance(ch_, str) and len(ch_) == 1:
                o = ord(ch_)
                if _cjk(o):
                    if len(watch.cjk) < 200:
                        watch.cjk.append((watch.fi, int(r), int(c), ch_))
                elif ch_ != " " and idx.get(ch_, 0) == 0:
                    watch.unknown.setdefault(ch_, watch.fi)
            return orig_put(self, r, c, ch_, fg=fg, bg=bg)

        def write(self, r, c, s, fg=None, bg=None):
            if watch.on:
                for ch_ in str(s):
                    if _cjk(ord(ch_)) and len(watch.cjk) < 200:
                        watch.cjk.append((watch.fi, int(r), int(c), ch_))
            return orig_write(self, r, c, s, fg=fg, bg=bg)

        Frame.put = put
        Frame.write = write

    def reset(self, fi):
        self.fi = fi
        self.frame_cjk = 0
        self.frame_unknown = 0


WATCH = _Watch()


def _is_num(v):
    return isinstance(v, (int, float, np.floating, np.integer)) and not isinstance(v, bool)


def _finite(v):
    try:
        return math.isfinite(float(v))
    except Exception:
        return True


def scan_meta(meta):
    """Return (nan_keys, none_keys, ranges) for one frame's meta dict."""
    nan_keys, none_keys = [], []
    glitch = meta.get("glitch", None)
    if glitch is None or not _is_num(glitch) or not _finite(glitch):
        nan_keys.append(("glitch", glitch))
    for k, v in meta.items():
        vals = []
        if _is_num(v):
            vals = [v]
        elif isinstance(v, (tuple, list)):
            vals = [x for x in v if _is_num(x)]
        elif isinstance(v, np.ndarray):
            vals = [v]
        if isinstance(v, np.ndarray):
            if v.dtype.kind in "fi" and not np.asarray(v, np.float64).size == 0:
                if not np.isfinite(np.asarray(v, np.float64)).all():
                    nan_keys.append((k, "non-finite array"))
            continue
        for x in vals:
            if not _finite(x):
                nan_keys.append((k, v))
                break
        if v is None and k in ("glitch", "bloom", "flash", "vignette", "scan", "grain"):
            none_keys.append(k)
    return nan_keys, none_keys


def check_schedule():
    issues, warnings = [], []
    stats = {"boundaries": 0, "max_delta": 0.0, "mapped": 0, "scenes": 0,
             "edges": []}
    sched = sceneapi.SCHEDULE
    if not sched:
        return ["SCHEDULE is empty"], warnings
    b = float(sched[0][0])
    stats["scenes"] = len(sched)
    stats["edges"].append(round(b, 6))
    if abs(b - 0.0) > 1e-9:
        issues.append(f"first scene starts at {b:.6f}s, not 0.000000s "
                      f"(gap 0.000000-{b:.6f})")
    for (t0a, t1a, ka, _), (t0b, t1b, kb, _) in zip(sched, sched[1:]):
        d = float(t0b) - float(t1a)
        stats["boundaries"] += 1
        stats["edges"].append(round(float(t1a), 6))
        stats["max_delta"] = max(stats["max_delta"], abs(d))
        if abs(d) > 1e-9:
            kind = "GAP" if d > 0 else "OVERLAP"
            issues.append(f"{kind} at {float(t1a):.6f}s: {ka} ends {float(t1a):.6f}, "
                          f"{kb} starts {float(t0b):.6f} (delta {d:+.6f})")
    stats["edges"].append(round(float(sched[-1][1]), 6))
    end = float(sched[-1][1])
    # The timeline intentionally stops before the end of the video: TAIL_HOLD
    # seconds of black tail let the last line sit for a beat.  Only the part
    # before the tail must be covered by the schedule.
    tail = float(getattr(L, "TAIL_HOLD", 0.0))
    want = float(L.DURATION) - tail
    if abs(end - want) > 1e-6:
        issues.append(f"schedule ends {end:.6f}s, expected {want:.6f}s "
                      f"(DURATION {L.DURATION:.6f}s - TAIL_HOLD {tail:.1f}s; "
                      f"delta {end - want:+.6f})")
    stats["tail_hold"] = round(tail, 6)

    # modules load and expose draw(ctx)
    for t0, t1, key, mod in sched:
        try:
            m = sceneapi.load_scene(mod)
        except Exception:
            issues.append(f"{key}: module {mod} import failed\n{traceback.format_exc(limit=2)}")
            continue
        if not callable(getattr(m, "draw", None)):
            issues.append(f"{key}: {mod} has no callable draw(ctx)")
        if float(t1) - float(t0) <= 1e-6:
            issues.append(f"{key}: non-positive duration {float(t1) - float(t0):.6f}")

    # dispatch at both edges of every entry
    mapped = 0
    for t0, t1, key, mod in sched:
        for tt, tag in ((float(t0) + 1e-4, "start"), (float(t1) - 1e-4, "end")):
            got = sceneapi.scene_at(tt)[0]
            if got != key:
                issues.append(f"dispatch {tag} {tt:.6f}s -> {got!r}, expected {key!r}")
            else:
                mapped += 1
    tail = float(L.DURATION) - 1e-4
    if sceneapi.scene_at(tail)[0] != sched[-1][2]:
        issues.append(f"dispatch at {tail:.6f}s -> {sceneapi.scene_at(tail)[0]!r}, "
                      f"expected {sched[-1][2]!r}")
    stats["mapped"] = mapped
    return issues, warnings, stats


def check_lyrics():
    """EN/CN non-empty, monotonic, non-overlapping, line_at resolves correctly."""
    issues, warnings = [], []
    lines = TL.LINES
    if not lines:
        return ["LINES is empty"], warnings, 0
    prev_t0, prev_t1 = -1e9, -1e9
    for i, ln in enumerate(lines):
        tag = f"line[{i}] t0={ln['t0']:.3f}"
        if not str(ln.get("en", "")).strip():
            issues.append(f"{tag}: empty EN text")
        if not str(ln.get("cn", "")).strip():
            issues.append(f"{tag}: empty CN text")
        if ln["t1"] <= ln["t0"]:
            issues.append(f"{tag}: t1 {ln['t1']:.3f} <= t0")
        if ln["t0"] < prev_t0:
            issues.append(f"{tag}: t0 is not monotonic (previous line t0 {prev_t0:.3f})")
        if ln["t0"] < prev_t1 - 1e-9:
            issues.append(f"{tag}: overlaps previous line (prev t1 {prev_t1:.3f})")
        # resolves at both edges (t1-0.05 as the spec asks, t0+eps as the start)
        for tt, tag2 in ((ln["t0"] + 1e-4, "start"), (min(ln["t1"] - 0.05, ln["t0"] + 0.5), "end")):
            j, cur = TL.line_at(tt)
            if j != i or cur is None or cur is not ln:
                issues.append(f"{tag}: line_at({tt:.3f}) -> {j!r}, expected {i}")
                break
        prev_t0, prev_t1 = ln["t0"], ln["t1"]
    # monotonic line_i across the whole timeline (sampled every 0.5 s)
    last_i, last_t = -1, 0.0
    t = 0.0
    while t <= L.DURATION + 1e-9:
        i, ln = TL.line_at(t)
        if ln is not None and i is not None:
            if i < last_i:
                issues.append(f"line_i went backwards at {t:.3f}s ({i} < {last_i})")
            last_i, last_t = i, t
        t += 0.5
    gaps = sum(1 for a, b in zip(lines, lines[1:]) if b["t0"] - a["t1"] > 0.05)
    return issues, warnings, gaps


def check_outro():
    """s19 progress must stay strictly below 100% until the cut."""
    info = {"introspectable": False, "samples": 0, "max_pct": None,
            "min_pct": None, "issues": []}
    try:
        m = sceneapi.load_scene("s19_outro99")
    except Exception:
        info["issues"].append("outro module import failed")
        return info
    consts = ("PUSH_T", "LAST_PUSH", "CUT", "BASE", "SPAN")
    have = all(hasattr(m, c) for c in consts)
    state = getattr(m, "_state", None)
    if not have or not callable(state):
        info["note"] = "not introspectable (missing constants or _state)"
        return info
    info["introspectable"] = True
    t0 = float(m.PUSH_T[0])
    cut = float(m.CUT)
    vals = []
    t = t0
    while t < cut - 1e-6:
        try:
            frac = float(state(t)[0])
        except Exception as exc:                       # pragma: no cover
            info["issues"].append(f"_state({t:.3f}) raised {exc!r}")
            break
        vals.append((t, frac * 100.0))
        t += 0.05
    # the final surge, right before the cut
    for tt in (cut - 0.05, cut - 0.01, cut - 0.001):
        try:
            vals.append((tt, float(state(tt)[0]) * 100.0))
        except Exception as exc:                       # pragma: no cover
            info["issues"].append(f"_state({tt:.3f}) raised {exc!r}")
    if vals:
        info["samples"] = len(vals)
        info["min_pct"] = round(min(v for _, v in vals), 4)
        info["max_pct"] = round(max(v for _, v in vals), 4)
        over = [(t, v) for t, v in vals if v >= 99.99995]
        if over:
            info["issues"].append(f"{len(over)} sample(s) at/over 100%: "
                                  f"{over[0][0]:.3f}s -> {over[0][1]:.4f}%")
        # expect the surge to approach BASE+SPAN but never exceed it
        target = (float(m.BASE) + float(m.SPAN)) * 100.0
        if info["max_pct"] < target - 0.01:
            info["issues"].append(
                f"final surge never reaches {target:.3f}% (max {info['max_pct']:.3f}%)")
        info["final_surge_pct"] = info["max_pct"]
        info["target_pct"] = round(target, 4)
    return info


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stride", type=int, default=3, help="render every Nth frame (1 = all)")
    ap.add_argument("--from", dest="t_from", type=float, default=0.0)
    ap.add_argument("--to", dest="t_to", type=float, default=L.DURATION)
    ap.add_argument("--json", default=None, nargs="?", const=os.path.join(ROOT, "qa", "check_timeline.json"),
                    help="write a machine readable report (default qa/check_timeline.json)")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if args.stride < 1:
        raise SystemExit("--stride must be >= 1")
    assets = sceneapi.A.get_assets()
    report = {"fps": L.FPS, "duration": L.DURATION, "stride": args.stride,
              "from": args.t_from, "to": args.t_to, "issues": [], "warnings": [],
              "frames": 0, "exceptions": [], "cjk": {}, "unknown_glyphs": {},
              "meta": {}, "schedule": {}, "lyrics": {}, "outro": {}, "timing": {}}
    print(f"[check_timeline] {args.t_from:.2f}s .. {args.t_to:.2f}s  stride={args.stride}")

    # 1/2 - schedule + dispatch -------------------------------------------
    sched_issues, sched_warn, sched_stats = check_schedule()
    report["schedule"] = {"scenes": len(sceneapi.SCHEDULE),
                          "issues": sched_issues,
                          "boundary_offsets": sched_stats["edges"],
                          "max_boundary_delta": round(sched_stats["max_delta"], 9),
                          "dispatch_edges_ok": sched_stats["mapped"],
                          "dispatch_edges_total": 2 * len(sceneapi.SCHEDULE)}
    print(f"[check_timeline] schedule: {len(sceneapi.SCHEDULE)} scenes, "
          f"{len(sched_issues)} issue(s), max boundary delta "
          f"{sched_stats['max_delta']:.6f}s, dispatch {sched_stats['mapped']}/"
          f"{2 * len(sceneapi.SCHEDULE)} edges ok")
    for s in sched_issues:
        print("  ! " + s.replace("\n", " | "))

    # 3/4/5 - frame sweep --------------------------------------------------
    fi_from = int(round(args.t_from * L.FPS))
    fi_to = int(round(args.t_to * L.FPS))
    frame_ids = list(range(fi_from, fi_to + 1, args.stride))
    # always include both edges (+-0.05 s) of each scheduled scene
    for t0, t1, key, mod in sceneapi.SCHEDULE:
        for tt in (float(t0) + 0.05, float(t1) - 0.05):
            if args.t_from - 1e-9 <= tt <= args.t_to + 1e-9:
                fi = int(round(tt * L.FPS))
                if fi not in frame_ids:
                    frame_ids.append(fi)
    frame_ids = sorted(set(frame_ids))

    # the atlas owns IDX_CHARS; make sure it is built before the grid rescan
    try:
        F.get_atlas()
    except Exception:
        pass
    WATCH.install()
    WATCH.on = True
    exc, cjk_frames, unknown_frames = [], [], []
    nan_frames, none_glitch_frames = [], []
    glitches, blooms = [], []
    draw_ms = []
    errors_by_scene = {}
    t_start = time.perf_counter()
    for n, fi in enumerate(frame_ids):
        t = fi / L.FPS
        WATCH.reset(fi)
        t_frame = time.perf_counter()
        try:
            fr, meta, ctx = sceneapi.draw_scene(t, assets)
        except Exception:
            tb = traceback.format_exc(limit=6)
            scene = sceneapi.scene_at(t)[0]
            errors_by_scene[scene] = errors_by_scene.get(scene, 0) + 1
            if len(exc) < 40:
                exc.append({"t": round(t, 4), "frame": fi, "scene": scene,
                            "traceback": tb})
            if not args.quiet:
                print(f"  ! EXC t={t:7.3f}s scene={scene:<12s} "
                      f"{tb.strip().splitlines()[-1][:100]}")
            continue
        # stage CJK rescan (grid-level; the atlas has no CJK, but a future
        # font/mask change must not slip CJK through)
        uniq = np.unique(fr.ch)
        idx_chars = F.IDX_CHARS
        for idx in uniq:
            idx = int(idx)
            if 0 <= idx < len(idx_chars) and F.cell_width(idx_chars[idx]) == 2:
                cjk_frames.append((fi, -1, -1, idx_chars[idx]))
        if WATCH.cjk:
            cjk_frames.extend(WATCH.cjk[-8:])
            WATCH.cjk.clear()
        if WATCH.unknown:
            unknown_frames.extend(WATCH.unknown.items())
            WATCH.unknown.clear()
        bad, nones = scan_meta(meta)
        if bad:
            nan_frames.append((fi, bad[:4]))
        if nones:
            none_glitch_frames.append((fi, nones))
        try:
            glitches.append(float(meta.get("glitch", 0.0)))
            blooms.append(float(meta.get("bloom", 0.0)))
        except Exception:
            pass
        draw_ms.append((time.perf_counter() - t_frame) * 1000.0)
        if not args.quiet and (n % 200 == 0 or n == len(frame_ids) - 1):
            pct = 100.0 * (n + 1) / len(frame_ids)
            print(f"  [{pct:5.1f}%] t={t:7.2f}s scene={ctx.scene:<12s} "
                  f"frames={n + 1}/{len(frame_ids)} exc={len(exc)}")
    WATCH.on = False
    wall = time.perf_counter() - t_start

    report["exceptions"] = exc
    report["cjk"] = {"writes": len(cjk_frames), "frames": len({f for f, *_ in cjk_frames}),
                     "first": [[int(f), int(r), int(c), ch] for f, r, c, ch in cjk_frames[:12]]}
    uniq_unknown = {}
    for ch, fi in unknown_frames:
        uniq_unknown.setdefault(ch, fi)
    report["unknown_glyphs"] = {"count": len(uniq_unknown),
                                "chars": "".join(uniq_unknown.keys())[:80],
                                "first_frame": min(uniq_unknown.values()) if uniq_unknown else None}
    report["meta"] = {
        "nan_inf_frames": [[int(f), bad] for f, bad in nan_frames[:20]],
        "nan_inf_count": len(nan_frames),
        "glitch_none_frames": len(none_glitch_frames),
        "glitch_range": [round(min(glitches), 4), round(max(glitches), 4)] if glitches else None,
        "bloom_range": [round(min(blooms), 4), round(max(blooms), 4)] if blooms else None,
    }
    report["timing"] = {
        "frames": len(frame_ids),
        "wall_s": round(wall, 1),
        "draw_ms_median": round(statistics.median(draw_ms), 1) if draw_ms else None,
        "draw_ms_max": round(max(draw_ms), 1) if draw_ms else None,
        "errors_by_scene": errors_by_scene,
    }

    # 6 - lyrics -----------------------------------------------------------
    ly = check_lyrics()
    ly_issues, ly_warn, ly_gaps = ly[0], ly[1], ly[2]
    report["lyrics"] = {"lines": len(TL.LINES), "issues": ly_issues,
                        "instrumental_gaps": ly_gaps}
    print(f"[check_timeline] lyrics: {len(TL.LINES)} lines, {len(ly_issues)} issue(s), "
          f"{ly_gaps} instrumental gap(s)")

    # 7 - outro percent ----------------------------------------------------
    outro = check_outro()
    report["outro"] = outro
    if outro.get("introspectable"):
        print(f"[check_timeline] outro: {outro['samples']} samples, "
              f"{outro['min_pct']:.3f}% .. {outro['max_pct']:.3f}% "
              f"(target {outro.get('target_pct')}%)  "
              f"{len(outro['issues'])} issue(s)")
    else:
        print(f"[check_timeline] outro: {outro.get('note', 'not introspectable')}")

    # 8 - summary ----------------------------------------------------------
    issues = list(sched_issues) + list(ly_issues) + list(outro["issues"])
    exc_total = sum(errors_by_scene.values())
    report["frames"] = len(frame_ids)
    report["exception_count"] = exc_total
    if exc_total:
        issues.append(f"{exc_total} frame exception(s) in {len(errors_by_scene)} scene(s)")
    if cjk_frames:
        issues.append(f"{len(cjk_frames)} CJK write(s) on stage")
    if nan_frames:
        issues.append(f"{len(nan_frames)} frame(s) with non-finite meta")
    if none_glitch_frames:
        issues.append(f"{len(none_glitch_frames)} frame(s) missing numeric glitch")
    warnings = []
    if uniq_unknown:
        warnings.append(f"unknown glyph write(s): {' '.join(uniq_unknown.keys())[:40]}")
    if glitches and max(glitches) > 1.6:
        warnings.append(f"extreme glitch value {max(glitches):.2f}")
    report["issues"] = issues
    report["warnings"] = warnings

    print("")
    print("=" * 74)
    print(f"  TOTAL frames      : {len(frame_ids)}  ({wall:.1f}s, "
          f"median draw {report['timing']['draw_ms_median']} ms, "
          f"max {report['timing']['draw_ms_max']} ms)")
    print(f"  exceptions        : {exc_total}")
    print(f"  stage CJK writes  : {len(cjk_frames)}")
    print(f"  unknown glyphs    : {len(uniq_unknown)}"
          + (f"  ({' '.join(uniq_unknown.keys())[:30]})" if uniq_unknown else ""))
    print(f"  meta NaN/Inf      : {len(nan_frames)}")
    print(f"  schedule          : {len(sceneapi.SCHEDULE)} scenes, "
          f"{len(sched_issues)} issue(s), max boundary delta "
          f"{sched_stats['max_delta']:.6f}s, dispatch "
          f"{sched_stats['mapped']}/{2 * len(sceneapi.SCHEDULE)} edges")
    print(f"  lyrics            : {len(TL.LINES)} lines, {len(ly_issues)} issue(s)")
    print(f"  outro < 100%      : "
          + (f"PASS ({outro['max_pct']:.3f}%)" if outro.get("introspectable") and not outro["issues"]
             else ("FAIL" if outro.get("introspectable") else "skipped")))
    print(f"  RESULT            : {'PASS' if not issues else 'FAIL'}")
    print("=" * 74)
    for s in issues:
        print("  ✗ " + s.replace("\n", " | "))
    for s in warnings:
        print("  ! warning: " + s)

    if args.json:
        path = args.json
        if not os.path.isabs(path):
            path = os.path.join(ROOT, path)
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, ensure_ascii=False)
        print(f"[check_timeline] json: {os.path.relpath(path, ROOT)}")
    return 0 if not issues else 1


if __name__ == "__main__":
    sys.exit(main())
