<!-- paths-to-modernity:plan-graph:start -->
<!-- schema-version: paths-to-modernity-plan-graph-v3 -->
<!-- Installation template: this block governs the target project after adoption. -->
## Plan Management

Architecture and multi-stage work is governed by the visible, version-controlled
`_plan/` directory. Markdown nodes under `_plan/<level>/` are the only editable
sources. Files under `_plan/structure/` are deterministic generated views and
must not be edited by hand. Use `_plan/structure/graph.json` for programmatic
discovery, require `schema_version: paths-to-modernity-plan-graph-v3`, then
follow a node's `source` field relative to the repository root. Reject
unsupported schema versions.

Plans decompose through exactly four levels:

```text
long-term (LT-###) -> mid-term (MT-###) -> short-term (ST-###) -> work-package (WP-###)
```

A work package is the terminal, directly executable unit. It may span several
steps or files, but owns one coherent outcome and is independently acceptable.
IDs are globally unique, immutable, zero-padded, and never reused. Every active
non-work-package node must decompose through all remaining levels to a work
package. A node has at most one decomposition parent; every active non-root
node has exactly one; long-term roots set `parent: null`. Cross-cutting relationships use typed edges.

Every node starts with YAML-style front matter in which each line maps a key
to a single-line JSON value, containing `id`, `title`, `level`, `status`,
`updated`, `parent`, `depends_on`, `enables`, `objective`, `deliverables`,
`acceptance`, `links`, and `evidence`.
Optional
typed references are `validates`, `supersedes`, and `conflicts_with`. Optional
planning details are `context` (problem, invariants, constraints, non-goals,
and success signals, including only useful members),
`qualities`, `tradeoffs`, `perspectives`,
`source_requirement`, `approach`, and `alternative_of`; omit them from ordinary
nodes that do not need them. These details are independently optional.
If present, `source_requirement` must resolve locally or identify an external
archive and must also be recorded in `links`. Work-package bodies contain
`Objective`, `Planned work`, `Decisions`, `Completion`, and `Evidence` sections.

Use `parent`/`decomposes_to` for hierarchy, `depends_on` for hard prerequisites,
`enables` for newly possible capability, `validates` for verification,
`alternative_of` for controlled sibling alternatives, and `supersedes` or
`conflicts_with` for lifecycle/design relationships. Decomposition, dependency,
alternative, and supersession graphs must be acyclic and contain no dangling IDs,
self-references, duplicate IDs, or orphaned active nodes.

Controlled alternatives must be sibling work packages sharing objective text,
invariant sets, and source requirements, with distinct non-empty approaches.
Record the common evaluation baseline and comparison decision in a linked
evaluation or Decisions section.

Local links are repository-relative without `..`. Every node links its own plan and at least
one intended or existing code, test, documentation, artifact, or evaluation
target. Planned links may be absent; links and evidence for `done` or
`superseded` nodes must exist or identify an external archive. Evidence must
also be recorded in links, in every status. External references have the form
`external:<non-empty archive identifier or URI>`. The validator checks their
syntax only; record who verified external completion evidence, when, and what
it establishes in the Evidence section or a linked evaluation.

Allowed statuses are `proposed`, `ready`, `in_progress`, `blocked`, `done`, and
`superseded`. Mark a work package `done` only when all acceptance criteria pass
and evidence is linked. Mark an ancestor `done` only when every descendant
work package is `done` or evidenced `superseded`.
Hard prerequisites must be `done` before work becomes `in_progress` or `done`.
Superseded plans retain evidence and must be referenced by a successor.

Before decomposing a materially ambiguous requirement, inspect available facts.
Ambiguity is material when two reasonable readings would change the outcome,
responsibility, acceptance, meaningful risk, or an irreversible
commitment. Distinguish evidence gaps from choices about value, responsibility,
authority, acceptable risk, and irreversible scope. The agent resolves
inspectable facts; it presents consequential boundary alternatives to the
decision owner (the authorized person or role). If the environment disables
interactive question tools, present the choice as plain conversational text
and stop for an answer; a missing prompt channel never turns a human choice
into a silent assumption. Record the selected inside/outside boundary,
affected interfaces, unresolved discoveries, retained qualities, and rationale
in a linked requirement or decision record. Keep the governing node
`proposed` until it is clear enough for the next responsible commitment; do not
delay a reversible discovery step merely to manufacture total certainty.

For deeper inquiry, planning-model guidance, or alternative comparison, use
the `paths-to-modernity` skill if available in the environment's skill catalog.
Start at its `SKILL.md` and follow the relevant reference links. These local
rules remain usable when the skill is unavailable; do not assume an absolute
installation path.

Before architecture implementation, locate the governing work package, confirm
its dependencies, and mark it `in_progress`; create one under the appropriate
parents if absent. At completion, link evidence, resolve the work package,
update eligible ancestors, rebuild, and run:

```bash
python3 -B _plan/validate.py
python3 -B _plan/build_graph.py
python3 -B _plan/build_graph.py --check
python3 -B -m unittest discover -s _plan -p 'test_*.py' -v
```

Commit source nodes and generated `graph.json`, `graph.md`, `graph.canvas`, and
`review.md` together. Keep runtime/domain evidence graphs in a separate
namespace and connect them only through links.
<!-- paths-to-modernity:plan-graph:end -->
