#!/usr/bin/env python3
"""Give freerouting the ground plane and the rail widths EasyEDA's DSN
export leaves out.

Usage: dsn_plane.py <in.dsn> <out.dsn>

EasyEDA Pro's "Autorouter DSN" carries pads, nets, rules and every
existing track (as `protect`), but no copper pour: to freerouting every
ground pad is an open connection, and it routes GND as tracks all over
the board, 846 open connections on this one, most of them ground.
This writes the plane the board actually has (C-04): Inner1 becomes a
`power` layer, which freerouting never routes on, and a GND `plane`
polygon covers it inside the edge clearance. Freerouting then joins each
ground pad to the plane with one via, which is what the finished board
does with its pour and stitching.

The plane is for the router's connectivity only; the pour in EasyEDA,
with the C6 antenna void (C-11), is still drawn there.

The widths are the second thing missing. The export writes one class per
net (153 of them) and gives every one the board's default 0.2 mm, so
freerouting routed `VSYS`, `VCELL` and `3V3_HP` at 0.2 mm when section 5
rates them at 2 A and demands 1.0 mm. Nothing in the DRC notices: it
measures clearance and connection, not copper section. This rewrites each
rail's class from the table in `power_widths.py`, so the router solves the
whole board with the rails already wide instead of us widening them
afterwards and displacing everything they touch.
"""
import re
import sys

from power_widths import RAILS, width_for

src, dst = sys.argv[1], sys.argv[2]
s = open(src, errors="replace").read()

# the file's unit: (resolution mil 1000)
MIL = 25.4


def set_class_width(text, net, width_mm):
    """Rewrite one net's class rule; the export gives every class 0.2 mm."""
    pattern = re.compile(r"(\(class\s+" + re.escape(net) + r"\s+'" + re.escape(net) +
                         r"'.*?\(rule\s*\(width\s+)([\d.]+)(\s*\))", re.S)
    return pattern.subn(lambda m: f"{m.group(1)}{width_mm / MIL * 1000:.2f}{m.group(3)}", text)


widened = []
for net, (rule, amps, row) in sorted(RAILS.items()):
    want = rule if rule is not None else width_for(amps)
    if want < 0.2:
        continue  # the board default already carries it
    s, n = set_class_width(s, net, want)
    if n:
        widened.append(f"{net} {want:.2f}")
    else:
        print(f"warning: no class for {net}; freerouting will route it at the default")
print(f"rail classes widened: {len(widened)} -- {', '.join(widened)}")

m = re.search(r"\(boundary\s*\(path\s+signal\s+[\d.]+((?:\s+-?[\d.]+)+)\s*\)\s*\)", s)
if not m:
    sys.exit("no boundary found")
nums = [float(v) for v in m.group(1).split()]
pts = list(zip(nums[0::2], nums[1::2]))
xs, ys = [p[0] for p in pts], [p[1] for p in pts]
inset = 11.8  # 0.3 mm edge clearance, in the file's mils
x0, y0, x1, y1 = min(xs) + inset, min(ys) + inset, max(xs) - inset, max(ys) - inset
plane = f"(plane GND (polygon Inner1 0 {x0:.2f} {y0:.2f} {x0:.2f} {y1:.2f} {x1:.2f} {y1:.2f} {x1:.2f} {y0:.2f}))"

before = s.count("(type signal)")
s, n_layer = re.subn(r"\(layer Inner1\s*\(type signal\)\s*\)", "(layer Inner1 (type power) )", s)
if n_layer != 1:
    sys.exit(f"expected one Inner1 signal layer, found {n_layer}")
# freerouting reads the structure in order and resolves the plane's layer
# when it meets it, so the plane goes after the last layer definition
last = list(re.finditer(r"\(layer \w+\s*\(type \w+\)\s*\)", s))[-1]
s = s[:last.end()] + "\n    " + plane + s[last.end():]
# EasyEDA names the layers of its existing wires by id (1, 2, 15, 16), not
# by the names its own structure section declares, and freerouting drops
# every such wire as "no shape": the whole hand-routed board was invisible.
LAYER_IDS = {"1": "TopLayer", "2": "BottomLayer", "15": "Inner1", "16": "Inner2"}
head, sep, wiring = s.partition("(wiring")
wiring, n_paths = re.subn(r"\(path\s+(\d+)\s", lambda m: f"(path {LAYER_IDS.get(m.group(1), m.group(1))} ", wiring)

# every existing via is exported on the 0.6 mm padstack; the P4's escape
# vias are 0.3 mm (p4_escape.py) and at 0.65 mm pitch two 0.6 mm vias
# would be a clearance violation freerouting then tries to repair
import json, os
here = os.path.dirname(os.path.abspath(__file__))
small = set()
for name in ("p4_escape.json",):
    for v in json.load(open(os.path.join(here, name)))["vias"]:
        if v["diameter"] < 0.5:
            # the export keeps y as it is: y' = y + 50 mm, no mirror
            small.add((round((v["x"] + 40) * 39.3701, 1), round((v["y"] + 50) * 39.3701, 1)))


def via_fix(m):
    x, y = float(m.group(2)), float(m.group(3))
    near = any(abs(x - sx) < 0.6 and abs(y - sy) < 0.6 for sx, sy in small)
    return f"(via {'via1' if near else m.group(1)} {m.group(2)} {m.group(3)}"


wiring, n_vias = re.subn(r"\(via\s+(via\d)\s+(-?[\d.]+)\s+(-?[\d.]+)", via_fix, wiring)
s = head + sep + wiring
n_small = len(re.findall(r"\(via via1 ", wiring))
open(dst, "w").write(s)
print(f"wiring: {n_paths} paths renamed to layer names, {n_vias} vias, {n_small} of them on the 0.3 mm padstack ({len(small)} expected)")
print(f"boundary {min(xs):.0f}..{max(xs):.0f} x {min(ys):.0f}..{max(ys):.0f} mil; plane inset {inset} mil on Inner1; "
      f"wires kept {len(re.findall(r'\(wire', s))}, protected {len(re.findall(r'\(type protect\)', s))}")
print("wrote", dst)
