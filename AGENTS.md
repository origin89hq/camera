# Working in this repository

For hosted PR reviews, follow `Code Review Rules` below without running the local
skills refresh. For other tasks, run `just skills-sync` from the repository root.
Read `skills/origin89-working/SKILL.md` and the relevant domain skills under the
immutable `path` printed by that command. Keep that snapshot for the task; do not
refresh it halfway through work. Before branch, commit, push, or PR operations,
read `skills/origin89-commits/SKILL.md` from that snapshot. Read local instructions
and preserve stronger project constraints and project-specific skills.

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

Confirmed problems left outside the current fix need an issue in the owning
repository: search with `gh`, reuse a matching issue or create one with evidence,
and return its URL. Follow the shared working skill's unfinished-work rule.
Respect posting restrictions; if filing is blocked, provide the draft and say why.
Finish authorized fixes instead of replacing them with backlog issues.

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

## Code Review Rules

Read the shared `origin89-review` skill and relevant domain skills when available.
In hosted review jobs that already provide `.origin89/engineering/skills/`, use
that checkout without running the local refresh. If shared context is missing,
review against the rules below and disclose that limit.

- Preserve EasyEDA source and filed fabrication exports. Board changes need
  the corresponding layout rule and checker evidence; keep copper failures visible.
- Distinguish Gerber and placement checks from electrical or bench qualification.
  Do not infer hardware safety from a passing host check or change artwork during review.
- Trace findings through callers and guards. Give the trigger, consequence, and
  precise location; distinguish completed checks from missing evidence. Leave
  formatting to the configured tools and avoid duplicate or speculative findings.
- Keep current PR defects in the review. Track confirmed pre-existing or explicitly
  deferred problems as issues when filing is authorized; comments-only reviewers
  provide a draft and state that it was not filed.
