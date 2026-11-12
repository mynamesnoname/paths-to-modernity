# WP-044: SH session Markdown archive (2026-10-16)

The decision owner requested a saved Markdown record of every model session's
prompts and reasoning. The new SH pre-analysis node has two model sessions:
spectral review and preliminary-classification injection.

## Implemented boundary

- Each session now writes its own Markdown file beside the hypothesis report:
  `<report-stem>_stage1_session.md` and `<report-stem>_stage2_session.md`.
- Each file contains the system prompt, exact input message objects (stage 2
  includes the prior transcript), exposed tool names, returned assistant text,
  tool calls with arguments and tool results. New events are appended as they
  arrive, leaving a partial record if a stage fails.
- Provider-returned `reasoning_content` or equivalent is recorded when exposed.
  The current DeepSeek tool-calling configuration disables thinking; its live
  run returned no separate reasoning field. The visible assistant messages and
  tool choices are still archived, without claiming access to hidden reasoning.
- A completed node stores each session file's path and SHA-256 digest. An
  incomplete run has its partial Markdown file even when it has no node.

## Checks

- Seventeen new-node tests passed, including returned-reasoning capture and
  failed-stage retention. The 24 existing Redrock SH tests passed earlier in
  the same implementation chain.
- A real QSO_4 ID-based run using the configured `deepseek-flash` model
  completed both stages. Its stage-1 and stage-2 Markdown files contain four
  and two returned graph events respectively; both digests match the node.
  Local ignored run: `.data/runs/sh-pre-analysis-qso4-id-recorded-20261016/`.
- Three earlier local QSO_4 SH smoke runs had saved `stream.jsonl` and rendered
  prompts. Their two stage files were reconstructed from those saved artifacts
  and marked as retrospective reconstructions. They cannot recover reasoning
  that the provider never returned.

This archive covers the new SH node. The legacy batch SH path already writes
its own `stream.md`; future graph nodes should use the same recorder when they
are implemented.
