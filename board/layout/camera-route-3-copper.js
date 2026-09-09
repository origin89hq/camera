// Camera node routing, pass 3 of 3: the copper. Ground planes on L2 and
// L3, a thermal-relief flood on the outer layers, a 3 mm stitching grid,
// a via fence along the RF run and return vias beside the D-PHY lanes.
// Last, because the router treats existing vias as obstacles and 700
// stitching vias laid before the ordinary nets are 700 walls.
//
// What this cannot do (CAMERA-LAYOUT.md, Acceptance): the pours have
// no holes, so the C6 antenna void (C-11) is drawn by hand afterwards,
// the pours rebuilt, and the stitching vias under it deleted.

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

clearRouting({ nets: ["GND"], items: ["zones"] });
plane({ net: "GND", layers: ["INNER_1", "INNER_2"], region: board(), zone: { padConnection: { mode: "solid" } } });
plane({ net: "GND", layers: "OUTER", region: board(), zone: { padConnection: { mode: "thermal" }, removeIslandsBelowMm2: 4 } });
// Stitching vias are the standard 0.6/0.3: "drc-min" would have laid nine
// hundred of the 0.3/0.15 vias the P4's escape needs, which is a floor for
// one package, not a size for the board.
const stitch = { diameterMm: 0.6, drillMm: 0.3 };
viaStitch("gnd_grid", { mode: "grid", net: "GND", region: board(), pitchMm: 3, via: stitch });
viaStitch("rf_fence", { mode: "along", net: "GND", routes: ["ANT_MOD", "HALOW_ANT"], pitchMm: 1.5, offsetMm: 0.6, rows: 1, via: stitch });
viaStitch("csi_return", { mode: "return", referenceNet: "GND", forNets: ["CSI_A_CLKP", "CSI_A_CLKN", "CSI_A_DATAP0", "CSI_A_DATAN0", "CSI_A_DATAP1", "CSI_A_DATAN1"], maxDistanceMm: 2, via: stitch });

runCopper();
