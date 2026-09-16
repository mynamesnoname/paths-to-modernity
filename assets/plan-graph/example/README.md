# Worked Plan Graph example

This fictional example teaches the optional repository implementation. It
contains LT → MT → ST → WP decomposition and two work packages. `WP-002`
depends on `WP-001`; hierarchy and execution order are separate relationships.
Do not copy these objectives into a real project.

## Learn the source model

Read [the requirement](_plan/requirements/REQ-001.md), then
[LT-001](_plan/long-term/LT-001.md) →
[MT-001](_plan/mid-term/MT-001.md) →
[ST-001](_plan/short-term/ST-001.md) →
[WP-001](_plan/work-package/WP-001.md).
Compare [WP-002](_plan/work-package/WP-002.md) for the dependency and for an
ordinary node without optional planning details.

WP-001 records context, desired qualities, tradeoffs, review perspectives, and
a source requirement. Its planned implementation link may point to a file that
does not exist yet; the contract allows absent planned targets, so the example
validates as written.

## Learn to consume the generated views

Open [_plan/structure/graph.json](_plan/structure/graph.json), check
`schema_version`, find WP-001, and follow its `source` path relative to this
example directory. Compare the JSON fields with the Markdown front matter.

[graph.md](_plan/structure/graph.md) is a navigable index;
[review.md](_plan/structure/review.md) collects optional planning details;
`graph.canvas` is a navigation view for compatible Canvas viewers such as
Obsidian. Reading Canvas is unnecessary for machine traversal or plan editing.
All four views are generated, not editable source plans.

For maintenance checks, return to the skill repository's [AGENTS.md](../../../AGENTS.md).
