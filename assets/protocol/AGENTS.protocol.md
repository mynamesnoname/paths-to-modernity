<!-- paths-to-modernity:protocol:start -->
<!-- schema-version: paths-to-modernity-protocol-v1 -->
## Paths to Modernity

This project is planned with the Paths to Modernity method. Load the
`paths-to-modernity` skill before acting on a materially ambiguous requirement,
an architecture decomposition, or a consequential choice. When the skill cannot
be loaded, follow the invariants below and the records already in this
repository; do not invent a parallel planning structure.

Invariants that hold whether or not the skill loads:

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

Project records live under `_aiHumanInteract/`:

- `plan/` — Plan Graph sources and generated views, when adopted
- `knowledge/` — knowledge-debt records, when adopted
- `state/active.md` — current work state, for recovery after compaction

After compaction, or in a new session, read `_aiHumanInteract/state/active.md`
before resuming, and verify that its pointers and its authorization still hold.
<!-- paths-to-modernity:protocol:end -->
