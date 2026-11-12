# WP-045 — basic-five SH incomplete-turn review and repair (2026-10-18)

## Observed run

- Source: `.data/output_/basic-five/20261017T202900Z-66015ae9/index.json` and QSO_4 node sessions; `example/basic` held five VI-quality-4 spectra. BGS_2 completed with zero surviving groups and a legitimate HS abstention. ELG_6, LRG_1 and QSO_116 completed with one surviving group each and provisional HS selections. QSO_4 failed during SH H1; five other SH nodes were complete. These are development examples, not an independent accuracy evaluation.
- The failed H1 session had a successful `write_lines_csv` result, followed by a plain assistant message saying it would write the report, then a natural stream end. No `write_report` call occurred. The SH guard correctly withheld stage 2 and the node. The old parallel `TaskGroup` propagated this as an `ExceptionGroup` and prevented a complete sample outcome.
- The session recorder's `output_tokens: 384000` came from provider `completion_tokens`; the visible answer was short. Neither the archive nor the client proves whether the count reflects hidden reasoning, a provider counter, a limit value or billable cost. Preserve the raw value, label the large visible-output gap as unverified, and do not silently replace it with a guessed estimate.

## Correction

- `sh_pre_analysis.py` now gives an incomplete phase one or phase two a single archived continuation turn using its existing transcript and tools. A completed CSV is not rewritten by the repair instruction; all original digest, report format and submission checks still apply. A second incomplete stream remains a failure.
- `graph_workflow.py` now lets independent SH tasks finish after a sibling raises. `sh_batch_summary.json` records completed node paths and failed referents; the sample remains failed when any hypothesis lacks a validated node. This preserves the all-hypotheses boundary rather than making a partial result look complete.
- `session_markdown.py` retains provider usage unchanged and adds an unverified usage note when reported output tokens dwarf visible content. No cost normalization is inferred.

## Verification and remaining issue

- New tests cover the premature first-phase stop, a successful continuation, sibling isolation, and the unusual provider usage record. The agentic suite passed 151 tests and the legacy suite passed 821 (9 skipped).
- Re-running only QSO_4 H1 from the frozen VI catalog under a new output directory succeeded: three stage-one model calls, one stage-two call, complete report and node. This run completed naturally and therefore validates the fixed input route but does not independently exercise the new continuation with a real provider; the deterministic test does.
- A downstream QSO_4 recovery run reused the five original SH nodes and the new H1 node. It reached FA: 60 vote session files existed, 59 had completed, and one had only an input prompt with no returned event for over four minutes. The run was deliberately terminated; no HS result or 5/5 completion is claimed. This exposes a separate missing per-vote timeout/retry boundary, not the original SH premature-finish defect. The partial recovery output remains under `.data/output_/basic-five/qso4-sh-recovery-7a7a2de1/` for inspection.
