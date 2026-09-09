#!/usr/bin/env python3
"""Which pieces of a net are not joined, and what is in each piece?

Usage: net_islands.py <net> [<net> ...]

Reads the newest router artifact (camera-drc.js refreshes it) and walks
the net's pads, tracks and vias by geometry (a track end on another
track, a via under a track, a track end inside a pad) into connected
pieces. Prints one line per piece with its pads and its free ends, which
is what a hand-drawn link needs to start from.

Why: EasyEDA's DRC names one pad per broken piece and `inspect_net` gives
one length per piece, and neither says which pads sit with which. A 3V3
net in three pieces with 49 pads was three guesses until this existed.
"""
import json
import math
import os
import sys

from padgeom import Board

TOL = 0.03  # mm; the assembler's own rounding is 0.001


def _along(a, b, p):
    vx, vy = b[0] - a[0], b[1] - a[1]
    l2 = vx * vx + vy * vy
    if l2 < 1e-12:
        return math.hypot(p[0] - a[0], p[1] - a[1])
    t = max(0.0, min(1.0, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / l2))
    return math.hypot(p[0] - a[0] - t * vx, p[1] - a[1] - t * vy)


class NetCopper:
    """Every pad, track and via of one net, in EasyEDA coordinates (y up)."""

    def __init__(self, board, net):
        raw = json.load(open(os.path.join(board.run_dir, "copilot-router-input.json")))["board"]
        self.net = net
        self.tracks = [
            {"layer": t["layer"], "width": t.get("widthMm"), "points": [(p["x"], -p["y"]) for p in t["points"]]}
            for g in raw["copper"] for t in raw["copper"][g]["tracks"] if t["net"] == net
        ]
        self.vias = [
            {"x": v["at"]["x"], "y": -v["at"]["y"], "d": v["diameterMm"]}
            for g in raw["copper"] for v in raw["copper"][g].get("vias", []) if v["net"] == net
        ]
        self.pads = [(p, [pad for pad in board.pads if pad.component == p["component"] and pad.number == p["number"]][0])
                     for p in raw["pads"] if p.get("net") == net]

    def _pad_hit(self, raw_pad, pad, x, y, layer):
        if layer not in raw_pad["layers"] and len(raw_pad["layers"]) < 2:
            return False
        x0, y0, x1, y1 = pad.rect()
        return x0 - TOL <= x <= x1 + TOL and y0 - TOL <= y <= y1 + TOL

    def islands(self):
        n_t, n_v = len(self.tracks), len(self.vias)
        parent = list(range(n_t + n_v + len(self.pads)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        def union(a, b):
            parent[find(a)] = find(b)

        for i, t in enumerate(self.tracks):
            for j, u in enumerate(self.tracks):
                if j <= i or t["layer"] != u["layer"]:
                    continue
                if any(_along(a, b, p) <= TOL for p in (t["points"][0], t["points"][-1]) for a, b in zip(u["points"], u["points"][1:])) or \
                   any(_along(a, b, p) <= TOL for p in (u["points"][0], u["points"][-1]) for a, b in zip(t["points"], t["points"][1:])):
                    union(i, j)
            for k, v in enumerate(self.vias):
                if any(_along(a, b, (v["x"], v["y"])) <= v["d"] / 2 for a, b in zip(t["points"], t["points"][1:])):
                    union(i, n_t + k)
            for m, (raw_pad, pad) in enumerate(self.pads):
                if any(self._pad_hit(raw_pad, pad, x, y, t["layer"]) for x, y in (t["points"][0], t["points"][-1])):
                    union(i, n_t + n_v + m)
        for k, v in enumerate(self.vias):
            for m, (raw_pad, pad) in enumerate(self.pads):
                if self._pad_hit(raw_pad, pad, v["x"], v["y"], "TOP") or self._pad_hit(raw_pad, pad, v["x"], v["y"], "BOTTOM"):
                    union(n_t + k, n_t + n_v + m)

        groups = {}
        for i in range(len(parent)):
            groups.setdefault(find(i), []).append(i)
        out = []
        for members in groups.values():
            tracks = [self.tracks[i] for i in members if i < n_t]
            vias = [self.vias[i - n_t] for i in members if n_t <= i < n_t + n_v]
            pads = [self.pads[i - n_t - n_v] for i in members if i >= n_t + n_v]
            length = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for t in tracks for a, b in zip(t["points"], t["points"][1:]))
            out.append({"tracks": tracks, "vias": vias, "pads": pads, "length": length})
        return sorted(out, key=lambda g: -g["length"])


def describe(board, net):
    copper = NetCopper(board, net)
    pieces = copper.islands()
    print(f"{net}: {len(pieces)} piece(s), {len(copper.pads)} pads, {len(copper.tracks)} tracks, {len(copper.vias)} vias")
    for n, g in enumerate(pieces):
        pads = " ".join(f"{p.component}.{p.number}" for _, p in g["pads"])
        layers = sorted({t["layer"] for t in g["tracks"]})
        print(f"  [{n}] {g['length']:.1f} mm on {layers or 'no track'}, {len(g['vias'])} vias, pads: {pads or '-'}")
        for v in g["vias"][:6]:
            print(f"      via ({v['x']:.3f}, {v['y']:.3f}) d {v['d']:.2f}")
        for _, p in g["pads"][:6]:
            print(f"      pad {p.component}.{p.number} ({p.x:.3f}, {p.y:.3f})")


if __name__ == "__main__":
    board = Board()
    for net in sys.argv[1:]:
        describe(board, net)
