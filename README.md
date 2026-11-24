# Paths to Modernity (PtM)

A **human–agent interaction, state, and execution infrastructure** for complex
project design — web and full-stack systems, scientific workbenches, and large
creative works.

Start with [SKILL.md](SKILL.md) and architectural decision record
[DEC-004](decisions/DEC-004-epistemic-pragmatic-four-graphs-and-hebbian-studio.md).

## Core Foundations

- **Epistemic vs. Pragmatic Actions (Kirsh & Maglio, 1994):** Human–agent
  dialogue focuses on *epistemic actions* — splitting turns into **Intents** and
  **Concepts**, resolving **Interpretive Variants** vs. **Implementation
  Alternatives**, and using fast reversible **epistemic prototypes** (SVG/UI
  demos as *physical rotation* rather than high-friction *mental rotation*).
  Pragmatic code execution is delegated primarily to the agent and deterministic
  software.
- **Three-Way Technical Triage & Knowledge Debt Bookmarks:** Recognizes the
  user's right to know adopted architectures and algorithms without forcing
  hollow "Agree" approvals. Consequential technical choices are triaged into
  *Understood & Agreed*, *Not Understood — Proceed with Prototype (`KD-###`
  Bookmark)*, or *Disagreed — Propose Counter-View*, with deterministic blast-radius
  reorganization when a bookmark is later rejected.
- **Federated Four-Graph Ecosystem (`_aiHumanInteract/`):**
  1. [Intent Graph](references/intent-graph.md) (`intent/`) — Verbatim utterances,
     concepts, variants, and epistemic prototypes (`Declared`).
  2. [Plan Graph v4](references/plan-graph.md) (`plan/`) — Layered `LT → MT → ST → WP`
     pragmatic execution plans and completion evidence (`Declared`).
  3. [Knowledge Debt](references/knowledge-debt.md) (`knowledge-debt/`) —
     Technical bookmarks, revisit triggers, and reorganization impact (`Declared`).
  4. [Scripts Graph](references/scripts-graph.md) (`scripts/`) — Two-pass AST
     module imports/calls, PageRank hubs, and plan coverage (`Observed`).
- **On-Device Embeddings + Hebbian Associative Memory & Curated Studio:**
  [Associative layer](references/hebbian-memory.md) (`hebbian/`) powered by
  Apple Silicon `mlx-community/Qwen3-Embedding-0.6B-4bit-DWQ` (with zero-dependency
  fallback), Dual-Path `Base + Flip` spreading retrieval, subagent recovery
  portraits in `AGENTS.md`, and a *DesignerlyLoop*-inspired interactive HTML
  workspace (`_aiHumanInteract/studio/index.html`).

## Quick Commands

```bash
# Build all four graphs, Hebbian synapses, Studio HTML, and subagent portrait
python3 -B scripts/ptm.py build /path/to/repository --with-portrait

# Run Dual-Path Retrieval (Base + Hebbian Spreading Activation Flip)
python3 -B scripts/ptm.py query /path/to/repository "your concept or intent query"

# Record 3-way technical disclosure triage or resolve a Knowledge Debt bookmark
python3 -B scripts/ptm.py kd impact /path/to/repository KD-001
python3 -B scripts/ptm.py kd resolve /path/to/repository KD-001 --verdict affirmed --note "..."

# Run regression suites
python3 -B scripts/test_plan_graph_bundle.py
python3 -B scripts/test_ptm_ecosystem.py
```

Worked examples live under [assets/plan-graph/example/](assets/plan-graph/example/README.md)
(minimal Plan Graph v4) and [assets/four-graph-example/](assets/four-graph-example/README.md)
(full four-graph Spectral Workbench showcase). For skill maintenance rules, follow
[AGENTS.md](AGENTS.md).
