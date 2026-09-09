#!/usr/bin/env python3
"""The sixteen nets the router could not do, routed by hand from the real
pads: the six MIPI D-PHY lanes on both sides of their series resistors,
the D-PHY reference resistor, and the two crystals with their loads.

Usage: csi_tracks.py <out.json> [<router run directory>]

Why by hand (CAMERA-LAYOUT.md C-20, C-31): the P4 orders its CSI pins
D1, CLK, D0 and puts the clock's N before its P; the Pi connector wants
CLK, D1, D0 with P before N, and holds its contacts in two rows 3.4 mm
apart with 0.4 mm between neighbours. So the clock must cross itself and
the D1 pair must cross the clock, and two layers cannot hold both
crossings in the same place. The router answered "polarity-swap-denied"
and "no-escape-path" for three runs. Here the two crossings are kept
apart: the clock's polarity crossing happens between the P4 and the
resistors (CLK N dips to the bottom layer through two vias, CLK P is
never interrupted), the group crossing between the resistors and the
connector (the D1 pair runs on the bottom layer to two vias between the
connector's rows). Six vias in all; every other lane stays on top.

Coordinates are EasyEDA mm, y up. The file carries tracks and vias in the
shape the shim serves and the extension draws; it moves no part. Widths:
0.13 mm for the lanes (the impedance solver's 100 ohm line at a 0.25 mm
gap in the ground flood), 0.2 mm for the crystals.
"""
import json
import math
import sys

from padgeom import Board

OUT = sys.argv[1] if len(sys.argv) > 1 else "csi_tracks.json"
board = Board(sys.argv[2] if len(sys.argv) > 2 else None)
print("pad geometry from", board.run_dir)

CSI_W = 0.13
XTAL_W = 0.2
VIA = {"diameter": 0.6, "drill": 0.3}

tracks = []
vias = []


def P(designator, number):
    p = board.pad(designator, number)
    return (round(p.x, 3), round(p.y, 3))


def track(net, layer, width, *points):
    tracks.append({"net": net, "layer": layer, "width": width, "points": [{"x": round(x, 3), "y": round(y, 3)} for x, y in points]})


def via(net, x, y):
    vias.append({"net": net, "x": round(x, 3), "y": round(y, 3), **VIA})


# Every pad this file relies on, checked against the board before anything
# is drawn: a moved part makes the waypoints wrong, and the file refuses
# rather than draw into the wrong place.
EXPECT = {
    ("U1", 47): (5.238, -3.765), ("U1", 46): (5.588, -3.765), ("U1", 45): (5.938, -3.765),
    ("U1", 44): (6.288, -3.765), ("U1", 43): (6.638, -3.765), ("U1", 42): (6.988, -3.765),
    ("U1", 48): (4.888, -3.765), ("U1", 99): (10.488, -13.765), ("U1", 100): (10.838, -13.765),
    ("U1", 104): (12.238, -13.765), ("U1", 1): (12.863, -13.14),
    ("R27", 1): (2.1, 1.15), ("R26", 1): (3.6, 1.15), ("R29", 1): (5.4, 1.15), ("R28", 1): (7.1, 1.15),
    ("R25", 1): (8.7, 1.15), ("R24", 1): (10.2, 1.15), ("R20", 1): (3.9, -2.353),
    ("J4", 9): (3.0, 9.9), ("J4", 8): (4.0, 6.52), ("J4", 6): (5.0, 6.52), ("J4", 5): (5.0, 9.9),
    ("J4", 3): (6.0, 9.9), ("J4", 2): (7.0, 6.52),
    ("Y2", 1): (11.0, -18.15), ("Y2", 3): (8.8, -19.85), ("C37", 1): (12.58, -18.5), ("C38", 1): (8.02, -21.5),
    ("Y1", 1): (15.9, -12.65), ("Y1", 2): (15.9, -15.15), ("C39", 1): (17.88, -12.6), ("C40", 1): (17.88, -14.6),
}
for (d, n), (x, y) in EXPECT.items():
    ax, ay = P(d, n)
    if abs(ax - x) > 0.05 or abs(ay - y) > 0.05:
        sys.exit(f"{d}.{n} is at ({ax}, {ay}), this file was drawn for ({x}, {y}); re-derive the waypoints")

# First halves: P4 pins to the resistors' lower pads. Six lanes leave the
# pads at 0.35 mm pitch and climb the corridor between the ring capacitors
# (x 4.6..7.6). The D1 pair turns left first and passes over R20/C20, the
# D0 pair turns right and passes over C30/C32; the clock pair swaps
# polarity in between: N jogs left and dips to the bottom layer, P climbs
# straight past N's via and comes to R29 on the left. Where two diagonals
# run parallel their intercepts differ by at least 0.37 mm (0.26 mm apart,
# for 0.13 mm lines at 0.127 mm clearance).
track("CSI_DATAP1", "top", CSI_W, P("U1", 47), (5.238, -2.5), (4.6, -1.862), (4.6, -0.3), (4.25, 0.05), (2.45, 0.05), (2.1, 0.4), P("R27", 1))
track("CSI_DATAN1", "top", CSI_W, P("U1", 46), (5.588, -2.2), (4.95, -1.562), (4.95, 0.0), (4.6, 0.35), (3.95, 0.35), (3.6, 0.7), P("R26", 1))
track("CSI_CLKN", "top", CSI_W, P("U1", 45), (5.938, -1.6), (5.6, -1.262), (5.6, -1.0))
via("CSI_CLKN", 5.6, -1.0)
track("CSI_CLKN", "bottom", CSI_W, (5.6, -1.0), (7.1, 0.25))
via("CSI_CLKN", 7.1, 0.25)
track("CSI_CLKN", "top", CSI_W, (7.1, 0.25), P("R28", 1))
track("CSI_CLKP", "top", CSI_W, P("U1", 44), (6.288, 0.3), (5.4, 1.188), P("R29", 1))
track("CSI_DATAP0", "top", CSI_W, P("U1", 43), (6.638, -1.222), (8.7, 0.84), P("R25", 1))
track("CSI_DATAN0", "top", CSI_W, P("U1", 42), (6.988, -1.272), (8.7, 0.44), (9.94, 0.44), (10.2, 0.70), P("R24", 1))
# The D-PHY reference resistor, C-38: pin 48 into R20's pad from the right.
track("CSI_REXT", "top", 0.15, P("U1", 48), (4.888, -3.2), (4.15, -2.462), (4.3, -2.4))

# Second halves: resistors' upper pads to the connector. The lower row's
# pads are 0.60 wide at 1.0 mm pitch, so a 0.13 mm line passes between two
# of them with 0.135 mm to spare; that is how the upper row is reached.
# Clock, on top, uncrossed now: P through the gap between pads 12 and 10
# to pad 9 in the upper row, N into pad 8 from below.
track("CSI_A_CLKP", "top", CSI_W, P("R29", 2), (5.4, 3.1), (3.5, 5.0), (3.5, 7.6), (3.0, 8.1), P("J4", 9))
track("CSI_A_CLKN", "top", CSI_W, P("R28", 2), (7.1, 3.0), (4.4, 5.7), (4.1, 6.0))
# D0, on top, uncrossed: P through the gap between pads 4 and 2 to pad 3.
track("CSI_A_DATAP0", "top", CSI_W, P("R25", 2), (8.7, 3.2), (6.5, 5.4), (6.5, 9.9), P("J4", 3))
track("CSI_A_DATAN0", "top", CSI_W, P("R24", 2), (10.2, 3.0), (7.4, 5.8), (7.0, 6.2))
# D1, the group crossing: under the clock on the bottom layer, from vias
# beside the resistors' upper pads to vias in the 1.6 mm between the
# connector's rows; then P down into pad 6 from above, N into pad 5's
# lower right corner.
track("CSI_A_DATAP1", "top", CSI_W, P("R27", 2), (2.1, 3.55))
via("CSI_A_DATAP1", 2.1, 3.55)
track("CSI_A_DATAP1", "bottom", CSI_W, (2.1, 3.55), (4.9, 8.15))
via("CSI_A_DATAP1", 4.9, 8.15)
track("CSI_A_DATAP1", "top", CSI_W, (4.9, 8.15), (5.0, 7.3), P("J4", 6))
track("CSI_A_DATAN1", "top", CSI_W, P("R26", 2), (3.6, 3.55))
via("CSI_A_DATAN1", 3.6, 3.55)
track("CSI_A_DATAN1", "bottom", CSI_W, (3.6, 3.55), (5.9, 8.15))
via("CSI_A_DATAN1", 5.9, 8.15)
track("CSI_A_DATAN1", "top", CSI_W, (5.9, 8.15), (5.5, 8.55), (5.2, 9.2), P("J4", 5))

# 40 MHz crystal, C-31: it hangs under the ring, its pad columns astride
# pins 99/100. Pin 100 drops straight through the ring gap between C14 and
# C16 into pad 1 (P, top right); pin 99 drops beside it, steps left into
# the channel between the crystal's pad columns and reaches pad 3 (N,
# bottom left). Both stubs are 0.127 mm: they pass the escape vias of
# pins 98 and 101 at 0.35 mm. The loads sit right and below.
track("XTAL_P", "top", CSI_W, P("U1", 100), (10.838, -18.0))
track("XTAL_P", "top", XTAL_W, (11.7, -18.15), (12.0, -18.45), (12.4, -18.5), P("C37", 1))
track("XTAL_N", "top", CSI_W, P("U1", 99), (10.488, -16.9), (9.9, -17.49), (9.9, -19.6), (9.55, -19.6))
track("XTAL_N", "top", XTAL_W, (8.8, -20.4), (8.8, -20.9), (8.3, -21.4), (8.2, -21.5), P("C38", 1))
# 32 kHz crystal, C-31: pin 1 along the corner into pad 1; pin 104 under
# the corner, over C16, into pad 2; the loads to the right.
# 32 kHz: pin 1's track drops 0.45 mm before it turns right, so the escape
# via of pin 2 (0.35 mm above) has its clearance.
track("XTAL_32K_P", "top", XTAL_W, P("U1", 1), (12.863, -13.6), (14.6, -13.6), (15.1, -13.1), (15.45, -13.1))
track("XTAL_32K_P", "top", XTAL_W, (16.3, -12.65), P("C39", 1))
track("XTAL_32K_N", "top", XTAL_W, P("U1", 104), (12.238, -14.2), (12.9, -14.3), (14.9, -14.3), (15.2, -14.6), (15.5, -14.9))
track("XTAL_32K_N", "top", XTAL_W, (16.3, -15.0), (17.5, -14.6), P("C40", 1))

# C-20: intra-pair skew is 3.4 mm by construction (the connector's two rows)
# and no more. Measured over the whole path, P4 pin to connector pad, both
# halves of each line; a via barrel is not counted. EasyEDA's own DRC
# reports these pairs against its 10 mil default, which no board with this
# connector can meet; this is the check that means something.
MAX_SKEW = 3.4


def length(net):
    return sum(math.hypot(b["x"] - a["x"], b["y"] - a["y"])
               for t in tracks if t["net"] == net for a, b in zip(t["points"], t["points"][1:]))


for lane, n in (("CLK", ""), ("DATA", "0"), ("DATA", "1")):
    p = length(f"CSI_{lane}P{n}") + length(f"CSI_A_{lane}P{n}")
    q = length(f"CSI_{lane}N{n}") + length(f"CSI_A_{lane}N{n}")
    print(f"pair {lane}{n}: P {p:.2f} mm, N {q:.2f} mm, skew {abs(p - q):.2f} mm")
    if abs(p - q) > MAX_SKEW:
        sys.exit(f"pair {lane}{n} skew {abs(p - q):.2f} mm is over C-20's {MAX_SKEW}; nothing written")

payload = {"components": [], "tracks": tracks, "vias": vias}
json.dump(payload, open(OUT, "w"), indent=1)
nets = sorted({t["net"] for t in tracks})
print(f"wrote {OUT}: {len(tracks)} tracks, {len(vias)} vias, {len(nets)} nets: {', '.join(nets)}")
