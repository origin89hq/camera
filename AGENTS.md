# Working in this repository

At the start of each new task, run `just skills-sync` from the repository root.
Read `skills/origin89-working/SKILL.md` and the relevant domain skills under the
immutable `path` printed by that command. Keep that snapshot for the task; do not
refresh it halfway through work. Read local instructions and preserve stronger
project constraints and project-specific skills.

If refresh reports cached content, continue with that verified cache and mention
that the script could not check for updates. If no cache is available or
validation fails, report the error; do not claim the shared rules loaded. Local
instructions and the user's request still apply. Do not overwrite local skill
files to fix a conflict without reconciling them.

[Origin89 engineering](https://github.com/origin89hq/engineering) owns the shared
rules. Keep only repository-specific architecture, commands, target constraints,
and exceptions below. Internal RFCs and research belong in
[internal-research](https://github.com/origin89hq/internal-research). Add documentation
only when its value and upkeep are clear; remove AI filler from every message.

## Board work

Read `CONTRIBUTING.md`, `board/CAMERA-LAYOUT.md`, and the board's Gerber
rules before changing artwork. Preserve the EasyEDA sources and archived
fabrication exports. Import new exports through `tools/import_easyeda_export.py`;
validation must not modify them. Placement and routing changes include their
source scripts and the generated checker result.

Run `just check` for the selected fabrication export. A failing copper rule is
a board finding: report it and keep the gate failing until the artwork is fixed.
Gerber validation does not establish electrical or bench qualification. This is
a Python/CAD repo; do not add Node or Cargo workspaces without actual consumers.
