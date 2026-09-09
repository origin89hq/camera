<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/origin89hq/brand/main/logos/origin89-horizontal-white.svg">
  <img src="https://raw.githubusercontent.com/origin89hq/brand/main/logos/origin89-horizontal-blue.svg" alt="Origin89" width="320">
</picture>

# Origin89 camera

![Development stage](https://img.shields.io/badge/development%20stage-concept-lightgrey.svg) Circuit specified, first copper drawn, nothing fabricated.

A trail camera that sends its pictures to the cabin over a Wi-Fi HaLow mesh,
so a site four hours from a road can be looked at without driving out. One
board, populated three ways: the camera, a relay that extends the mesh, and
the base at the cabin that talks to the controller. The processor is the
ESP32-P4 with a MIPI camera, chosen for night pictures; the radio is a HaLow
module.

| File | What it is |
| --- | --- |
| [CAMERA-MESH.md](CAMERA-MESH.md) | The product: what it does, the mesh, the power budget, what has to be measured before anything is built |
| [board/CAMERA-NODE.md](board/CAMERA-NODE.md) | The circuit specification the schematic is drawn from: blocks, rails, pin budget, the decisions left to draw time |
| [board/CAMERA-LAYOUT.md](board/CAMERA-LAYOUT.md) | The placement and routing rules, numbered `C-nn`, with their reasons |
| [board/layout/](board/layout/) | The placement and routing scripts that produced the first copper, in the order they run |
| [drawings/](drawings/) | The build and schedule drawings |

Every part is a candidate until it has been picked with its datasheet open.
The next step is the night-picture test on the P4 evaluation board; the
schematic is drawn against the result, not before it.

## Design source and exports

Design source: [`board/easyeda/origin89-camera.eprj2`](board/easyeda/), the
EasyEDA Pro project of this board alone, split out of the controller's.
Export of 2026-09-09: [`board/build/2026-09-09/`](board/build/2026-09-09/),
Gerbers, [bill of materials](board/build/2026-09-09/bom.csv),
[pick-and-place](board/build/2026-09-09/pick-and-place.csv), schematic PDF,
STEP and one DXF of every layer. The STEP is in Git LFS, so install
`git-lfs` before cloning or it comes down as a pointer file; it carries every
part but C59, which has no model. Nothing has been fabricated from it.

The Gerbers are checked by `tools/validate_gerbers.py`, the same script the
hardware repository runs on the controller, against
[`board/gerber-rules.json`](board/gerber-rules.json): the C-02 keep-outs at
the four mounting holes and the C-11 antenna void, layer by layer. It runs
in CI on every push and it is red on the 2026-09-09 export: the ground pour
reaches every mounting hole on all four layers, 29 mm² of copper inside the
3.5 mm keep-out at each, where C-02 wants none and C-03 wants the hole on
no net. The fix is the controller's: a prohibited region at each hole on
every copper layer, then the pours rebuilt. It is tracked as
[issue #1](https://github.com/origin89hq/camera/issues/1), and the check
goes green when the next export passes. Nothing has been fabricated from
this export, so no board carries the fault.

```sh
pip install gerbonara shapely
python tools/validate_gerbers.py board/gerber-rules.json board/build/2026-09-09/gerber.zip
```

Exports are filed with `tools/import_easyeda_export.py board <export folder>`,
the same way the [hardware repository](https://github.com/origin89hq/hardware)
files the controller's: the date becomes the directory and each file gets
the name its kind always gets.

## Licence

Design files and drawings under the CERN Open Hardware Licence version 2,
weakly reciprocal ([LICENSE](LICENSE)); the scripts under MIT OR Apache-2.0
([LICENSE-MIT](LICENSE-MIT), [LICENSE-APACHE](LICENSE-APACHE)).
