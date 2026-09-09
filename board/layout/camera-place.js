// Camera node placement, written from CAMERA-LAYOUT.md (C-nn rules).
// Portrait 80 x 100 mm, all parts top side, door band at the bottom,
// LED band at the top, antenna top-left, C6 module top-right.

// 1. Board and global rules
board.rect(80, 100, {
  layers: ["top"],
  defaultLayer: "top",
  clearance: 0.3,
  edge: 0.8,
});
boardHole.corners({ drill: 3.2, diameter: 3.2, keepout: 3.5, inset: 4 });

// C-06 door band (bottom 12 mm): only the three door parts.
constraintRegion("door_band", {
  allow: { blocks: ["microsd", "usb", "power_switch"] },
  shape: region.rect({ anchor: anchor("board.bottom"), width: 80, height: 12 }),
});
// C-09 pyro window: 26 x 22 mm on the axis, 28 mm below centre; nothing but the optics inside.
constraintRegion("pyro_window", {
  allow: { blocks: ["pyro", "pyro_supply", "als"] },
  shape: region.rect({ anchor: anchor("board.center"), width: 24, height: 16, offset: { x: 0, y: 28 } }),
});
// C-41 LED driver band: 30 x 12 mm under the LED row, only the boost.
constraintRegion("led_driver_band", {
  allow: { blocks: ["led_boost"] },
  shape: region.rect({ anchor: anchor("board.top"), width: 30, height: 12, offset: { x: 0, y: 10 } }),
});
// C-07 LED band (top 10 mm): only the LED row.
constraintRegion("led_band", {
  allow: { blocks: ["led_string"] },
  shape: region.rect({ anchor: anchor("board.top"), width: 80, height: 10 }),
});

// 2. Functional blocks
block("mcu", ["U1"], "mcu");
block("xtal40", ["Y2", "C37", "C38"], "mcu", null, { placement: "satellite", attachTo: "mcu", anchor: pin("U1", "100") });
block("xtal32k", ["Y1", "C39", "C40"], "mcu", null, { placement: "satellite", attachTo: "mcu", anchor: pin("U1", "104") });
block("dec_lp", ["C1", "C2", "C3"], "mcu", null, { placement: "satellite", attachTo: "mcu", anchor: pin("U1", "9") });
block("dec_hp0", ["C23", "C24"], "mcu", null, { placement: "satellite", attachTo: "mcu", anchor: pin("U1", "26") });
block("dec_io4", ["C4"], "mcu", null, { placement: "satellite", attachTo: "mcu", anchor: pin("U1", "62") });
block("dec_psram", ["C28", "C29"], "mcu", null, { placement: "satellite", attachTo: "mcu", anchor: pin("U1", "59") });
block("dec_vo4", ["C35"], "mcu", null, { placement: "satellite", attachTo: "mcu", anchor: pin("U1", "74") });
block("dec_ldo_dcdc", ["C17", "C18", "C19"], "mcu", null, { placement: "satellite", attachTo: "mcu", anchor: pin("U1", "77") });
block("dec_hp2", ["C25"], "mcu", null, { placement: "satellite", attachTo: "mcu", anchor: pin("U1", "76") });
block("dec_mipi", ["C30", "C31", "C32"], "mcu", null, { placement: "satellite", attachTo: "mcu", anchor: pin("U1", "41") });
block("dec_flashio", ["C33", "C34"], "mcu", null, { placement: "satellite", attachTo: "mcu", anchor: pin("U1", "30") });
block("dec_usbphy", ["C20", "C21", "C22"], "mcu", null, { placement: "satellite", attachTo: "mcu", anchor: pin("U1", "51") });
block("dec_top", ["C5", "C14", "C15", "C16"], "mcu", null, { placement: "satellite", attachTo: "mcu", anchor: pin("U1", "96") });
block("dec_hp3", ["C26"], "mcu", null, { placement: "satellite", attachTo: "mcu", anchor: pin("U1", "91") });
block("core_buck", ["U7", "L2", "C36", "C27"], "power", null, { placement: "satellite", attachTo: "mcu", anchor: pin("U1", "54") });
block("flash", ["U8", "R15"], "mcu", null, { placement: "satellite", attachTo: "mcu", anchor: pin("U1", "27") });
block("reset", ["R3", "C41"], "mcu", null, { placement: "satellite", attachTo: "mcu", anchor: pin("U1", "103") });
block("straps", ["R4", "R16", "R17"], "mcu", null, { placement: "satellite", attachTo: "mcu", anchor: pin("U1", "66"), allowDisconnected: true });
block("csi_rext", ["R20"], "mcu", null, { placement: "satellite", attachTo: "mcu", anchor: pin("U1", "48") });
block("usb_series", ["R18", "R19"], "generic", null, { placement: "satellite", attachTo: "mcu", anchor: pin("U1", "52"), allowDisconnected: true });
block("buttons", ["SW1", "SW2"], "connector", null, { allowDisconnected: true });
block("status_led", ["D4", "R21"], "generic");

block("usb", ["J1", "D1", "R1", "R2"], "connector");
block("microsd", ["J6", "R40", "R41", "R42", "R43", "R44", "R45", "C53", "C54"], "connector");
block("sd_esd", ["D5", "D6", "D7", "D8", "D9", "D10"], "connector", null, { placement: "satellite", attachTo: "microsd", anchor: pin("J6", "7"), allowDisconnected: true });
block("power_switch", ["SW3"], "connector");
block("switch_pulls", ["R38", "R39", "C52"], "connector", null, { placement: "satellite", attachTo: "power_switch", anchor: pin("SW3", "3"), allowDisconnected: true });

block("charger", ["U2", "C6", "C8", "C9", "R5", "R6", "R7", "R8", "R9", "RT1", "D2", "D3"], "power");
block("cell_in", ["J2", "JP1"], "connector");
block("solar_in", ["J3"], "connector");
block("buck3v3", ["U3", "L1", "R10", "C7", "C10"], "power");
block("buckboost", ["U6", "L3", "C47", "C48", "C49", "C50", "R34"], "power");
block("sw_cam", ["U4", "C11", "R35"], "power");
block("sw_rf", ["U5", "C12", "R36"], "power");
block("sw_sd", ["U10", "C51", "R37"], "power");
block("cell_sense", ["Q1", "Q2", "R11", "R12", "R13", "R14", "C13"], "analog");

block("csi_conn", ["J4", "C42", "C43", "R30", "R31", "R32"], "connector");
block("csi_series", ["R24", "R25", "R26", "R27", "R28", "R29"], "mcu", null, { placement: "satellite", attachTo: "mcu", anchor: pin("U1", "44"), allowDisconnected: true });
block("ircut", ["U9", "C44", "C45", "J5"], "generic");
block("als", ["Q3", "R33", "C46"], "sensor", null, { placement: "satellite", attachTo: "pyro", anchor: pin("U13", "4") });
block("pyro", ["U13"], "sensor");
block("pyro_supply", ["R54", "C59", "C60"], "sensor", null, { placement: "satellite", attachTo: "pyro", anchor: pin("U13", "2") });

block("led_boost", ["U12", "C61", "L4", "D11", "C62", "C63", "R55", "R56", "C64"], "power");

block("halow", ["U14", "R60", "R61", "R75", "C65", "C66", "C58"], "rf");
block("halow_series", ["R57", "R58", "R59"], "rf", null, { placement: "satellite", attachTo: "halow", anchor: pin("U14", "24"), allowDisconnected: true });
block("halow_straps_a", ["R62", "R63", "R64", "R65", "R66", "R67"], "rf", null, { placement: "satellite", attachTo: "halow", anchor: pin("U14", "12"), allowDisconnected: true });
block("halow_straps_b", ["R68", "R69", "R70", "R71", "R72", "R73", "R74"], "rf", null, { placement: "satellite", attachTo: "halow", anchor: pin("U14", "33"), allowDisconnected: true });
block("antenna", ["J8", "R76"], "rf");
block("c6", ["U11"], "rf");
block("c6_support", ["R46", "C55", "R47", "C56", "C57"], "rf", null, { placement: "satellite", attachTo: "c6", anchor: pin("U11", "8") });
block("c6_pullups", ["R48", "R49", "R50", "R51", "R52", "R53"], "rf", null, { placement: "satellite", attachTo: "c6", anchor: pin("U11", "26"), allowDisconnected: true });

module("power_area", ["charger", "cell_in", "solar_in", "buck3v3", "buckboost", "sw_cam", "sw_rf", "sw_sd", "cell_sense"], { anchor: anchor("board.left") });
blockClearance("pyro", "buckboost", 8, "critical");
blockClearance("pyro", "buck3v3", 8, "critical");
blockClearance("pyro", "led_boost", 8, "critical");
blockClearance("als", "buck3v3", 6, "critical");
module("radio_area", ["halow", "antenna"], { anchor: anchor("board.left") });

// 3. Mechanics
// C-06 door band, left to right: microSD, USB-C, switch.
component("J6").block("microsd").role("connector").top().edgeMount("bottom", { face: "outward", x: -20, overhang: 0 });
component("J1").block("usb").role("connector").top().edgeMount("bottom", { face: "outward", x: 0, overhang: 1 });
component("SW3").block("power_switch").role("connector").top().rotations(0, 180).edgePlace("bottom", { inset: 1, face: "any", x: 22 });
// C-07 LED row along the top edge.
componentGrid("led_row", [["D12", "D13", "D14", "D15", "D16", "D17", "D18", "D19", "D20", "D21"]], {
  at: anchor("board.top"),
  offset: { x: -27.9, y: 5 },
  columnPitch: 6.2,
  block: "led_string",
  role: "connector",
  layer: "top",
  rotate: 0,
});
// C-10 antenna at the left edge, upper half (this DSL counts y downward: negative = up).
component("J8").block("antenna").role("connector").top().edgePlace("left", { inset: 0.5, face: "outward", y: -25 });
// C-11 C6 module at the right edge, upper half, antenna outward.
component("U11").block("c6").role("main_ic").top().edgePlace("right", { inset: 0.5, face: "outward", y: -22 });
// C-12 cell and solar on the left edge, lower half.
component("J2").block("cell_in").role("connector").top().edgePlace("left", { inset: 1, face: "any", y: 20 });
component("J3").block("solar_in").role("connector").top().edgePlace("left", { inset: 1, face: "any", y: 32 });
// C-09 pyro on the centreline above the door band.
component("U13").block("pyro").role("main_ic").top().edgePlace("bottom", { inset: 22, face: "any", x: 0 });
// C-13 test points in one grid at the right edge, lower half.
componentGrid("tps_a", [
  ["TP1", "TP2", "TP3"],
  ["TP4", "TP5", "TP6"],
  ["TP7", "TP8", "TP9"],
], {
  at: anchor("board.bottom_right"),
  offset: { x: -13, y: -34 },
  columnPitch: 4.5,
  rowPitch: 3,
  block: "testpoints_a",
  role: "connector",
  layer: "top",
  rotate: 0,
});
componentGrid("tps_b", [
  ["TP10", "TP11", "TP12"],
  ["TP13", "TP14", "TP15"],
  ["TP16", "TP17", "TP18"],
], {
  at: anchor("board.bottom_right"),
  offset: { x: -13, y: -45 },
  columnPitch: 4.5,
  rowPitch: 3,
  block: "testpoints_b",
  role: "connector",
  layer: "top",
  rotate: 0,
});

// Roles for the ICs so the solver treats them as block hearts.
component("U1").block("mcu").role("main_ic").top();
component("U2").block("charger").role("main_ic").top();
component("U3").block("buck3v3").role("main_ic").top();
component("U6").block("buckboost").role("main_ic").top();
component("U7").block("core_buck").role("main_ic").top();
component("U8").block("flash").role("main_ic").top();
component("U9").block("ircut").role("main_ic").top();
component("U12").block("led_boost").role("main_ic").top();
component("U14").block("halow").role("main_ic").top();
component("Y1").block("xtal32k").role("crystal").top();
component("Y2").block("xtal40").role("crystal").top();
// Lens on the axis, 8 mm above centre (y is downward here): the camera module sits right in front of it.
component("J4").block("csi_conn").role("connector").top().fixed({ x: 0, y: -8, rotate: 0, layer: "top" });
component("J5").block("ircut").role("connector").top();
component("JP1").block("cell_in").role("connector").top();
component("SW1").block("buttons").role("connector").top();
component("SW2").block("buttons").role("connector").top();
component("D4").block("status_led").role("indicator").top();

// 4. Electrical placement intent
// C-30: the P4 at the centre.
near(comp("U1"), comp("J4"), "critical");
clearance(comp("U1"), comp("J4"), 2, "critical");
// C-08: camera connector under the P4's CSI edge, through the series resistors.
signalPath("csi_clk_p", [[pin("U1", "44"), pin("R29", "1"), { maxDistance: 8 }], [pin("R29", "2"), pin("J4", "9"), { maxDistance: 12 }]], { priority: "critical", shape: "straight" });
signalPath("csi_clk_n", [[pin("U1", "45"), pin("R28", "1"), { maxDistance: 8 }], [pin("R28", "2"), pin("J4", "8"), { maxDistance: 12 }]], { priority: "critical", shape: "straight" });
signalPath("csi_d0_p", [[pin("U1", "43"), pin("R25", "1"), { maxDistance: 8 }], [pin("R25", "2"), pin("J4", "3"), { maxDistance: 12 }]], { priority: "critical", shape: "straight" });
signalPath("csi_d0_n", [[pin("U1", "42"), pin("R24", "1"), { maxDistance: 8 }], [pin("R24", "2"), pin("J4", "2"), { maxDistance: 12 }]], { priority: "critical", shape: "straight" });
signalPath("csi_d1_p", [[pin("U1", "47"), pin("R27", "1"), { maxDistance: 8 }], [pin("R27", "2"), pin("J4", "6"), { maxDistance: 12 }]], { priority: "critical", shape: "straight" });
signalPath("csi_d1_n", [[pin("U1", "46"), pin("R26", "1"), { maxDistance: 8 }], [pin("R26", "2"), pin("J4", "5"), { maxDistance: 12 }]], { priority: "critical", shape: "straight" });
// C-10: the RF run, module pad to U.FL through the 0 R.
signalPath("rf", [[pin("U14", "40"), pin("R76", "1"), { maxDistance: 5, preferFacingPads: true }], [pin("R76", "2"), pin("J8", "1"), { maxDistance: 8, preferFacingPads: true }]], { priority: "critical", shape: "straight" });
// USB pair: connector -> ESD -> series resistors -> P4.
signalPath("usb_dp", [[pin("J1", "A6"), pin("D1", "3"), { maxDistance: 5 }], [pin("D1", "4"), pin("R18", "1"), { maxDistance: 70 }], [pin("R18", "2"), pin("U1", "53"), { maxDistance: 5 }]], { priority: "high", shape: "flexible" });
signalPath("usb_dn", [[pin("J1", "A7"), pin("D1", "1"), { maxDistance: 5 }], [pin("D1", "6"), pin("R19", "1"), { maxDistance: 70 }], [pin("R19", "2"), pin("U1", "52"), { maxDistance: 5 }]], { priority: "high", shape: "flexible" });

// C-31: crystals tight to their pins, far from the inductors.
veryNear(pin("Y2", "1"), pin("U1", "100"), "critical");
veryNear(pin("Y1", "1"), pin("U1", "1"), "critical");
veryNear(pin("C37", "1"), pin("Y2", "1"), "critical");
veryNear(pin("C38", "1"), pin("Y2", "3"), "critical");
veryNear(pin("C39", "1"), pin("Y1", "1"), "critical");
veryNear(pin("C40", "1"), pin("Y1", "2"), "critical");

clearance(comp("Y2"), comp("L2"), 5, "critical");
clearance(comp("Y2"), comp("L3"), 10, "critical");
clearance(comp("Y2"), comp("L4"), 10, "critical");
clearance(comp("Y1"), comp("L2"), 5, "critical");
clearance(comp("Y1"), comp("L3"), 10, "critical");
clearance(comp("Y1"), comp("L4"), 10, "critical");
// C-32 core buck loop.
criticalPair(pin("U7", "3"), pin("L2", "1"), { maxDistance: 3, hard: true });
criticalPair(pin("U7", "4"), pin("C36", "1"), { maxDistance: 3 });
criticalPair(pin("L2", "2"), pin("C27", "1"), { maxDistance: 3 });
// C-33 buck-boost.
corePairs("buckboost", [
  [pin("U6", "8"), pin("L3", "1")],
  [pin("U6", "6"), pin("L3", "2")],
  [pin("U6", "10"), pin("C47", "1")],
  [pin("U6", "4"), pin("C48", "1")],
], { maxDistance: 4.5 });
clearance(comp("U6"), comp("U13"), 10, "high");
clearance(comp("L3"), comp("U13"), 10, "high");
// C-34 always-on buck away from the pyro and light sensor.
corePairs("buck3v3", [
  [pin("U3", "2"), pin("C7", "1")],
  [pin("U3", "7"), pin("L1", "1")],
  [pin("L1", "2"), pin("C10", "1")],
], { maxDistance: 4 });
clearance(comp("L1"), comp("U13"), 10, "critical");
clearance(comp("L1"), comp("Q3"), 10, "critical");
// C-35 P4 decoupling, per pin.
capCluster(["C1", "C2"], { powerNet: "3V3", returnNet: "GND", target: pin("U1", "9"), maxRows: 1, gap: 0.3, priority: "critical" });
bypass(["C3"], pin("U1", "21"), "critical");
capCluster(["C23", "C24"], { powerNet: "VDD_HP", returnNet: "GND", target: pin("U1", "26"), maxRows: 1, gap: 0.3, priority: "critical" });
bypass(["C4"], pin("U1", "62"), "critical");
capCluster(["C28", "C29"], { powerNet: "1V8_PSRAM", returnNet: "GND", target: pin("U1", "59"), maxRows: 1, gap: 0.3, priority: "critical" });
capCluster(["C30", "C31", "C32"], { powerNet: "2V5_MIPI", returnNet: "GND", target: pin("U1", "41"), maxRows: 1, gap: 0.3, priority: "critical" });
capCluster(["C33", "C34"], { powerNet: "VDD_FLASH", returnNet: "GND", target: pin("U1", "30"), maxRows: 1, gap: 0.3, priority: "critical" });
bypass(["C35"], pin("U1", "74"), "high");
bypass(["C17"], pin("U1", "75"), "critical");
bypass(["C25"], pin("U1", "76"), "critical");
capCluster(["C18", "C19"], { powerNet: "3V3", returnNet: "GND", target: pin("U1", "77"), maxRows: 1, gap: 0.3, priority: "critical" });
bypass(["C5"], pin("U1", "85"), "critical");
bypass(["C26"], pin("U1", "91"), "critical");
bypass(["C14"], pin("U1", "96"), "critical");
capCluster(["C15", "C16"], { powerNet: "3V3", returnNet: "GND", target: pin("U1", "102"), maxRows: 1, gap: 0.3, priority: "critical" });
capCluster(["C20", "C21", "C22"], { powerNet: "3V3", returnNet: "GND", target: pin("U1", "51"), maxRows: 1, gap: 0.3, priority: "critical" });
// C-38 CSI reference resistor at its pin.
near(pin("R20", "1"), pin("U1", "48"), "high");
// C-40 flash close to its pins.
criticalPair(pin("U8", "6"), pin("U1", "32"), { maxDistance: 10 });
veryNear(pin("R15", "2"), pin("U8", "1"), "high");
// C-37 protection at the connectors.
veryNear(pin("D1", "3"), pin("J1", "A6"), "critical");
near(comp("D5"), comp("J6"), "high");
near(comp("D10"), comp("J6"), "high");
// C-39 HaLow series resistors at the module's SDIO pads.
veryNear(pin("R57", "1"), pin("U14", "24"), "critical");
veryNear(pin("R58", "1"), pin("U14", "23"), "critical");
veryNear(pin("R59", "1"), pin("U14", "25"), "critical");
capCluster(["C65", "C66"], { powerNet: "3V3_RF", returnNet: "GND", target: pin("U14", "17"), maxRows: 1, gap: 0.3, priority: "high" });
// C-41 LED boost right under the LED band, shunt at the driver.
near(comp("U12"), anchor("board.top"), "critical");
criticalPair(pin("U12", "3"), pin("L4", "2"), { maxDistance: 3, hard: true });
criticalPair(pin("D11", "2"), pin("U12", "3"), { maxDistance: 5 });
veryNear(pin("C62", "1"), pin("D11", "1"), "critical");
veryNear(pin("R55", "1"), pin("U12", "6"), "critical");
veryNear(pin("C61", "1"), pin("U12", "5"), "critical");
// C-42 IR-cut driver near the camera connector.
near(comp("U9"), comp("J4"), "high");
near(comp("J5"), comp("J4"), "high");
// C-09 light sensor beside the pyro.
near(comp("Q3"), comp("U13"), "high");
// Charger input parts at the charger.
veryNear(pin("C6", "1"), pin("U2", "10"), "critical");
veryNear(pin("C9", "1"), pin("U2", "1"), "critical");
veryNear(pin("RT1", "1"), pin("U2", "6"), "high");
near(comp("D2"), comp("J3"), "high");
// The C6's SDIO pull-ups near its pins, its EN network at the module.
veryNear(pin("R46", "2"), pin("U11", "8"), "high");
capCluster(["C56", "C57"], { powerNet: "3V3", returnNet: "GND", target: pin("U11", "3"), maxRows: 1, gap: 0.3, priority: "high" });
// The camera rail's capacitors at the connector.
capCluster(["C42", "C43"], { powerNet: "3V3_CAM", returnNet: "GND", target: pin("J4", "15"), maxRows: 1, gap: 0.3, priority: "high" });
// The three load switches sit between the buck-boost and their loads.
near(comp("U4"), comp("J4"), "normal");
near(comp("U5"), comp("U14"), "normal");
near(comp("U10"), comp("J6"), "normal");

// 5. Output and solver
silkscreen.designators({ enabled: true, height: 1, rotations: [0, 90], margin: 0.2 });
solver({
  grid: 0.5,
  ignoredSignals: ["GND"],
  compactness: "normal",
});
