#!/usr/bin/env python3
"""Hand placement of the parts around the ESP32-P4, written as a file the
shim serves back as a finished layout (tools/copilot-shim, `@local-placement`).

Usage: p4_cluster.py <out.json> [<router run directory>]

Coordinates are EasyEDA mm, y up. Pad geometry comes from the newest
router run (padgeom.py); the parts listed below are moved to the positions
in `plan`, everything else is checked against but never moved. Nothing is
written while any moved part overlaps anything. Each capacitor's pad-to-pin
distance is printed, because C-35 says 3 mm and a number beats a feeling.
"""
import json
import sys

from padgeom import Board, Placement

OUT = sys.argv[1] if len(sys.argv) > 1 else "p4_cluster.json"
board = Board(sys.argv[2] if len(sys.argv) > 2 else None)
print("pad geometry from", board.run_dir)

u1 = board.pad("U1", 1)
assert abs(u1.x - 12.863) < 0.01 and abs(u1.y + 13.14) < 0.01, "U1 moved; the ring coordinates below were laid out around (7.863, -8.765)"

# rotation: 0 = long axis along x. A part on the left or right ring is 0,
# on the top or bottom ring 90. The 0402 capacitors sit 7.3 mm from the
# P4's centre: 1.45 mm between a P4 pad tip and their pad, which is two
# staggered rows of 0.4 mm vias, one under every signal pin. At 6.55 mm the
# channel was 0.56 mm, no via fitted, and twelve signals a side had to
# leave between eight capacitors; the router left fifteen nets open. The
# capacitor's pad is still 1.9-2.3 mm from the pin's. The 0603 bulk parts
# sit at 7.1 where a pin does not need to leave. Along a side the 0402 pitch is 1.25 mm, so a 10 mm side holds
# eight (one per supply pin, which is what C-35 asks) with 0.75 mm
# between pads, room for two 0.127 mm signal lines to leave the chip.
U1X, U1Y = 7.863, -8.765
RING4 = 7.45
R4, R6 = U1X + RING4, U1X + 7.1     # right ring, 0402 / 0603
L4 = U1X - RING4                    # left ring, 0402
T4, T6 = U1Y + RING4, U1Y + 7.2     # top ring; the 0603s at 7.2 so a via under pin 51 clears R20's pad
B4 = U1Y - RING4                    # bottom ring
COL_L = -1.9                        # second column left, 0402
COL_R = 19.2                        # column right of the 32 kHz crystal

plan = {
    # right side, pins 1..26 (y -13.14 .. -4.39)
    "C23": (R6, -3.9, 0),         # pin 26 VDD_HP, 10 uF; a hair above the pin so pin 25 can leave
    "C3":  (R4, -6.14, 0),        # pin 21 3V3
    "C1":  (COL_R, -8.4, 0),      # 3V3 10 uF, outer column: a 0603 in the ring walled off pins 13-17
    "C2":  (R4, -10.34, 0),       # pin 9 3V3
    "Y1":  (15.9, -13.9, 270),    # pins 1 / 104, 32 kHz; pad 1 (P) is the upper one
    "C39": (18.3, -12.6, 0),      # XTAL_32K_P load
    "C40": (18.3, -14.6, 0),      # XTAL_32K_N load
    "C15": (COL_R, -6.4, 0),      # 3V3 10 uF
    "R3":  (COL_R, -18.8, 0),     # EN pull-up
    # left side, pins 53..78 (y -4.39 .. -13.14): one 0402 per supply pin
    "R18": (0.1, -2.9, 0),        # pin 53 USB_DP_C series, above the ring
    # eight slots at 1.25 mm: 0.75 mm between neighbouring pads, which is
    # two 0.127 mm signal lines per gap; at 1.15 mm it was one, and the
    # router left SPI_MISO and its neighbours with no way out
    # slots by rail, not by nearest pin: pins 71-77 are seven supply pins
    # on six rails in 2.1 mm, and a capacitor serves every pin of its own
    # rail within 2.8 mm of its slot
    "C24": (L4, -4.5, 0),         # VDD_HP, pin 54
    "C4":  (L4, -5.75, 0),        # 3V3, pin 62
    "C28": (L4, -7.0, 0),         # 1V8_PSRAM, pins 59 and 67
    "C19": (L4, -8.25, 0),        # 3V3 second, pin 62 again
    "C29": (L4, -9.5, 0),         # 1V8_PSRAM, pins 67 and 72
    "C34": (L4, -10.75, 0),       # VDD_FLASH, pin 71
    "C35": (L4, -12.0, 0),        # VDDO_4, pin 74
    "C31": (L4, -13.25, 0),       # 2V5_MIPI, pin 73
    # two corner slots under pins 75-77; the ring alone has four slots
    # within 2.3 mm of those pins and five rails want them
    "C17": (2.8, -15.0, 0),       # 3V3, pins 75 and 77
    "C25": (0.9, -14.9, 0),       # VDD_HP, pin 76
    "C22": (COL_L, -10.5, 0),     # 3V3 10 nF
    "C21": (COL_L, -11.65, 0),    # 3V3 third
    "C18": (-3.3, -14.2, 0),      # 3V3 10 uF
    # top side, pins 27..52 (x 12.24 .. 3.49); CSI corridor x 4.6..7.6 kept free
    "R19": (-3.0, -1.3, 90),      # pin 52 USB_DN_C series (full-speed USB, 6 mm is nothing)
    "C20": (2.3, T6, 90),         # pin 51 3V3, 4.7 uF
    "R20": (3.9, T6, 90),         # pin 48 CSI_REXT, the D-PHY reference: C-38 wants it at the pin
    "C30": (8.2, T4, 90),         # pin 41 2V5_MIPI 1 uF
    "C32": (9.4, T4, 90),         # pin 41 2V5_MIPI 10 nF
    "C33": (11.19, T4, 90),       # pin 30 VDD_FLASH 1 uF
    # CSI series resistors, one row between the ring and J4, pairs side by side
    # The row is 1.8 mm above the ring so four lanes can turn under it; the
    # order is the P4's (D1, CLK, D0), so the first halves run straight up.
    # The Pi connector wants CLK, D1, D0: the D1 pair's second half crosses
    # the clock on the bottom layer (camera-route-1-critical.js).
    "R27": (2.1, 1.9, 90),        # CSI_DATAP1 (pin 47)
    "R26": (3.6, 1.9, 90),        # CSI_DATAN1 (pin 46)
    "R29": (5.4, 1.9, 90),        # CSI_CLKP   (pin 44): P left, as the connector has it
    "R28": (7.1, 1.9, 90),        # CSI_CLKN   (pin 45): N right; its lane dips under P on the way (csi_tracks.py)
    "R25": (8.7, 1.9, 90),        # CSI_DATAP0 (pin 43)
    "R24": (10.2, 1.9, 90),       # CSI_DATAN0 (pin 42)
    "U8":  (16.0, 2.6, 90),       # flash, up and right so the top ring is free
    # bottom side, pins 79..104 (x 3.49 .. 12.24). The 40 MHz crystal
    # hangs under the ring, not in it: in the ring it covered eight pins
    # that then had no way out. Its pads are diagonal, so the far one is
    # 6.3 mm from its pin (C-31 says why that is accepted). The stubs
    # from pins 99/100 pass between C14 and C16
    "C5":  (5.6, B4, 90),         # pin 85 3V3
    "C26": (7.7, B4, 90),         # pin 91 VDD_HP
    "C14": (9.4, B4, 90),         # pin 96 3V3
    "C16": (11.4, B4, 90),        # pins 101/102 3V3
    "Y2":  (9.9, -19.0, 180),     # pins 99/100, 40 MHz, under the ring: P pad top right, N bottom left
    "C37": (13.0, -18.5, 0),      # XTAL_P load, right of the crystal, pad 1 toward it
    "C38": (7.6, -21.5, 180),     # XTAL_N load, under the crystal's N pad, pad 1 toward it
    "C41": (13.5, -16.9, 90),     # pin 103 EN RC
    # core buck at the FB/EN corner (pins 78/79)
    "U7":  (0.6, -17.5, 0),       # TLV62569
    "C36": (-3.3, -16.4, 0),      # its input capacitor
    "L2":  (4.6, -20.2, 0),       # its inductor
    "C27": (5.6, -23.3, 0),       # its output capacitor, 22 uF, under the inductor
}

placement = Placement(board, plan, face="U1", keep_rotation=("C37", "C38", "C39", "C40"))
hits, boxes = placement.collisions()
for a, b in hits:
    print(f"OVERLAP {a} {tuple(round(v, 2) for v in boxes[a])}  vs  {b} {tuple(round(v, 2) for v in boxes[b])}")

print("\nnearest P4 pin on the same net (pad to pad, mm):")
for d, dist, net, pin in placement.pin_distances("U1"):
    print(f"  {d:4s} {net:12s} pin {pin:>3s}  {dist:.2f}{'' if dist <= 3.0 else '   <-- over 3 mm'}")

if hits:
    sys.exit(f"{len(hits)} overlaps; nothing written")
placement.write(OUT)
print(f"\nwrote {OUT}: {len(plan)} components")
