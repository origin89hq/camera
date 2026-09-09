#!/usr/bin/env python3
"""Draw one track on the routing layers, around everything already there.

    from hand_route import Copper
    copper = Copper()                       # newest router artifact
    r = copper.route("I2C_SCL", (14.063, -10.69), (12.419, 10.397), goal_layers=("TOP",))
    copper.verify("I2C_SCL", r)             # (gap, offender): exact, not the grid

Usage as a script: hand_route.py <net> x0 y0 x1 y1 [width]

A* over a 0.05 mm grid on Top, Inner2 and Bottom, every other net's pad,
track and via inflated by its own half width plus the clearance plus
ours, the board edge by its own rule; a layer change is allowed on any
cell where a via clears both layers and costs VIA_COST of path. The path
comes back as straight and 45-degree runs per layer plus the vias, and
`verify` measures it against the exact shapes so a corner the grid cut is
caught before the board sees it.

Why: freerouting stops with a handful of connections open and its answer
to "why" is a window that says nothing. A link drawn by eye from a
preview was 0.09 mm from a capacitor once. The artifact has every shape;
drawing against it is the honest way to finish by hand.
"""
import heapq
import json
import math
import os
import sys

from padgeom import Board, Pad

CLEARANCE = 0.127
EDGE = 0.3
STEP = 0.05
BEND = 0.03  # extra cost per direction change: fewer stairs, straighter copper
MARGIN = 4.0  # mm around the two ends that the search may wander into
HOLE_TO_HOLE = 0.254
VIA_COST = 0.8  # a via costs as much as 0.8 mm of track: taken when it saves more than that
LAYERS = ("TOP", "INNER_2", "BOTTOM")  # Inner1 is the plane (C-04); a through via reaches all three

DIRS = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
        (1, 1, math.sqrt(2)), (1, -1, math.sqrt(2)), (-1, 1, math.sqrt(2)), (-1, -1, math.sqrt(2))]


def seg_point(a, b, p):
    vx, vy = b[0] - a[0], b[1] - a[1]
    l2 = vx * vx + vy * vy
    if l2 < 1e-12:
        return math.hypot(p[0] - a[0], p[1] - a[1])
    t = max(0.0, min(1.0, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / l2))
    return math.hypot(p[0] - a[0] - t * vx, p[1] - a[1] - t * vy)


def seg_seg(a, b, c, d):
    """Distance between segments a-b and c-d."""
    def cross(o, p, q):
        return (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0])
    if (cross(a, b, c) * cross(a, b, d) < 0) and (cross(c, d, a) * cross(c, d, b) < 0):
        return 0.0
    return min(seg_point(a, b, c), seg_point(a, b, d), seg_point(c, d, a), seg_point(c, d, b))


def point_in_poly(p, poly):
    inside = False
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        if (y0 > p[1]) != (y1 > p[1]) and p[0] < x0 + (p[1] - y0) * (x1 - x0) / (y1 - y0):
            inside = not inside
    return inside


def seg_poly(a, b, poly):
    """Distance from segment a-b to a filled polygon; 0 inside it."""
    if point_in_poly(a, poly) or point_in_poly(b, poly):
        return 0.0
    return min(seg_seg(a, b, c, d) for c, d in zip(poly, poly[1:] + poly[:1]))


def seg_rect(a, b, r):
    """Distance from segment a-b to an axis-aligned rectangle (x0, y0, x1, y1)."""
    x0, y0, x1, y1 = r
    if (x0 <= a[0] <= x1 and y0 <= a[1] <= y1) or (x0 <= b[0] <= x1 and y0 <= b[1] <= y1):
        return 0.0
    edges = [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]
    return min(seg_seg(a, b, c, d) for c, d in edges)


class Copper:
    """Everything on the board that a new track has to keep away from."""

    def __init__(self, run_dir=None):
        self.board = Board(run_dir)
        raw = json.load(open(os.path.join(self.board.run_dir, "copilot-router-input.json")))["board"]
        self.tracks = [(t["net"], t["layer"], t.get("widthMm") or 0.2, [(p["x"], -p["y"]) for p in t["points"]])
                       for g in raw["copper"] for t in raw["copper"][g]["tracks"]]
        self.vias = [(v["net"], v["at"]["x"], -v["at"]["y"], v["diameterMm"]) for g in raw["copper"] for v in raw["copper"][g].get("vias", [])]
        self.pads = [(p.get("net", ""), p["layers"], Pad(p)) for p in raw["pads"]]
        # a prohibited region is copper's obstacle whatever the net: the C6's
        # antenna void (C-11) took three ground stubs that were drawn without it
        self.keepouts = [([(q["x"], -q["y"]) for q in k["polygon"]["outer"]], k.get("layers") or [], k.get("forbid") or {})
                         for k in (raw.get("keepouts") or []) if k.get("polygon", {}).get("outer")]
        xs = [x for x, _ in self.board.outline]
        ys = [y for _, y in self.board.outline]
        self.edge = (min(xs), min(ys), max(xs), max(ys))

    def obstacles(self, layer, net):
        """(kind, shape, keep) for everything not on `net` that touches `layer`,
        or every layer when `layer` is None (a through via meets the inner
        tracks too, and one landed on an Inner2 wire before this said so);
        keep is the distance our centreline must stay from the shape."""
        out = []
        for n, lay, w, pts in self.tracks:
            if n != net and (layer is None or lay == layer):
                for a, b in zip(pts, pts[1:]):
                    out.append(("seg", (a, b), w / 2))
        for n, x, y, d in self.vias:
            if n != net:
                out.append(("circle", (x, y), d / 2))
        for n, layers, pad in self.pads:
            if n != net and (layer is None or layer in layers or len(layers) > 1):
                out.append(("rect", pad.rect(), 0.0))
        for poly, layers, forbid in self.keepouts:
            if forbid.get("tracks", True) and (layer is None or layer in layers):
                out.append(("poly", poly, 0.0))
        return out


    def check(self, net, layer, pts, width=0.127):
        """Smallest gap between the polyline and anything not on its net, with the
        offender. The rule is CLEARANCE: a result below it is a violation, a
        result below zero is an overlap."""
        worst = (float("inf"), None)
        obstacles = self.obstacles(layer, net)
        for a, b in zip(pts, pts[1:]):
            for kind, shape, keep in obstacles:
                d = distance(kind, shape, a, b) - keep - width / 2
                if d < worst[0]:
                    worst = (d, (kind, shape))
            x0, y0, x1, y1 = self.edge
            for p in (a, b):
                d = min(p[0] - x0, x1 - p[0], p[1] - y0, y1 - p[1]) - width / 2 - EDGE + CLEARANCE
                if d < worst[0]:
                    worst = (d, ("edge", None))
        return worst

    def check_via(self, net, at, diameter=0.6, drill=0.3, obstacles=None, vias=None, holes=None):
        """Smallest gap between a via at `at` and anything not on its net, on
        every layer, and hole to hole against every via and drilled pad whatever
        the net. A via 0.06 mm from its own net's via is still two holes. The
        rule is CLEARANCE; a gap of 0.03 mm once passed as "positive" and put four
        return vias against the D-PHY lanes."""
        worst = float("inf")
        for kind, shape, keep in (self.obstacles(None, net) if obstacles is None else obstacles):
            worst = min(worst, distance(kind, shape, at, at) - keep - diameter / 2)
        x0, y0, x1, y1 = self.edge
        worst = min(worst, min(at[0] - x0, x1 - at[0], at[1] - y0, y1 - at[1]) - diameter / 2 - EDGE + CLEARANCE)
        for n, x, y, d in (self.vias if vias is None else vias):
            worst = min(worst, math.hypot(at[0] - x, at[1] - y) - drill / 2 - d / 4 - HOLE_TO_HOLE)  # the other hole is about half its ring
        for n, layers, pad in (self.pads if holes is None else holes):
            if len(layers) > 1:
                worst = min(worst, distance("rect", pad.rect(), at, at) - drill / 2 - HOLE_TO_HOLE)
        return worst

    def find_via_spot(self, net, near, diameter=0.6, drill=0.3, radius=1.5, margin=0.0, at_least=0.0):
        """The via position closest to `near`, at least `at_least` away, whose gap
        to everything else is CLEARANCE plus `margin`; None if there is none."""
        best = None
        steps = int(radius / STEP)
        reach = radius + diameter + CLEARANCE + margin + HOLE_TO_HOLE
        obstacles = _near(self.obstacles(None, net), near, reach)  # the whole board's shapes, once, not per candidate
        vias = [v for v in self.vias if math.hypot(v[1] - near[0], v[2] - near[1]) < reach + v[3]]
        holes = [p for p in self.pads if len(p[1]) > 1 and math.hypot(p[2].x - near[0], p[2].y - near[1]) < reach + max(p[2].w, p[2].h)]
        for i in range(-steps, steps + 1):
            for j in range(-steps, steps + 1):
                at = (round(near[0] + i * STEP, 3), round(near[1] + j * STEP, 3))
                dist = math.hypot(i * STEP, j * STEP)
                if dist > radius or dist < at_least or (best is not None and dist >= best[0]):
                    continue
                if self.check_via(net, at, diameter, drill, obstacles, vias, holes) >= CLEARANCE + margin:
                    best = (dist, at)
        return best[1] if best else None

    def route(self, net, start, goal, width=0.127, start_layers=LAYERS, goal_layers=LAYERS, via=(0.6, 0.3), margin=MARGIN):
        """Tracks and vias joining start to goal, or None if the grid found no way.

        Returns {"tracks": [(layer, [points])], "vias": [(x, y)]}. A start on a
        through via may leave on either layer; a goal on an SMD pad names its
        layer in `goal_layers`. Every layer change costs VIA_COST and is only
        taken on a cell where a via of `via` (diameter, drill) clears both
        layers.
        """
        ex0, ey0, ex1, ey1 = self.edge
        inset = EDGE + max(width, via[0]) / 2
        window = (max(min(start[0], goal[0]) - margin, ex0 + inset), max(min(start[1], goal[1]) - margin, ey0 + inset),
                  min(max(start[0], goal[0]) + margin, ex1 - inset), min(max(start[1], goal[1]) + margin, ey1 - inset))
        grid = Raster(self, net, window, width, via)
        s, g = grid.cell(start), grid.cell(goal)
        if not (grid.inside(s) and grid.inside(g)):
            return None
        for c in (s, g):  # the ends are on our own self; a neighbour's inflation may reach them
            for L in LAYERS:
                grid.blocked[L][c[0] * grid.ny + c[1]] = 0
        if os.environ.get("HR_DEBUG"):
            print(f"grid {grid.nx}x{grid.ny}; blocked top {sum(grid.blocked['TOP'])} bottom {sum(grid.blocked['BOTTOM'])}; "
                  f"via cells {sum(grid.via_ok)}", file=sys.stderr)

        def h(c):
            dx, dy = abs(c[0] - g[0]), abs(c[1] - g[1])
            return (max(dx, dy) - min(dx, dy)) + min(dx, dy) * math.sqrt(2)

        ny = grid.ny
        best, came, heap = {}, {}, []
        tie = 0  # heap entries never compare beyond (f, tie): a direction of None is not orderable
        for L in start_layers:
            best[(s, L, None)] = 0.0
            heapq.heappush(heap, (h(s), tie, 0.0, s, L, None))
            tie += 1
        found = None
        while heap:
            f, _, cost, c, L, d = heapq.heappop(heap)
            if c == g and L in goal_layers:
                found = (c, L, d)
                break
            if best.get((c, L, d), float("inf")) < cost:
                continue
            blocked = grid.blocked[L]
            for dx, dy, w in DIRS:
                n = (c[0] + dx, c[1] + dy)
                if not grid.inside(n) or blocked[n[0] * ny + n[1]]:
                    continue
                if dx and dy and (blocked[(c[0] + dx) * ny + c[1]] or blocked[c[0] * ny + c[1] + dy]):
                    continue  # no squeezing diagonally between two blocked cells
                nd = (dx, dy)
                nc = cost + w + (BEND if d is not None and nd != d else 0.0)
                if nc < best.get((n, L, nd), float("inf")):
                    best[(n, L, nd)] = nc
                    came[(n, L, nd)] = (c, L, d)
                    tie += 1
                    heapq.heappush(heap, (nc + h(n), tie, nc, n, L, nd))
            own = c in grid.own
            if (own or grid.via_ok[c[0] * ny + c[1]]) and c != s:
                nc = cost + (0.0 if own else VIA_COST / STEP)
                for other in LAYERS:
                    if other == L or nc >= best.get((c, other, None), float("inf")):
                        continue
                    best[(c, other, None)] = nc
                    came[(c, other, None)] = (c, L, d)
                    tie += 1
                    heapq.heappush(heap, (nc + h(c), tie, nc, c, other, None))
        if found is None:
            return None
        steps = []
        k = found
        while k is not None:
            steps.append(k)
            k = came.get(k)
        steps.reverse()
        runs, vias = [], []
        for c, L, d in steps:
            if runs and runs[-1][0] == L:
                runs[-1][1].append(c)
            else:
                if runs and c not in grid.own:
                    vias.append(grid.point(c))
                runs.append((L, [c]))
        tracks = []
        for n, (L, cells) in enumerate(runs):
            pts = [start if n == 0 else grid.point(cells[0])]
            for i in range(1, len(cells) - 1):
                d0 = (cells[i][0] - cells[i - 1][0], cells[i][1] - cells[i - 1][1])
                d1 = (cells[i + 1][0] - cells[i][0], cells[i + 1][1] - cells[i][1])
                if d0 != d1:
                    pts.append(grid.point(cells[i]))
            pts.append(goal if n == len(runs) - 1 else grid.point(cells[-1]))
            if len(cells) > 1:
                tracks.append((L, pts))
        return {"tracks": tracks, "vias": vias}

    def verify(self, net, result, width=0.127, via=(0.6, 0.3)):
        """Exact clearance of a `route` result: (smallest clearance, offender)."""
        worst = (float("inf"), None)
        for L, pts in result["tracks"]:
            worst = min(worst, self.check(net, L, pts, width), key=lambda w: w[0])
        for at in result["vias"]:
            worst = min(worst, (self.check_via(net, at, *via), ("via", at)), key=lambda w: w[0])
        return worst


def distance(kind, shape, a, b):
    if kind == "seg":
        return seg_seg(a, b, shape[0], shape[1])
    if kind == "circle":
        return seg_point(a, b, shape)
    if kind == "poly":
        return seg_poly(a, b, shape)
    return seg_rect(a, b, shape)




def _near(obstacles, at, reach):
    """The obstacles whose bounding box comes within `reach` of `at`."""
    out = []
    for kind, shape, keep in obstacles:
        if kind == "circle":
            d = math.hypot(at[0] - shape[0], at[1] - shape[1]) - keep
        elif kind == "rect":
            d = math.hypot(max(shape[0] - at[0], 0, at[0] - shape[2]), max(shape[1] - at[1], 0, at[1] - shape[3]))
        else:
            d = seg_point(shape[0], shape[1], at) - keep
        if d <= reach:
            out.append((kind, shape, keep))
    return out





class Raster:
    """One layer's cells a track centreline may not enter, plus the cells a
    via may sit on, over the search window."""

    def __init__(self, copper, net, window, width, via):
        self.x0, self.y0, x1, y1 = window
        self.nx, self.ny = int((x1 - self.x0) / STEP) + 1, int((y1 - self.y0) / STEP) + 1
        self.blocked = {L: self._paint(copper.obstacles(L, net), CLEARANCE + width / 2) for L in LAYERS}
        holes = [("circle", (x, y), d / 4) for _, x, y, d in copper.vias] + \
                [("rect", pad.rect(), 0.0) for _, layers, pad in copper.pads if len(layers) > 1]
        via_blocked = self._paint(copper.obstacles(None, net), CLEARANCE + via[0] / 2)
        for i, b in enumerate(self._paint(holes, HOLE_TO_HOLE + via[1] / 2)):
            via_blocked[i] |= b
        self.via_ok = bytearray(1 if not b else 0 for b in via_blocked)
        # a via of our own net already there is a layer change for free
        self.own = {self.cell((x, y)) for n, x, y, _ in copper.vias if n == net}

    def cell(self, p):
        return (round((p[0] - self.x0) / STEP), round((p[1] - self.y0) / STEP))

    def point(self, c):
        return (round(self.x0 + c[0] * STEP, 3), round(self.y0 + c[1] * STEP, 3))

    def inside(self, c):
        return 0 <= c[0] < self.nx and 0 <= c[1] < self.ny

    def _paint(self, obstacles, extra):
        nx, ny, x0, y0 = self.nx, self.ny, self.x0, self.y0
        out = bytearray(nx * ny)
        for kind, shape, keep in obstacles:
            r = keep + extra
            if kind == "circle":
                cx, cy = shape
                bx0, by0, bx1, by1 = cx - r, cy - r, cx + r, cy + r
            elif kind == "rect":
                bx0, by0, bx1, by1 = shape[0] - r, shape[1] - r, shape[2] + r, shape[3] + r
            elif kind == "poly":
                bx0, by0 = min(p[0] for p in shape) - r, min(p[1] for p in shape) - r
                bx1, by1 = max(p[0] for p in shape) + r, max(p[1] for p in shape) + r
            else:
                a, b = shape
                bx0, by0 = min(a[0], b[0]) - r, min(a[1], b[1]) - r
                bx1, by1 = max(a[0], b[0]) + r, max(a[1], b[1]) + r
            i0, i1 = max(0, int((bx0 - x0) / STEP)), min(nx - 1, int((bx1 - x0) / STEP) + 1)
            j0, j1 = max(0, int((by0 - y0) / STEP)), min(ny - 1, int((by1 - y0) / STEP) + 1)
            for i in range(i0, i1 + 1):
                px = x0 + i * STEP
                for j in range(j0, j1 + 1):
                    py = y0 + j * STEP
                    if kind == "circle":
                        hit = math.hypot(px - cx, py - cy) < r
                    elif kind == "rect":
                        dx = max(shape[0] - px, 0, px - shape[2])
                        dy = max(shape[1] - py, 0, py - shape[3])
                        hit = dx * dx + dy * dy < r * r
                    elif kind == "poly":
                        hit = seg_poly((px, py), (px, py), shape) < r
                    else:
                        hit = seg_point(a, b, (px, py)) < r
                    if hit:
                        out[i * ny + j] = 1
        return out



if __name__ == "__main__":
    net = sys.argv[1]
    a = (float(sys.argv[2]), float(sys.argv[3]))
    b = (float(sys.argv[4]), float(sys.argv[5]))
    width = float(sys.argv[6]) if len(sys.argv) > 6 else 0.127
    copper = Copper()
    result = copper.route(net, a, b, width)
    if result is None:
        sys.exit("no path")
    d, who = copper.verify(net, result, width)
    length = sum(math.hypot(q[0] - p[0], q[1] - p[1]) for _, pts in result["tracks"] for p, q in zip(pts, pts[1:]))
    print(json.dumps({"tracks": [{"net": net, "layer": L.lower().replace("_", ""), "width": width, "points": [{"x": x, "y": y} for x, y in pts]} for L, pts in result["tracks"]],
                      "vias": [{"net": net, "x": x, "y": y, "diameter": 0.6, "drill": 0.3} for x, y in result["vias"]]}))
    print(f"{len(result['tracks'])} runs, {len(result['vias'])} vias, {length:.2f} mm, clearance {d:.3f} mm to {who}", file=sys.stderr)
