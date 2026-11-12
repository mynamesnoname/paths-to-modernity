# Unified demo / CLI run contract

Date: 2026-10-28.

## Contract

Both `demo.py` and `scripts/main.py` create one immutable run directory
`<output-root>/<UTC timestamp>-<uuid8>/`, write each sample under `<run>/<sample>/`,
and maintain `<run>/index.json` (schema `forma-run-index-v1`, written atomically after
every sample). `demo.py` and the graph workflow use `summarize_hs`; the legacy workflow
uses the same wrapper and additionally writes `<run>/in_brief.csv`.

## Input selection

`scripts/main.py` now accepts:

- `--file-name NAME` — single sample;
- `--samples A B C` — explicit batch;
- `--all` — every `*.<input-format>` file in the input directory;
- `--input-dir`, `--input-format` (default `fits`), `--output-root`;
- `--preflight-only` — resolve inputs, read FIBERMAP labels, and report missing files
  without creating a run directory or calling Redrock/the model.

Environment fallbacks: `INPUT_DIR`, `INPUT_FORMAT`, `OUTPUT_DIR`, `FILE_NAME`,
`FILE_BATCH_*`. Sample names are validated; absolute paths, separators and `..` are
rejected, closing the `os.path.join` escape found in the old CLI.

## Verification

- `tests/agentic_graph/test_run_contract.py`: name validation, fresh run dirs, atomic
  index, FIBERMAP truth, missing-truth summary.
- `tests/agentic_graph/test_main_contract.py`: single/batch/`--all` preflight, missing
  file, traversal rejection, no output side effect.
- `tests/agentic_graph/test_main_graph_selection.py`: one run dir, one index, graph row.
- `tests/agentic_graph`: 185 tests OK.
- `tests/reasoning`: 492 tests, only the two pre-existing missing-fixture errors.
- Live: `scripts/main.py --workflow agentic-graph --file-name BGS_2` produced a fresh run
  directory with `index.json` and `BGS_2/`. The first attempt hit a transient provider
  `BadRequestError` in SH H1; the retry completed HS-stage with `LRG/BGS` at
  z=0.159146 (VI type match). This is a provider-side failure, not a contract error.

## Limits

- The legacy workflow is exercised structurally (same factory/config/output root); a full
  live legacy run was not repeated in this change.
- `demo.py` keeps its fixed five-sample default and its own output root
  (`.data/output_/demo`); it shares the run-directory and index code.
