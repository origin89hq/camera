#!/usr/bin/env python3
"""Check the camera board's placement against CAMERA-LAYOUT.md.

Usage: validate_camera_placement.py [<router run directory>]

Reads real pad geometry (see padgeom.py) from the newest router run, or
the one given, and measures every C-nn rule that a placement can satisfy
or break: bands, axis, crystals, converters, the P4's capacitors, and
overlaps between any two parts. Exit 0 when everything passes, 1 on any
FAIL. What this cannot see (copper, pours, the antenna void, the
impedance report) is listed under Acceptance in the document.

Distances are pad to pad on the named net where the rule is about a
connection, centre to centre where it is about a field (an inductor, the
pyro), and the document says which.
"""
import itertools
import sys

from padgeom import Board, overlaps

EPS = 1e-3  # EasyEDA's 0.1 mm grid comes back as 6.2000000004; a check is not a float comparison
# Parts that cast a shadow on the pyro window. L2 is not among them: the
# core buck is off whenever the pyro is the only thing awake (the P4 drives
# EN_DCDC low in deep sleep), and it is 1.5 mm high.
TALL = ["U11", "U14", "L1", "L3", "L4", "J6", "J1", "SW3", "J4", "U13"]
DOOR = ("J6", "J1", "SW3")
SUPPLY_NETS = ("3V3", "VDD_HP", "1V8_PSRAM", "2V5_MIPI", "VDD_FLASH", "VDDO_4")


class Report:
    def __init__(self):
        self.failures = []

    def check(self, req, label, value, limit, kind="<="):
        ok = value <= limit + EPS if kind == "<=" else value >= limit - EPS
        print(f"  {'ok  ' if ok else 'FAIL'} {req:5} {label}: {value:.2f} mm ({'max' if kind == '<=' else 'min'} {limit})")
        if not ok:
            self.failures.append(f"{req} {label}")

    def expect(self, req, label, ok, detail=""):
        print(f"  {'ok  ' if ok else 'FAIL'} {req:5} {label}{(': ' + detail) if detail else ''}")
        if not ok:
            self.failures.append(f"{req} {label}")


def mechanical(b, r):
    xs = [p[0] for p in b.outline]
    ys = [p[1] for p in b.outline]
    r.check("C-01", "outline width off 80", abs(max(xs) - min(xs) - 80.0), 0.05)
    r.check("C-01", "outline height off 100", abs(max(ys) - min(ys) - 100.0), 0.05)
    r.check("C-01", "outline centred (max offset)", max(abs(max(xs) + min(xs)), abs(max(ys) + min(ys))) / 2, 0.1)
    holes = {(round(h.x), round(h.y)) for h in b.holes()}
    r.expect("C-02", "four holes at (±36, ±46)", holes == {(36, 46), (-36, 46), (36, -46), (-36, -46)}, str(sorted(holes)))
    bottom = [d for d in b.designators() if b.layer(d) != 1]
    r.expect("C-05", "every part on the top side", not bottom, ", ".join(bottom))


def bands(b, r):
    door = set(DOOR)
    below = {d for d in b.designators() if b.centre(d)[1] < -38}
    r.expect("C-06", "door band holds J6, J1, SW3", door <= below, ", ".join(sorted(door - below)) + " missing")
    # a door part's own satellites (CC resistors and ESD at the USB, the
    # card's pull-ups, TVS and supply capacitor) belong at the connector:
    # anything sharing a net other than ground or the always-on rail with a
    # door part may sit in the band, nothing else may
    door_nets = {p.net for d in door for p in b.pads_of(d) if p.net not in ("GND", "3V3", "")}
    strangers = {d for d in below - door if not any(p.net in door_nets for p in b.pads_of(d))}
    r.expect("C-06", "nothing but the door parts and their satellites in the band", not strangers, ", ".join(sorted(strangers)))
    order = sorted(door, key=lambda d: b.centre(d)[0])
    r.expect("C-06", "door order J6, J1, SW3 left to right", order == ["J6", "J1", "SW3"], " ".join(order))
    leds = [f"D{n}" for n in range(12, 22)]
    above = {d for d in b.designators() if b.centre(d)[1] > 40}
    r.expect("C-07", "LED band holds D12-D21", set(leds) <= above, ", ".join(sorted(set(leds) - above)) + " missing")
    r.expect("C-07", "nothing else in the LED band", above <= set(leds), ", ".join(sorted(above - set(leds))))
    ys = [b.centre(d)[1] for d in leds]
    r.check("C-07", "LED row straight (y spread)", max(ys) - min(ys), 0.3)
    xs = sorted(b.centre(d)[0] for d in leds)
    pitches = [xs[i + 1] - xs[i] for i in range(len(xs) - 1)]
    r.check("C-07", "LED pitch (min)", min(pitches), 5.8, ">=")
    r.check("C-07", "LED pitch (max)", max(pitches), 6.2)


def axis(b, r):
    jx, jy = b.centre("J4")
    r.check("C-08", "J4 on the centreline |x|", abs(jx), 0.3)
    r.check("C-08", "J4 8 mm above centre |y-8|", abs(jy - 8), 0.5)
    for pin in range(42, 48):
        p = b.pad("U1", pin)
        # the series resistor: one pad on the P4's net, the other on J4's
        for res in ("R24", "R25", "R26", "R27", "R28", "R29"):
            pads = b.pads_of(res)
            if any(q.net == p.net for q in pads):
                near = next(q for q in pads if q.net == p.net)
                far = next(q for q in pads if q.net != p.net)
                jpad = next(q for q in b.pads_of("J4") if q.net == far.net)
                r.check("C-08", f"CSI pin {pin} -> {res} -> J4 path", p.distance(near) + far.distance(jpad), 15.0)
                break
        else:
            r.expect("C-08", f"CSI pin {pin} has a series resistor", False)
    px, py = b.centre("U13")
    r.check("C-09", "pyro on the centreline |x|", abs(px), 1.0)
    r.check("C-09", "pyro about 28 mm below centre |y+28|", abs(py + 28), 4.0)
    r.check("C-09", "light sensor Q3 beside the pyro", b.centre_distance("U13", "Q3"), 10.0)
    for d in TALL:
        if d != "U13":
            r.check("C-09", f"{d} clear of the pyro window", b.centre_distance("U13", d), 8.0, ">=")


def edges(b, r):
    x, y = b.centre("J8")
    r.check("C-10", "U.FL on the left edge (x)", x, -30, "<=")
    r.check("C-10", "U.FL upper half |y-25|", abs(y - 25), 10.0)
    a = b.pad("U14", 40)
    rf_in = next(q for q in b.pads_of("R76") if q.net == a.net)
    rf_out = next(q for q in b.pads_of("R76") if q.net != a.net)
    r.check("C-10", "RF run U14.40 -> R76 -> J8", a.distance(rf_in) + rf_out.distance(b.pad("J8", 1)), 15.0)
    x, y = b.centre("U11")
    r.check("C-11", "C6 module at the right edge (x)", x, 20, ">=")
    r.check("C-11", "C6 module in the upper half (y)", y, 0, ">=")
    for d in ("J2", "J3"):
        x, y = b.centre(d)
        r.check("C-12", f"{d} on the left edge (x)", x, -30, "<=")
        r.check("C-12", f"{d} in the lower half (y)", y, 0, "<=")
    r.check("C-12", "JP1 beside J2", b.centre_distance("JP1", "J2"), 10.0)
    for n in range(1, 19):
        x, y = b.centre(f"TP{n}")
        r.expect("C-13", f"TP{n} in the right lower quadrant", x >= 20 and y <= 0, f"({x:.1f}, {y:.1f})")
    for d in ("SW1", "SW2"):
        r.check("C-13", f"{d} off the door edge (y)", b.centre(d)[1], -38, ">=")


def placement(b, r):
    # the 40 MHz crystal hangs under the ring; its far pad is allowed 6.5 mm (C-31 says why)
    for xtal, pins in (("Y2", (99, 100)), ("Y1", (1, 104))):
        for pin in pins:
            p = b.pad("U1", pin)
            d = min(q.distance(p) for q in b.pads_of(xtal) if q.net == p.net)
            r.check("C-31", f"{xtal} to pin {pin} ({p.net})", d, 6.5 if (xtal, pin) == ("Y2", 99) else 5.0)
        for coil in ("L1", "L3", "L4"):
            r.check("C-31", f"{xtal} clear of {coil}", b.centre_distance(xtal, coil), 10.0, ">=")
        r.check("C-31", f"{xtal} clear of L2", b.centre_distance(xtal, "L2"), 5.0, ">=")
    for d in ("U6", "L3"):
        for v in ("Y1", "Y2", "U13"):
            r.check("C-33", f"{d} clear of {v}", b.centre_distance(d, v), 10.0, ">=")
    for d in ("U3", "L1"):
        r.check("C-34", f"{d} clear of the pyro", b.centre_distance(d, "U13"), 10.0, ">=")
        r.check("C-34", f"{d} clear of Q3", b.centre_distance(d, "Q3"), 5.0, ">=")
    caps = [d for d in b.designators() if d.startswith("C")]
    for p in b.pads_of("U1"):
        if p.net not in SUPPLY_NETS:
            continue
        best = None
        for c in caps:
            for q in b.pads_of(c):
                if q.net == p.net:
                    dd = q.distance(p)
                    if best is None or dd < best[0]:
                        best = (dd, c)
        r.check("C-35", f"pin {p.number} {p.net} capacitor ({best[1]})", best[0], 3.0)
    r.check("C-38", "R20 to pin 48 (CSI_REXT)", min(q.distance(b.pad("U1", 48)) for q in b.pads_of("R20") if q.net == "CSI_REXT"), 3.0)
    for res in ("R57", "R58", "R59"):
        r.check("C-39", f"{res} at the HaLow module", b.pad_distance(res, "U14"), 5.0)
    flash = min(b.pad("U1", n).distance(q) for n in range(27, 34) for q in b.pads_of("U8") if q.net == b.pad("U1", n).net)
    r.check("C-40", "flash U8 to the P4's QSPI pins", flash, 10.0)
    r.check("C-40", "R15 at U8", b.pad_distance("R15", "U8", "FLASH_CS"), 5.0)
    for d in ("U12", "D11", "C62"):
        y = b.centre(d)[1]
        r.expect("C-41", f"{d} just below the LED band", 25 <= y <= 40, f"y = {y:.1f}")
    r.check("C-41", "L4 at its driver U12 (switch-node loop)", b.pad_distance("L4", "U12", "FLASH_SW"), 8.0)
    r.check("C-41", "C62 at D11", b.pad_distance("C62", "D11", "VLED"), 4.0)
    for d in ("U9", "J5"):
        r.check("C-42", f"{d} near the camera connector", b.centre_distance(d, "J4"), 15.0)


def collisions(b, r):
    boxes = {d: b.box(d) for d in b.designators()}
    hits = [(a, c) for a, c in itertools.combinations(sorted(boxes), 2) if overlaps(boxes[a], boxes[c])]
    r.expect("C-05", "no two parts overlap (pad extents + 0.25 mm)", not hits, ", ".join(f"{a}/{c}" for a, c in hits[:12]))


def main():
    b = Board(sys.argv[1] if len(sys.argv) > 1 else None)
    print(f"placement from {b.run_dir}")
    r = Report()
    for section in (mechanical, bands, axis, edges, placement, collisions):
        print(f"\n{section.__name__}")
        section(b, r)
    print()
    if r.failures:
        print(f"{len(r.failures)} FAIL:")
        for f in r.failures:
            print("  " + f)
        return 1
    print("all placement checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
