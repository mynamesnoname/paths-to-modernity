<!-- paths-to-modernity:protocol:start -->
<!-- schema-version: paths-to-modernity-protocol-v3 -->
## Paths to Modernity

This project is planned and governed with the Paths to Modernity infrastructure.
Load the `paths-to-modernity` skill before acting on a materially ambiguous
intent, an architecture decomposition, or a consequential technical choice. When
the skill cannot be loaded, follow the invariants and entry routes below; do not
invent a parallel planning structure.

Invariants that hold whether or not the skill loads:

- **Epistemic before pragmatic; physical rotation over mental rotation.** Use
  dialogue and quick reversible prototypes to clarify intents and concepts;
  declare consequential technical choices (3-way triage) before pragmatic coding.
- **Silence is not permission.** Authorization must be given explicitly. It may
  be granted once for a stated scope; it is never inferred from an unanswered
  report.
- **Authorization, understanding, and evidence are separate.** A recorded gap in
  understanding never widens what may be done, and recording a gap never
  substitutes for a test, a measurement, or a reference.
- **Readiness is relative to the next commitment.** A plan is ready when the next
  responsible step is well founded, not when every question has an answer.
- **One editable source per decision.** Generated views, indexes, and summaries
  are outputs. Never edit them as the authority.

Recovery entry routes under `_aiHumanInteract/`:

- `intent/nodes/` (`intent/structure/graph.json`) — Intent Graph & concepts (epistemic)
- `plan/` (`plan/structure/graph.json`) — Plan Graph v4 sources & views (pragmatic)
- `knowledge-debt/nodes/` (`knowledge-debt/structure/graph.json`) — Knowledge-debt bookmarks
- `scripts/structure/graph.json` — Scripts Graph AST dependencies & plan coverage
- `hebbian/associations.json` — Embedding + Hebbian associative memory & hubs
- `studio/index.html` — Self-contained interactive four-graph studio
- `state/active.md` — Active session checkpoint for recovery after compaction

After compaction, or in a new session, read the Project Portrait block (if
present) and `_aiHumanInteract/state/active.md` first, verify that pointers and
authorization still hold, and load only the neighborhood needed for the next step.
<!-- paths-to-modernity:protocol:end -->
