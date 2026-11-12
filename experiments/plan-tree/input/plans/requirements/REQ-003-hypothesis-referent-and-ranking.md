# REQ-003 — Run-local fit referent, neutral analysis label, separate ranking

## Governing interpretation — 2026-10-10

The user's 2026-10-10 decision below **supersedes** the 2026-10-09 proposal to
use the Redrock number as the only name in prompts and filenames. Preserve that
earlier decision as history, not as an implementation instruction. Current
semantics are:

- A `redrock_fit` node has a content-derived graph ID for cross-run alignment
  when the fit content is unchanged. Redrock `znum` (`redrock_index` in the graph)
  is a **run-local, 0-based referent attribute**. It may be renumbered if Redrock
  returns the same fits in a different order; do not use it alone to align runs.
- `H1...Hn` and `single_hypothesis/{N}` are **run-local, neutral presentation
  labels**, drawn from a recorded random permutation. They do not enter any
  node's identity basis, including model-derived `HypothesisNode` or `ClaimNode`.
- Synthesis priority is a separate result keyed to the stable fit node ID, with
  the run-local `znum` and neutral label available through the persisted map.
  Neither priority nor a presentation label is an identifier.

Within one run, the map must be one-to-one among fit node ID, `znum`, and neutral
label. Across runs, compare by fit node ID when it is stable; if scientific fit
content changes and the ID changes, record an explicit fit-matching decision
rather than silently matching by `znum` or directory number.

Implementation prerequisite: the current `RedrockFitNode` hashes the whole
`rrdetails.h5` checksum into each fit ID. A row-order change could therefore
move fit IDs even when their individual fit fields are unchanged. `WP-019`
must separate that file-level checksum from per-fit identity, and `WP-006` must
test row permutations and duplicate-fit collisions before cross-run alignment
can rely on fit IDs.

## Raw request

Recorded verbatim from the repository user on 2026-10-09, answering what a
Redrock candidate should be in the Evidence Graph and how its identity should be
denominated:

> redshift统一使用redrock fit进入分析流程时分配的编号为指代编号。后续在prompt和流程中统一使用redrock编号为唯一指代编号。经过hypothesis synthesis流程产生的排名应作为一个node，或者至少是一个属性，另外记录。

And, separately, on where the continuum model comes from:

> continuum使用切比雪夫多项式算法拟合的，参照 VisualInterpreter.py 的352到360行

## Historical distilled reading — superseded in part on 2026-10-10

Three requirements, not one:

1. **One referent per redshift.** A redshift hypothesis is referred to by the
   number Redrock assigns the fit when it enters the analysis flow — the `znum`
   field of the `zfit` rows in `{name}_rrdetails.h5`. Not by a rank, not by a
   position in a display table, not by a folder index.
2. **Superseded:** the earlier proposal said prompts and the flow should use the
   Redrock number as the *only* name for a hypothesis. The 2026-10-10 decision
   replaces this with a neutral `H` label and an explicit per-run mapping.
3. **The ranking is real information and must not be discarded — but it is not
   identity.** The ordering that the hypothesis-synthesis flow produces is to be
   recorded as its own node, or at minimum as an attribute, kept separate from
   the referent.

## Why this is not cosmetic

Measured on the frozen `QSO_116` run, the two schemes disagree completely:

| Synthesis table order | Label seen by the model | Redrock `znum` |
|---|---|---|
| 1st | H6 (z = 2.9197) | **0** |
| 2nd | H5 (z = 0.7079) | 1 |
| 3rd | H3 (z = 0.2121) | 2 |
| 4th | H1 (z = 0.5424) | **5** |
| 5th | H2 (z = -0.0006) | 3 |
| 6th | H4 (z = -0.0010) | 4 |

`single_hypothesis/N` and the `H1...H6` labels are a **score rank**, while
`hypothesis_synthesis` re-orders the same six again by its own assessment. So
today a single fit carries at least three different names, and the name a prompt
uses is produced by a scoring step that can reorder between runs.

Path note: the `N_emission + N_absorption` phrasing describes the brute-force
matching (BFM, `REDROCK=false`) path in `VI.py`, where `score` defaults to
`N_emission + N_absorption`. The current default Redrock path (`REDROCK=true`)
does not use that formula: `_redrock_to_hypotheses()` sets
`score = 100 / (1 + deltachi2)` and sorts that score descending. In Redrock-mode
output `N_emission` is `rr['npixels']` and is therefore identical across the
retained fits, so the line-count phrase must not be read as describing Redrock
runs. Redrock's `deltachi2` is also not an absolute fit-quality score — it is
the chi-squared distance to the next worse good fit, and Redrock assigns the
last row `0` by construction — so that formula should not be read as a quality
ranking either. Either way the H label is a computed, unstable score rank; the
2026-10-10 neutral random-label decision supersedes it.

That collides with an acceptance criterion already recorded in `WP-002`: node
identifiers must be stable under repeated construction from identical inputs. An
identifier derived from a rank changes whenever the ranking changes, which is
exactly the failure the two-family identifier policy was designed to avoid.

## Invariants

- **Graph identity is stable across equivalent reruns.** It must not depend on
  Redrock's run-local `znum`, a neutral label, ranking, display order, or the
  ambient environment.
- **The ranking stays visible.** Moving the referent must not delete the ranking;
  it is evidence of how the analysis reasoned and is recorded separately.
- **One fit, one graph ID; multiple named roles.** The within-run map is
  one-to-one. A fit may have a `znum` and a neutral `H` alias, but neither is
  confused with its graph ID or with synthesis priority.
- **No retroactive reinterpretation of the baseline.** `ST-001` froze an artifact
  contract whose file names encode the rank; a change to those names changes the
  inventory that the baseline's 49-common-paths claim rests on.

## Historical decision 2026-10-09 — superseded by 2026-10-10

Asked how far requirement 2 should reach, the repository user chose: **record the
constraint now, and do not create a carrying node yet.** So:

- At that time requirement 2 was a recorded constraint without an owning work
  package. It is no longer current: `WP-020` now carries the neutral-label
  replacement.
- The consequence is named rather than hidden: until a carrier exists, the labels
  a prompt uses (`H1...H6`, derived from the score rank) still disagree with the
  Redrock number the graph uses — the exact inconsistency this requirement exists
  to remove under the old proposal. Under the current decision, label and
  `znum` disagreement is intentional blinding; the persisted map must resolve it.
- The settled part remains `znum` as a 0-based, run-local Redrock attribute,
  stored as `redrock_index` by `WP-006` after `WP-019` extends the schema.
- `WP-011` must ground model-derived claims to the fit graph ID. The neutral
  label and run-local `znum` are traceable through the map owned by `WP-020`.


## Decision 2026-10-10 — neutralise analysis labels, keep referent and priority as attributes

The repository user supplied the concrete numbering scheme and asked for it to be
written into the plan:

> 将redrock的结果编号作为属性；single hypothesis中的H1等编号应随机安排；
> 最后的hypothesis synthesis部分，表示假设分析优先级的编号也应是一种属性。
> 中间文件的文件名用single hypothesis的序号排列。这一办法是为了避免在分析阶段
> 泄露redrock的排序，一方LLM过度相信redrock，产生bias。

Distilled design:

1. **Run-local referent is an attribute.** The Redrock-assigned number (`znum`,
   stored as `redrock_index` by `WP-019`/`WP-006`) identifies a fit within that
   run. It is not the fit's cross-run graph ID and must not control analysis
   order, prompt labels, or filenames.
2. **Analysis labels are random and recorded.** `H1...Hn` and the
   `single_hypothesis/{N}` filenames are assigned by a random permutation drawn
   independently of `znum`, redshift, `chi2`, `deltachi2`, `score`, and the order
   in which Redrock returned the fits. Canonicalize the fit-ID set before the
   seeded permutation so row reordering cannot change the map on replay. The
   permutation and its seed must be persisted as run provenance so every artifact
   can be traced back to its referent.
3. **Synthesis priority is a separate attribute.** The ranking produced by
   hypothesis synthesis is attached to the stable fit node ID (or represented by
   its own node when the graph supports it). It is evidence about the analysis
   outcome, not an identifier; the stored map also shows its run-local `znum` and
   neutral `H` label.
4. **Intermediate filenames keep the neutral sequence.** The
   `single_hypothesis/{N}_*` artifact shape frozen by `ST-001` is preserved; `N`
   maps to a referent only through the recorded label map.
5. **The analysis stage must not leak Redrock ordering.** No analysis-step prompt
   or intermediate filename may expose `znum`, `chi2`, `deltachi2`, `score`, or
   the `Match #N`/`H` ordering derived from them. This is the bias mitigation the
   design exists to provide.

Carrier: `WP-020` (`ST-006`) now carries the neutral-label and synthesis-priority
work. `WP-019` and `WP-006` continue to carry only the referent-attribute part.

Baseline consequence: the artifact path inventory is unchanged, but comparisons
resolve each path through its run's label map and align equivalent fits by graph
ID, not by path index or `znum`. `single_hypothesis/1` may denote a different fit
on the next run. Where fit IDs differ, an explicit matching rule or adjudication
is needed; `znum` equality alone does not establish equivalence.
