#!/usr/bin/env python3
"""Is every hand-drawn segment still on the board?

Usage: verify_hand_copper.py [<router run directory>]

Reads the copper from the newest router artifact (run camera-drc.js first
for a fresh one) and checks that every segment of csi_tracks.json and
p4_escape.json is covered, on its own net and layer, by copper on the
board, and still at the width the file asks for. The assembler splits a
polyline where another track meets it, so coverage is measured as the
summed length of collinear board segments, not as one identical segment.
Exit 1 on anything missing or widened.

Why: routers rip up pre-existing copper as a "blocker" when a net will not
route (one run's log said `Ripped 1V8_PSRAM`) and a result that is
applied may have kept the damage. The hand copper is the reproducible
part of this board; count it before judging anything else.

The width is checked because it went wrong silently: freerouting's session
carried a 0.2 mm copy of a 0.127 mm escape stub, the copy landed on top of
the original, and the wider track sat 0.0995 mm from two escape vias where
the drawn one had 0.136. Coverage alone said the copper was there.
"""
import json
import math
import os
import sys

from padgeom import Board

HERE = os.path.dirname(os.path.abspath(__file__))
board = Board(sys.argv[1] if len(sys.argv) > 1 else None)
raw = json.load(open(os.path.join(board.run_dir, "copilot-router-input.json")))["board"]["copper"]
on_board = [(t["net"], t["layer"], t.get("widthMm") or 0.0, [(p["x"], -p["y"]) for p in t["points"]]) for g in raw for t in raw[g]["tracks"]]
hand = [t for f in ("csi_tracks.json", "p4_escape.json") for t in json.load(open(os.path.join(HERE, f)))["tracks"]]


def along(a, b, p):
    """Where p falls along a-b (0..1) and how far off the line it is."""
    vx, vy = b[0] - a[0], b[1] - a[1]
    length2 = vx * vx + vy * vy
    t = ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / length2
    off = abs((p[0] - a[0]) * vy - (p[1] - a[1]) * vx) / math.sqrt(length2)
    return t, off


missing, widened = [], []
for t in hand:
    pts = [(p["x"], p["y"]) for p in t["points"]]
    for a, b in zip(pts, pts[1:]):
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        if length < 1e-6:
            continue
        covered = at_width = 0.0
        for net, layer, width, q in on_board:
            if net != t["net"] or layer != t["layer"].upper():
                continue
            for c, d in zip(q, q[1:]):
                tc, oc = along(a, b, c)
                td, od = along(a, b, d)
                if oc < 0.02 and od < 0.02:
                    lo, hi = max(0.0, min(tc, td)), min(1.0, max(tc, td))
                    if hi > lo:
                        covered += (hi - lo) * length
                        if abs(width - t["width"]) < 0.02:
                            at_width += (hi - lo) * length
        if covered < length - 0.05:
            missing.append((t["net"], t["layer"], a, b, round(covered, 2), round(length, 2)))
        elif at_width < length - 0.05:
            widened.append((t["net"], t["layer"], a, b, t["width"], round(at_width, 2), round(length, 2)))

segments = sum(len(t["points"]) - 1 for t in hand)
print(f"hand segments: {segments}, board tracks: {len(on_board)}, missing: {len(missing)}, wrong width: {len(widened)}")
for m in missing[:20]:
    print("   missing", m)
for w in widened[:20]:
    print("   width  ", w)
sys.exit(1 if missing or widened else 0)
