# FA vote bands — label study on the 2026-10-19 run

Date: 2026-10-22. Run: `graph-*` five-spectrum demo, artifact directory
`example/basic/output/20261019T110542Z-e9a5abd8` (committed in the demo repository).
Read-only analysis; no new model calls.

## Question

Do the FA seats resolve disputed features, and does the vote distribution behave as the
band design assumes (assured at the edges, low-reference in the middle)?

## Subjects

The run contains 364 FA targets with three seats each: 285 feature-reality, 76 doublet,
1 Ly-alpha forest, 2 SH review. 342 targets were unanimous (66 yes, 275 no); 22 were 2-1.

The decision owner labelled all 22 disputed targets and a balanced random sample of 50
unanimous targets (25 yes / 25 no, stratified over feature and doublet, seed 20261022).
Doublet rows are scored on **pair corroboration**, not on the presence of absorption: a real
trough whose two components cannot be resolved counts as negative for the doublet task
(this changed the verdict on two Na D rows, #9 and #31, both blended at ~7 A separation and
~36-70 A FWHM).

Uncertain (`U`) rows are excluded from accuracy.

## Results

| Sample | Scored | Correct | Accuracy | 95% Wilson CI |
|---|---:|---:|---:|---:|
| Unanimous (3-0) | 45 | 45 | 100% | 92-100% |
| Disputed (2-1) | 14 | 8 | 57% | 33-79% |
| Disputed, single seat | 42 seats | 22 | 52% | 38-67% |

Weighted by the run's natural class mix (66 unanimous-yes, 275 unanimous-no), the unanimous
estimate is 100%; combining the 342 unanimous and 22 disputed targets gives approximately
**97% over the 364 targets**.

Selective policy implied by the bands:

| Policy | Coverage | Accuracy on answered |
|---|---:|---:|
| Answer only when unanimous | 342/364 = 94% | 45/45 = 100% |
| Answer everything (2-of-3 majority) | 100% | ≈97% |

Token cost of the seats (same run): 6.59 M total, 67% FA feature reality, 31% FA doublet;
1.32 M tokens per spectrum. Three seats per target.

## Interpretation

- Agreement is a strong confidence signal: 45/45 unanimous targets were correct.
- Disagreement is not resolved by the third vote: the majority is right on 8/14 and a random
  single seat on 22/42, with overlapping intervals. The extra seats buy **triage**, not
  accuracy.
- The current three-seat runtime can only produce `3/3` and `0/3` assured bands; `2/3` is a
  middle-band case. The four-band design (totals >= 5) therefore requires either more seats
  or an explicit mapping rule for `2/3`.
- Prompt design is binary by intent: abstention is expressed as a split vote, not as a third
  answer. The labels support keeping prompts binary.

## Limitations

- One expert's labels; 8 of 22 disputed rows were `U` and are excluded, which biases the
  accuracy estimate toward the clearer cases.
- 14 scored disputed rows give a wide interval; the honest claim is "no measured advantage
  of the majority over a single seat", not "voting is useless".
- The unanimous sample is balanced 25/25 rather than frequency-weighted; the stratified
  estimate, not the raw 50-row mean, is the reported number.
- Full per-row tables and figures are kept in the workspace review folder
  (`_interactWithMyAgentFriends/design/assessment-20261022/`), which is Git-ignored; this note
  is the tracked summary.

## Follow-up

- Declare the band boundaries and the `N = 3` mapping in code and in the report contract.
- Route middle-band features to review instead of majority-deciding them.
- Re-run this labelling on a second run and a second labeller before treating 100% / 57% as
  stable.
