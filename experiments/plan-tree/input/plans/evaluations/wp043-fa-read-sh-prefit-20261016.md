# WP-043 verification — 2026-10-16

## Recovery point

- The pre-change tree was committed and pushed as `28292c7` on
  `origin/feature/evidence-graph` before implementation.

## Contract and offline evidence

- FA accepts a matrix centre and computes the declared half-window from the
  frozen `analysis_method.audit.feature_read_half_angstrom` value. Its free-range
  reader remains available for edge and composite checks.
- SH checks an in-coverage predicted line against a local, sign-compatible CWT
  candidate before running a targeted Gaussian fit. Complete registered pairs
  are handled as one doublet attempt. Each executed attempt is archived as JSON
  and displayed below the unchanged CWT and Predicted Lines tables. A failed
  attempt has no adoptable centre; a successful optimizer result is still only
  a candidate measurement.
- `write_lines_csv` accepts precomputed fit centres through the same provenance
  validator as agent-called fits, and does not attach CWT ridge/SNR to them.
  A live SH run exposed a second provenance issue: one Na D component fit was
  also written under the blended `Na D_abs` label. Candidate measurements now
  carry their target line, and the writer rejects a different label for that
  same fitted centre. It also rejects a blended label counted alongside an
  adopted component of the registered doublet, even when a CWT trough
  coincides. The focused regression uses this exact component/blend
  relationship; the full FITS run began before the correction was loaded.
- Separate suite discovery avoids the repository's `tests/evaluation` package
  shadowing the top-level `evaluation` package. Final results: reasoning 493 run
  (490 passed, 3 skipped), runtime 43 passed, evidence 278 passed, evaluation
  6 passed. The reasoning suite includes the numerical-display and blended-line
  provenance regressions.
- The prompt authority inventory was regenerated: 72 classified statements,
  zero problems. An existing audit manifest line shift and a Type 1/2 class
  label were classified. Tests that froze an old 100 Å FA window now read the
  effective method configuration, whose current value is 150 Å.

## Real-model check

- Isolated QSO_4 Redrock hypothesis H2 used the retained real NPZ and the
  configured model. The run is at `.data/runs/wp043/QSO_4_H2/` (local, ignored).
  It produced two prefit attempts, both warnings (Na D doublet and Mg I), no
  adopted fit centre, no repeated fit tool call, a 25-row CSV and a report.
  Its verdict was `SUPPORTED`, with a narrow-line AGN interpretation at
  redshift 0.238. This checks prompt/tool integration for one hypothesis; it
  does not measure population-level classification quality.
- A first full FITS attempt stopped before hypothesis analysis because the
  invoking shell omitted the conda `rrdesi` directory from `PATH`. The retry
  used the existing binary and template paths.

## Full FITS run

The QSO_4 retry at `.data/runs/wp043/full-QSO4-retry/` completed (local,
ignored). Redrock supplied six hypotheses; all six SH stages wrote prefit
archives and CSV catalogs. FA called `read_feature` once for each of its 36
matrix rows, wrote a schema-valid 36-row verdict, and produced six cleaned
catalogs. The final report was written with `type=QSO`, `redshift=0.2387`,
and defect grade `MEDIUM`. This is an execution check on one familiar sample,
not an independent science calibration. The FA trace is roughly 0.8 MB, so
the per-row raw reads have a material context and latency cost. The model
accepted them in this run; a compact read representation remains a future
performance option.

This full process had imported the code before the later precision-display,
immediate FA file recognition, and blend-duplication corrections. Its execution
evidence covers the read and prefit wiring, while the final corrections are
covered by focused offline tests and a separate post-fix H4 model check.

The post-fix H4 run at `.data/runs/wp043/QSO_4_H4_postfix/` completed with the
configured model. The CSV adopted Na D1 and Na D2 from `fit_doublet`, while
`Na D_abs` had no adopted centre or source. One `write_lines_csv` call succeeded;
the model did not need a repair turn. The offline regression separately proves
the writer refuses a duplicated blend if a model does propose one. This is one
real-model check of the correction, not a rate estimate.
