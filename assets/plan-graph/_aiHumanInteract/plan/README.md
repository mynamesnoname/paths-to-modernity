# Plan Graph

Schema version: `paths-to-modernity-plan-graph-v4`.

This is a quick guide supplied by the installation bundle. Once copied into a
target project's `_aiHumanInteract/plan/`, it describes that project's tools.

Markdown nodes under the four level directories are the editable sources.
Files under `structure/` are deterministic projections; never edit them by
hand.

```text
long-term (LT-###) -> mid-term (MT-###) -> short-term (ST-###) -> work-package (WP-###)
```

This file is a non-normative quick guide installed with the tools. The complete
project contract belongs in the repository's governing `AGENTS.md`, and the
validator/graph builder enforce its machine-checkable subset. Use
`structure/graph.json` for machine discovery, then follow each node's `source`
field for its complete narrative and evidence. `review.md` is a generated
human view of optional context, qualities, tradeoffs, perspectives, and
alternative comparisons. `graph.html` is a self-contained interactive reader
with status filtering, keyword search, and node details. Canvas is optional for reading; all
views are generated together.

`install-manifest.json` records additions owned by the installer. To remove
them, locate the matching `paths-to-modernity` skill via the environment's
skill catalog. Its root is the directory containing its `SKILL.md`; from
there run `python3 -B scripts/install_plan_graph.py <repository> --uninstall --dry-run`,
then omit `--dry-run` to remove unchanged owned content. Changed installed
files or governance cause refusal. Use the same skill entry point for
requirement inquiry or alternative comparison; ordinary graph operations
below need only the installed tools.

Run from the repository root after every source-node change:

```bash
python3 -B _aiHumanInteract/plan/validate.py
python3 -B _aiHumanInteract/plan/build_graph.py
python3 -B _aiHumanInteract/plan/build_graph.py --check
python3 -B -m unittest discover -s _aiHumanInteract/plan -p 'test_*.py' -v
```

The installed tools deliberately contain no invented project plans. Create the
LT/MT/ST/WP nodes from actual requirements before running validation.
