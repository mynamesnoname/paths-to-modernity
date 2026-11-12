# REQ-010 — Shift to evidence-driven agentic graph reasoning

Decision owner: project user, 2026-10-16.

Raw direction: “分析一下当前剩余plan，如果plan对agent推理的准确性没有绝对帮助的话，就终止这些plan，git push后准备切换到agentic graph reasoning。” The preceding discussion identified progressively disclosed graph context and an observation → question → measurement → graph update loop as the desired direction.

Clarification from the decision owner, 2026-10-16: “不应该以现在的evidence graph为基础，以免带进很多垃圾。” The new graph's schema, node identities, edge vocabulary and execution state must be designed from the SH reasoning requirements, independently of the existing Evidence Graph.

Further decision-owner clarification, 2026-10-16: SH first part produces pre-analysis only, not required question nodes. Within a run, CWT feature IDs are shared across hypotheses; Gaussian fit IDs and their FA effects remain local to their Redrock hypothesis, with no wavelength-based merging. FA votes update an observed-feature entry's signal state after the vote requirement is met. Returning to a specified analysis node forks a reasoning branch; preserve every branch, its analysis outputs and a JSON lineage trace. Graph-guided questions and actions begin downstream of the SH/FA handoff.

## Outcome and boundary

- Optimize the quality of spectral classification, redshift selection and evidence adjudication before optimizing call count or latency. Keep cost and termination limits as safety controls and measured tradeoffs.
- Treat the live investigation graph as the scientific reasoning state: record open questions, node lifecycle, actions, observations, judgments and their revisions. A revisit to a specified reasoning node must preserve prior evidence and decisions, identify downstream judgments made stale by the change, and produce an auditable new path. Keep the scientific graph, LangGraph execution graph and plan graph distinct.
- Do not inherit the existing `FORMA.core.evidence` node/edge schema or construct the new graph by projecting the old graph. Start from primary spectrum data, Redrock hypotheses and validated measurement results; define any ontology or tool adapter against the new contract. The old Evidence Graph is only a historical implementation and comparison artifact.
- Let each new observation or rule finding expose unresolved, answerable questions about the active redshift hypotheses. Select a bounded next action from its expected ability to resolve one of those questions; persist the reason, inputs, output and effect on graph state.
- Disclose a compact view first and expand relevant ontology, evidence and alternative-hypothesis neighborhoods on demand. Mandatory deterministic rules must run independently of whether the model opens a node.
- Preserve the distinction between measured observation, model assertion, formal rule result and unresolved or unknown state. No graph edge or absent line alone establishes a physical fact.
- Keep standalone Redrock batch execution, scientific input identity, truth-label isolation, output contracts, retries and auditable prompt/tool provenance. Do not require a graph database, RDF conversion or the future app for the initial pilot. Preserve the existing pipeline as a runnable comparison path while the new path is designed and tested.

## Acceptance orientation

- Replays show that actions are tied to explicit unresolved questions, repeated reads of already available measurements are avoided, and unsupported tool arguments fail without silently changing scientific state.
- Representative real FITS/LLM runs compare classification, redshift, adopted lines, abstentions and failures against a recorded fixed-pipeline baseline. Model variation is separated from a graph-control effect with repeated runs where a causal claim is made.
- Held-out labels, if used, remain isolated from model-facing context. The 16-spectrum legacy challenge is a retrospective diagnostic, not an independent calibration set.
- Tool use, tokens and latency are reported, but lower cost never substitutes for a worse scientific conclusion.

## Open design choices

The first work package defines the live graph's node/revision semantics, question/action schema, graph snapshot boundaries, revisit and stopping policy before implementation. Reuse only specifically reviewed input readers, measurement tools, reference knowledge, model client and runtime services through explicit adapters. No dependency on the old Evidence Graph is required. Whether to expand beyond SH or change persistence technology is a later decision informed by measured behavior.

The decision owner chose a separate implementation boundary in the current branch instead of copying most of the old source tree into a backup directory. Git history and `feature/evidence-graph` preserve the prior implementation; `agenticGraphReasoningDesign/` preserves the initial, non-executable sketches.
