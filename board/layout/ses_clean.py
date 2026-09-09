#!/usr/bin/env python3
"""Strip a freerouting session down to what EasyEDA may import, and take
the vias out of it for the shim.

Usage: ses_clean.py <in.ses> <out.ses>

Writes <out.ses>, plus <out>-vias.json and <out>-vias-local.js beside it.

EasyEDA Pro's session import is lossy in four ways that cost a morning:
it re-creates the file's `protect` items (the hand copper freerouting
was told not to touch) at its own default width on top of the
originals; it lets freerouting's own wires on the hand-routed nets through
(0.2 mm patches laid where the export had dropped a segment inside a
pad); it copies the hand-drawn vias; and it makes every via 0.6 mm
whatever the file says, which turns freerouting's 0.3 mm choices in the
escape's channel into collisions. So this drops every item on the
seventeen hand-routed nets, every `protect` item and every via on a
hand-drawn via, and moves the remaining vias out of the session into a
BoardAssemble file for tools/copilot-shim's `@local-placement` route,
each with the size freerouting chose. The tracks go in through EasyEDA's
import; the vias go in through the shim. Layer names are left alone:
Inner2 lands on EasyEDA's Inner8 and is moved by hand.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HAND_NETS = {"CSI_A_CLKN", "CSI_A_CLKP", "CSI_A_DATAN0", "CSI_A_DATAN1", "CSI_A_DATAP0", "CSI_A_DATAP1",
             "CSI_CLKN", "CSI_CLKP", "CSI_DATAN0", "CSI_DATAN1", "CSI_DATAP0", "CSI_DATAP1", "CSI_REXT",
             "XTAL_32K_N", "XTAL_32K_P", "XTAL_N", "XTAL_P"}
K = 39370.1  # session units (1/1000 mil) per mm; x' = x + 40 mm, y' = y + 50 mm
SIZES = {"via0": (0.6, 0.3), "via1": (0.3, 0.15)}

src, dst = sys.argv[1], sys.argv[2]
s = open(src, errors="replace").read()
hand_vias = [(v["x"], v["y"]) for f in ("csi_tracks.json", "p4_escape.json") for v in json.load(open(os.path.join(HERE, f)))["vias"]]

head, sep, body = s.partition("(network_out")
if not sep:
    sys.exit("no network_out section")
blocks = re.split(r"(?=\(net\s)", body)
kept, vias = [], []
dropped = {"hand nets": 0, "protect": 0, "via copies": 0}
for b in blocks:
    # freerouting writes every net name but GND in quotes; the quotes are
    # not part of the name, and a via placed as `"3V3"` sits on a net of
    # its own that touches nothing; 184 of them did, once
    m = re.match(r'\(net\s+"?([^\s()"]+)"?', b)
    net = m.group(1) if m else None
    if net in HAND_NETS:
        dropped["hand nets"] += b.count("(wire") + b.count("(via ")
        continue
    b, n = re.subn(r"\(wire\s*\(path[^()]*\)\s*\(type protect\)\s*\)", "", b)
    dropped["protect"] += n
    b, n = re.subn(r"\(via\s+via\d\s+-?[\d.]+\s+-?[\d.]+\s*\(type protect\)\s*\)", "", b)
    dropped["protect"] += n

    def take_via(mm):
        x, y = float(mm.group(2)) / K - 40, float(mm.group(3)) / K - 50
        if any(abs(x - hx) < 0.06 and abs(y - hy) < 0.06 for hx, hy in hand_vias):
            dropped["via copies"] += 1
        else:
            d, drill = SIZES[mm.group(1)]
            vias.append({"net": net, "x": round(x, 3), "y": round(y, 3), "diameter": d, "drill": drill})
        return ""

    if net:
        b = re.sub(r"\(via\s+(via\d)\s+(-?[\d.]+)\s+(-?[\d.]+)\s*\)", take_via, b)
    kept.append(b)

out = head + sep + "".join(kept)
open(dst, "w").write(out)
stem = os.path.splitext(dst)[0]
json.dump({"components": [], "tracks": [], "vias": vias}, open(stem + "-vias.json", "w"), indent=1)
open(stem + "-vias-local.js", "w").write(f"// @local-placement {stem}-vias.json\n")
small = sum(1 for v in vias if v["diameter"] < 0.5)
print(f"session: {out.count('(wire')} wires, 0 vias; shim: {len(vias)} vias ({small} of 0.3 mm); dropped {dropped}")
print("wrote", dst, "and", stem + "-vias.json")
