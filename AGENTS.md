# AGENTS.md — Paths to Modernity skill maintenance

These instructions govern maintenance of this skill repository. They are
separate from the governance fragment installed into target projects.

## Sources and generated files

- `SKILL.md` contains the runtime entry point and shared decision guidance.
- `references/model.md`, `inquiry.md`, and `alternatives.md` describe the
  general planning method.
- `references/plan-graph.md` is the normative Plan Graph specification and
  owns the mapping from concepts to fields.
- `assets/plan-graph/` is the installation bundle. Keep its tools and
  installed guidance aligned with the specification.
- `assets/protocol/` holds the project-level protocol block and the recovery
  skeleton that `scripts/adopt_project.py` injects into a target project. The
  block is generated output, not a second copy of the skill: keep it to
  pointers and the four invariants, and change its wording in one place.
- `assets/plan-graph/example/_aiHumanInteract/plan/structure/` contains generated views;
  never edit them by hand.
- `agents/openai.yaml` is UI metadata, not runtime instructions.
- `experiments/plan-tree/` is an exploratory 2.5D renderer plus a frozen
  FORMA input snapshot. It is not part of the installed bundle; do not wire
  it into `build_graph.py` without an explicit decision.

## Change protocol

Change the specification, tools, installed guidance, example, and regression
checks together when changing the graph contract. Bump the schema version for
breaking changes to fields, levels, identifiers, relationships, or lifecycle.
Do not silently accept old source fields or overwrite local governance;
consumers and the installer reject unsupported versions instead of migrating
them.

Use `apply_patch` for hand edits. From this directory, regenerate the example
and run the bundle regression:

```bash
python3 -B assets/plan-graph/_aiHumanInteract/plan/build_graph.py --root assets/plan-graph/example/_aiHumanInteract/plan
python3 -B scripts/test_plan_graph_bundle.py
```

Adopting the protocol into a project (AGENTS.md block, CLAUDE.md pointer,
`_aiHumanInteract/state/active.md` skeleton):

```bash
python3 -B scripts/adopt_project.py /path/to/repository --dry-run
python3 -B scripts/adopt_project.py /path/to/repository
python3 -B scripts/adopt_project.py /path/to/repository --upgrade-block
```

Migrating a target project installed by an earlier bundle:

```bash
python3 -B scripts/migrate_plan_graph_v3.py /path/to/repository --dry-run
python3 -B scripts/migrate_plan_graph_v3.py /path/to/repository
python3 -B scripts/migrate_plan_graph_v3.py /path/to/repository --replace-governance-block
```

The last form is only for a governance block the migration refused because its
hash does not match the v3 manifest: move local rules outside the markers first.

Ownership is recorded, never inferred from matching content. `adopt_project.py`
writes `created_block` / `created_claude`; anything older or unrecorded is kept
on uninstall, and `migrate_plan_graph_v3.py` trusts only the `block_sha256` the
v3 installer recorded.

The regression checks installation preview and removal, schema alignment,
source validity, and generated-view freshness. Success ends with
`Plan Graph v4 bundle checks passed`.

For skill packaging checks, locate the available `skill-creator` through the
environment's skill catalog and run its `scripts/quick_validate.py` with this
directory as the argument. Do not assume a machine-specific installation path.
If that validator is unavailable, report the packaging check as unavailable;
the local bundle regression remains independently runnable.

Do not invent target-project objectives in the reusable bundle. Preserve
installer conflict checks and ownership checks during upgrades.
