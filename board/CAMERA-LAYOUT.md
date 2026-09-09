# Camera node — PCB layout requirements

What the camera node's board must satisfy, and **why**, in the form
[LAYOUT-REQUIREMENTS.md](https://github.com/origin89hq/hardware/blob/main/boards/controller-a/LAYOUT-REQUIREMENTS.md) gave the controller. The
circuit's reasoning is in [CAMERA-NODE.md](CAMERA-NODE.md); this file
extracts only what constrains placement and routing. Requirements are
numbered `C-nn`.

Unlike board A, this board is not going to a layout house: it is placed
and routed here, from this file, with the same discipline. Every
distance that matters is written down before the copper exists, because
nothing in a netlist records which distances were deliberate.

---

## 1. What the board is

One PCB, populated three ways (camera, relay, base). It sits **behind
the front window of a trail-camera housing**, component side toward the
scene, battery behind it. That decides the whole geometry:

- the **top side faces the window**: the camera flex, the pyro, the
  light sensor and the IR LEDs all look forward, so they are top-side
  parts, and there is no bottom-side assembly at all (one pass at JLC,
  like board A);
- the **bottom edge is the service door**: the OFF/SETUP/ON switch, the
  USB-C and the microSD sit on it, behind one gasket, and nothing else
  does;
- the **antenna leaves at the top**: the U.FL is near the top-left
  corner, the pigtail goes straight up to the RP-SMA bulkhead on the
  housing's roof;
- the housing is **bought, not drawn**: the makers of the generic trail
  cameras sell the empty shell (front and back, gasket, IR window, lens
  opening, Fresnel, battery bay, latches, tripod nut) and a plain one
  takes paint. Nobody publishes the PCB size of those shells, but every
  body in the class is **90 mm wide** (Suntek HC-801 135 × 90 × 76,
  Stealth Cam DS4K 150 × 90 × 83, and the rest of the class the same), so a board
  cannot be wider than about 80 mm, and a clamshell keeps its batteries
  in the back half, so the front half offers more than 100 mm of height.
  **The board is designed at 80 × 100 now, on that reasoning, and
  adjusted to a measured shell before the boards are ordered**. A
  shell arrives in the time routing takes, and if its cavity, lens hole,
  PIR window, IR window, battery contacts, antenna boss or door disagree,
  C-01, C-02 and C-06 to C-09 are redrawn and the periphery re-routed.
  What survives a change of outline is everything pinned to the P4
  (section 4), which is why that is placed first and by hand. The front
  board for a bigger LED array is whatever the shell's lid holds.

## 2. Mechanical and stackup

| ID | Requirement | Why |
|---|---|---|
| **C-01** | Outline **80 × 100 mm, portrait**, 1.6 mm FR-4, origin at the board centre (x ±40, y ±50); the design dimension, **checked against a measured shell before the boards are ordered** (section 1) | The compact estimate for 214 footprints at density 0.4 is 99 × 66 mm; a portrait 80 × 100 gives the same area with the shape a camera housing wants (tall, narrow, lens above pyro above door), is the widest board a 90 mm body admits, and stays inside JLC's ≤100 × 100 price tier. Four layers with a 0.35 mm QFN and three differential pairs want the routing room, not a denser board. Routing goes ahead on this outline; what a shell can still move is the periphery, and the periphery is a day to re-route |
| **C-02** | Four **M3** holes, 3.2 mm finished drill, **3.5 mm keep-out radius on all copper layers and both silkscreens**, centres 4 mm in from each corner (**±36, ±46**) | Nylon standoffs in a plastic housing, as on board A. The keep-out is a hair larger than A-02's because this board has inner planes: a plane flashed at a hole is a short to a screw head |
| **C-03** | Holes on **no net** | Plastic housing, nothing to bond to; the cell's negative is bonded once, elsewhere, if at all (A-03) |
| **C-04** | **4 layers: L1 signal, L2 solid ground, L3 power, L4 signal**, JLC04161H-7628, ENIG | L2 is the reference under the MIPI pairs, the RF trace and both crystals. It is unbroken beneath all of them, without exception (A-05's rule, same reason) |
| **C-05** | **All parts top side.** No bottom assembly | One JLC pass, one pick-and-place file, one side to inspect; the bottom faces the battery and carries only copper |
| **C-06** | **Service door band: the bottom 12 mm of the board** (y from −50 to −38) holds `J6` (microSD, card exits the bottom edge), `J1` (USB-C, overhanging), `SW3` (slide switch, actuator through the door), left to right at about x = −20, 0, +22, and **nothing else but their own satellites** (the USB's CC resistors and ESD diode, the card's pull-ups and TVS, which C-37 puts at the connector) | Three things a person touches, one gasket. The widths are 17.2 + 10.4 + 14.3 = 42 mm of a 64 mm edge between the corner keep-outs, so they fit with finger room. A fourth part on that edge means a wider door and a bigger housing |
| **C-07** | **LED band: the top 10 mm** (y from +40 to +50) holds `D12`–`D21` in one row at 6 mm pitch and nothing else | Ten 3528 emitters in a line behind one strip of window. The flash driver sits just below the band; the string's return runs straight back to it |
| **C-08** | **The optical axis is the board's vertical centreline.** `J4` (camera flex) is pinned at **x = 0, 8 mm above the board centre**, and the P4 follows it: within **15 mm pad-to-pad of the P4's CSI pins** (`U1` pins 42–48) through the six series resistors `R24`–`R29`, the resistors at the P4 | The lens sits on the housing front directly over the connector, the way every trail camera on the market is laid out: IR panel above, lens centre-high, PIR window below on the same axis. The D-PHY lanes are the fastest thing on the board (up to 1.5 Gbps per lane), so the P4 goes beside the lens, not the other way round. The number was 12 and the first placement measured 12.6–13.1: the difference is the connector's pinned height, which the shell will set, and 3 mm of D-PHY trace is 20 ps against a 667 ps unit interval. Skew and coupling (C-20) are the constraint at these lengths, not loss |
| **C-09** | `U13` (pyro) on the same axis, **about 28 mm below the board centre** (36 mm under the lens, above the door band), its lens window free of tall parts within 8 mm; `Q3` (light sensor) beside it | The Fresnel lens in the housing is aimed at the pyro; the light sensor must see the same sky. Tall parts (the C6 module, the HaLow module, the inductors) cast shadows on both. `L2`, the core buck's 1.5 mm inductor, is exempt: it is off whenever the pyro is the only thing awake (the P4 drives `EN_DCDC` low in deep sleep) and it sits at the P4's FB/EN corner, which is where C-32 needs it |
| **C-10** | `J8` (U.FL) on the **left edge, upper half** (y ≈ +25), `U14` (HaLow module) beside it with its `ANT_WIFI` pad facing `J8`, the RF run `U14.40 → R76 → J8.1` **under 15 mm, 50 Ω coplanar on L1 over solid L2**, ground stitched both sides | An RF pigtail inside a plastic box is the only path the radio has; the on-board run is loss and mismatch that no antenna gain buys back. The two unpopulated shunt pads of the π-network sit on this run |
| **C-11** | `U11` (ESP32-C6 module, base only) at the **right edge, upper half**, antenna end at the board edge, **no copper on any layer under its antenna keep-out**, and Espressif's ≥ 15 mm to any housing material | A module antenna over copper is a module that does not connect (A-15, same words, same reason). It is only fitted on the base, but the void is in every board |
| **C-12** | `J2` (cell) and `J3` (solar) on the **left edge, lower half**, `JP1` (sleep-current jumper) beside `J2` | The battery is behind the board; its lead comes round the left edge. The jumper is the one thing the bench touches on every board (the sleep measurement), so it stays at the edge with the cell |
| **C-13** | `SW1`/`SW2` (boot/reset) inside the board, not on the door edge; the 18 test points in one accessible grid at the **right edge, lower half** | These are bench controls: USB Serial/JTAG flashes the P4 without the boot button (CAMERA-NODE.md). Nothing a person needs in the field is anywhere but the door |

## 3. Impedance

| ID | Net | Target |
|---|---|---|
| **C-20** | `CSI_CLKP/N`, `CSI_DATAP0/N0`, `CSI_DATAP1/N1`, and their `CSI_A_*` continuations past `R24`–`R29` | **100 Ω** differential ±10 %, MIPI D-PHY: 0.127 mm lines at a 0.25 mm gap in the L1 ground flood over unbroken L2 (grounded coplanar, 103 Ω by the router's solver; the fab's report is the witness). **Routed by hand** (`tools/camera-layout/csi_tracks.py`), because the P4 orders its lanes D1, CLK, D0 with the clock's N before its P, and the Pi connector wants CLK, D1, D0 with P before N: the clock must cross itself and D1 must cross the clock, and no placement removes either. Two layer changes, kept apart so two layers suffice: `CSI_CLKN` dips to L4 between the P4 and `R28` (two vias, the clock's P never interrupted), and the `CSI_A_DATAP1/N1` pair runs on L4 from its resistors to two vias in the 1.6 mm between the connector's rows (four vias). **Six vias in all, none on the clock's P, none on D0**; a return via beside each (pass 3). Intra-pair skew is **3.4 mm by construction** (the connector's contacts sit in two rows 3.4 mm apart), which is 23 ps against a 100 ps budget; the ±0.15 mm this row once asked for was impossible on any board with this connector. The series resistor is part of the path, not the end of it. **The number is the whole lane's**, chip pad to connector contact across both halves, and `csi_tracks.py` measures it (3.26, 2.6 and 1.1 mm). EasyEDA's pair rule sees one half at a time: the connector half carries the 3.4 plus 0.3 of routing, the chip half 0.4–1.2 the other way, so its `differentialPair` length tolerance is set to **3.8 mm** (the bound of a half, not of the lane), and the DSL cannot write it (`camera-drc.js` says why) |
| **C-21** | `ANT_MOD` / `HALOW_ANT` | **50 Ω** single-ended coplanar on L1, L2 reference, ≤ 15 mm |
| **C-22** | `USB_DP/DN`, `USB_DP_C/DN_C`, `USB_DP_J/DN_J` | Two ordinary nets routed together on L1, **not a declared pair**. Declared as 90 Ω pairs they failed the router's impedance stage twice (the path crosses `R18`/`R19` and starts at a 0.35 mm corner), and each failure dropped the router into recovery routing over the whole board (section 7). Full-speed USB on a service port tolerates the loss |

## 4. Placement

| ID | Requirement | Why |
|---|---|---|
| **C-30** | `U1` (P4) near the board centre, rotated so its CSI edge (pins 34–52) faces `J4` | The QFN's bottom edge carries flash, DSI, CSI and USB; the flash goes left of it, the camera below it, the USB down to the door |
| **C-31** | `Y2` (40 MHz) under the capacitor ring with its near pad within **5 mm** of `U1` pin 100 and its far pad within **6.5 mm** of pin 99 (a four-pad crystal's pads are diagonal: sat in the ring, both were under 3 mm, and the eight pins behind its body had no way out; the escape of the whole side is worth 1.3 mm of crystal stub), `C37`/`C38` beside it; `Y1` (32 kHz) within **5 mm** of pins 104/1 with `C39`/`C40`; both crystals **≥ 10 mm from `L1`, `L3`, `L4` and their switch nodes**, and **≥ 5 mm from `L2`** (the core buck is 0.5 A at 1.1 V from 3.3 V, over an unbroken L2, and the P4 wants it at its own pins; the first placement could not hold 10 mm to it without pushing the crystals off theirs); no track under either crystal on any layer, unbroken L2 beneath | A-17 and A-28, same aggressors, same victims. The 32 kHz crystal is also the wake schedule: its ±20 ppm is the whole reason the mesh's windows line up. **Pin the P4 to the centre and the crystals to the P4.** Clearance rules alone lost three times on board A |
| **C-32** | Core buck `U7`/`L2`/`C27`/`C36`: input capacitor to `VIN`/`GND` loop minimal, `L2` at the `SW` pin, `C27` at the `VDD_HP` side, the `FB_DCDC`/`EN_DCDC` lines short and away from `L2` | The P4 regulates this loop through its own `FB_DCDC` pin; a long feedback trace is an antenna into the core supply |
| **C-33** | Buck-boost `U6`/`L3`: `L3` between `L1`/`L2` pads, `C47` at `VIN`, `C48`/`C49` at `VOUT`, exposed pad on a via array to L2; `≥ 10 mm` from both crystals and from `U13` | The 2 A rail. Its exposed pad is the only heatsink it has |
| **C-34** | `3V3` buck `U3`/`L1`: `C7` at `VIN`, `C10` at `VOUT`, `L1` at `SW`; the whole cluster **≥ 10 mm centre-to-centre from `U13`** and ≥ 5 mm from `Q3` | The pyro reads microvolts. The always-on converter is the one aggressor that never stops. The light sensor is a phototransistor into 100 k, read at 1 Hz through 100 nF; an inductor's field does not reach it, so it may sit closer than the pyro. All distances in this document are centre-to-centre unless stated |
| **C-35** | Every P4 supply pin has its capacitor **within 3 mm** of the pin, on L1, returned to L2 by its own via: `C1`/`C2` (pin 9), `C3` (21), `C23`/`C24` (26), `C4` (62), `C28`/`C29` (59/67/72), `C30`–`C32` (41), `C33`/`C34` (30/71), `C35` (74), `C17` (75), `C25` (76), `C18`/`C19` (77), `C5` (85), `C26` (91), `C14` (96/101), `C15`/`C16` (102), `C20`–`C22` (51). Where a pin has two or three, the **first** is within 3 mm in the ring at the pins; the others sit in an outer column within 10 mm. **The pin capacitors are 0402** (100 nF C1525, 1 µF C52923, 10 nF C15195, 22 pF C1555, all JLC basic parts), in a ring 6.55 mm from the P4's centre at 1.15 mm pitch; the 10 µF and 4.7 µF bulk parts stay 0603 in the outer column | The EV board's decoupling is copied pin for pin; the only way to lose it is distance. A 0.35 mm QFN side is 10 mm and holds six 0603 parts; the left side has eight supply pins on six nets, and with 0603 parts pins 71 and 73 measured 7–11 mm from their nearest capacitor. 0402 puts one at every pin at 1.1–1.6 mm. The bulk parts do not move to 0402: a 10 µF 0402 is a 6.3 V part that loses half its capacitance at 3.3 V. The placement solver put every one of these 3–6 mm out and both crystals 9–15 mm out, six runs in a row, and two local repairs ended in overlaps. So **everything in this section is placed from a file, not by the solver**: `tools/camera-layout/p4_cluster.py` writes the 48 positions from the real pad geometry, refuses to write while anything overlaps, prints each capacitor's pad-to-pin distance, and the shim's `@local-placement` route moves exactly those parts and nothing else |
| **C-36** | `U1`'s exposed pad on a **5 × 5 via array** to L2 | 0.5 A core current and a 400 MHz chip; the pad is the thermal and the ground path |
| **C-37** | `D5`–`D10` (microSD TVS) at `J6`, on the connector side of the pull-ups; `D1` (USB ESD) at `J1`, before `R18`/`R19` | A-11: a clamp downstream of what it protects protects nothing |
| **C-38** | `R20` (`CSI_REXT` 4.02 k) within 3 mm of pin 48, its return to L2 at the pin | The D-PHY's reference current; a long trace on it is jitter |
| **C-39** | `U14`'s 22 Ω series resistors `R57`–`R59` at the module's SDIO pads; the 13 strap pull-downs may sit anywhere within 10 mm of the module | The straps are DC; the SPI lines run at up to 50 MHz |
| **C-40** | Flash `U8` within **10 mm** of `U1` pins 27–33, `R15` at `U8` pin 1 | QSPI at up to 80 MHz; the EV board keeps it this close |
| **C-41** | `U12`/`L4`/`D11`/`C62` (LED boost) directly below the LED band, `C62` at `D11`'s cathode, `R55` (shunt) with its ground return to L2 at `U12` pin 4 and `R56`/`C64` at the shunt, not at the P4 | The switch node swings 15 V at 1.2 MHz; the shunt is a 200 mV measurement |
| **C-42** | `U9` (IR-cut driver) and `J5` within 15 mm of `J4` | The filter's coil rides the same lens holder as the flex |

## 5. Power

| ID | Net | V | A | Note |
|---|---|---|---|---|
| **C-50** | `VCELL`, `VCELL_J`, `VSYS` | 3.0–4.5 | 2.0 | Cell to charger to both converters. ≥ 1.0 mm on L1/L3, the charger's `SYS` and `BAT` pins on short wide copper |
| **C-51** | `3V3` | 3.3 | 0.75 | Always-on rail: P4 domains, flash, pyro, C6. An L3 island |
| **C-52** | `3V3_HP` | 3.3 | 2.0 | Buck-boost to the three switches. ≥ 1.0 mm |
| **C-53** | `3V3_CAM`, `3V3_RF`, `3V3_SD` | 3.3 | 0.5 / 0.5 / 0.3 | Switched sub-rails. `3V3_RF` reaches `U14`'s `VBAT`/`VDDIO`/`VDD_FEM` on ≥ 0.5 mm |
| **C-54** | `VDD_HP` | 1.1 | 0.5 | The core. `L2` to the four `VDD_HP` pins on ≥ 0.8 mm copper, `C27` at the inductor, then the pin capacitors |
| **C-55** | `VLED` | ≤ 38 | 0.15 | The open-string clamp reaches 38 V: 0.3 mm clearance around `VLED` and `FLASH_SW`, `C62` is the 50 V part |
| **C-56** | `1V8_PSRAM`, `2V5_MIPI`, `VDD_FLASH` | – | ≤ 0.05 | The P4's own LDO outputs. Each capacitor at the output pin, then a short run to the load pin |

## 6. Silkscreen

`OFF · SETUP · ON` beside the switch with an arrow for each position;
`USB` and `microSD` beside their openings; `+` at the cell connector;
the board name and revision at the right edge. Reference designators
everywhere, 1 mm text, readable under a headlamp.

## 7. Acceptance

Zero DRC violations; every `C-2x` impedance reported by the fabricator;
the placement checker green (`layout/validate_camera_placement.py`,
which measures every rule above from the real pads, the router's input
artifact rather than the pad-less PCB export board A's checker had to
calibrate around, and refuses two parts that overlap); the antenna void and
the hole keep-outs checked on the Gerbers by `tools/validate_gerbers.py`
against `gerber-rules.json` beside this file, green, which the 2026-09-09
export is not: its pours reach every mounting hole (C-02, C-03, issue #1);
and one rendered picture of the board, top side, to compare against the
measured shell before the five boards are ordered.

The checker was made to go red before it was trusted: on the solver's
placement it fails C-31 five ways (both crystals off their pins, the
40 MHz one 9.3 mm from L3) and C-38, and it found three overlaps the
solver had left (`J8`/`SW1`, `L4`/`U12`, `C63`/`L4`) that nothing else
had noticed.

Two things the tools cannot check and a person must, learned on the first
routing attempt: the router's copper pours have no holes, so the C6
antenna void (C-11) is a prohibited region drawn in EasyEDA after routing
(**x 33.5 to 40, y 14 to 29, every copper layer, forbidding tracks,
copper, fill and plane zones but not components**, since the module's own
body sits in it), the pours rebuilt and the stitching vias under it
deleted; and the
router's line-width floor is 0.127 mm, so the MIPI pairs reach 100 Ω with
0.127 mm lines and a 0.25 mm gap, not with thinner lines (the
fabricator's impedance report is the witness, not the DSL's calculator).

**The P4's escape is drawn, not routed** (`layout/p4_escape.py`).
The router's own fanout left 26 of the QFN-104's 0.35 mm pins without a
legal stub, and five passes over the ring never got past 118 of 151 nets.
So the escape is a file: a 0.3/0.15 mm via under every signal pin, in two
staggered rows 5.65 and 6.2 mm from the chip's centre (neighbouring vias
0.65 mm apart, a stub passing the next pin's via with 0.137 mm to spare),
a 0.127 mm stub from the pad, and a stub from every supply pin to its ring
capacitor (via, turn, pad centre). Every via and stub is checked against
every other part's pads and the copper already on the board before it is
written, and anything refused is printed with its reason rather than drawn
wrong. JLC's four-layer floor is a 0.15 mm hole in a 0.25 mm via, and the
board's via rule follows the escape at 0.3/0.15. The router then starts
from vias, never from the package.

The escape changes one thing about the router, learned by watching two
runs. Sixty-six nets now start as partial copper (a stub and a via), and
when the router's impedance stage fails on any declared pair it falls back
to *ordinary recovery*, which completes every partial net on the board,
in or out of the pass's list: 1100 mm of track on fifteen nets that were
never asked for, half of it dangling, twice. The USB pairs were what
failed (C-22 says why they are ordinary nets now), and every pass names
the nets it may not touch (`ignoreNets`) as well as the ones it may
(`onlyNets`); `onlyNets` alone did not hold against the recovery.

**The core rail and the PSRAM's 1.8 V are drawn too** (same file, C-54,
C-56). Mazed by the router, `VDD_HP` took 85 mm and six vias and `3V3`
292 mm and thirty-six; the DSL cannot pour an island on L3 (its plane
regions are the whole board or nothing) and the shim draws only on L1
and L4. So `VDD_HP` is an L on L4, 0.8 mm wide (C-54), 8.3 mm from the chip's
centre (down the left side from pin 54 past pin 76, along the bottom to
pin 91), with a 0.127 mm spur from each pin's escape via (2 mm between
the neighbouring vias, 125 mA each; the pitch allows nothing wider), a
via down to `L2`'s output pad and an L1 run from there to `C27`; pin 26 reaches it on L3 by the router, because
a right leg would have walled every right-side escape on L4 for one pin.
`1V8_PSRAM` joins its three left-side pins on a shorter L4 run inside the
L. The escapes those runs wall off leave on L3, which is what L3 is for.

Three more runs are drawn because the router took them the long way
round, measured on its own output: `VDD_HP`'s test point `TP11` is 25 mm
from the chip and got 180 mm of 0.8 mm track around the left and bottom
edges, so the L's bottom leg carries on east to a via 7 mm short of the
test point's column, and the router finishes from there; `VDD_FLASH` got
156 mm for `U8`, `R15` and `TP15`, so it leaves pin 30's via on L4 along
the top of the ring to a via at `U8` and one at `R15`, the test point
beyond being the router's; `I2C_SCL` got 115 mm for two pads 11 mm apart,
so it runs on L1 over the camera connector's upper row to its pull-up.
Each was 1.7 to 3.6 times the spread of its own pads. Drawn all the way to
both test points, with a right leg for pin 26, the runs walled L4 along
the whole right side and the router rolled a 45-minute pass back rather
than finish. A hand run stops where the router's own path was the
problem, not one millimetre further.

**The routing is freerouting's, through EasyEDA's own DSN export and
session import** (`layout/dsn_plane.py` before, `ses_clean.py`
after). The DSL router never got past 138 of 151 nets and rolled a
45-minute pass back to nothing; freerouting, given the same board, routed
it to a handful of open connections in twelve passes, with the plane
doing ground. What the export and the import get wrong is fixed in
those two files, not by hand, and the sequence is: board at hand copper
only, export, `dsn_plane.py`, freerouting (threads 1, Inner1 inactive,
Top and Bottom vertical, Inner2 horizontal), export session,
`ses_clean.py`, import the session, move Inner8 to Inner2, assemble the
vias `ses_clean.py` wrote through the shim, then the checks below. The
session quotes every net name but `GND`; a via placed as `"3V3"` sits on
a net of its own and joins nothing, and 184 of them did once.

**What freerouting leaves is finished against the artifact, not by eye.**
It stopped with `3V3` in three pieces, `I2C_SCL` and `HALOW_RST` in two,
and a dozen wires 3.5–4.8 mil from a pad. `net_islands.py` says which pads
sit in which piece; `hand_route.py` draws a link on L1/L4 through an A*
grid with every other net's copper inflated by its width and the
clearance, a via wherever one clears every layer, and measures the result
against the exact shapes before it goes on the board. The first version
looked at the outer layers only and put a via through an L3 wire. Two
escape vias it could not reach at all: their pocket on L4 is 1 × 2 mm,
walled by the `1V8_PSRAM` rail and the neighbouring escapes, which is the
same wall freerouting hit. Those links are drawn in the editor, where a
track can be pushed aside; a router that moves nothing cannot pass there.
Freerouting's ground (452 mm of L1 chaining between pads) is deleted:
the pours and the stitching grid (pass 3) do ground, and a ground stub
4 mil from a pad is a stub, not a design. Removing copper goes through
`clearRouting` on the whole net, and the extension is patched
(`tools/copilot-shim`) so the shim draws on L3 as well as L1 and L4;
the repair of one bad segment is therefore: copy the net's copper out of
the artifact, drop the segment, redraw it, clear the net, put the copy
back. Two of the sealed escapes opened that way, `I2C_SCL` leaving on
L3 where nothing else could.

**A hand-drawn width can be replaced without the copper moving.** The
session carried a 0.2 mm copy of a 0.127 mm escape stub; the copy landed
on top of the original and covered it, so the coverage check passed while
the wider track sat 0.0995 mm from two escape vias where the drawn one
had 0.136. `verify_hand_copper.py` now measures the width as well as the
path. Two stubs are still wider than drawn (`USB_DN_C`, `3V3`); both
clear 0.37 mm and stay, because a stub the router widened where there is
room is not the same defect as one widened in the channel.

**The ring capacitors' ground pads had no path, and the pours hid it.**
Under the left column L4 carries the `VDD_HP` trunk and L3 carried four
of freerouting's signals along the channel, so no via fitted beside or
under a pad; on L1 every ground pad sat between two escape exits.
Freerouting had left them open; the first pour then "connected" them
through islands that touched nothing, which is why island removal is on
for every plane and why the count to read after a pour is the DRC's, not
the picture's. `ring_ground.py` is the fix: `BOOT`, `SPI_SCK`,
`HALOW_WAKE`, `USB_DP`, `RXD0` and `FLASH_CK` are cleared, a 0.3/0.15 mm
via goes under each column capacitor straddling its ground pad, the top
row is stubbed to `C33`'s via, and the six nets come back around all of
it. Every other ground pad the DRC named gets a via with a stub, 0.6 mm
where it fits; the stitching grid itself is 0.6/0.3, not the DRC minimum,
because the P4's via floor is a floor for one package.

**Count the hand copper after every routing run.** The router rips
pre-existing copper as a "blocker" when a net will not route: its log
said `Ripped 1V8_PSRAM` of a run that then put tracks on a forbidden layer,
rolled back and applied nothing after 45 minutes. A run that *is* applied
may have done the same and kept it. The number to check is the track and
via count of the three hand files together, read back from the router's
input artifact, before anything else is judged; the hand copper is the
reproducible part of this board and a routing result is not.
