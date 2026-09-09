#!/usr/bin/env python3
"""The periphery repairs the checker found in the solver's placement, as a
second hand placement (tools/copilot-shim, `@local-placement`).

Usage: periphery.py <out.json> [<router run directory>]

Three overlaps and one distance, none of which the solver reported:
the boot button on the U.FL, the LED boost inductor on its driver and
its capacitor, and the HaLow module's series resistors 6 mm from the pads
they serve (C-39 says 5). Everything here sits in the region a measured
shell may redraw; the fixes are small moves, made so routing does not
start on top of a collision.
"""
import sys

from padgeom import Board, Placement

OUT = sys.argv[1] if len(sys.argv) > 1 else "periphery.json"
board = Board(sys.argv[2] if len(sys.argv) > 2 else None)
print("pad geometry from", board.run_dir)

plan = {
    # C-13: boot and reset buttons inside the board; SW1 was touching the U.FL
    "SW1": (-35.4, 31.0, 180),
    "SW2": (-35.4, 36.8, 0),
    # C-41: the boost inductor was on top of its driver and its capacitor
    "L4":  (12.8, 19.3, -90),
    # C-31/C-33: the 40 MHz crystal now hangs under the P4's ring and was
    # 9.8 mm from the buck-boost inductor; 0.3 mm down makes it 10.1
    "L3":  (9.5, -29.1, 0),
    # C-39: the 22 ohm series resistors take the column nearest the module's
    # SDIO pads; the two strap pull-downs that held it (DC, anywhere within
    # 10 mm) take the series resistors' old places one column out
    "R58": (-17.6, 12.7, 0),      # MM_MOSI, pad 23
    "R57": (-17.6, 14.2, 0),      # MM_SCK, pad 24
    "R59": (-17.6, 15.7, 0),      # MM_MISO, pad 25
    "R68": (-14.5, 12.8, 0),      # MM_GPIO7 strap
    "R70": (-14.5, 14.5, 0),      # MM_GPIO9 strap
}

placement = Placement(board, plan, face="U14")
hits, boxes = placement.collisions()
for a, b in hits:
    print(f"OVERLAP {a} {tuple(round(v, 2) for v in boxes[a])}  vs  {b} {tuple(round(v, 2) for v in boxes[b])}")
print("\nnearest U14 pad on the same net (pad to pad, mm):")
for d, dist, net, pad in placement.pin_distances("U14"):
    print(f"  {d:4s} {net:12s} pad {pad:>3s}  {dist:.2f}")
if hits:
    sys.exit(f"{len(hits)} overlaps; nothing written")
placement.write(OUT)
print(f"\nwrote {OUT}: {len(plan)} components")
