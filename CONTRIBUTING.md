# Contributing

A rule in [CAMERA-LAYOUT.md](board/CAMERA-LAYOUT.md) or
[CAMERA-NODE.md](board/CAMERA-NODE.md) carries its reason. Propose a change
to a rule by arguing with the reason, in an issue, before anyone moves
copper. A change to a board file comes with the rule it serves and the check
that shows it kept: `tools/validate_gerbers.py` for the copper,
`board/layout/validate_camera_placement.py` for the placement.

Say what was measured and on which board. "Works on the bench" with a board
revision and a date is a result; "should work" is not. Nothing here has been
fabricated, so every distance in the layout document is still a promise.

The placement and routing are generated, not drawn by hand in the editor.
[board/layout/README.md](board/layout/README.md) lists the files in the
order they run. If you change a placement, regenerate its JSON rather than
editing the JSON, and run the placement checker on a fresh artifact.

File a fabrication export with `tools/import_easyeda_export.py board <folder>`.
It dates the directory, fixes the names, and refuses to change a file that
is already filed. Then run the Gerber check and put the result, pass or the
rule numbers that failed, in the README.
