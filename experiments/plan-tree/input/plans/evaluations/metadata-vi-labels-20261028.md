# VI labels moved to METADATA: reader and type-mapping fixes

Date: 2026-10-28.

## New file format

`example/basic/*.fits` no longer contain a `FIBERMAP` HDU. The single-row
`METADATA` BinTable carries `TARGETID`, `TILEID`, `TARGET_RA`, `TARGET_DEC`,
`VI_SPECTYPE`, `VI_Z`, `VI_QUALITY`, `SNR_sum` and `quality`. Spectral data are
per-arm `B/R/Z_WAVELENGTH`, `_FLUX`, `_IVAR`, `_MASK` and `_RESOLUTION` arrays;
the primary HDU has no object metadata.

`VI_SPECTYPE` for the three galaxies is now `GALAXY` (not BGS/ELG/LRG), so type
comparison can only distinguish galaxy vs QSO unless another source supplies the
subtype.

## Fixes

- New `src/FORMA/core/fits_labels.py`: reads the first available label table from
  `FIBERMAP` or `METADATA`, exposes `TARGETID`, and maps VI types to candidate-type
  sets (`GALAXY -> {ELG, LRG/BGS}`).
- `run_contract.read_truth` and `summarize_hs` delegate to it; demo and CLI index
  rows regain truth, redshift error and type matching.
- `core/evidence/builders/spectrum.py` reads `TARGETID` from either table.
- `scripts/run_baseline.py`, `evaluation/agentic_graph/run_basic_five.py` and both
  calibration selectors read labels through the shared helper; selectors accept a
  `GALAXY` FITS label against a subtype CSV row.
- `test_run_contract`, `test_main_contract` and `test_basic_five_runner` expectations
  follow `GALAXY`; the boundary selector test skips when the ignored `.test_set`
  dataset is absent.

## Verification

- `demo.py --preflight-only`, `scripts/main.py --preflight-only`,
  `run_basic_five.py --preflight-only`: VI labels present, `GALAXY`/`QSO`.
- `_load_spectrum_from_fits(..., arm_names=["B","R","Z"])`: 7604 samples, `VI_Z=0.159`,
  `VI_SPECTYPE=GALAXY`.
- `read_vi_truth` and `target_id_from_hdul` return `METADATA BinTable columns` and the
  correct TARGETID.
- `tests/agentic_graph`: 187 tests OK.
- `tests/reasoning`: 492 tests OK, with 12 data-dependent skips (baseline run
  artifacts and optional datasets); the boundary tests run against `_test_set`.

## Limits

- Galaxy subtype (BGS/ELG/LRG) is not recoverable from the new files; comparisons are
  galaxy-vs-QSO only unless a subtyped source is supplied.
- A full five-spectrum run was deliberately not repeated.
