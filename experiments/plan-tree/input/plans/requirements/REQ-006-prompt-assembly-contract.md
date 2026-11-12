# REQ-006 — Organize batch prompt assembly

Decision owner: project user, 2026-10-12.

Raw request: “可以，请你写一个整理prompt的plan，暂不执行。” This follows the discussion of Python-built user prompts, typed input contexts, instruction/data boundaries, versioning, and representative evaluation.

## Outcome and boundary

- Keep the current fixed Redrock batch pipeline and its stage-specific local system prompts. Organize prompt assembly as versioned, reviewable application code with validated inputs and deterministic rendering.
- Cover active model-facing stages, starting with Redrock single-hypothesis verification. Preserve the scientific rule owners in the ontology; a renderer must not become a second threshold registry.
- Separate trusted methodology and output instructions from run observations and prior-stage artifacts. Treat earlier model-written reports as evidence, not new instructions. Enforce file/tool permissions in code, not through textual delimiters.
- Record the effective system prompt, user input, tool/schema configuration, ontology version, model identity, and render version or digest for each run without storing API keys, raw secret configuration, or unnecessary duplicate spectra.
- Keep CSV, Markdown, brief JSON, graph references, Unknown/null semantics, retry behavior, and Redrock-only mode compatible. Distinguish rendering or parsing failure from a scientifically justified Unknown result.

## Acceptance boundary

- Typed or validated prompt input objects and pure rendering functions are exercised by representative offline fixtures, including masks, missing data, doublets, and adversarial text in prior-stage reports.
- Full model-facing prompt tests check role placement, ontology authority, truth-label leakage, artifact paths, and output contracts. Tests compare behavior-relevant facts rather than freezing incidental whitespace.
- A prompt change that may alter scientific decisions receives a recorded representative FITS/LLM comparison before release; this plan does not authorize that run now. A provider-specific structured-output migration is conditional on demonstrated endpoint support.

## Outside this request

- No implementation, model calls, FITS runs, or prompt rewriting in this planning turn.
- An interactive app, resumable harness sessions, user annotation permissions, and conversation storage need separate product decisions. The batch job must remain independently runnable.

Design input: `docs/architecture/prompt-context-review.md`.
