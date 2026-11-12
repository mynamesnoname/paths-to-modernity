# REQ-011 — Vote bands and materialized abstention

Decision owner: project user, 2026-10-22.

## Raw direction

> 我在设计这个 session 的时候就划定了 [0,25%]/[25,50%]/[50,75%]/[75%,1] 这四个阈值（总票数可以为 5 或更高）；
> 以 Y/Total 为例，若比例落在 [75%,1]，就称 Y assured，[0,25%] 称 N assured；
> 中间两档称为有争议但偏向 Y/偏向 N。
> 我在设计概念里也倾向认为中间两档的参考性不高，会是审查环节的重点争议区域，
> 如此投票只是为了将 LLM 弃权具象化，我怕直接设计“弃权”票会导致 LLM 只选择弃权。

## Band definition

For an odd vote total `N >= 5` and `r = Y/N`:

| Band | Name | Intended use |
|---|---|---|
| `r <= 0.25` | N assured | treat as a negative observation |
| `0.25 < r < 0.50` | leaning N | advisory only; review candidate |
| `0.50 < r < 0.75` | leaning Y | advisory only; review candidate |
| `r >= 0.75` | Y assured | treat as a positive observation |

The two middle bands are deliberately *not* decision-grade. They mark the region where the
vote has not converged and where human review is expected to concentrate.

## Why votes rather than an abstain option

The binary prompt has no "insufficient evidence" answer. Abstention is materialised by the
**distribution of independent votes**, not by a third answer the model can choose. The
decision owner's concern is behavioural: an explicit abstain option is likely to become the
model's default under uncertainty, collapsing the signal we want to measure. Voting keeps
each seat forced to commit and makes disagreement observable.

## Implications

- The vote ratio is a **calibration and triage signal**, not a probability. Middle-band
  entries must not be reported as confident decisions.
- Prompts stay binary; band semantics live in code, never in the per-seat prompt.
- Vote totals may exceed three; the band definitions must hold for any odd `N >= 5`.
  The current runtime uses three seats, which cannot populate all four bands; decide whether
  three-seat runs only ever yield assured/unanimous or whether `2/3` maps to "leaning".
- Middle-band cases are the review set. A review workflow that consumes exactly these rows
  is part of the deliverable, not an afterthought.

## Evidence available at drafting

The 2026-10-19 five-spectrum run was labelled by the decision owner (22 disputed targets,
50 unanimous targets; see `_aiHumanInteract/plan/evaluations/fa-vote-bands-20261022.md`):

- unanimous targets: 45/45 correct after the doublet semantics fix;
- disputed targets: 2-of-3 majority correct on 8/14, single seats on 22/42;
- answering only the unanimous 94% of targets would have been 100% correct on the answered set.

This supports treating disagreement as a review trigger rather than a majority decision.

## Open questions

- Exact inclusivity of the 25/50/75 boundaries for odd totals (e.g. `2/5 = 40%`, `3/5 = 60%`).
- Whether `N = 3` runs are allowed to report any "assured" band, or only unanimous results.
- Escalation: second round of votes, a different model, or a human reviewer.
- Whether band membership is recorded per feature state, per report, or both.
