#!/usr/bin/env python3
"""The P4's escape, drawn by hand: a via under every signal pin, in two
staggered rows in the channel between the pad tips and the capacitor
ring, and a stub from every supply pin to its ring capacitor.

Usage: p4_escape.py <out.json> [<router run directory>]

Why (CAMERA-LAYOUT.md C-35, C-36 and the acceptance notes): the
router could not get the QFN-104's 0.35 mm pins out (its own fanout
left 26 pins without a legal stub) and every placement it was offered
made it worse. At 0.35 mm pitch, two rows of 0.3 mm vias 0.55 mm apart
are the geometry: neighbouring vias are 0.65 mm apart, a stub passes the
next pin's via with 0.137 mm to spare at 0.127 mm clearance, and the
1.45 mm channel holds both rows with 0.3 mm to the capacitors. JLC's
four-layer floor is a 0.15 mm hole in a 0.25 mm via; these are 0.3/0.15.

Every via and every stub is checked against every pad of every other
part and against the copper already on the board (the hand-routed lanes
and crystals) before anything is written; a pin that has no legal via
is reported with the reason, not drawn wrong. Coordinates are EasyEDA
mm, y up.
"""
import json
import math
import os
import sys

from padgeom import Board

OUT = sys.argv[1] if len(sys.argv) > 1 else "p4_escape.json"
board = Board(sys.argv[2] if len(sys.argv) > 2 else None)
print("pad geometry from", board.run_dir)

U1X, U1Y = 7.863, -8.765
PAD_V = 5.0          # pad centre from the chip centre
ROWS = (5.65, 6.2)   # via rows, from the chip centre
VIA_D, VIA_DRILL = 0.3, 0.15
STUB_W = 0.127
CLEAR = 0.127
STUB_DIAG_V = 6.3    # a supply stub turns toward its capacitor here
MAX_CAP_SHIFT = 0.9  # a supply stub reaches a capacitor this far along the side (C30 sits 0.86 from pin 41)
# a pin whose own column is blocked (a resistor pad over it) steps aside
# this far, 45 degrees first, before it goes out to its row
SIDESTEPS = (-0.5, 0.5, -0.35, 0.35)

HAND = {"CSI_A_CLKN", "CSI_A_CLKP", "CSI_A_DATAN0", "CSI_A_DATAN1", "CSI_A_DATAP0", "CSI_A_DATAP1",
        "CSI_CLKN", "CSI_CLKP", "CSI_DATAN0", "CSI_DATAN1", "CSI_DATAP0", "CSI_DATAP1", "CSI_REXT",
        "XTAL_32K_N", "XTAL_32K_P", "XTAL_N", "XTAL_P"}
SUPPLY = {"3V3", "VDD_HP", "1V8_PSRAM", "2V5_MIPI", "VDD_FLASH", "VDDO_4"}

# side -> (outward unit vector, along unit vector)
SIDES = {
    "right": ((1, 0), (0, 1)),
    "left": ((-1, 0), (0, 1)),
    "top": ((0, 1), (1, 0)),
    "bottom": ((0, -1), (1, 0)),
}


def side_of(p):
    dx, dy = p.x - U1X, p.y - U1Y
    if abs(dx) > abs(dy):
        return "right" if dx > 0 else "left"
    return "top" if dy > 0 else "bottom"


def to_uv(x, y, side):
    out, along = SIDES[side]
    dx, dy = x - U1X, y - U1Y
    return (dx * along[0] + dy * along[1], dx * out[0] + dy * out[1])


def to_xy(u, v, side):
    out, along = SIDES[side]
    return (round(U1X + along[0] * u + out[0] * v, 3), round(U1Y + along[1] * u + out[1] * v, 3))


# obstacles: every pad that is not U1's, as rectangles with their net and name
obstacles = [(p.rect(), p.net, f"{p.component}.{p.number}") for p in board.pads if p.component != "U1"]

# the artifact splits copper into what the router may not touch and what it
# may; both are obstacles here. Its y points down.
copper_segments = []  # (x0, y0, x1, y1, half width, net, layer)
copper_vias = []      # (x, y, radius, net)
raw = json.load(open(os.path.join(board.run_dir, "copilot-router-input.json")))["board"]["copper"]
for group in ("fixed", "editable"):
    for t in raw[group]["tracks"]:
        pts = t["points"]
        for a, b in zip(pts, pts[1:]):
            copper_segments.append((a["x"], -a["y"], b["x"], -b["y"], t["widthMm"] / 2, t["net"], t["layer"]))
    for v in raw[group]["vias"]:
        copper_vias.append((v["at"]["x"], -v["at"]["y"], v["diameterMm"] / 2, v["net"]))
print(f"existing copper: {len(copper_segments)} segments, {len(copper_vias)} vias")


def rect_point_distance(r, x, y):
    x0, y0, x1, y1 = r
    return math.hypot(max(x0 - x, 0, x - x1), max(y0 - y, 0, y - y1))


def seg_point_distance(x0, y0, x1, y1, x, y):
    vx, vy = x1 - x0, y1 - y0
    L2 = vx * vx + vy * vy
    t = 0 if L2 == 0 else max(0, min(1, ((x - x0) * vx + (y - y0) * vy) / L2))
    return math.hypot(x - (x0 + t * vx), y - (y0 + t * vy))


def seg_seg_distance(a, b):
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b

    def orient(px, py, qx, qy, rx, ry):
        return (qx - px) * (ry - py) - (qy - py) * (rx - px)

    o1, o2 = orient(ax0, ay0, ax1, ay1, bx0, by0), orient(ax0, ay0, ax1, ay1, bx1, by1)
    o3, o4 = orient(bx0, by0, bx1, by1, ax0, ay0), orient(bx0, by0, bx1, by1, ax1, ay1)
    if o1 * o2 < 0 and o3 * o4 < 0:
        return 0.0
    return min(seg_point_distance(ax0, ay0, ax1, ay1, bx0, by0), seg_point_distance(ax0, ay0, ax1, ay1, bx1, by1),
               seg_point_distance(bx0, by0, bx1, by1, ax0, ay0), seg_point_distance(bx0, by0, bx1, by1, ax1, ay1))


def rect_seg_distance(r, seg):
    x0, y0, x1, y1 = r
    if x0 <= seg[0] <= x1 and y0 <= seg[1] <= y1:
        return 0.0
    edges = ((x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0))
    return min(seg_seg_distance(e, seg) for e in edges)


def via_block(x, y, net, own_vias):
    """Why a via of VIA_D at (x, y) is illegal, or None."""
    r = VIA_D / 2
    for rect, pnet, name in obstacles:
        if pnet != net and rect_point_distance(rect, x, y) < r + CLEAR - 1e-6:
            return f"pad {name} ({pnet})"
    for sx0, sy0, sx1, sy1, hw, snet, _ in copper_segments:
        if snet != net and seg_point_distance(sx0, sy0, sx1, sy1, x, y) < r + hw + CLEAR - 1e-6:
            return f"track {snet}"
    for vx, vy, vr, vnet in copper_vias + own_vias:
        if vnet != net and math.hypot(vx - x, vy - y) < r + vr + CLEAR - 1e-6:
            return f"via {vnet}"
    return None


def seg_block(seg, net, hw, own_vias):
    """Why a track segment of half width hw is illegal, or None."""
    for rect, pnet, name in obstacles:
        if pnet != net and rect_seg_distance(rect, seg) < hw + CLEAR - 1e-6:
            return f"pad {name} ({pnet})"
    for sx0, sy0, sx1, sy1, shw, snet, layer in copper_segments:
        if layer == "TOP" and snet != net and seg_seg_distance((sx0, sy0, sx1, sy1), seg) < hw + shw + CLEAR - 1e-6:
            return f"track {snet}"
    for vx, vy, vr, vnet in copper_vias + own_vias:
        if vnet != net and seg_point_distance(seg[0], seg[1], seg[2], seg[3], vx, vy) < vr + hw + CLEAR - 1e-6:
            return f"via {vnet}"
    return None


def path_block(points, net, own_vias):
    for a, b in zip(points, points[1:]):
        why = seg_block((a[0], a[1], b[0], b[1]), net, STUB_W / 2, own_vias)
        if why:
            return why
    return None


# the pins that need an escape, by side
pins = {}
for p in board.pads_of("U1"):
    if not p.number.isdigit() or int(p.number) > 104:
        continue
    if p.net in HAND or p.net in ("", "GND"):
        continue
    side = side_of(p)
    u, v = to_uv(p.x, p.y, side)
    pins.setdefault(side, []).append((int(p.number), p.net, u))
for side in pins:
    pins[side].sort()

tracks = []
vias = []
placed_vias = []  # (x, y, r, net)
report = {}       # pin -> (side, net, row, sidestep)
skipped = []


def track(net, *points, layer="top", width=STUB_W):
    tracks.append({"net": net, "layer": layer, "width": width,
                   "points": [{"x": round(x, 3), "y": round(y, 3)} for x, y in points]})


def via(net, x, y, diameter=VIA_D, drill=VIA_DRILL):
    vias.append({"net": net, "x": round(x, 3), "y": round(y, 3), "diameter": diameter, "drill": drill})
    placed_vias.append((x, y, diameter / 2, net))


def try_escape(side, num, net, u, row, du):
    """A via at (u+du, row) with its stub; None on success, else the reason."""
    x, y = to_xy(u + du, ROWS[row - 1], side)
    why = via_block(x, y, net, placed_vias)
    if why:
        return why
    px, py = to_xy(u, PAD_V, side)
    points = [(px, py)] + ([to_xy(u + du, PAD_V + abs(du), side)] if du else []) + [(x, y)]
    why = path_block(points, net, placed_vias)
    if why:
        return "stub: " + why
    track(net, *points)
    via(net, x, y)
    report[num] = (side, net, row, du)
    return None


for side, lst in pins.items():
    prev_num, prev_row = None, None
    for num, net, u in lst:
        preferred = 1 if num % 2 else 2
        rows = [preferred, 3 - preferred]
        if prev_num is not None and num == prev_num + 1 and prev_row in rows:
            # the neighbour's row: its via is 0.35 mm along, this one's must not be
            rows.remove(prev_row)
        reasons = []
        row_taken = None
        for row in rows:
            why = try_escape(side, num, net, u, row, 0)
            if why is None:
                row_taken = row
                break
            reasons.append(f"row {row}: {why}")
        if row_taken is None:
            for du in SIDESTEPS:
                for row in (2, 1):
                    why = try_escape(side, num, net, u, row, du)
                    if why is None:
                        row_taken = row
                        break
                    reasons.append(f"row {row} {du:+.2f}: {why}")
                if row_taken is not None:
                    break
        if row_taken is None:
            skipped.append((side, num, net, "; ".join(reasons)))
        prev_num, prev_row = num, row_taken

# supply stubs: from a supply pin's via toward the ring capacitor of its net
cap_stubs = []
for side, lst in pins.items():
    for num, net, u in lst:
        if net not in SUPPLY or num not in report:
            continue
        row, du = report[num][2], report[num][3]
        vu = u + du
        best = None
        for p in board.pads:
            if p.component == "U1" or p.net != net or not p.component.startswith("C"):
                continue
            pu, pv = to_uv(p.x, p.y, side)
            if 6.6 <= pv <= 7.6 and abs(pu - vu) <= MAX_CAP_SHIFT:
                if best is None or abs(pu - vu) < abs(best[1] - vu):
                    best = (p, pu, pv)
        if best is None:
            continue
        p, pu, pv = best
        shift = abs(pu - vu)
        v_row = ROWS[row - 1]
        start = to_xy(vu, v_row, side)
        end = (round(p.x, 3), round(p.y, 3))
        # three shapes, prettiest first: out of the via and 45 degrees into
        # the capacitor's pad centre; out past the second row, 45 degrees as
        # far as the pad's height allows and level for the rest; out past
        # the second row and level. A 45-degree leg that starts lower runs
        # over the neighbouring pin's second-row via.
        shapes = []
        if shift < 1e-6:
            shapes.append([start, end])
        else:
            v_t = pv - shift
            if v_t >= v_row + 0.1:
                shapes.append([start, to_xy(vu, v_t, side), end])
            over = STUB_DIAG_V + 0.25
            s = min(shift, pv - over)
            shapes.append([start, to_xy(vu, over, side), to_xy(vu + math.copysign(s, pu - vu), over + s, side), to_xy(pu, over + s, side), end])
            shapes.append([start, to_xy(vu, over, side), to_xy(pu, over, side), end])
        why = None
        for points in shapes:
            points = [q for i, q in enumerate(points) if i == 0 or q != points[i - 1]]
            why = path_block(points, net, placed_vias)
            if why is None:
                track(net, *points)
                cap_stubs.append((num, p.component, len(points)))
                break
        if why:
            skipped.append((side, f"stub {num}->{p.component}", net, why))

# The core rail and the PSRAM's 1.8 V on the bottom layer (C-54, C-56).
# Mazed by the router VDD_HP took 85 mm and six vias and 3V3 292 mm and
# 36; the DSL cannot pour an island on L3 (its plane regions are the
# whole board or nothing) and the shim draws only on TOP and BOTTOM. So
# VDD_HP is an L on the bottom layer 8.3 mm from the chip's centre
# (down the left side from pin 54 past pin 76, along the bottom to pin
# 91) with a spur from each pin's escape via, a via down to L2's output
# pad and a top-layer run from there to C27. Pin 26 (top right) reaches
# the L on the inner layer by the router: a right leg would wall every
# right-side escape on the bottom layer for one pin. 1V8_PSRAM joins its
# three left-side pins on a shorter run inside the L; the two never cross
# because the L's spurs at pins 54 and 76 bracket the 1V8 pins.
RING_V, RING_W, CHAMFER = 8.3, 0.8, 0.8  # C-54: the trunk is 0.8 mm; only the spurs between the escape vias are thinner
INNER_V = 7.1
BOTTOM_VIA = (0.6, 0.3)
raw_pads = json.load(open(os.path.join(board.run_dir, "copilot-router-input.json")))["board"]["pads"]
through = {(p["component"], p["number"]) for p in raw_pads if "BOTTOM" in p.get("layers", [])}


def seg_block_bottom(seg, net, hw, own_vias):
    """A bottom-layer segment sees only through-hole pads, vias and copper."""
    for (rect, pnet, name) in obstacles:
        comp, _, num = name.partition(".")
        if (comp, num) in through and pnet != net and rect_seg_distance(rect, seg) < hw + CLEAR - 1e-6:
            return f"pad {name} ({pnet})"
    for sx0, sy0, sx1, sy1, shw, snet, layer in copper_segments:
        if layer == "BOTTOM" and snet != net and seg_seg_distance((sx0, sy0, sx1, sy1), seg) < hw + shw + CLEAR - 1e-6:
            return f"track {snet}"
    for vx, vy, vr, vnet in copper_vias + own_vias:
        if vnet != net and seg_point_distance(seg[0], seg[1], seg[2], seg[3], vx, vy) < vr + hw + CLEAR - 1e-6:
            return f"via {vnet}"
    return None


def bottom_path(net, width, points, label):
    why = None
    for a, b in zip(points, points[1:]):
        why = seg_block_bottom((a[0], a[1], b[0], b[1]), net, width / 2, placed_vias)
        if why:
            break
    if why:
        skipped.append(("bottom", label, net, why))
        return False
    track(net, *points, layer="bottom", width=width)
    return True


def via_of(num):
    side, net, row, du = report[num]
    u = next(u for n, _, u in pins[side] if n == num)
    return side, to_xy(u + du, ROWS[row - 1], side), u + du


power = []
vdd = [n for n, r in report.items() if r[1] == "VDD_HP"]
if all(n in report for n in (54, 76, 91)):
    left_x = U1X - RING_V
    # the bottom leg sits 0.77 mm inside the ring radius: it goes on east
    # to the test point and must stay out from under the 40 MHz crystal
    # (its body ends at -17.4) and clear of the bottom row's vias
    bottom_y = -16.3
    corner_y = bottom_y + CHAMFER
    y54, y76, y26 = via_of(54)[1][1], via_of(76)[1][1], via_of(26)[1][1]
    x91 = via_of(91)[1][0]
    tp11 = next(q for q in board.pads_of("TP11") if q.net == "VDD_HP")
    # the trunk runs 0.3 mm past the outermost spurs: two tracks that meet
    # end to end are merged by the assembler into one at the narrower width,
    # and the left leg came back 0.13 mm wide above pin 76. Past pin 91 it
    # carries on east and rises to the test point: routed, that stub went
    # 180 mm round the left and bottom edges of the board.
    # centred in the 1.22 mm between TP11 and TP14; the top-layer stub is
    # narrower than the via so its round end stays inside the via's edge
    # The leg ends on a via 7 mm short of the test point's column, and the
    # router takes it from there on whichever layer is free: drawn all the
    # way to TP11, with a right leg for pin 26, the run walled the bottom
    # layer along the whole right side and the router rolled a 45-minute
    # pass back rather than finish. Pin 26 reaches the L by the router too.
    east_via = (24.5, bottom_y)
    ring = [(left_x, y54 + 0.3), (left_x, corner_y), (left_x + CHAMFER, bottom_y), east_via]
    if bottom_path("VDD_HP", RING_W, ring, "VDD_HP L"):
        power.append("VDD_HP L")
        if via_block(*east_via, "VDD_HP", placed_vias) is None:
            via("VDD_HP", *east_via, *BOTTOM_VIA)
            power.append("east via")
        else:
            skipped.append(("bottom", "east via", "VDD_HP", via_block(*east_via, "VDD_HP", placed_vias)))
    for num in (54, 76, 91):
        side, (vx, vy), _ = via_of(num)
        end = {"left": (left_x, vy), "bottom": (vx, bottom_y)}[side]
        if bottom_path("VDD_HP", STUB_W, [(vx, vy), end], f"spur {num}"):
            power.append(f"spur {num}")
    # down to the core buck: a via just above L2's output pad, the pad from
    # the top, then L2 to C27 on top
    l2 = next(q for q in board.pads_of("L2") if q.net == "VDD_HP")
    c27 = next(q for q in board.pads_of("C27") if q.net == "VDD_HP")
    vx, vy = l2.x, l2.y + l2.h / 2 + 0.127 + BOTTOM_VIA[0] / 2 + 0.05
    if via_block(vx, vy, "VDD_HP", placed_vias) is None and bottom_path("VDD_HP", RING_W, [(vx, bottom_y), (vx, vy)], "drop to L2"):
        via("VDD_HP", vx, vy, *BOTTOM_VIA)
        track("VDD_HP", (vx, vy), (l2.x, l2.y), width=RING_W)
        run = [(l2.x, l2.y), (l2.x, c27.y + 1.8), (c27.x - 0.3, c27.y + 1.1), (c27.x - 0.3, c27.y)]
        why = path_block(run, "VDD_HP", placed_vias)
        if why:
            skipped.append(("top", "L2 to C27", "VDD_HP", why))
        else:
            track("VDD_HP", *run, width=RING_W)
            power.append("L2->C27")
    else:
        skipped.append(("bottom", "drop to L2", "VDD_HP", via_block(vx, vy, "VDD_HP", placed_vias) or "path"))

if all(n in report for n in (59, 67, 72)):
    inner_x = U1X - INNER_V
    ys = [via_of(n)[1][1] for n in (59, 67, 72)]
    if bottom_path("1V8_PSRAM", 0.3, [(inner_x, max(ys) + 0.3), (inner_x, min(ys) - 0.3)], "1V8 run"):
        power.append("1V8 run")
    for num in (59, 67, 72):
        _, (vx, vy), _ = via_of(num)
        if bottom_path("1V8_PSRAM", STUB_W, [(vx, vy), (inner_x, vy)], f"spur {num}"):
            power.append(f"spur {num}")

# Two more runs the router took the long way round (156 mm for the
# flash's supply, 115 mm for a clock between two pads 11 mm apart).
# VDD_FLASH leaves pin 30's escape via on the bottom layer, east along the
# top of the ring to a via at R15 and on to its test point, with a branch
# to the flash's supply pin; pin 71's end of the net reaches pin 30 by the
# router. I2C_SCL runs on top, over the camera connector's upper row, to
# its pull-up.
far = []
if 30 in report:
    _, (px, py), _ = via_of(30)
    u8 = next(q for q in board.pads_of("U8") if q.net == "VDD_FLASH")
    r15 = next(q for q in board.pads_of("R15") if q.net == "VDD_FLASH")
    # the run stops at R15's via; the test point beyond it is the router's
    # (drawn to TP15 it walled the top right of the bottom layer)
    y_run = -2.115
    r15_via = (r15.x, r15.y - r15.h / 2 - 0.127 - BOTTOM_VIA[0] / 2 - 0.15)
    trunk = [(px, py), (px, y_run), (r15_via[0] - (y_run - r15_via[1]), y_run), r15_via]
    ok = bottom_path("VDD_FLASH", 0.2, trunk, "VDD_FLASH run")
    for name, at, pad in (("R15", r15_via, r15),):
        if ok and via_block(*at, "VDD_FLASH", placed_vias) is None:
            via("VDD_FLASH", *at, *BOTTOM_VIA)
            track("VDD_FLASH", at, (pad.x, pad.y), width=0.2)
            far.append(name)
        elif ok:
            skipped.append(("bottom", f"via at {name}", "VDD_FLASH", via_block(*at, "VDD_FLASH", placed_vias)))
    u8_via = (u8.x, u8.y - u8.h / 2 - 0.127 - BOTTOM_VIA[0] / 2 - 0.1)
    bx = u8.x - 0.47
    branch = [(bx, y_run), (bx, u8_via[1] - 0.47), u8_via]
    if ok and via_block(*u8_via, "VDD_FLASH", placed_vias) is None and bottom_path("VDD_FLASH", 0.2, branch, "U8 branch"):
        via("VDD_FLASH", *u8_via, *BOTTOM_VIA)
        track("VDD_FLASH", u8_via, (u8.x, u8.y), width=0.2)
        far.append("U8")
    elif ok:
        skipped.append(("bottom", "via at U8", "VDD_FLASH", via_block(*u8_via, "VDD_FLASH", placed_vias) or "path"))

j4 = next(q for q in board.pads_of("J4") if q.net == "I2C_SCL")
r30 = next(q for q in board.pads_of("R30") if q.net == "I2C_SCL")
y_over = j4.y + j4.h / 2 + 0.127 + STUB_W / 2 + 0.15
scl = [(j4.x, j4.y), (j4.x, y_over), (r30.x, y_over), (r30.x, r30.y)]
why = path_block(scl, "I2C_SCL", placed_vias)
if why:
    skipped.append(("top", "I2C_SCL", "I2C_SCL", why))
else:
    track("I2C_SCL", *scl)
    far.append("I2C_SCL")

# The ring's own supply links, the ones the autorouter left open after
# everything else: the 2.5 V capacitors joined along the top ring, pin 73's
# load capacitor reached on top through the 0.7 mm between C34 and C35 and
# round the ring's foot, the two outer 3V3 capacitors joined, and pins 75
# and 77 (both 3V3, one VDD_HP pin between them) joined on the bottom
# layer between their own vias.
links = []


def top_link(net, points, label):
    why = path_block(points, net, placed_vias)
    if why:
        skipped.append(("top", label, net, why))
    else:
        track(net, *points)
        links.append(label)


c30 = next(q for q in board.pads_of("C30") if q.net == "2V5_MIPI")
c32 = next(q for q in board.pads_of("C32") if q.net == "2V5_MIPI")
top_link("2V5_MIPI", [(c30.x, c30.y), (c32.x, c32.y)], "C30-C32")
if 73 in report:
    _, (vx, vy), _ = via_of(73)
    c31 = next(q for q in board.pads_of("C31") if q.net == "2V5_MIPI")
    c34 = next(q for q in board.pads_of("C34") if q.net != "GND")
    c35 = next(q for q in board.pads_of("C35") if q.net != "GND")
    # west along pin 73's own row: it is the midpoint between the vias of
    # pins 72 and 74, and a 0.127 mm track has 0.146 mm to pass between
    # them; then down the west side of the ring's outer (ground) pads and
    # into C31's supply pad from below
    outer = min(q.x - q.w / 2 for q in board.pads_of("C35") + board.pads_of("C31"))
    x_out = outer - 0.127 - STUB_W / 2 - 0.1
    below = c31.y - c31.h / 2 - 0.127 - STUB_W / 2 - 0.15
    pts = [(vx, vy), (x_out + 0.3, vy), (x_out, vy - 0.3), (x_out, below + 0.3), (x_out + 0.3, below), (c31.x, below), (c31.x, c31.y)]
    top_link("2V5_MIPI", pts, "73-C31")
c21 = next(q for q in board.pads_of("C21") if q.net == "3V3")
c22 = next(q for q in board.pads_of("C22") if q.net == "3V3")
top_link("3V3", [(c22.x, c22.y), (c21.x, c21.y)], "C21-C22")
if 75 in report and 77 in report:
    _, a75, _ = via_of(75)
    _, a77, _ = via_of(77)
    if bottom_path("3V3", STUB_W, [a75, a77], "75-77"):
        links.append("75-77")

payload = {"components": [], "tracks": tracks, "vias": vias}
json.dump(payload, open(OUT, "w"), indent=1)
print("power on the bottom layer:", " ".join(power))
print("far runs:", " ".join(far))
print("ring links:", " ".join(links))
for side in ("right", "top", "left", "bottom"):
    rows = [(n, r) for n, r in report.items() if r[0] == side]
    print(f"{side:6s}: {len(rows)} vias  " + " ".join(f"{n}:{r[2]}{'*' if r[3] else ''}" for n, r in sorted(rows)))
print("supply stubs (points):", " ".join(f"{n}->{c}({k})" for n, c, k in cap_stubs))
for s in skipped:
    print("SKIPPED", s)
print(f"wrote {OUT}: {len(tracks)} tracks, {len(vias)} vias")
