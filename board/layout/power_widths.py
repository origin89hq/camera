#!/usr/bin/env python3
"""Do the power rails have the copper section 5 says they need?

Usage: power_widths.py [<router run directory>]

For every rail in section 5 of CAMERA-LAYOUT.md, compares the copper
actually on the board against the width that row demands, and against the
IPC-2221 width for its current where the row states none. Exit 1 on a rail
whose *widest* copper is below its own rule: that is not a bottleneck
somewhere, it is a rail that was never widened at all.

Why this is the check, and why the DRC will not make it: an autorouter
given a DSN export routes at one width, because the export carries no
per-net width class. Every track freerouting laid on this board is
0.2 mm, `VSYS` and `3V3_HP` at 2 A included, and the DRC calls that
routed because clearance and connection are all it measures. At 0.2 mm
and 1 oz, 2 A is roughly a 90 C rise.

A rail legitimately narrows at its last hop (a 0.127 mm spur into one
P4 pin carries that pin's share), so a minimum width means nothing on
its own. The maximum does: if the widest copper on a 2 A rail is 0.2 mm,
no part of it was ever drawn for 2 A.

A via counts as copper of equivalent width: its barrel is a tube of
plating, pi * d * 25 um, which for a 0.3 mm via is about 0.67 mm of
1 oz track and for a 0.6 mm via about 1.35 mm.
"""
import json
import math
import os
import sys
from collections import defaultdict

from padgeom import Board

PLATING_MM = 0.025  # JLC's barrel plating
COPPER_MM = 0.035  # 1 oz outer
SNAP = 0.02  # mm; endpoints closer than this are the same node

# section 5 of CAMERA-LAYOUT.md: the width each rail's own row demands,
# and the current it carries. A rule of None means the row states no width.
RAILS = {
    "VCELL": (1.0, 2.0, "C-50"),
    "VCELL_J": (1.0, 2.0, "C-50"),
    "VSYS": (1.0, 2.0, "C-50"),
    "VIN_CHG": (None, 1.0, "C-50"),
    "VUSB": (None, 1.0, "C-50"),
    "VSOLAR": (None, 0.5, "C-50"),
    "3V3": (None, 0.75, "C-51"),
    "3V3_HP": (1.0, 2.0, "C-52"),
    "3V3_CAM": (None, 0.5, "C-53"),
    "3V3_RF": (0.5, 0.5, "C-53"),
    "3V3_SD": (None, 0.3, "C-53"),
    "VDD_HP": (0.8, 0.5, "C-54"),
    "VLED": (None, 0.15, "C-55"),
    "FLASH_SW": (None, 0.15, "C-55"),
    "BUCK_SW": (None, 0.8, "C-52"),
    "BUCK_HP_SW": (None, 0.6, "C-52"),
    "BB_L1": (None, 2.5, "C-52"),
    "BB_L2": (None, 2.5, "C-52"),
}


def width_for(amps, rise_c=10.0):
    """IPC-2221 external-layer width in mm for a current and a 10 C rise."""
    area_mil2 = (amps / (0.048 * rise_c ** 0.44)) ** (1 / 0.725)
    return area_mil2 / (COPPER_MM / 0.0254 * 1000 / 1000) * 0.0254 / 1000 * 1e3 / 1.378


class Rail:
    """One net's copper as a graph, so the copper that carries everything
    can be told from the copper that feeds one capacitor."""

    def __init__(self, board, raw, net):
        self.net = net
        self.node = {}
        self.edges = []  # (a, b, width_mm, what)
        self.pad_nodes = {}
        for group in raw["copper"].values():
            for t in group["tracks"]:
                if t["net"] != net:
                    continue
                width = t.get("widthMm") or 0.2
                pts = [(p["x"], -p["y"]) for p in t["points"]]
                for a, b in zip(pts, pts[1:]):
                    if math.hypot(b[0] - a[0], b[1] - a[1]) > 1e-6:
                        self.edges.append((self._id(a, t["layer"]), self._id(b, t["layer"]), width, "track"))
            for v in group.get("vias", []):
                if v["net"] != net:
                    continue
                at = (v["at"]["x"], -v["at"]["y"])
                equivalent = math.pi * v["diameterMm"] * PLATING_MM / COPPER_MM
                layers = ["TOP", "INNER_1", "INNER_2", "BOTTOM"]
                for upper, lower in zip(layers, layers[1:]):
                    self.edges.append((self._id(at, upper), self._id(at, lower), equivalent, "via"))
        for p in raw["pads"]:
            if p.get("net") != net:
                continue
            pad = next(q for q in board.pads if q.component == p["component"] and q.number == p["number"])
            name = f"{p['component']}.{p['number']}"
            x0, y0, x1, y1 = pad.rect()
            hit = [n for (key, layer), n in self.node.items()
                   if (layer in p["layers"] or len(p["layers"]) > 1)
                   and x0 - SNAP <= key[0] * SNAP <= x1 + SNAP and y0 - SNAP <= key[1] * SNAP <= y1 + SNAP]
            self.pad_nodes[name] = set(hit)
            for a, b in zip(hit, hit[1:]):  # the pad itself ties its own copper together
                self.edges.append((a, b, 99.0, "pad"))

    def _id(self, point, layer):
        key = ((round(point[0] / SNAP), round(point[1] / SNAP)), layer)
        return self.node.setdefault(key, len(self.node))

    def bridges(self):
        """Every edge whose removal splits the net, with the pads it isolates."""
        adjacency = defaultdict(list)
        for i, (a, b, w, what) in enumerate(self.edges):
            adjacency[a].append((b, i))
            adjacency[b].append((a, i))
        seen, low, order, found = {}, {}, [0], []
        for root in list(adjacency):
            if root in seen:
                continue
            stack = [(root, -1, iter(adjacency[root]))]
            seen[root] = low[root] = order[0]
            order[0] += 1
            while stack:
                node, came, it = stack[-1]
                advanced = False
                for nxt, edge in it:
                    if edge == came:
                        continue
                    if nxt in seen:
                        low[node] = min(low[node], seen[nxt])
                    else:
                        seen[nxt] = low[nxt] = order[0]
                        order[0] += 1
                        stack.append((nxt, edge, iter(adjacency[nxt])))
                        advanced = True
                        break
                if not advanced:
                    stack.pop()
                    if stack:
                        parent = stack[-1][0]
                        low[parent] = min(low[parent], low[node])
                        if low[node] > seen[parent]:
                            found.append(came)
        return found

    def side_of(self, without):
        """Which pads sit on each side of one removed edge."""
        adjacency = defaultdict(list)
        for i, (a, b, w, what) in enumerate(self.edges):
            if i == without:
                continue
            adjacency[a].append(b)
            adjacency[b].append(a)
        start = self.edges[without][0]
        seen, stack = {start}, [start]
        while stack:
            for nxt in adjacency[stack.pop()]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        here = [p for p, nodes in self.pad_nodes.items() if nodes & seen]
        there = [p for p, nodes in self.pad_nodes.items() if nodes and not (nodes & seen)]
        return here, there


def main():
    board = Board(sys.argv[1] if len(sys.argv) > 1 else None)
    raw = json.load(open(os.path.join(board.run_dir, "copilot-router-input.json")))["board"]
    bad = 0
    print(f"{'rail':13s}{'row':6s}{'need':>7s}{'widest':>8s}{'at rule':>9s}   verdict")
    for net, (rule, amps, row) in sorted(RAILS.items()):
        tracks = [(t.get("widthMm") or 0.2, [(p["x"], -p["y"]) for p in t["points"]])
                  for g in raw["copper"].values() for t in g["tracks"] if t["net"] == net]
        if not tracks:
            print(f"{net:13s}{row:6s}{'':>7s}{'':>8s}{'':>9s}   no copper")
            continue
        need = rule if rule is not None else width_for(amps)
        widest = max(w for w, _ in tracks)
        total = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for _, pts in tracks for a, b in zip(pts, pts[1:]))
        at_rule = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for w, pts in tracks
                      for a, b in zip(pts, pts[1:]) if w >= need - 0.005)
        ok = widest >= need - 0.005
        bad += 0 if ok else 1
        share = f"{100 * at_rule / total:.0f}%" if total else "-"
        print(f"{net:13s}{row:6s}{need:7.2f}{widest:8.3f}{share:>9s}   "
              f"{'ok' if ok else 'NO COPPER AT THIS WIDTH'} ({amps} A, {total:.0f} mm of track)")
    print(f"\n{bad} rail(s) whose widest copper is below the rule")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
