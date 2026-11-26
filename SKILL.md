---
name: paths-to-modernity
description: Human-agent interaction, state, and execution infrastructure for project design (web/full-stack engineering, scientific tools, large creative works). Decompose dialogue into intents and concepts, use epistemic actions and prototypes to clarify variants and alternatives, triage technical disclosures with knowledge-debt bookmarks, maintain federated Intent / Plan / Knowledge-Debt / Scripts graphs with Hebbian associative retrieval, and recover context via subagent portraits. Do not use for routine one-step edits that need no planning or state governance.
---

# Paths to Modernity

Serve complex project design — web and full-stack systems, scientific workbenches,
and large creative works — as a **human–agent interaction, state, and execution
infrastructure**. Turn uncertain intent into clear, traceable structures without
drowning the person in uninformative technical approvals.

Following Kirsh & Maglio (1994), separate two kinds of work:

- **Epistemic actions (认知性行动)** improve human–agent understanding by
  reducing memory load, mental simulation steps, and misinterpretation risk:
  splitting dialogue into **intents** and **concepts**, surfacing different
  readings, building quick visual/interactive **epistemic prototypes** ("physical
  rotation" instead of costly mental rotation), and curating externalized graphs.
- **Pragmatic actions (实践性行动)** directly advance the deliverable (writing
  code, wiring modules, running tests). Once intent boundaries and technical
  disclosures are settled, pragmatic execution belongs primarily to the agent and
  deterministic software.

Choices about values, experience, responsibility, and acceptable consequences
belong to the authorized **decision owner**, who has the right to know which
technologies pragmatic work adopts without having to evaluate every mechanism
ahead of practice.

## Establish context

The **target project** is the repository, product, creative work, or system to
which the design applies. Read its applicable `AGENTS.md` (including any
recovery portrait and `_aiHumanInteract/state/active.md`), existing graphs, and
decision history. Follow an existing coherent local contract rather than
overwriting it.

The **skill root** is the directory containing this loaded `SKILL.md`. Resolve
the links below relative to it. Planning alone does not authorize pragmatic
implementation.

## Read the needed detail

| Resource | Read when |
|---|---|
| [Intent Graph & epistemic inquiry](references/intent-graph.md) | Splitting dialogue turns into intents (`INT-###`) and concepts, choosing between verbal questions vs. epistemic prototypes (SVG/UI demos), or maintaining `_aiHumanInteract/intent/` |
| [Inquiry](references/inquiry.md) | Two reasonable readings could change the outcome, responsibility, acceptance, meaningful risk, or an irreversible commitment |
| [Planning model](references/model.md) | Defining a plan's objective, context, decomposition, qualities, or review perspectives |
| [Alternatives](references/alternatives.md) | Consequential implementation alternatives need comparison under a shared outcome and evaluation baseline |
| [Knowledge debt & technical triage](references/knowledge-debt.md) | Declaring technical choices before pragmatic execution (3-way triage), recording `KD-###` bookmarks, or reorganizing graphs when a bookmark is resolved |
| [Spec Graph](references/spec-graph.md) | Crystallizing standing invariants (*Do / Do NOT*), canonical domain glossary terms, development standards, or verifiable contracts under `_aiHumanInteract/specs/`, or checking spec blast radius (`ptm.py spec impact`) |
| [Plan Graph](references/plan-graph.md) | Working with `_aiHumanInteract/plan/structure/graph.json` (`paths-to-modernity-plan-graph-v4`) or installing/upgrading pragmatic plan infrastructure |
| [Scripts Graph](references/scripts-graph.md) | Extracting AST/import/call codebase dependencies and plan coverage under `_aiHumanInteract/scripts/` |
| [Verification & evaluation](references/verification-and-evaluation.md) | Running deterministic test receipts with SHA-256 staleness tracking (`ptm.py verify`) or invoking an isolated perspective subagent to record substantive evaluations (`evaluations/EVAL-###.md`) |
| [Episodic dialogue & SQLite memory](references/episodic-memory.md) | Logging or importing multi-topic conversation turns, disentangling `Turn -> Span -> Thread (THR-###)` in `_aiHumanInteract/.cache/memory.sqlite`, searching raw dialogue (`ptm.py memory search`), or folding settled threads into 1-line capsules |
| [Associative memory & portraits](references/hebbian-memory.md) | Running on-device embeddings + Hebbian spreading retrieval (`_aiHumanInteract/hebbian/`) or refreshing the subagent recovery portrait in `AGENTS.md` |
| [Worked example](assets/plan-graph/example/README.md) | Learning how source records and generated views fit together |

## Interaction, state, and execution workflow

Use the depth needed for the next commitment; omit ceremony on small tasks.

1. **Extract intents, disentangle parallel dialogue threads, and preserve raw wording.**
   Keep epistemic conversation in one natural stream for the human while letting
   `scripts/ptm.py memory log` (or `import-jsonl`) disentangle multi-topic turns
   into atomic sub-turn `Spans` and single-topic virtual `Threads` (`THR-###`) in
   `_aiHumanInteract/.cache/memory.sqlite`. Split multi-intent turns into coherent
   intents (`INT-###`) while keeping `raw_utterance` (and `THR-###` provenance) so
   later summaries never silently drift; fold settled threads (`ptm.py memory fold`)
   into compact capsules rather than waiting for lossy global compaction.
2. **Decompose concepts and run epistemic inquiry.** Identify key concepts inside
   each intent. Inspect code and facts yourself first. When a concept admits
   multiple goal-changing readings, contrast them; remember that interpretations
   implying different goals are not implementation alternatives to score on one
   baseline. When verbal imagination is high-friction, build a quick reversible
   **epistemic prototype** (SVG, interactive HTML demo, or sample output) so the
   user can compare by seeing rather than guessing.
3. **Compare consequential alternatives and protect qualities.** Once the outcome
   is shared, compare meaningful implementation or experiential alternatives
   against a shared baseline, keeping desired qualities distinct from functional
   acceptance tests.
4. **Declare consequential techniques and run three-way triage.** Before starting
   a new pragmatic implementation scope, state the 1–5 consequential technologies,
   architectures, or algorithms (and their cost if wrong) for the user to sort:
   - *Understood and agreed* → informed acceptance;
   - *Not understood, proceed with reversible prototype* → provisional acceptance
     plus a linked `KD-###` bookmark in `_aiHumanInteract/knowledge-debt/`;
   - *Disagreed, propose counter-view* → revise the plan before executing.
5. **Crystallize standing specs, execute pragmatic plans, and maintain federated graphs.**
   Promote durable invariants (*Do / Do NOT*), ubiquitous glossary terms,
   standards, and verifiable contracts into `_aiHumanInteract/specs/nodes/SPEC-###.md`
   so standing rules survive after one-off work packages close. Before authoring a
   new Intent, Spec, or Plan node (or when inspecting an existing one), probe
   cross-graph relevance via `scripts/ptm.py related <repo> <node-id|draft-file|text>`
   (and `scripts/ptm.py spec impact <repo> <SPEC-ID>` before amending an active
   spec). Then decompose approved intents into pragmatic Plan Graph nodes
   (`LT/MT/ST/WP`), execute code changes, and let `scripts/ptm.py build` validate
   links, scan the Scripts Graph, update Hebbian co-activation weights, and render
   the 3-stratum 5-graph Studio (`_aiHumanInteract/studio/index.html`).
6. **Run dual-track verification and context-separated evaluation.**
   - *Formal validation:* Execute `scripts/ptm.py verify <repo>` to run the test
     suite and record deterministic pass/fail receipts plus SHA-256 content
     hashes in `_aiHumanInteract/scripts/verification-status.json`. Any later
     edit to governed code or tests automatically downgrades affected `SPEC`,
     `Plan`, and `Script` nodes from `verified` to `stale` until re-verified.
   - *Content evaluation:* Never self-certify subjective `Intent.qualities` in
     the coding trace. Spawn an isolated perspective subagent (`research` or
     `browser`) with `raw_utterance` + `qualities` + `SPEC` guardrails +
     runnable artifacts/screenshots, and persist its findings (including any
     `concerns` or `at_risk_qualities`) in `_aiHumanInteract/plan/evaluations/EVAL-###.md`
     (`ptm.py eval scaffold`).
7. **Revisit bookmarks and reorganize when understanding matures.** When practice
   clarifies an open `KD-###` bookmark, resolve it as `affirmed` (closing the
   gap) or `rejected` (computing impact across linked Plan, Spec, and Intent
   nodes to supersede and reorganize affected branches).
8. **Refresh recovery state and subagent portrait.** On key milestones, update
   `_aiHumanInteract/state/active.md` and invoke the subagent portrait summarizer
   (`ptm portrait`) to keep `AGENTS.md` ready for instant recovery after context
   compaction or session switches.

## Repository-local infrastructure

Inspect applicable `AGENTS.md` files first. Use `scripts/adopt_project.py` to
adopt the protocol and entry routing block, `scripts/install_plan_graph.py` for
the strict Plan Graph v4 bundle, and `scripts/ptm.py` for unified four-graph
indexing, AST script scanning, Knowledge Debt impact tracing, Hebbian Dual-Path
retrieval, Studio visualization, and portrait generation.

## Working principles

- **One editable source per decision; views are generated.** Never hand-edit
  `graph.json`, `graph.canvas`, `graph.html`, or `studio/index.html` as authority.
- **Authorization, understanding, and evidence are orthogonal.** Silence never
  grants permission; a Knowledge Debt bookmark never substitutes for a test or
  widens scope.
- **Physical rotation beats mental rotation.** Prefer a fast, reversible visual
  or runnable prototype over forcing a person to imagine abstract specifications.
- **Separate edge provenance.** Keep `Declared` (authored), `Observed` (AST/static),
  and `Associative` (Hebbian + embedding) connections explicitly typed.
- **Readiness is relative to the next commitment.** A bounded discovery task or
  epistemic prototype can proceed while broader architecture stays provisional.
