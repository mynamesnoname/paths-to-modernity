# EV-001 — Modernist plan representation variants

## Evaluation target

Compare two representations of `REQ-001`:

1. optional structured facets embedded in canonical plan metadata;
2. interpretation stored only in a linked Markdown brief.

## Criteria

- traceability to the raw requirement;
- human readability;
- machine discovery and validation;
- duplication and schema cost;
- ability to compare and preserve rejected alternatives;
- compatibility with existing plans and generated views.

## Result

| Criterion | Embedded optional facets | Linked brief only |
|---|---|---|
| Raw-intent traceability | Explicit `source_requirement` plus linked brief | Direct link to brief |
| Human readability | Compact skeleton in node; full prose remains linked | Strong narrative readability |
| Machine discovery | Typed and present in `graph.json` | Indistinguishable from an ordinary documentation link |
| Validation | Essence shape, provenance, sibling relation, and technique are checked | Only path existence can be checked |
| Projection at original evaluation | Automatically grouped in the v2 `atelier.md` | Requires interpreting prose |
| Legacy cost | No optional keys emitted for unfaceted nodes | No schema cost |
| Drift risk | Distilled fields can diverge from raw prose | Interpretive claims cannot be compared mechanically |

## Decision

Select the embedded-facet representation in `WP-016`, but keep the raw
requirement as a linked immutable source. This hybrid preserves the strongest
part of the linked-brief variant without making prose the machine contract.

`WP-017` is superseded rather than deleted. Its different technique and this
comparison remain visible as a historical comparison with `WP-016`.

## Observed boundary

The facets are valuable only when normalization would erase material intent.
Ordinary execution plans should not acquire them automatically. The generated
JSON therefore omits absent optional fields. The v2 `atelier.md` omitted unfaceted
plans entirely; the v3 replacement `review.md` renders optional context and approaches.

## Plan Graph v3 migration note

The original comparison selected embedded details and retained the linked brief. Under v3, `alternative_of` requires identical objective text and invariant sets. WP-016 and WP-017 have different objectives, so the migration retains their source requirement, comparison, conflict, and supersession without an `alternative_of` edge.
