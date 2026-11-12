# REQ-005 — Redrock-only single-hypothesis verification

Decision owner: project user, 2026-10-12.

Raw request: “我们不做nomad方法了，全力改写redrock方法。请删除nomad/BFM方法相关内容。之后请改写redrock方法的提示词。”

## Boundary

- The active FITS pipeline and standalone SH harness accept Redrock hypotheses only. Unsupported historical mode selections fail explicitly before model or spectrum access.
- Remove the inactive BFM matcher/scorer and its active prompt, imports, configuration remnants, and current-method documentation. Preserve historical plan/evaluation records as evidence of earlier decisions; annotate their retirement through WP-024 instead of rewriting history.
- Keep CWT-first verification and Gaussian fallback. The Redrock SH prompt states methodology and output contracts; line, doublet, width, edge and offset parameters are supplied at runtime from the ontology registry and calibrated predicate definitions.
- Keep the CSV, Markdown report, and structured summary interfaces used by FA and HS. No new scientific threshold is approved by this request.

## Acceptance

1. No active caller can enter Nomad/BFM processing; unsupported selection raises an explicit error.
2. The prompt is shorter, Redrock-specific, and retains mask/absence distinction, CWT-first fitting fallback, uncertainty, output order, and downstream-compatible artifacts.
3. The input includes relevant ontology-backed facts, and prompt authority audit plus local regression tests pass.
