# WP-045 · SH line review and code-owned type entry (2026-10-18)

## Decision and change

BGS_2 H3 exposed premature rejection: Redrock found z=0.15896775446705771 (VI z=0.159), but the former SH report treated an uncertain Ca K/H fitted depth order, weak [O II]/[O III] and absent Balmer emission as a reason for an overall `NOT SUPPORTED`/`null` result. The global `null` gate then pruned the hypothesis before its LRG/BGS graph could inspect Dn4000 and Ca H/K. The decision owner specified a code-owned **ordered evidence check**, not a first-match final classification.

New FITS graph runs use `sh_line_review.py`: a single model tool phase submits a full ID-based CSV and judgments, with a session transcript and artifact digests. It writes no SH report and no preliminary type. The historical `sh_pre_analysis.py` contract stays readable for archived runs. After FA, `type_entry_router.py` checks [Ne V], QSO diagnostics, Dn4000/Ca H/K, and [O II]/[O III] in that order, records all results and source references, and opens an initial type graph. `record_entry_route` makes the code-derived working entry state replayable across branch forks. No positive entry evidence is `unresolved`, rather than a model-authored `null` prune. Type-graph reporting remains downstream.

The current graph controller opens **one initial graph per hypothesis** and records all other eligible graphs. Whether several eligible graphs should execute on separate branches, or be deferred to explicit recheck, remains a decision-owner question; no multi-graph execution is claimed here.

## BGS_2 evidence

- Historical H3 SH×FA archive: Ca K `fit:H3:0004` and Ca H `fit:H3:0005` both have adopted signal. Replaying the new router against those archived votes selected `LRG/BGS`; the frozen Dn4000 value was 1.5309836684. Running the existing LRG/BGS graph on that replay returned `survive`, `candidate_type=LRG/BGS`. These are read-only scientific inputs with new diagnostic route artifacts under the ignored `.data/output_/basic-five/20261017T202900Z-66015ae9/BGS_2/diagnostics/`; they do not replace the historical run result.
- One H3 line-review session with the configured live model completed in 2 model calls. It wrote 25 judgments, a CSV and an archived transcript; it wrote neither `report.md` nor a second-stage classification. The model retained both Ca components and the [O II] fit. It also marked individual [O III] fit components despite the pair separation warning; individual feature reality remains subject to FA and the doublet relation remains advisory, so this single session does not establish [O III] as a credible doublet.
- A mixed import using the new H3 node and the other five historical SH nodes succeeded: six hypotheses and 33 scoped feature entries; H3 has no SH report artifact. This verifies migration coexistence, not scientific compatibility of the two modes.
- The replay uses historical FA ballots, whereas the live line-only SH table has different pairings. A complete new FITS→SH→FA→types→HS result for BGS_2 has **not** been run. The observed `survive` is a path check, not a new final classification or independent scientific validation.

## Verification

- `tests/agentic_graph/test_line_review_router.py`: line-only tool contract, no report/class, Ca route and fork replay.
- `tests/agentic_graph/test_graph_workflow.py`: new SH node through FA and code route to the LRG/BGS graph and HS.
- `PYTHONPATH=src /home/user/apps/miniconda3/envs/forma/bin/python -B -m unittest discover -s tests/agentic_graph -p 'test_*.py' -q`: 154 tests passed before final documentation and source-reference tightening.
- The same 154-test agentic suite passed again after source-reference checks and phase-marker validation. The full suite (`-s tests -t . -q`) passed 821 tests with 9 skipped. `_aiHumanInteract/plan/validate.py`, generated graph check and 15 plan tests passed.

## Remaining risks

An unpaired SH `NOT_FOUND` line has no FA vote; type graphs need targeted reads where missing a line matters. The router records every positive family but executes only one starting graph in the current controller. The existing type-graph validators still use a field named `classification`; in new runs it is a code-owned **working route value**, not an SH model judgment or final object type. Full BGS_2 end-to-end compatibility and competing-type cases remain open.
