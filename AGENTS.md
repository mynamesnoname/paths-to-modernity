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
- `assets/plan-graph/example/_aiHumanInteract/plan/structure/` contains generated views;
  never edit them by hand.
- `agents/openai.yaml` is UI metadata, not runtime instructions.

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
