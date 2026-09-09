"""Real pad geometry of the board currently open in EasyEDA.

The easyeda-copilot MCP's `get_current_pcb` export has component centres
but no pads. Every `run_pcb_router_dsl` call, even a rules-only one, writes
the board it saw to `$TMPDIR/easyeda-copilot-mcp/copilot-router/pcb-dsl-*/`:
`copilot-router-input.json` carries every pad's absolute position and
shape (y pointing down), `easyeda-routing-input.json` every part's centre,
rotation and layer (y pointing up). This module reads the two into one
`Board` in EasyEDA coordinates, y up, millimetres.
"""
import glob
import json
import math
import os
import tempfile

FREE_PADS = "eFREEPADCOMPONENT"  # the board's loose pads and mounting holes, one board-sized pseudo part


def newest_run():
    runs = sorted(
        glob.glob(os.path.join(tempfile.gettempdir(), "easyeda-copilot-mcp", "copilot-router", "pcb-dsl-*", "copilot-router-input.json")),
        key=os.path.getmtime,
    )
    if not runs:
        raise SystemExit("no router run found; run any run_pcb_router_dsl transaction first (camera-drc.js is rules only)")
    return os.path.dirname(runs[-1])


def _rotate(x, y, degrees):
    a = math.radians(degrees)
    return (x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a))


class Pad:
    __slots__ = ("component", "number", "net", "x", "y", "w", "h")

    def __init__(self, raw):
        self.component = raw["component"]
        self.number = raw["number"]
        self.net = raw.get("net", "")
        self.x = raw["at"]["x"]
        self.y = -raw["at"]["y"]
        s = raw["shape"]
        if s.get("kind") == "rect":
            # the pad's own rotation: a 0603's pads are 0.8 x 0.9 in the
            # footprint and 0.9 x 0.8 on a part turned 90 degrees, and a
            # via placed against the smaller box was 0.09 mm from the copper
            a = math.radians(raw.get("rotationDeg", 0))
            w, h = s["widthMm"], s["heightMm"]
            self.w = abs(w * math.cos(a)) + abs(h * math.sin(a))
            self.h = abs(w * math.sin(a)) + abs(h * math.cos(a))
        elif "diameterMm" in s:
            self.w = self.h = s["diameterMm"]
        else:  # polygon: points relative to the pad centre, in the pad's own frame
            pts = [_rotate(q["x"], q["y"], raw.get("rotationDeg", 0)) for q in s["polygon"]["outer"]]
            self.w = 2 * max(abs(px) for px, _ in pts)
            self.h = 2 * max(abs(py) for _, py in pts)

    def rect(self):
        return (self.x - self.w / 2, self.y - self.h / 2, self.x + self.w / 2, self.y + self.h / 2)

    def distance(self, other):
        return math.hypot(self.x - other.x, self.y - other.y)


class Board:
    def __init__(self, run_dir=None):
        self.run_dir = (run_dir or newest_run()).rstrip("/")
        router = json.load(open(os.path.join(self.run_dir, "copilot-router-input.json")))
        easy = json.load(open(os.path.join(self.run_dir, "easyeda-routing-input.json")))
        self.pads = [Pad(p) for p in router["board"]["pads"]]
        self.parts = easy["components"]
        self.outline = [(x, y) for x, y in easy["boardOutline"]["path"]]
        self._by_part = {}
        for p in self.pads:
            self._by_part.setdefault(p.component, []).append(p)

    def designators(self):
        return [d for d in self.parts if d != FREE_PADS]

    def has(self, designator):
        return designator in self.parts

    def centre(self, designator):
        x, y = self.parts[designator]["location"]
        return (x, y)

    def rotation(self, designator):
        return self.parts[designator]["rotation"]

    def layer(self, designator):
        return self.parts[designator]["layer"]

    def pads_of(self, designator):
        return self._by_part.get(designator, [])

    def pad(self, designator, number):
        for p in self.pads_of(designator):
            if p.number == str(number):
                return p
        raise KeyError(f"{designator} has no pad {number}")

    def holes(self):
        return [p for p in self.pads_of(FREE_PADS) if p.number.startswith("MH")]

    def extents(self, designator):
        rects = [p.rect() for p in self.pads_of(designator)]
        return (min(r[0] for r in rects), min(r[1] for r in rects), max(r[2] for r in rects), max(r[3] for r in rects))

    def box(self, designator, margin=0.25):
        x0, y0, x1, y1 = self.extents(designator)
        return (x0 - margin, y0 - margin, x1 + margin, y1 + margin)

    def box_if_moved(self, designator, x, y, rotation, margin=0.25):
        """The part's box after moving its centre to (x, y) at `rotation`."""
        cx, cy = self.centre(designator)
        x0, y0, x1, y1 = self.extents(designator)
        corners = [_rotate(px - cx, py - cy, -self.rotation(designator)) for px, py in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
        moved = [_rotate(px, py, rotation) for px, py in corners]
        xs = [p[0] + x for p in moved]
        ys = [p[1] + y for p in moved]
        return (min(xs) - margin, min(ys) - margin, max(xs) + margin, max(ys) + margin)

    def pads_if_moved(self, designator, x, y, rotation):
        cx, cy = self.centre(designator)
        out = []
        for p in self.pads_of(designator):
            lx, ly = _rotate(p.x - cx, p.y - cy, -self.rotation(designator))
            nx, ny = _rotate(lx, ly, rotation)
            out.append((nx + x, ny + y, p.net))
        return out

    def centre_distance(self, a, b):
        ax, ay = self.centre(a)
        bx, by = self.centre(b)
        return math.hypot(ax - bx, ay - by)

    def pad_distance(self, a, b, net=None):
        """Nearest pad-to-pad distance between two parts, optionally on one net."""
        best = None
        for p in self.pads_of(a):
            if net is not None and p.net != net:
                continue
            for q in self.pads_of(b):
                if net is not None and q.net != net:
                    continue
                d = p.distance(q)
                if best is None or d < best:
                    best = d
        return best

    def nearest_shared_net(self, a, b, ignore=("GND", "")):
        """Closest pair of pads on a common net that is not ground: (distance, net, pad number on b)."""
        best = None
        for p in self.pads_of(a):
            if p.net in ignore:
                continue
            for q in self.pads_of(b):
                if q.net == p.net:
                    d = p.distance(q)
                    if best is None or d < best[0]:
                        best = (d, p.net, q.number)
        return best


def overlaps(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


class Placement:
    """A hand placement: designator -> (x, y, rotation), checked against every
    other part on the board and written in the shape the shim serves.

    EasyEDA snaps what it is given to its 0.1 mm grid, so the plan is
    snapped first and the checks run on what the board will become. With
    `face`, every two-pad C or R is turned so the pad it shares with that
    part is nearer that part: pad 1 of a C0603 lands at -x in rotation 0,
    and a ring capacitor placed "radially" once had its signal pad on the
    outside, measuring 3.1 mm where 1.9 was there.
    """

    def __init__(self, board, plan, face=None, keep_rotation=()):
        self.board = board
        for d in plan:
            if not board.has(d):
                raise KeyError(f"{d} is not on the board")
        self.face = face
        self.keep_rotation = set(keep_rotation)  # parts whose rotation the plan states outright (a crystal's loads face the crystal, not the chip)
        self.plan = {d: (round(x, 1), round(y, 1), self._facing(d, round(x, 1), round(y, 1), r)) for d, (x, y, r) in plan.items()}

    def _facing(self, d, x, y, rotation):
        if self.face is None or d in self.keep_rotation or not (d.startswith("C") or d.startswith("R")) or len(self.board.pads_of(d)) != 2:
            return rotation
        fx, fy = self.board.centre(self.face)
        face_nets = {p.net for p in self.board.pads_of(self.face)} - {"GND", ""}
        best = None
        for r in (rotation, (rotation + 180) % 360):
            for px, py, net in self.board.pads_if_moved(d, x, y, r):
                if net in face_nets:
                    dist = math.hypot(px - fx, py - fy)
                    if best is None or dist < best[0]:
                        best = (dist, r)
        return best[1] if best else rotation

    def boxes(self):
        boxes = {d: self.board.box(d) for d in self.board.designators()}
        for d, (x, y, rotation) in self.plan.items():
            boxes[d] = self.board.box_if_moved(d, x, y, rotation)
        return boxes

    def collisions(self):
        """Pairs (a, b) where a moved part overlaps anything, moved or not."""
        boxes = self.boxes()
        hits = set()
        for d in self.plan:
            for o in self.board.designators():
                if o != d and overlaps(boxes[d], boxes[o]):
                    hits.add(tuple(sorted((d, o))))
        return sorted(hits), boxes

    def pin_distances(self, chip):
        """For each moved C/R/Y part: (designator, distance, net, chip pad) to
        the nearest pad of `chip` on a shared non-ground net."""
        chip_pads = [p for p in self.board.pads_of(chip) if p.net not in ("GND", "")]
        out = []
        for d in self.plan:
            if d.startswith("U"):
                continue
            best = None
            for px, py, net in self.board.pads_if_moved(d, *self.plan[d]):
                for p in chip_pads:
                    if p.net == net:
                        dist = math.hypot(px - p.x, py - p.y)
                        if best is None or dist < best[0]:
                            best = (dist, net, p.number)
            if best:
                out.append((d, *best))
        return out

    def payload(self):
        return {"components": [{"designator": d, "x": x, "y": y, "rotate": r, "layer": "top"} for d, (x, y, r) in self.plan.items()]}

    def write(self, path):
        json.dump(self.payload(), open(path, "w"), indent=1)
