# Empirical parameter survey (2026-10-13)

Read-only survey of judgement numbers hard-coded in `src/FORMA/`, run for `WP-040`
under the decision-owner criterion: **a number that encodes how we choose to judge
is an empirical knob (declarable, configurable); a physical or structural fact is
not.**  Line numbers are against the 2026-10-13 10:41 snapshot.

普查（只读）判断数值的归属，判据由决策人给出：编码"我们选择如何判断"的数值是可声明、可
配置的经验旋钮；物理与结构事实不可配置。

## Converted by WP-040

| declaration | value | where it is read now |
|---|---|---|
| `membership:offset-quality` | trapezoid −80 / −20 / +20 / +80 Å | `fuzzy.offset_quality`, SH run message, FA/RA registry render |
| `membership:broad-qso` | ramp 1500 → 2000 km/s, **both endpoints derived** from `rule:formal-qso2-nev-requirement.has_broad_lines` and `rule:formal-width-class-match.width_consistency_score` | same |
| `membership:detection-snr` | ramp 5 → 10 (upper endpoint derived from `rule:formal-detection-snr.detection_snr`) | same |
| `membership:line-inventory` | ramp 2 → 4 (lower endpoint derived from `rule:formal-line-inventory.n_likely_lines`) | same, plus `harness_rules` |
| `parameter:evidence.same-feature-tolerance` | 1.0 Å | `evidence_refs.same_feature_tolerance_angstrom`, `builders/analysis.py` |
| `parameter:evidence.catalog-copy-tolerance` | 0.1 Å | `builders/analysis.py` |
| `parameter:sh.redshift-search-half-window` | 0.1 Δz | `HypothesisAnalyst` batch, `single_hypothesis._build_user_message` fallback |

## Still hard-coded (backlog)

Grouped by consumer; every row is empirical unless marked physical.

**Fitting and search windows (SH tools, 3–5 copies each).** `window_half` 200 Å
(`single_hypothesis.py:114`, `tools.py:359/461/720`), doublet window 300 Å
(`:136`, `tools.py:520/702`), `width_3sigma` 25 Å (`:135`, `tools.py:519/701`,
registry `fitwin:narrow`), separation tolerance 5 Å (`:138`, `tools.py:522/704`,
rule `sep_deviation` rhs), CaHK width-class override (`:457`), min samples 10/20,
σ-init floor 2.0 Å, centre bound ±50 Å, fitted σ floor 1.0 Å, `maxfev` budgets.

**CWT internals (`utils/cwt_feature_finder.py`).** noise window 50 px, noise floor
fraction 0.1, ridge pixel tolerance 10, FWHM pixel floor 2.0, σ-init scale 0.85,
baseline median width `max(51, n//20)`, **amplitude error fraction 0.15** (invented,
feeds the evidence graph), width-class cuts <1000 / <2000 km/s (a private class
vocabulary that includes the non-registry class "intermediate").

**Continuum (`utils/VI.py`, `VisualInterpreter.py`).** Chebyshev degree bounds
1–10, score weights `MAD*10 + (|skew|−0.5)²*5 + deg*0.2`, residual clip 95th
percentile, mask width ±3σ, min fit points 20.

**Redrock adapter.** score mapping `100/(1+Δχ²)`, archetype Legendre degree 2 /
prior 0.1 (live values — never passed through `ParamsConfig`).

**Assumed effective SNR.** `VisualInterpreter.py:391` uses **7.0** while
`VI.py:518/695/702/730` uses **5.0** for the same IVAR-missing fallback.

**Auditor.** verified-feature merge 2.0 Å (`AnalysisAuditor.py:904`) versus 1 Å
`int(wl)` binning in the same file; 4000 Å / 7800 Å literals in the RA prompt
template (`result_auditor.py:144-145`, owned by registry rule conditions and
therefore not overridable); `_BROAD` line-name tuple (`auditor_rules.py:26`)
restating registry `width_class="broad"`; missing-line assessment match 1.0 Å.

**Harness rules.** `_KEEP_STATUSES` / `_KEPT` (duplicated sets), O III 47.9 Å
(duplicates registry `doublet:oiii`), neutral width score 1.0, outflow min lines 2.

**Runtime / routing.** forest verdict match floor `max(1.0, |λ_err|)` (twice),
`routing.py` ambiguous ≥ 0.6 (unreachable — the orchestrator passes 0.0), fast-mode
n_features ≤ 1 and median SNR < 1.0.

**Argumentation.** `accept_threshold` 0.5, `reject_threshold` −0.25, relation
weight 0.5, score cap ±1.0 — no in-pipeline caller today; the frozen calibration
chose 0.7 / 0.0.

**Index / synthesis.** Dn4000 min samples 3+3 px, z-scatter min lines 2, feature-key
1 Å binning (6 sites in 3 files), O II slope-change window 25 Å (5 copies), O II
guards, top-quartile 25 %.

**LLM temperature.** 0.1 (SH, auditors) / 0.3 (report writer, result auditor) / 0.0
(summary extraction) while `LLM_TEMPERATURE` exists and is bypassed by these calls.

## Duplicates worth fixing first

1. **2000 km/s appears in ≥6 places**; only `rule:formal-width-class-match`'s
   operand threshold is overridable, so overriding it does **not** move
   `AnalysisAuditor._BROAD_WIDTH_KMS`, the CWT width classifier or KB prose.
2. **1000 km/s**: registry `rule:formal-width-class-contradiction` versus the CWT
   classifier's private cut.
3. **200 Å / 300 Å / 5 Å fit windows** across the tool schema and the tool bodies.
4. **1 Å binning** in three files versus **2.0 Å** for the same class of operation in
   `AnalysisAuditor.py:904`.
5. **Assumed SNR 7.0 vs 5.0** for one fallback.
6. **σ→FWHM** 2.35482 vs 2.355 vs `np.sqrt`; **c** 2.99792458e5 vs 3e5.
7. **Kept-status sets** duplicated between `harness_rules` and `auditor_rules`.

## Decisions this survey raises

- LLM temperature: three literals bypass `LLM_TEMPERATURE` — is sampling temperature
  inside the "empirical knob" policy, or a model-call policy recorded elsewhere?
- `prompt_audit` audits **markdown only**; judgement numbers embedded in Python
  prompt templates (4000/7800 Å, "±300 Å", "100–300 Å") escape it. Make templates
  auditable, or move those numbers to declarations.
- `kb/lines.md:54` states a median-SNR < 1.5 bound and the audit record claims a code
  parameter owns it; no such parameter exists.
- Dead numbers better deleted than declared: `_DOUBLET_PARAMS` (tools.py:501-510),
  `HA.py:50` z category, `VisualInterpreter.py:409` `n_iterations`,
  `scientific_method.json` (declares itself not loaded), `grade_parameters.py`
  (retired loader that still parses).
- `evaluation/` and `scripts/` duplicate `z_tolerance` (0.005) and hold the frozen
  calibration 0.7/0.0 that `src/`'s `EvaluatorConfig` (0.5/−0.25) never reads; no
  `evaluation/` or `scripts/` number is consumed by a pipeline stage.

## Re-audit 2026-10-15 (current code, four parallel read-only passes)

The 2026-10-13 line numbers are against `ec8ad55^`; the 2026-10-14 commit
`ec8ad55` plus the same-day B/C/D checkpoints resolved most of the list. What the
re-audit found, area by area:

**Shipped since the survey (no action left).** Gaussian fit/search windows
(`single_window_half_angstrom`, `doublet_window_half_angstrom`,
`doublet_separation_tolerance_angstrom`, min samples, σ floors, centre bound,
`maxfev`) are declared in `analysis_method.json` and read in the tool bodies; the
LLM-facing schemas carry `float | None = None`; `width_3sigma` resolves through
`build_width3sigma_map()`. `analysis_method.json` also owns the CWT knobs (noise
window/floor, ridge drift, FWHM floor, baseline width, `amplitude_error_estimate_fraction`),
the continuum score weights, residual clip, mask width and min points, the Dn4000
and z-scatter sample floors, the top-quartile fraction, the verified-feature merge
(2.0 Å) and missing-line match (1.0 Å) distances, and the [O II] search window.
`config/model_calls.json` owns all seven stage temperatures (`LLM_TEMPERATURE` is now
unreachable). The assumed-SNR **7.0-versus-5.0 split is gone** (one declaration,
`instrument.missing_noise_effective_snr_placeholder`). The Redrock
`100/(1+Δχ²)` score is deleted. The CWT private 1000/2000 km/s cuts now resolve
`rule:formal-width-class-contradiction` / `rule:formal-width-class-match`, and the
2.0 Å merge reads its declaration.

**Fixed in this re-audit** (each guarded by `tests/reasoning/test_declared_values_read.py`):

| previously bypassed declaration | bypass | now |
|---|---|---|
| `rule:formal-blue-edge-risk` / `rule:formal-oh-zone-risk` bounds | `harness/result_auditor.py:145-146` restated `4000 Å` / `7800` while the FA prompt rendered the records | both renderers call the new shared `rule_parameters.rule_condition_bound()` |
| `parameter:evidence.same-feature-tolerance` | `ontology/runtime.py:122/155` used `max(1.0, …)` in both branches | both branches read the declared tolerance |
| `analysis_method.audit.oii_slope_search_half_angstrom` | three tool wrappers defaulted `search_window = 25.0`, so the declaration was never reached (one copy was never even registered) | defaults are `None`; the dead copy is deleted |
| `cwt.wavelet_response_snr_threshold` / `min_ridge_length` | detector fallbacks `5.0` / `2` contradicted the declared `8.0` / `4` | fallbacks removed; the declaration is the only default |
| `continuum.chebyshev_min_degree` / `max_degree` | an always-`False` `hasattr(params, …)` guard fell back to `1` / `10`, in the live fit and in the frozen recompute | both read the method profile through `_continuum_bounds()` |

**Still open (this package's remaining backlog).**

1. ~~**Per-doublet fit-width class**~~ — **done 2026-10-15** (decision owner:
   the doublet follows its components). `DoubletRecord.fit_width_class` now
   declares the class (default `narrow`, preserving every other doublet) and
   `doublet:cahk` declares `absorption`; the harness hint and the tool's
   `width_3sigma` fallback both resolve it through the fit-window map, so the
   number rendered in the run message and the number the fit starts from are one
   declaration. Consequence recorded: CaHK's starting sigma moves from 30 Å
   (`broad` 90/3, the former hard-coded branch) to ≈6.7 Å (`absorption` 20/3);
   `width_3sigma` is the optimizer's initial guess, not a bound.
2. ~~**Feature-identity binning**~~ — **done 2026-10-15** following the decision
   owner's review at the end of this section. The twelve `int(wl)` identity sites
   (the review found three more than this list had: the doublet component-status
   matches at `hypothesis_synthesis.py:288/289/294`) now resolve through
   `verdict_io.bind_feature()`, which answers "same feature?" by the *declared*
   separation and returns three states: `bound` (unique candidate), `ambiguous`
   (several candidates), `unmatched` (none). Nothing is resolved by picking the
   nearest. Grouping uses deterministic complete-linkage merging
   (`merge_items_within_tolerance`, representative = lowest centre, members
   recorded). The identity check now also runs **where the verdict is written**
   (`write_feature_verdict`/`write_result_verdict` path): an unmatched or ambiguous
   row is refused with the offending row and the nearest distance named, and an
   accepted row records its `matched_center`. Cleaned CSVs carry
   `feature_audit_status`/`feature_audit_candidates`; the synthesis matrix keeps an
   unbound feature with `identity_status`/`identity_reason` and says so in the row
   and in the count.
   **Remaining**: the graph projection does not yet turn a non-`bound` status into
   a `quality_issue` node, and an ID cross-check would need the matrix to expose
   stable feature IDs to the model (a prompt/schema decision).
   **Review repair 2026-10-16**: the synthesis matrix, cleaned CSV and doublet
   component lookup now retain the verdict's emission/absorption type. The
   write-time check alone was insufficient while later joins discarded it: a
   peak `REMOVE` could remove a coincident trough. Regression tests cover both
   matrix and cleaned CSV paths; unknown type stays unbound.
3. ~~**Kept-status vocabulary**~~ — **done 2026-10-15** (decision owner: delete
   the leftovers). The vocabulary is declared once in `src/FORMA/core/line_status.py`
   (`LIKELY`/`MARGINAL`/`NOT_FOUND`/`MASKED`, each with its meaning and whether it
   asserts a measurement) and every consumer imports a **named predicate** for the
   question it asks: `is_kept_evidence` (both rule adapters, the plotting helper,
   the auditor's row filters), `is_measured`, `status_rank` (the summary tables),
   `claim_assertion` (the graph projection, which lost its private
   `CLAIM_ASSERTION_BY_STATUS` dict). The two rule adapters' duplicate
   `{"LIKELY","MARGINAL"}` sets are gone, and `ESTIMATED`/`SPURIOUS` — consumers with
   no producer — are deleted, together with the `CONFIRMED` value that survived
   nowhere. The summary now lists **every** declared status (including `MASKED`,
   which the old order silently skipped) and counts them in its footer. The write
   boundary validates the vocabulary: `write_lines_csv` refuses an unknown status
   with a repairable error naming the row, instead of writing a value that one
   stage would display and the rules would silently drop.
4. ~~**Registry restatements**~~ — **done 2026-10-15** (decision owner: fix
   autonomously). `auditor_rules._BROAD` is gone: the auditor's broad inventory is
   now `_broad_line_names()`, which reads `width_class="broad"` **and** an
   emission/both `line_type` from the registry, so a reclassification follows
   automatically and an absorption record can never enter it. `47.9` is read from
   `doublet:oiii.rest_separation` (still not configurable — a physical fact with
   one authority). The width check no longer writes sentinels: the operand is the
   **measured margin** from the pivot in the direction the line's class demands
   (`-1850.0` for a 3850 km/s line whose class wants less than 2000, `-800.0` for a
   1200 km/s broad line), and a `both`/`absorption` line contributes **no value**,
   leaving the operand unknown instead of a `+1.0` that merely sat on the passing
   side. The dead `per_line_width` dict was removed with it. The outflow rule keeps
   its two-line requirement, now **declared**: the operand's `missing_meaning` is
   `not_applicable` and its description states the requirement, so a hypothesis with
   fewer than two pairable lines records
   `operand 'delta_v_kms' unknown or missing; missing_meaning=not_applicable`
   instead of a bare null; and a line with no declared ionization potential is no
   longer treated as `0 eV` (it cannot be paired, which previously could invent a
   velocity).
   Related registry fix in the same pass: `line:mgii-2800-abs` is
   `width_class="absorption"` (it was the only absorption line marked `broad`), and
   its citation was corrected — the KB puts the BLR on the *emission* side
   ("broad emission (QSO BLR) and narrow absorption (ISM)"), which the old citation
   had inverted. This was live, not cosmetic: as a `broad` line an absorption row
   was scored as a claimed broad emission line and polluted `claimed_broad_fwhm_kms`.
   Tests: `tests/reasoning/test_registry_restatements.py` (14). Suites: 729 pass.
   Follow-up the same day: the outflow inapplicability now names its cause (the
   evaluator accepts a per-operand `missing_reasons`, so the trace reads "only 1
   kept emission line(s) …" or "1 of 2 kept emission lines have no declared
   ionization potential ([N II]a) …"), and `[S II]`/`[N II]` declare their
   ionization potentials (23.34 / 29.60 eV, the convention the registry already
   follows for Mg II, C III], C IV, He II and [Ne V]). Recorded observation: the two
   oxygen entries use the KB's other rendering (the energy that produced the ion),
   which the ordinal outflow contrast does not care about but which is a
   data-quality note. Tests: 17 in the same file; suites 732 pass.
5. ~~**CWT width-class vocabulary**~~ — **done 2026-10-15** (decision owner: two
   vocabularies, each declared). `width_class` had been naming two questions: the
   class of a *line* (`LineRecord.width_class` in the registry) and the measured band
   of a *feature* (the CWT catalog column and the contradiction matrix row). The
   second had no declaration, so `intermediate` existed only in two code expressions
   and one prompt sentence, and its boundaries were read from different rule
   declarations by the two producers. Now
   `src/FORMA/core/reasoning/ontology/feature_width.py` declares the band vocabulary
   (`narrow`/`intermediate`/`broad`, each with its meaning and its note for the
   width-conflict question) and names **one owner per boundary**: the
   narrow/intermediate boundary is `rule:formal-width-class-contradiction`'s
   `claimed_broad_fwhm_kms`, and the intermediate/broad boundary is
   `rule:formal-qso-broad-width`'s `fwhm_kms` (the CWT finder used to read that
   boundary from the width-consistency pivot — same 2000 km/s, wrong owner). Both
   producers call `band_of()`, the catalog write validates the column and fails
   loudly on an undeclared value, and the FeatureAuditor prompt legend is rendered
   from the declaration (`legend()`), including the middle band's declared meaning:
   consistent with a narrow-class claim, not enough for a broad-class claim, never a
   conflict by itself. The executable rule is unchanged (its pivot stays 2000 km/s);
   only the labels and their authority moved. `row_width`'s representative is now
   explicit and traceable (`row_width_from`). Tests:
   `tests/reasoning/test_feature_width_vocabulary.py` (12). Suites: 744 pass.
6. ~~**Dead code**~~ — **done 2026-10-15**, with two entries reclassified and one
   correction, all recorded below.
   **Removed**: `HA.py`'s `category` (`'low' if z < 1.0 else 'high'`, never read by
   anything, and an undeclared empirical threshold at that); `tools.py`'s
   `_WIDTH_3SIGMA_MAP` (an import-time snapshot of the fit windows with no reader,
   which could disagree with the value the fit actually used — active fitting calls
   `build_width3sigma_map()` per use), together with the four `Width3SigmaRecord`
   citations that pointed at it (now at
   `config/analysis_method.json`/`gaussian_fit.width_3sigma_angstrom_by_class`) and
   the schema docstring that named it; and `RoutingFeatures`' unread fields
   (`snr_median`, `snr_is_assumed`, `n_redrock_fits`) plus the OH-zone/blue-edge
   branch, whose flags the caller never set and whose fall-through already returned
   the same `standard` mode — so it could not change a decision, only a reason
   string. The orchestrator no longer computes the SNR values nobody read, and the
   routing test now pins that the feature count alone decides.
   **Correction**: `LLM_TEMPERATURE` is *not* dead. It is the client default for the
   calls that do not set their own temperature (the VLM path and `BaseAgent`), while
   the audited stages pass `temperature_for(stage)` from `config/model_calls.json`.
   The knob stays, and the "default 0.1" documentation now says which calls it
   governs and where the per-stage values live.
   **Retired 2026-10-15** (decision owner's rule: every JSON configuration lives
   in `config/`, and `config/grade_parameters.json` never existed): the loader
   `src/FORMA/core/reasoning/ontology/grade_parameters.py` and
   `tests/reasoning/test_grade_parameters.py` were deleted, the diagnostic stopped
   reporting injected parameters, the harness trace lost its empty
   `applied_grade_parameters` placeholder, WP-012's links/evidence were pruned with a
   dated retirement note in its body, and
   `docs/architecture/defect-grade-parameters.md` carries a dated note above the
   historical design. Historical diagnostic artifacts keep the values they recorded.
   **Kept**: `evaluation/calibration/parameters.json` is a dated calibration *record*
   (`forma-calibration-v1`, thresholds with per-predicate justifications, 2026-10-10)
   and WP-012 evidence; having no code reader is its nature, not a defect, and
   deleting it would destroy provenance.
   **Corrected twice**: `LLM_TEMPERATURE` first looked dead, then live, and after
   checking every acquisition point it is dead for live calls — `runtime.get_model()`
   is called only by `BaseAgent.__init__`, and the helper that uses those clients
   (`call_llm_with_context`) is referenced only from commented-out code in
   `VisualInterpreter`; every live stage builds its own client with
   `temperature_for(stage)` from `config/model_calls.json`. The knob stays because the
   commented-out PNG/vision path is preserved history by policy, and README plus
   `model_config.py` now state exactly that.
   Tests: 743 pass.
7. ~~**Duplicates that still disagree**~~ — **done 2026-10-15** (decision owner:
   Form A for the tolerance; the constants needed no ruling).
   **`z_tolerance`**: the evaluation now reads the pipeline's declared
   `config/analysis_method.json` → `evaluation.redshift_tolerance` through
   `evaluation/declared_parameters.py`, so one criterion has one source and the two
   halves of the feedback loop agree. `compare_candidate.py`,
   `evaluator_calibration.py`, `calibration_tuner.py`, `defect_annotation.py`,
   `run_ablations.py` and `scripts/run_baseline.py` lost their `0.005` criteria; the
   comparison record carries `z_tolerance_source` next to the value; the tighter VI
   margin survives only as `REPORTED_VI_MARGIN_Z`, a reported margin (the
   comparison's keys were renamed from `within_0.005_*` to
   `within_reported_margin_*` and the artifact regenerated). Origin recorded: the
   *code default* in `analysis_method.py` was 0.005 while the shipped profile said
   0.01, so a profile-less checkout judged differently; the default now mirrors the
   profile. Visible effect: the calibration report's `top_score_contains_correct`
   moves 3 → 4 — one unit the evaluation used to call a redshift failure is a match,
   which is what the pipeline always judged it to be.
   **σ→FWHM and `c`**: declared once in `src/FORMA/core/constants.py`
   (`SIGMA_TO_FWHM = 2·√(2·ln 2)` computed, `FWHM_TO_SIGMA`, and
   `SPEED_OF_LIGHT_KMS = 2.99792458e5`), replacing the truncated `2.35482` in the
   fitting tools, the rounded `2.355` in `utils/VI.py`, the CWT finder's own
   expression, and the CWT catalog's `3e5`. Consequence recorded: the mask half-width
   derives from the exact factor, so three frozen fixtures' masked-point pins moved by
   2–7 points (regenerated, as was the graph-subset fixture); and the CWT catalog's
   `FWHM_km_s` no longer differs from the cleaned CSV's by 0.069 % — the difference
   that could flip a declared width band within ~1.4 km/s of a boundary.
   Tests: `tests/reasoning/test_declared_evaluation_axes.py` (6) with source guards.
   Suites: 740 pass.
8. ~~**Prompt authority over Python templates**~~ — **done 2026-10-15** (decision
   owner: render the read window and the break from their declarations; leave the
   "100–300 Å" tool hint as the nominal figure it is).
   The audit reads eight `.md` files, so numbers in Python prompt strings and tool
   descriptions were outside its coverage — and two of the three were not merely
   uncovered but wrong or undeclared. **The README-side fix**: the Lyα forest section
   rendered "±300 Å" while `analysis_method.audit.feature_read_half_angstrom` declares
   100 Å, so the text now renders the declared value
   (`_auditor_read_half_angstrom()`); the Dn4000 break's wavelength is now read from
   `index:dn4000`'s red band edge through `query.dn4000_break_angstrom()`, which the
   Dn4000 labels, the auditor's feature list and the `read_spectrum_region` tool
   description all render (the tool's model-facing description is set explicitly,
   because a docstring must be a literal). The "100–300 Å" window hint stays as a
   nominal instruction with no declaration behind it, by decision.
   **Audit extension — done the same day.** `evaluation/baseline/audit_prompt_numbers.py`
   reads the **rendered** prompts of archived runs (the same extraction the leakage
   inspector uses, now exposed as `model_facing_prompts`) and checks every unit-bearing
   number in a guidance line against `prompt_audit.canonical_values()` — the registry's
   records plus the effective method profile, 282 declared values. The prompt surface
   itself is derived mechanically (five signals: loads a skill, defines `@tool`, passes
   `system_prompt=`, builds a system message, keeps a named prompt constant) and frozen
   as `DECLARED_PROMPT_SURFACE`; a new module that assembles prompt text appears as
   `missing` and fails the check instead of reopening the hole. Nine modules are
   currently on the surface.
   **Recorded limits**: the audit proves a number is *declared*, not that the sentence
   means the right thing — 300 Å is itself a declared doublet window, so the wrong Lyα
   sentence would have passed it (a test pins that observation); only archived text is
   audited, and only the initial prompt plus tool results; and matching is by value with
   a tolerance, so a derived quantity is accepted whenever it coincides with a declared
   value. Consequence: on two archived runs the audit reports ~190 hits that are mostly
   *measurements quoted inside sentences*, so it is stored as a report
   (`evaluation/baseline/prompt_number_audit.json`), not yet as a pass/fail gate; a
   "measurement context" discriminator is the remaining work.
   Tests: `tests/reasoning/test_prompt_numbers_rendered.py` (4) and
   `tests/reasoning/test_prompt_surface_audit.py` (8). Suites: 752 pass.
9. ~~**Undeclared fast-mode gate**~~ — **done 2026-10-15** (decision owner: the
   principle is *insufficient evidence is not audited*, degrading to a null redshift,
   with at most a coarse classification guess from the continuum and the feature width).
   `parameter:execution.insufficient-evidence-threshold` (kind `scalar`, unit
   "credible features", value 1.0, with the decision recorded in its `basis` and its
   consumers named) now owns the threshold, and
   `src/FORMA/core/runtime/execution_policy.py` declares the stage sets, the omitted
   stages and the gate's operand: **credible** detections — CWT rows the detector did
   not mark as pseudo-peaks — instead of raw counts, so pseudo-peak noise can no longer
   buy audits while one credible feature routes fast. The decision, operand, declared
   threshold and omitted stages are recorded in `{name}_routing.json` and the telemetry.
   The outcome follows the principle: an insufficient-evidence run reports
   `redshift: null` with the new declared reason code `insufficient_evidence`
   (`in_brief_contract.UNAVAILABLE_REASONS`), and `ReportWriter` withholds any redshift
   it would otherwise have emitted. Docs updated: `adaptive-execution.md` (why fast is
   chosen, what is recorded) and `defect-grade-contract.md` (the new field and code).
   Tests: `tests/runtime/test_routing.py` extended (17) with the declaration, the omitted
   stages, the credible-count semantics, the withheld redshift and the reason code.
   Suites: 757 pass.
   **Review repair 2026-10-16**: routing and its artifact no longer depend on
   telemetry being enabled. Fast publishes a deterministic final report with no
   adopted redshift or defect rating; zero-feature reports use `no_candidate`
   for rating and `insufficient_evidence` for redshift unavailability. The
   per-spectrum JSON summary and batch CSV now preserve the redshift reason.
10. **Cross-stage immutable parameter object** — **handed over 2026-10-15** to
    [`WP-041`](../work-package/WP-041.md) ("Freeze declared parameters per run and trace
    prompt authority end to end"), because the fix changes how every stage obtains
    configuration rather than which number owns a decision. Verified while handing over:
    33 direct loader call sites (75 including the effective-value readers), the loaders
    do not cache (`load_analysis_method` re-reads and re-validates per call),
    `effective_parameters.json` is written once at result-writing time and therefore
    proves nothing about which values a given stage sampled, and prompts are extracted
    but never linked to their declarations. The 2026-10-16 review corrected
    WP-041's acceptance: the freeze is per spectrum run; authority needs a
    per-value manifest, not just two digests; only deterministic stage inputs
    require identical prompt digests on re-render. The Redrock subprocess boundary
    remains open. WP-041 is still `proposed`.
    **Update 2026-10-15 (implementation, decision owner: execute WP-041).** The node is
    now `in_progress` and the first increment landed **aligned with the 2026-10-16 review**:
    the freeze is per spectrum run as the review corrected; the loaders return the frozen
    snapshot for the run's own source; the digest is recorded in
    `RunTelemetry.frozen_parameter_digest` and in `effective_parameters.json`.
    `tests/reasoning/test_frozen_parameters.py` (6) covers the mid-run edit, the post-clear
    re-read, the three-source snapshot, digest-payload coupling and a guard against direct
    declaration reads. Not yet done, and now worded as the review requires: the **per-value
    authority manifest** (which declaration supplied each rendered number, not two digests),
    reproducibility restricted to **deterministic stage inputs**, and the **Redrock
    subprocess boundary**, for which this pass only recorded evidence (materialised CLI
    arguments; the subprocess reads no project JSON) without closing the question.
## Excluded by construction (physical, structural or recorded policy)

These are deliberately **not** configurable knobs; the list exists so an audit can
tell an omission from a decision (`docs/architecture/numeric-configuration-boundary.md`
holds the same boundary in prose):

- **Physical constants and facts** — the Gaussian σ→FWHM factor
  (2√(2 ln 2)), the speed of light, rest wavelengths and [O III]'s 47.9 Å
  separation (registry-owned), skyline wavelengths, Dn4000 band edges, and the
  statistical MAD→σ constant 1.4826.
- **Structural numbers** — array/pixel-shape guards, `median_filter` odd-size
  parity, the √(2π) integral factor, 0/1 booleans and index subscripts. The
  former 1 Å integer identity bin was retired by item 2 in favour of the
  declared feature-separation tolerance.
- **Instrument and process settings** — nominal arm ranges, Redrock subprocess
  options (`NMINIMA`, `NNEAREST`, `OMP_NUM_THREADS`, archetype Legendre degree and
  prior σ), concurrency, retries and connection settings: `.env`, not science.
- **Recorded policy** — the seven stage temperatures (`config/model_calls.json`),
  the rule-parameter override surface with its derived aliases, and the frozen
  calibration values 0.7/0.0 in `evaluation/calibration/calibration_parameters_frozen.json`,
  which is marked historical and never read by `src/`.
