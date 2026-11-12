# FA read windows scaled by measured FWHM

Date: 2026-10-26. Decision owner: project user.

## Change

The agentic FA nodes no longer read a single fixed Å window. Each side is
`max(configured minimum half-width, factor × measured FWHM)`.

- Single feature (`build_feature_window`): `half = max(audit.feature_read_half_angstrom,
  audit.feature_read_fwhm_factor × FWHM)` where FWHM is the frozen measurement's
  `FWHM_A`/`fwhm`, or `fwhm_km_s × centre / c` when only a velocity width exists.
- Doublet (`build_doublet_window`): the left side uses the blue component's measured
  FWHM and the right side the red component's,
  `[λ_left − margin_left, λ_right + margin_right]` with
  `margin = max(doublet_review.context_margin_angstrom, context_fwhm_factor × FWHM)`.
- Missing or unusable widths fall back to the configured minimum.

The JSON parameters keep their names but now mean **minimum** read half-width/margin;
`feature_read_fwhm_factor` and `context_fwhm_factor` are new and default to 1.5.
Legacy fixed-read tools (`AnalysisAuditor`, RA reads) still use the value as their exact
half-width because they have no FWHM at read time; this change is scoped to the agentic
FA path.

## Effect

- Narrow lines keep the old floor (100 Å example config, 150 Å local profile).
- Broad lines widen: with a 1.5 factor, FWHM 100 Å at the floor 150 Å gives a 150 Å
  half-width, a QSO broad line with FWHM 10000 km/s at 6000 Å (200.2 Å) gives 300.3 Å, and
  the wings beyond the old fixed window are still covered (1.5 FWHM = 3.53σ, 99.96% of a
  Gaussian, edge height 0.2% of peak).
- A doublet with a wide blue component and a narrow red component gets an asymmetric
  window instead of a symmetric fixed margin.
- Compared with a 2.0 factor, the read window is 25% narrower for broad features while
  still enclosing essentially the whole Gaussian; narrow features remain floor-dominated.

## Verification

- `tests/agentic_graph/test_fa_feature_reality.py`: measured-Å and km/s conversion cases.
- `tests/agentic_graph/test_fa_doublet.py`: per-side margins from each component.
- `tests/agentic_graph`: 176 tests OK.
- `tests/reasoning`: 492 tests, only the two pre-existing missing-fixture errors.

## Limits

- The factor and floors are analysis conventions, not physical widths; the window is a
  read region, not a detection threshold.
- No change to measurement values, vote prompts or output schemas.
