# WP-045 — SH hypothesis-local line alignment (2026-10-18)

## Decision and scope

The decision owner requested a report-before-write alignment step after a type
graph has completed its judgments. One line has at most one selected feature.
The trigger is multiple kept lines claiming the same hypothesis-local feature;
`NOT_FOUND`, `MASKED`, and FA-rejected measurements are excluded. Ordinary
collisions remain `TBD`. Diagnostic collisions for QSO, ELG, and LRG/BGS may
receive independent anonymous pixel-selection votes. QSO [O III] alone is not
a diagnostic trigger. Type-graph decisions and frozen SH/FA rows do not change.

## Implemented contract

- The branch node records the original shared measurement IDs, affected line
  IDs, fixed predicted positions, eligibility, per-slot data coverage, all
  attempts, model usage, the final per-slot vote tally, and an immutable
  `aligned_claims` projection for future HS consumers. Every vote has its
  own Markdown session and immutable execution ID; candidate IDs cite vote
  artifacts. Source digests and trace events allow branch replay.
- The model sees only anonymous ordered slots, their predicted wavelengths,
  emission/absorption sign, and NPZ sample IDs/flux/validity. It returns a
  peak or valley with two outer reference points, or `null`, for each slot.
  Code checks pixel validity, order, unique extremum IDs, slot boundaries,
  and positive contrast. Amplitude and FWHM are explicitly three-point
  envelope proxies using the declared outer-reference sigma convention.
- Ca K/H uses two slots. Hε is intentionally not decomposed from the red Ca H
  region. Hβ/[O III]a/[O III]b uses fixed wavelength-ordered slots; two
  observed peaks retain their original slots. A `null` slot only means no
  separately defensible signal in that vote, never physical absence.
- The normal QSO, ELG, and LRG/BGS live wrappers run alignment before their
  reports. QSO's code-owned line table annotates affected rows and appends
  per-line vote outcomes. ELG and LRG/BGS deterministic reports cite the new
  alignment node. Direct offline graph runners retain their prior no-model
  behavior for comparison.

## Verification and limits

Synthetic tests exercise shared-feature detection, Ca expansion and two-valley
resolution, QSO [O III] exclusion, Hβ/[O III] positional identity with two
detected peaks, invalid cross-slot selections, complete vote/session archiving,
and ELG report ordering with a trace citation. The graph-specific suite passes
129 tests. The full
repository suite and plan checks are recorded with the final verification
result in WP-045. No new real FITS/LLM alignment case was run, and vote
accuracy has not been independently established. Existing type decisions are
not recalculated after this advisory step.
