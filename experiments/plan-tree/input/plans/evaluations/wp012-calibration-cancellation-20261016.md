# Decision: cancel WP-012 independent defect-grade validation (2026-10-16)

## Decision and owner

The project decision owner cancelled the remaining WP-012 acceptance requiring
independent human-expert defect-severity ratings for `HIGH` / `MEDIUM` / `LOW`.
This is a permanent removal from the current FORMA plan, not evidence that the
assessment passed or a promise to run it later. The owner also directed that
WP-014 and its ancestors no longer wait for WP-012.

## Retained result and claim boundary

The fuzzy predicates, argument evaluator, defect-grade semantics, null reasons,
and related implementation/tests remain useful. WP-042 accepts that narrower
implementation result and explicitly **does not** accept empirical agreement
with expert defect-severity judgments. WP-012 retains its original objective,
acceptance criteria, history and evidence, but is `superseded`, not `done`.

`HIGH` / `MEDIUM` / `LOW` remain ordinal descriptions of defects in the checks
actually performed. `null` with a reason remains the outcome when a defect
grade cannot be assigned. These labels are not probabilities of a correct
classification or redshift, and the current project must not call them
independently calibrated or expert-validated. Historic correctness/ECE reports
cannot stand in for the cancelled expert assessment. The persisted legacy field
name `calibrated_confidence` does not by itself establish calibration.

The cost of this decision is an explicit scientific limitation: expert-grade
agreement, serious-defect miss rate, and grade reliability across spectra are
unknown. A future project wishing to make those claims needs a new authorized
plan and independently assessed data; no such work is silently inherited here.

## Dependency and acceptance changes

- WP-042 supersedes WP-012 and accepts only the implemented fuzzy/evaluator and
  defined-grade contract, with offline evidence.
- WP-014 drops WP-012 as a hard prerequisite. It still owes its own production
  fast-mode, budget, stop/escalation and routing-record acceptance evidence.
- ST-006 no longer claims independent defect-grade calibration. MT-002's
  ablation/graph claim is similarly limited; their status must be judged against
  the revised, explicit acceptance criteria, not against WP-012's old report.
- ST-012/WP-037 continue to own independent classification/redshift labels and
  graph/output-contract checks. They do not inherit expert-grade validation.

This decision changes plan scope and scientific claims only. It does not change
the runtime rating algorithm or re-run an LLM evaluation.
