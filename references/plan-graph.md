# Plan Graph specification

Use this optional implementation when a project needs repository-local source
plans with machine-readable links and generated navigation views. Follow an
existing coherent local planning system when one is already in use.

The sections through the node legality checklist define the consumption and
source contract. The final two sections cover installing and editing the
infrastructure and apply only when establishing or maintaining it.

## Authority and version

This document defines the source contract and generated JSON schema.
`assets/plan-graph/` is the installation bundle implementing that contract.
Its governance fragment (`AGENTS.plan-management.md`) and README are templates
for target projects, not additional instructions for the skill's runtime reader.

The exact generated JSON field is:

```json
{"schema_version": "paths-to-modernity-plan-graph-v3"}
```

Consumers must reject unsupported versions before interpreting nodes or edges.
A disagreement between this specification and the bundled tools is a defect.
After adoption, the target project's applicable `AGENTS.md` governs local work;
deliberate local adaptations must keep their tools and contract consistent.

## Source plans and generated views

Markdown nodes are the editable source of truth. The builder generates:

| File under `_plan/structure/` | Purpose |
|---|---|
| `graph.json` | Machine discovery: version, normalized nodes, and typed edges |
| `graph.md` | Markdown index and Mermaid relationship diagram |
| `graph.canvas` | Navigation in compatible Canvas viewers such as Obsidian |
| `review.md` | Context, qualities, tradeoffs, perspectives, and alternatives when present |

For machine discovery, check the version, locate a node by ID, then follow its
`source` path relative to the repository root. Read the source for decisions
and full evidence. Canvas is unnecessary for nonvisual consumption. Coordinates,
colors, array position, and layout carry no planning semantics.

For a first reading, use the [worked example](../assets/plan-graph/example/README.md).

## Repository structure

Adopting this implementation means using four decomposition levels:

```text
long-term (LT-###) → mid-term (MT-###) → short-term (ST-###) → work-package (WP-###)

_plan/
  requirements/   Durable requirements and boundary decisions
  evaluations/    Comparison results and completion evidence
  long-term/      LT source nodes
  mid-term/       MT source nodes
  short-term/     ST source nodes
  work-package/   WP executable leaves
  structure/      Generated views
  README.md
  install-manifest.json
  validate.py
  build_graph.py
  test_plan_graph.py
```

A work package owns one coherent, independently acceptable outcome and can
span several steps or files. Every active higher-level node decomposes through
all remaining levels to work packages. Long-term roots set `parent: null`;
every other active node has exactly one parent. Cross-cutting relationships use
typed edges. IDs are globally unique, immutable, three-digit zero-padded, and
never reused. The general planning method does not require these four levels.

Requirement and evaluation records are narrative Markdown, not graph nodes:
they carry no front matter contract, and the validator checks them only as
link targets. Give them stable filenames (for example `REQ-001.md`) because
nodes reference them through `source_requirement` and `links`.

## Concepts and fields

This table is the mapping from the [planning model](model.md) to this schema.

| Concept | Source field | Requirement |
|---|---|---|
| Desired outcome | `objective` | Required non-empty string |
| Supporting plan context | `context` | Optional object: `problem` string; `invariants`, `constraints`, `non_goals`, `success_signals` string arrays; include only relevant members |
| Desired character in use | `qualities` | Optional string array |
| Competing aims or open tradeoffs | `tradeoffs` | Optional string array |
| Review viewpoints | `perspectives` | Optional string array; free-text names, not an enumeration |
| Raw requirement or decision record | `source_requirement` | Optional reference, also recorded in `links` |
| Proposed way to achieve the outcome | `approach` | Optional non-empty string; required for compared alternatives |
| Controlled alternative to another work package | `alternative_of` | Optional work-package ID; rules below |
| Associated files and evidence locations | `links` | Required categorized object of non-empty reference arrays |
| Completion evidence | `evidence` | Required reference array; may be empty before completion |

The plan brief consists of the objective and any useful context. Qualities,
tradeoffs, perspectives, context, and approach are independently optional.
They do not require each other. Do not add empty fields to ordinary nodes.
If `context` is supplied, it must contain at least one supported member.
Its string values and supplied arrays must be non-empty.

For materially ambiguous requirements, use [inquiry](inquiry.md), preserve the
chosen scope and decision owner in a durable requirement or decision record,
and link it from the plan. Keep the governing node `proposed` until it passes
the readiness gate in [inquiry](inquiry.md) for its next responsible
commitment. A bounded discovery work package can be ready while the larger
design remains unsettled.

## Source node contract

Each `_plan/<level>/<ID>.md` begins with YAML-style front matter in which each
line maps a key to a single-line JSON value. The bundled parser uses only
Python's standard library.

```yaml
---
id: "WP-001"
title: "Define a routing trace"
level: "work-package"
status: "ready"
updated: "2026-09-15"
parent: "ST-001"
depends_on: []
enables: []
objective: "Make each routing decision reproducible."
deliverables: ["A versioned trace schema"]
acceptance: ["A stored trace contains all inputs needed to reproduce the route"]
links: {"plan": ["_plan/work-package/WP-001.md"], "code": ["src/routing_trace.py"]}
evidence: []
---
```

Required fields are `id`, `title`, `level`, `status`, `updated`, `parent`,
`depends_on`, `enables`, `objective`, `deliverables`, `acceptance`, `links`,
and `evidence`. Deliverables and acceptance must be non-empty string arrays.
`updated` is the date of the last material change, in `YYYY-MM-DD` format.
Optional node-reference arrays are `validates`, `supersedes`, and
`conflicts_with`; other optional fields are defined in the mapping above.
Unknown fields are rejected.

Work-package bodies contain `Objective`, `Planned work`, `Decisions`,
`Completion`, and `Evidence` sections. Higher levels may use shorter narratives.
Keep approach choices and review findings in Decisions when no additional
structured field is useful.

## Relationships and lifecycle

- `parent` generates a parent-to-child `decomposes_to` edge.
- `depends_on` generates a prerequisite-to-dependent `prerequisite_for` edge.
- `enables` points to a newly possible capability, and must not duplicate a
  hard prerequisite.
- `validates` points from a validating plan to the plan it verifies.
- `alternative_of` points from an alternative to its comparison baseline.
- `supersedes` points from a successor to a superseded plan.
- `conflicts_with` identifies incompatible plans.
- Implementation files are recorded in `links`, not an `implements` node edge.

Decomposition, dependency, alternative, and supersession graphs must be acyclic.
No IDs may dangle, and no relationship may reference its own node.

Allowed statuses are `proposed`, `ready`, `in_progress`, `blocked`, `done`,
and `superseded`. Hard prerequisites must be `done` before a node can be
`in_progress` or `done`. Completion requires acceptance to be satisfied and
evidence recorded; the validator checks structure and references, not the truth
of acceptance claims. A higher-level node can be `done` only when every
descendant work package is `done` or evidenced `superseded`.
A superseded node retains evidence and must be referenced by a successor.

For controlled alternatives, use [alternatives](alternatives.md). Both nodes
must be work packages under the same parent, with the same `source_requirement`,
`objective`, and invariant set, and different non-empty `approach` values.
The validator compares objective text exactly and invariants as sets. Reuse
the baseline text to avoid accidental drift. Shared evaluation scenarios,
comparison budget, and decision criteria belong in a linked evaluation or
Decisions record; the validator cannot assess their adequacy.

## File links and evidence

`links` maps category names to references, for example `plan`, `code`,
`tests`, `docs`, `artifacts`, or `evaluation`. Categories other than `plan`
are open to project needs.

- Local references are repository-relative paths without `..`.
- Every node includes its own source in `links.plan` and at least one
  reference in another category.
- Planned targets may be absent. Local links and evidence for `done` or
  `superseded` nodes must exist.
- Every evidence reference must also be in `links`, regardless of status.
- If supplied, `source_requirement` must exist locally or be an external
  reference, and must also be in `links`.
- Runtime or domain evidence graphs remain separate models. Link their
  schemas, tests, reports, or evaluations through files.

External references use `external:<locator>`, where the locator is a
non-empty archive identifier or URI, for example
`external:https://example.org/archive/report-42`. The tool checks the syntax
but makes no network request and cannot verify existence, accessibility,
authenticity, or acceptance. Before relying on external completion evidence,
record who checked it, when, and what it establishes in the Evidence section
or linked evaluation. The `external:` prefix is a declaration, not verification.

## Node legality checklist

The validator enforces every rule below. Check a new or edited node against
this list before running the tools.

Identity and hierarchy:

- `id` is globally unique, immutable, three-digit zero-padded, and never reused.
- Long-term roots set `parent: null`; every active non-long-term node has
  exactly one parent one level up.
- Decomposition, dependency, alternative, and supersession graphs are acyclic,
  with no dangling IDs and no self-references.

Required fields:

- All of `id`, `title`, `level`, `status`, `updated`, `parent`, `depends_on`,
  `enables`, `objective`, `deliverables`, `acceptance`, `links`, and `evidence`
  are present; unknown fields are rejected.
- `updated` uses `YYYY-MM-DD`; `deliverables` and `acceptance` are non-empty
  string arrays; `status` is one of the six allowed values.

Links and evidence:

- `links.plan` contains the node's own source path, and at least one other
  category is present.
- Local references are repository-relative without `..`; external references
  use the `external:` prefix.
- Every `evidence` entry also appears in `links`; a supplied
  `source_requirement` exists locally or is external and also appears in
  `links`.
- Planned targets may be absent; links and evidence of `done` or `superseded`
  nodes must exist.

Optional planning details:

- `context` contains at least one supported member, with non-empty strings and
  arrays; `qualities`, `tradeoffs`, `perspectives`, and `approach` are
  independently optional.
- `alternative_of` points to a sibling work package with identical `objective`
  text, the same invariant set, the same `source_requirement`, and a different
  non-empty `approach`.

Lifecycle and bodies:

- Hard prerequisites are `done` before the node becomes `in_progress` or `done`.
- A higher-level node is `done` only when every descendant work package is
  `done` or evidenced `superseded`; a superseded node keeps its evidence and is
  referenced by a successor.
- Work-package bodies carry `Objective`, `Planned work`, `Decisions`,
  `Completion`, and `Evidence` sections.

## Installation and removal

The **skill root** is the directory containing the loaded `SKILL.md`; resolve
it from the actual skill location. Run these commands there, substituting the
target repository path:

```bash
python3 -B scripts/install_plan_graph.py /path/to/repository --dry-run
python3 -B scripts/install_plan_graph.py /path/to/repository
```

If the authorized task includes adopting project governance, inspect applicable
`AGENTS.md` files for an equivalent contract and add `--update-agents` to both
commands when it is missing. Absence means missing semantics, not a missing
heading. Reconcile conflicting local rules before installation.

The installer refuses differing files and older installations. It records its
additions in `_plan/install-manifest.json`, independently of project plans.
Preview removal from the same skill installation:

```bash
python3 -B scripts/install_plan_graph.py /path/to/repository --uninstall --dry-run
python3 -B scripts/install_plan_graph.py /path/to/repository --uninstall
```

Removal checks ownership and hashes, removes unchanged installed files and
the unchanged marked governance block, and removes only empty directories.
Changed installed content causes refusal. It does not delete source plans.
When an older installation or locally edited files prevent replacement,
reconcile or remove the existing installation manually first.

## Editing plans and rebuilding views

Run from the target repository root after changing source nodes:

```bash
python3 -B _plan/validate.py
python3 -B _plan/build_graph.py
python3 -B _plan/build_graph.py --check
python3 -B -m unittest discover -s _plan -p 'test_*.py' -v
```

The builder validates before generating all four views. `--check` validates
and checks freshness without writing. Commit source nodes and generated views
together. For bundle-maintainer checks, follow the skill's [AGENTS.md](../AGENTS.md).
