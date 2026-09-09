// Camera node routing, the full pass: every net at once, on a board that
// holds the hand-routed lanes and crystals and the P4's escape. The
// three-pass plan (critical nets first, then the rest) died with the
// escape: sixty-six nets now start as a stub and a via, and any pass with
// a shorter list ends in the router's "ordinary recovery" completing them
// with detours (CAMERA-LAYOUT.md, section 7). With every net in scope
// the main router does that work instead. Section 5 gives the currents.
//
// Order: camera-clear-router.js, p4-escape-local.js assembled, this
// (repeat while nets stay open), camera-route-3-copper.js.

stack({
  boardThicknessMm: 1.6,
  fallbackCopperThicknessOz: 1,
  layers: [
    { kind: "copper", name: "TOP", thicknessOz: 1 },
    { kind: "dielectric", name: "PP7628", thicknessMm: 0.2104, relativePermittivity: 4.4, material: "FR-4 7628" },
    { kind: "copper", name: "INNER_1", thicknessOz: 0.5 },
    { kind: "dielectric", name: "core", thicknessMm: 1.065, relativePermittivity: 4.6, material: "FR-4 core" },
    { kind: "copper", name: "INNER_2", thicknessOz: 0.5 },
    { kind: "dielectric", name: "PP7628b", thicknessMm: 0.2104, relativePermittivity: 4.4, material: "FR-4 7628" },
    { kind: "copper", name: "BOTTOM", thicknessOz: 1 },
  ],
});

drc({
  // C-04: L2 is the ground plane and stays unbroken. A track on it is a
  // slot in the reference under the MIPI lanes and the crystals. L3 is
  // the power layer and carries signals too: a 0.35 mm QFN-104 does not
  // escape on two routing layers (9 of 33 nets did), it does on three.
  allowedLayers: ["TOP", "INNER_2", "BOTTOM"],
  trackWidthMm: 0.2,
  minTrackWidthMm: 0.127,
  clearanceMm: 0.127,
  edgeClearanceMm: 0.3,
  holeToHoleClearanceMm: 0.254,
  via: { diameterMm: 0.6, drillMm: 0.3, minDiameterMm: 0.3, minDrillMm: 0.15 },
});

// The previous pass poured the ground zones; the router treats zones as
// obstacles, so they go before routing and come back after. The outer
// flood is declared because it is what prices the pairs as coplanar.
clearRouting({ nets: ["GND"], items: ["zones"] });
plane({ net: "GND", layers: ["INNER_1"], region: board(), zone: { padConnection: { mode: "solid" } } });
plane({ net: "GND", layers: "OUTER", region: board(), zone: { padConnection: { mode: "thermal" }, removeIslandsBelowMm2: 4 } });

// The hand-routed nets (csi_tracks.py) are copper already and stay
// untouched; their intents are restated so a repair, if the router
// attempts one, keeps them.
for (const n of ["CSI_CLKP", "CSI_CLKN", "CSI_DATAP0", "CSI_DATAN0", "CSI_DATAP1", "CSI_DATAN1", "CSI_A_CLKP", "CSI_A_CLKN", "CSI_A_DATAP0", "CSI_A_DATAN0", "CSI_A_DATAP1", "CSI_A_DATAN1", "XTAL_P", "XTAL_N", "XTAL_32K_P", "XTAL_32K_N"]) {
  signalNet(n, { priority: "critical", viaPreference: "forbid", allowedLayers: "TOP" });
}

// C-21 the RF run: 50 ohm coplanar on L1 over L2, no vias, both net names.
for (const n of ["ANT_MOD", "HALOW_ANT"]) {
  signalNet(n, { priority: "critical", viaPreference: "forbid", allowedLayers: "TOP", impedance: { targetOhm: 50, referenceNet: "GND" } });
}

// C-22 USB: two ordinary nets routed together on L1, not a declared pair
// (declared as pairs they failed the impedance stage and the whole board
// fell into recovery routing). CSI_REXT is hand copper.
for (const n of ["USB_DP_C", "USB_DN_C", "USB_DP", "USB_DN", "USB_DP_J", "USB_DN_J"]) {
  signalNet(n, { priority: "high", viaPreference: "avoid", allowedLayers: ["TOP", "BOTTOM"], trackWidthMm: 0.2, minTrackWidthMm: 0.127 });
}
signalNet("CSI_REXT", { priority: "critical", viaPreference: "forbid", allowedLayers: "TOP" });

// Core-buck feedback and enable: short, planar, first.
for (const n of ["FB_DCDC", "EN_DCDC"]) {
  signalNet(n, { priority: "critical", viaPreference: "avoid" });
}

// Flash SPI: routed early, vias avoided.
for (const n of ["FLASH_CS", "FLASH_Q", "FLASH_WP", "FLASH_HOLD", "FLASH_CK", "FLASH_D"]) {
  signalNet(n, { priority: "high", viaPreference: "avoid" });
}
// Radio SPI and the SD bus: important, ordinary geometry.
for (const n of ["SPI_SCK", "SPI_MOSI", "SPI_MISO", "MM_SCK", "MM_MOSI", "MM_MISO", "HALOW_CS", "HALOW_IRQ", "HALOW_BUSY", "SD1_CLK", "SD1_CMD", "SD1_D0", "SD1_D1", "SD1_D2", "SD1_D3"]) {
  signalNet(n, { priority: "high" });
}

// Section 5 power, by current.
powerNet("VCELL", { maxCurrentA: 2, maxTempRiseC: 10 });
powerNet("VCELL_J", { maxCurrentA: 2, maxTempRiseC: 10 });
powerNet("VSYS", { maxCurrentA: 2, maxTempRiseC: 10 });
powerNet("VIN_CHG", { maxCurrentA: 1, maxTempRiseC: 10 });
powerNet("VUSB", { maxCurrentA: 1, maxTempRiseC: 10 });
powerNet("VSOLAR", { maxCurrentA: 0.5, maxTempRiseC: 10 });
powerNet("3V3", { maxCurrentA: 0.75, maxTempRiseC: 10 });
powerNet("3V3_HP", { maxCurrentA: 2, maxTempRiseC: 10 });
powerNet("3V3_CAM", { maxCurrentA: 0.5, maxTempRiseC: 10 });
powerNet("3V3_RF", { maxCurrentA: 0.5, maxTempRiseC: 10 });
powerNet("3V3_SD", { maxCurrentA: 0.3, maxTempRiseC: 10 });
powerNet("VDD_HP", { maxCurrentA: 0.5, maxTempRiseC: 10, priority: "high" });
powerNet("BUCK_HP_SW", { maxCurrentA: 0.6, maxTempRiseC: 10, viaPreference: "forbid" });
powerNet("BUCK_SW", { maxCurrentA: 0.8, maxTempRiseC: 10, viaPreference: "forbid" });
powerNet("BB_L1", { maxCurrentA: 2.5, maxTempRiseC: 10, viaPreference: "forbid" });
powerNet("BB_L2", { maxCurrentA: 2.5, maxTempRiseC: 10, viaPreference: "forbid" });
powerNet("VLED", { maxCurrentA: 0.3, maxTempRiseC: 10, clearanceMm: 0.3 });
powerNet("FLASH_SW", { maxCurrentA: 1.2, maxTempRiseC: 10, viaPreference: "forbid", clearanceMm: 0.3 });
powerNet("1V8_PSRAM", { maxCurrentA: 0.1 });
powerNet("2V5_MIPI", { maxCurrentA: 0.1 });
powerNet("VDD_FLASH", { maxCurrentA: 0.1 });

// The P4's escape is copper already (p4_escape.py): the router continues
// from those vias and never draws its own fanout at the package.
disableFanout(component("U1"));
runAll();
