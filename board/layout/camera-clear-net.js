// Remove one net's tracks and vias so a hand file can redraw it without
// touching the rest of the copper. Edit NET, run, then serve the redrawn
// tracks. The stack rides along because a four-layer board refuses a DSL
// without it.
const NET = "XTAL_N";
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
clearRouting({ nets: [NET], items: ["tracks", "vias"] });
runCopper();
