#!/usr/bin/env python3
"""Ground for the P4's left ring, by rip-up: six freerouting nets leave the
channel under the capacitor column, a 0.3/0.15 mm ground via goes under
each capacitor's body straddling its ground pad, the top row is stubbed
to C33's via, and the six nets come back around all of it on three layers.

Usage: ring_ground.py [<router run directory>]   -> finish/ripup.json

Why: the ring capacitors' ground pads had no path. Under the column the
bottom layer carries the VDD_HP trunk (C-54) and Inner2 carried BOOT,
SPI_SCK, HALOW_WAKE and USB_DP running the channel's length, so no via
fitted beside or under a pad; on top every pad sat between two escape
exits. freerouting had left them open too, and the pours only hid it
with islands that touched nothing. The nets that moved were chosen
because they are two- or three-pad nets with no hand copper beyond the
escape stub, and FLASH_CK because its top run walled C30/C32's island.
The file is the record of what was drawn; it was computed against the
board as it stood before the rip-up, so a rerun needs that state.
"""
import json
import math
import os
import sys
import time

import hand_route as hr

hr.VIA_COST = 3.0
HERE = os.path.dirname(os.path.abspath(__file__))
S = os.path.join(HERE, "finish")
ART = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].startswith("/") else None
MOVE = ["FLASH_CK", "RXD0", "USB_DP", "HALOW_WAKE", "BOOT", "SPI_SCK"]
c = hr.Copper(ART)
hand = json.load(open(os.path.join(HERE, "p4_escape.json")))
lname = lambda L: {"TOP": "top", "BOTTOM": "bottom", "INNER_2": "inner2"}[L]
P = lambda d, n: (lambda p: (p.x, p.y))(c.board.pad(d, n))

# the board as it will be after clearRouting on the five nets
c.tracks = [t for t in c.tracks if t[0] not in MOVE]
c.vias = [v for v in c.vias if v[0] not in MOVE]
out = {"components": [], "tracks": [], "vias": []}
# the ground vias already found for the pads outside the ring (LEDs, USB, J6,
# the C6 module, R20); C34 and C4 get an under-body via below instead
gp = json.load(open(S + "/gnd-pads.json"))
old = {(-2.07, -11.1), (-1.72, -6.0)}
for v in gp["vias"]:
    if (round(v["x"], 2), round(v["y"], 2)) in old: continue
    c.vias.append(("GND", v["x"], v["y"], v["diameter"])); out["vias"].append(v)
for t in gp["tracks"]:
    pts = [(p["x"], p["y"]) for p in t["points"]]
    if (round(pts[-1][0], 2), round(pts[-1][1], 2)) in old: continue
    c.tracks.append(("GND", "TOP", t["width"], pts)); out["tracks"].append(t)
print("ground vias for the other pads:", len(out["vias"]), "vias", len(out["tracks"]), "stubs")
# their hand escape stubs and vias come back first
for t in hand["tracks"]:
    if t["net"] in MOVE:
        pts = [(p["x"], p["y"]) for p in t["points"]]
        c.tracks.append((t["net"], t["layer"].upper(), t["width"], pts)); out["tracks"].append(t)
for v in hand["vias"]:
    if v["net"] in MOVE:
        c.vias.append((v["net"], v["x"], v["y"], v["diameter"])); out["vias"].append(v)
print("hand copper back:", len(out["tracks"]), "stubs", len(out["vias"]), "vias")

# ground vias under the column capacitors, straddling the ground pad's inner edge
for d in ["C35", "C31", "C34", "C19", "C28", "C4"]:
    p = c.board.pad(d, 2)
    at = (0.25, round(p.y, 3))
    g = c.check_via("GND", at, 0.3, 0.15)
    print(f"{d}.2 ground via at {at}: gap {g:.3f}", "OK" if g >= hr.CLEARANCE else "FAIL")
    if g >= hr.CLEARANCE:
        out["vias"].append({"net": "GND", "x": at[0], "y": at[1], "diameter": 0.3, "drill": 0.15}); c.vias.append(("GND", at[0], at[1], 0.3))
        # the ring overlaps the pad by 0.13 mm; a short stub makes the joint explicit
        stub = [(round(p.x, 3), round(p.y, 3)), at]
        out["tracks"].append({"net": "GND", "layer": "top", "width": 0.2, "points": [{"x": x, "y": y} for x, y in stub]}); c.tracks.append(("GND", "TOP", 0.2, stub))

# the top-row capacitors: their pour island has no via; a stub joins C30.2 to
# C32.2 and on to C33.2, whose via is 0.5 mm away; FLASH_CK, which walled
# the island on TOP, is re-routed afterwards and crosses on INNER_2
for a, b in (("C30", "C32"), ("C32", "C33")):
    pa, pb = c.board.pad(a, 2), c.board.pad(b, 2)
    stub = [(round(pa.x, 3), round(pa.y, 3)), (round(pb.x, 3), round(pb.y, 3))]
    g, who = c.check("GND", "TOP", stub, 0.2)
    print(f"ground stub {a}.2 -> {b}.2: gap {g:.3f}", "OK" if g >= hr.CLEARANCE else f"FAIL {who}")
    if g >= hr.CLEARANCE:
        out["tracks"].append({"net": "GND", "layer": "top", "width": 0.2, "points": [{"x": x, "y": y} for x, y in stub]}); c.tracks.append(("GND", "TOP", 0.2, stub))
print("FLASH_CK pads", [(p.component + "." + p.number, round(p.x, 2), round(p.y, 2)) for _, _, p in c.pads if p.net == "FLASH_CK"],
      "hand vias", [(v["x"], v["y"]) for v in hand["vias"] if v["net"] == "FLASH_CK"])

# the nets again, each around everything drawn before it
def draw(net, a, b, width=0.2, sl=hr.LAYERS, gl=hr.LAYERS, margin=6.0):
    t0 = time.time()
    for w in (width, 0.127):
        r = c.route(net, a, b, w, start_layers=sl, goal_layers=gl, margin=margin)
        if r is None:
            print(f"  {net} {a}->{b} w{w}: no path ({time.time()-t0:.0f}s)"); continue
        g, who = c.verify(net, r, w)
        L = sum(math.hypot(q[0] - p[0], q[1] - p[1]) for _, pts in r["tracks"] for p, q in zip(pts, pts[1:]))
        print(f"  {net} {a}->{b} w{w}: {len(r['vias'])} vias, {L:.1f} mm, gap {g:.3f} ({time.time()-t0:.0f}s) layers {[l for l, _ in r['tracks']]}")
        if g < hr.CLEARANCE:
            print("   offender", who); continue
        for Lr, pts in r["tracks"]:
            c.tracks.append((net, Lr, w, pts)); out["tracks"].append({"net": net, "layer": lname(Lr), "width": w, "points": [{"x": x, "y": y} for x, y in pts]})
        for x, y in r["vias"]:
            c.vias.append((net, x, y, 0.6)); out["vias"].append({"net": net, "x": x, "y": y, "diameter": 0.6, "drill": 0.3})
        return True
    return False

which = [a for a in sys.argv[1:] if not a.startswith("/")] or MOVE
ok = True
if "FLASH_CK" in which:
    via = next((v["x"], v["y"]) for v in hand["vias"] if v["net"] == "FLASH_CK")
    far = next(p for _, _, p in c.pads if p.net == "FLASH_CK" and p.component != "U1")
    ok &= draw("FLASH_CK", via, (far.x, far.y), gl=("TOP",), margin=3.0)
if "RXD0" in which:
    ok &= draw("RXD0", (1.663, -10.34), P("TP6", 1), gl=("TOP",))
if "USB_DP" in which:
    ok &= draw("USB_DP", P("R18", 1), P("D1", 4), sl=("TOP",), gl=("TOP",))
if "HALOW_WAKE" in which:
    ok &= draw("HALOW_WAKE", (1.663, -9.64), P("R17", 1), gl=("TOP",))
    ok &= draw("HALOW_WAKE", P("R17", 1), P("U14", 6), sl=("TOP",), gl=("TOP",))
if "BOOT" in which:
    ok &= draw("BOOT", (1.663, -8.94), P("R4", 2), gl=("TOP",))
    ok &= draw("BOOT", P("R4", 2), P("SW1", 1), sl=("TOP",), gl=("TOP",))
    ok &= draw("BOOT", P("SW1", 1), P("SW1", 2), sl=("TOP",), gl=("TOP",))
if "SPI_SCK" in which:
    ok &= draw("SPI_SCK", (1.663, -6.84), P("R57", 2), gl=("TOP",))
json.dump(out, open(S + "/ripup.json", "w"), indent=1)
open(S + "/ripup-local.js", "w").write(f"// @local-placement {S}/ripup.json\n")
print("ripup.json:", len(out["tracks"]), "tracks", len(out["vias"]), "vias; all routed:", ok)
