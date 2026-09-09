// Rules only. The full transaction in camera-route.js checks its per-net
// widths against the board's *current* global minimum before it applies
// its own, so a changed floor has to be on the board first. Running this
// also refreshes the router's input artifact, which is where every pad's
// absolute position is read from (p4_cluster.py, validate_camera_placement.py).
// The board is four layers, and the DSL refuses to run on one without the
// dielectrics declared, so the JLC04161H-7628 stack rides along.
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
  trackWidthMm: 0.2,
  minTrackWidthMm: 0.127,
  clearanceMm: 0.127,
  edgeClearanceMm: 0.3,
  holeToHoleClearanceMm: 0.254,
  // the floor is the P4's escape (p4_escape.py): 0.3 mm vias on 0.15 mm holes,
  // JLC's four-layer minimum is 0.25/0.15
  via: { diameterMm: 0.6, drillMm: 0.3, minDiameterMm: 0.3, minDrillMm: 0.15 },
});

// C-22: USB is three pairs of ordinary nets, not declared pairs. The board
// still carried the declarations, so every freerouting wire at the 5 mil
// clearance it was given failed a 6 mil pair rule nothing asked for.
for (const id of ["usb", "usb_c", "usb_j"]) deleteDiffPair(id);
// C-20's 3.4 mm intra-pair skew for the six CSI pairs is set in EasyEDA's
// rules dialog, not here: diffPair({ maxSkewMm }) writes a preset on the two
// nets and the pair DRC reads the pair's own preset, so the line ran and
// the rule stayed at 0.254 mm (get_pcb_drc_rules is the witness).

applyDrcRules();
