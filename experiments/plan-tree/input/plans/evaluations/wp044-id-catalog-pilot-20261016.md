# WP-044: SH measurement-ID pilot (2026-10-16)

The decision owner proposed replacing model-copied CSV measurements with IDs for
each CWT feature and Gaussian fit component. This pilot applies only to the new
agentic-graph path; the legacy batch SH writer remains available. The first
version below assigned IDs while constructing each SH catalog. The VI-boundary
revision at the end of this record supersedes that placement.

## Contract implemented

- The adapter freezes a per-hypothesis line/measurement catalog. Registry line
  IDs and run-local `cwt:em`, `cwt:abs` and `fit` IDs are shown to the model.
- `write_lines_csv` accepts `line_id`, `measurement_id`, `status`, optional
  `reason_codes` and `comment`. The model cannot submit measured numeric fields.
  Code resolves full-precision values and writes the existing 14-column CSV.
- The tool rejects missing/duplicate/unknown IDs, wrong emission/absorption
  kind, a fit for another line, a measurement outside the line's redshift
  window, invalid fit flags (`center_at_bound`, `fit_failed`), inconsistent
  status/measurement pairs and false `MASKED` claims. It also rejects an
  adopted doublet component plus its blended label as independent evidence.
- The scoped node records paths and SHA-256 digests for the catalog, ID
  judgments, CSV and report. The first two are new artifacts.

## Evidence and limits

- Focused SH node tests: 15 passed; legacy Redrock SH tests: 24 passed.
- One live QSO_4 hypothesis 2 run using the configured `deepseek-flash` model:
  two stages completed, 25 ID judgments became 25 CSV rows, and the provisional
  class was `Type 2 QSO` at the fixed Redrock redshift. The first CSV call tried
  to reuse a Na D1 fit component for the blended Na D label and was rejected;
  the second call repaired it. No numeric measurement fields appeared in the
  model's CSV tool arguments. Four node artifact digests matched their files.
- Local ignored run: `.data/runs/sh-pre-analysis-qso4-id-20261016/`. It is a
  historical smoke result in this workspace, not a tracked acceptance corpus.
  Its original runner predates the required `vi_catalog_path` handoff.
- Na D_abs became `NOT_FOUND` while the weak Na D components remain
  `MARGINAL`. The current four-state vocabulary does not clearly represent
  "unresolved blended identity"; decide this before treating this status as a
  scientific absence. The writer proves only that a `MASKED` nominal position
  falls in a declared mask, not that a full local line window has no data.
- ID validation cannot verify all prose statements in the Markdown report or
  certify that a line identity is scientifically correct. The live report is
  therefore provisional and must be audited separately.

## VI-boundary revision (2026-10-16)

- `prepare_vi_measurements` runs after Redrock and before any new SH session.
  It adds `cwt:em:*` / `cwt:abs:*` IDs once to the VI CWT detections, runs the
  existing targeted prefit for each specified hypothesis, and assigns each fit
  component an ID of the form `fit:<hypothesis-ref>:<ordinal>`. It archives a
  run manifest, the shared CWT list, fit attempts and one full-precision
  measurement catalog per hypothesis. IDs are scoped by the run manifest;
  reusing a VI output directory is rejected.
- The new SH adapter requires `vi_catalog_path`. It checks run ID, hypothesis
  reference, redshift, NPZ path, NPZ SHA-256 and wavelength coverage before
  rendering the prompt. It performs no Gaussian fit and allocates no IDs.
  Direct construction of a scoped catalog without upstream IDs is rejected.
- In a local QSO_4 NPZ smoke using two archived Redrock hypotheses
  (`z=0.6713696831689161` and `z=0.23787248591105023`), both catalogs held
  the same 54 CWT IDs. The first hypothesis yielded 10 fit components from 9
  attempts; the second yielded 3 components from 2 attempts. A mocked SH
  handoff rendered the second hypothesis context with shared CWT IDs and its
  own fit IDs. No LLM call or scientific verdict was made. Local ignored
  artifacts: `.data/runs/vi-measurement-qso4-20261016/`.
- `tests/agentic_graph/test_vi_measurements.py` checks cross-hypothesis CWT
  identity, distinct fit IDs, immutable output directory, rejection of ID
  rebinding, SH non-refitting and NPZ mutation detection. The new graph-wide
  orchestrator, FA consumption and revision/invalidation policy remain open.
