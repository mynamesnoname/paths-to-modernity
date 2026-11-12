# WP-037 acceptance analysis — real-workflow graph chain, 2026-10-16

Status: **reviewed, acceptance decision open**. Data: 14 real
FITS/Redrock/LLM runs under `.data/runs/wp037/` (10 in the graph-on/off sweep, 3 graph-on
reruns, 1 graph-off rerun); the 10 successful pair runs are analysed here. Script:
`evaluation/wp037_acceptance.py`; machine summary:
`evaluation/wp037_acceptance_summary.json` (the raw run tree remains local and ignored).

状态：**已复核，验收决定尚未作出**。数据：`.data/runs/wp037/` 下 14 次真实
FITS/Redrock/LLM 运行（10 次主扫描 + 3 次 graph-on 重跑 + 1 次 graph-off 补跑）；本文分析其中
成功的 10 次成对运行。脚本：`evaluation/wp037_acceptance.py`；机器摘要：
`evaluation/wp037_acceptance_summary.json`（原始运行树仅保存在本地、被 Git 忽略）。

## 1. Graph chain and provenance (criterion 1)

Every selected graph-on run saved `{name}_evidence_graph.json` (schema
`forma-evidence-graph-v1`; 243–312 nodes, 419–602 edges). The following table
reports **undirected component membership**, not a causal or directed path:

| Fixture | inbound `concerns` | reaches fit / claim / rule / observation | selected fit in component | FITS sha | NPZ sha |
|---|---|---|---|---|---|
| BGS_2 | 35 | yes / yes / yes / yes | yes | ✓ | ✓ |
| ELG_6 | 37 | yes / yes / yes / yes | yes | ✓ | ✓ |
| LRG_1 | 39 | yes / yes / yes / yes | yes | ✓ | ✓ |
| QSO_116 | 23 | yes / yes / yes / yes | yes | ✓ | ✓ |
| QSO_4 | 31 | yes / yes / yes / yes | yes | ✓ | ✓ |

The spectrum node carries `input_fits_sha256` and `spectrum_npz_sha256`. The
analysis script reloaded each document through the typed validator and checked
both hashes against the local FITS/NPZ bytes; all five selected graph-on runs
matched. The selected fit is also reachable from the decision by directed `supports` and
`derived_from` edges. Rule findings instead have inbound `concerns` edges to the
decision; a directed walk outward from the decision does **not** reach them.
The saved-graph `explain_decision` query composes these records and validates
cross-layer references (zero invalid references in these five graphs). Many
line claims have explicit unresolved measurement referents; they must not be
described as measured observations merely because the graph is connected.

## 2. Rule and link coverage (criterion 4)

The registry declares **23 formal rules** (`ONTOLOGY.formal_rules`); every saved graph's
decision component contains exactly **23 distinct `rule:` ids**. All 23 records
have `evaluated=true`, but **11–17 per graph have outcome `unknown`**. Thus 23/23
is trace-record coverage, not 23 determinate scientific evaluations. Link kinds
present: `identifies`, `claims`, `concerns`, `derived_from`, `observed_in`,
`contradicts`, `supports`.

## 3. Graph-on versus graph-off (criterion 2, recorded policy)

Policy: same frozen config (a **single frozen digest** `d636732d…ac16e` across all 10 runs),
same fixtures, sequential. This controls declared parameters, but one successful
run per fixture and mode **cannot separate model variation from graph effects**.
The four reruns replaced failed cells; they are not independent repetitions for
estimating outcome variation.

| Fixture | graph-on | graph-off | note |
|---|---|---|---|
| BGS_2 | GALAXY z=0.1588 MEDIUM | **Unknown, z=null** | off abstained |
| ELG_6 | GALAXY 0.1068 HIGH | GALAXY 0.1068 HIGH | identical |
| LRG_1 | GALAXY 0.2725 LOW | GALAXY 0.2718 MEDIUM | Δz 6.3e-4 vs 7.9e-5; confidence flip |
| QSO_116 | QSO 2.9199 conf=null | **Unknown, z=null** | on withheld only the rating; off withheld class and redshift |
| QSO_4 | **GALAXY** 0.2381 MEDIUM | QSO 0.2381 MEDIUM | on class conflicts with VI label; off class agrees |

Cost: graph-on vs graph-off — prompt tokens 6.735 M vs 6.293 M (**+7.0%**), model calls 271
vs 260 (**+4.2%**), median wall 263 s vs 250 s (**+5.3%**). These are observed
differences in five selected pairs, not stable overhead estimates. The QSO_4
class flip is a concrete adverse result; the sample cannot establish whether
it is stochastic or graph-caused.

## 4. Independent labels (criterion 3)

VI_Z/VI_SPECTYPE read from the FITS FIBERMAP. These are reference labels
independent of the pipeline's output, but the **five spectra are the project's
reused basic fixtures**, not an independent held-out sample. Denominators explicit.

| Fixture | mode | VI | run | z_VI | z_run | Δz/(1+z) | conf |
|---|---|---|---|---|---|---|---|
| BGS_2 | on | BGS | GALAXY | 0.1590 | 0.1588 | 1.7e-4 | MEDIUM |
| BGS_2 | off | BGS | Unknown | 0.1590 | — | — | null |
| ELG_6 | on/off | ELG | GALAXY | 0.1068 | 0.1068 | 0 | HIGH |
| LRG_1 | on | LRG | GALAXY | 0.2717 | 0.2725 | 6.3e-4 | LOW |
| LRG_1 | off | LRG | GALAXY | 0.2717 | 0.2718 | 7.9e-5 | MEDIUM |
| QSO_116 | on | QSO | QSO | 2.9183 | 2.9199 | 4.1e-4 | null |
| QSO_116 | off | QSO | Unknown | 2.9183 | — | — | null |
| QSO_4 | on | QSO | GALAXY | 0.2381 | 0.2381 | 0 | MEDIUM |
| QSO_4 | off | QSO | QSO | 0.2381 | 0.2381 | 0 | MEDIUM |

Statistics over the 10 runs: classification **7/10** match (2 abstentions + 1 class flip);
redshift available in 8 (2 abstentions), **median |Δz|/(1+z) = 3.93e-5, max = 6.3e-4**;
confidence known in 7.

Defect-rating field: recorded on the decision node (schema `forma-evidence-node-v4`,
producer `result_auditor`). QSO_116-on exposes two stages of the rating:
`result_auditor/verdict.json` has the model's raw `MEDIUM`; the deterministic
rule reconciliation withheld it as `null / unresolved_rule_conflict` in the
graph, report and in_brief. The old run has no persisted resolved-verdict
artifact, so its file-level audit trail is incomplete. The implementation now
writes `result_auditor/resolved_verdict.json` while preserving the raw verdict;
the 2026-10-16 post-prompt QSO_4 run below demonstrates this path with both
files present and `MEDIUM` on both sides. **No independent
defect-severity agreement is claimed**; that assessment was cancelled in
`WP-012` and documented by `WP-042`.

## 5. Deviations and failures

The sweep's four failures (2 × report-missing, 2 × degenerate-output `max_prompt_tokens`)
are recorded in WP-037 with their diagnoses. All four affected fixture×mode cells were
rerun under the current code and **all passed** (final reports 9.6–11.6 KB). The
option-1 repair and the counter-reset/termination-record paths were **not exercised by the
reruns** (no trigger, no escalation); they are unit-tested only.

## 6. Review and decision boundary

The five real graph-on runs demonstrate graph persistence, deserialization,
decision/fit links, rule records and FITS/NPZ hashes. They also expose a wrong
QSO_4 class, an audit-source divergence for QSO_116, four initial failures and
large numbers of `unknown` rule outcomes. The reference labels are from reused
fixtures. One pair per fixture does not identify a graph effect separately from
LLM variation. The compact summary is versionable, but the raw run tree is
ignored, so a fresh checkout cannot rerun the graph analysis from these
artifacts alone. This evidence supports a **bounded engineering demonstration**;
it does not yet justify the unqualified claim that the graph chain is fit for
batch use or that the comparison met its stochastic-separation criterion.

The decision owner must choose whether to narrow WP-037's gate to this bounded
demonstration or retain the original independent-sample and comparison-policy
acceptance. No approval of the stronger fitness statement is recorded here.

## 7. Targeted post-prompt real rerun, 2026-10-16

The decision owner requested a new real FITS → Redrock → LLM test of QSO_116
and QSO_4 after the QSO_4 [Ne V] prompt corrections. Both ran sequentially
with `EVIDENCE_GRAPH=true`, `RUN_MODE=s`, inputs in `example/basic/`, the real
`.env` model service, and the serial Redrock shim (`rrdesi --mp 1`). The ignored
raw archive is `.data/runs/wp037/post-prompt-20261016/`: separate output roots,
logs, `runlog.tsv`, input/prompt/KB SHA-256 hashes and Git HEAD. The worktree
was dirty; Git HEAD alone does not identify the exact tested prompts. The
frozen effective-parameter digest was `d636732d…ac16e` in both runs.

| Fixture | Exit / telemetry | Model calls / tool rounds | Wall | VI label and z | Final output | Graph rules |
|---|---|---:|---:|---|---|---|
| QSO_116 | 0 / `ok` | 39 / 47 | 249 s | QSO, 2.9183 | `Unknown`, z=null, grade=null (`no_candidate`) | 6 evaluated, all `unknown` |
| QSO_4 | 0 / `ok` | 45 / 65 | 359 s | QSO, 0.2381 | QSO, z=0.2387, grade=`MEDIUM` | 23 evaluated: 6 pass, 6 fail, 11 unknown |

Both runs saved a final report, in_brief, telemetry and a graph that
deserializes. The decision components reach a fit, claim, rule and observation;
saved FITS/NPZ digests match the inputs. Neither run recorded a budget breach,
failure or escalation. Both FeatureAuditor first calls failed schema validation
and succeeded on retry. These are successful end-to-end executions, not
uninterrupted first-attempt model outputs. Wall times were observed while
another real run overlapped, so they are not controlled latency comparisons.

QSO_4's [Ne V] 4242.4 Å was `is_real=true`, reliability `high`, `KEEP` in FA;
HS selected the z≈0.238 narrow-line QSO/Type 2 interpretation; RA kept
`audited_class=QSO`, `nev_convincing=true` and confirmed [Ne V]. The raw and
resolved RA verdict files are both present and agree on `MEDIUM`; the graph,
in_brief and final report agree on QSO and z=0.2387. Its normalized redshift
error against VI is about 4.85×10⁻⁴. This removes the *observed* Galaxy
misclassification in this one rerun, but does not measure its recurrence rate
or isolate a prompt effect from stochastic model variation. The RA also removed
Ca K and G-band partly because “no stellar absorption [is] expected” for QSO;
that premise is too categorical for a host-dominated Type 2 AGN, even if the
particular weak dips are artifacts. This remains a scientific reasoning gap.

QSO_116 did **not** reproduce the earlier graph-on QSO result. SH listed
Lyα, C IV and C III] as plausible broad lines at z≈2.92; FA retained only the
4768 Å feature and removed C IV 6072 Å and C III] 7474 Å. HS then rejected
both the Lyα and alternative Mg II single-line interpretations, said the Lyα
forest was absent, and abstained. The older graph-on rerun instead FLAGged
C IV as real and interpreted the blueward depression as forest, yielding QSO
at z=2.9199. The new `no_candidate` path legitimately skipped the live RA,
so there is a guard-written raw `UNCERTAIN` verdict but no
`resolved_verdict.json`; its graph has only six `unknown` rule records because
there was no selected hypothesis to audit. The two different forest and C IV
judgments need an evidence-based check before claiming reliable QSO_116
classification. One new run cannot show whether the change came from prompt
edits or ordinary model variation.

The targeted rerun therefore verifies the QSO_4 correction in one execution
and the persisted resolved-verdict path for a live RA, while exposing a
QSO_116 abstention and two FA format retries. It does not close the broader
independent-sample or repeated-run acceptance conditions above.
