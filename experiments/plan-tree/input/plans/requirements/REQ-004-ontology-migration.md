# REQ-004 — Complete the ontology migration

## Raw request

On 2026-10-10 the user asked: “请修复你提出的问题。对ontology移植给出下一步计划。具体的实际流程验证暂时不跑。”

## Boundary and current state

`ST-005` establishes a versioned registry and a query adapter. It does not yet
make the whole reasoning flow ontology governed. The harness still contains
diagnostic prose and thresholds; some deterministic paths retain embedded line
data. `WP-011` and `WP-012` are open. The next plan must identify the remaining
facts and rules, choose their authoritative representation, and specify how
runtime decisions will consume them with inspectable provenance.

This request authorizes a plan and local fixes. A real FITS → Redrock → LLM
execution and held-out evaluator calibration are deferred; neither is claimed
as evidence in this change. Keep those gates explicit in their existing plans.

## Invariants

- Scientific rest wavelengths have one authoritative source and retain units,
  precision, aliases, and citations.
- A claim or rule conclusion must be traceable to the ontology version and to
  observed graph evidence. Unknown coverage or detectability cannot become
  negative spectral evidence.
- Legacy narrative guidance may remain for explanation, but executable facts
  and constraints must have a single owned representation.
- Preserve current output contracts and hypothesis referents while migrating.

## Completion signal

A reviewed inventory maps each active knowledge use to an ontology concept or
explicitly classifies it as narrative guidance; machine-checkable rules are
validated; runtime consumers use the registry; offline parity and trace tests
pass. Real workflow compatibility and held-out calibration remain separate
release gates under `ST-004` and `WP-012`.

## 2026-10-16 decision amendment

The final sentence above records the original release-gate boundary. The
decision owner has since cancelled WP-012's independent expert defect-grade
assessment. WP-012 is superseded by WP-042, which retains only the implemented
predicate/evaluator and defined-grade result. The real-workflow graph and
independent classification/redshift gate remains under ST-012/WP-037. The
scientific claim limit is recorded in
`_aiHumanInteract/plan/evaluations/wp012-calibration-cancellation-20261016.md`.
