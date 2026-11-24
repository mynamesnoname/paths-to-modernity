# Associative memory (Hebbian + embeddings) and recovery portraits

Read this reference when building or querying cross-graph associative links
(`_aiHumanInteract/hebbian/`), configuring local embeddings, or refreshing the
project recovery portrait in `AGENTS.md`.

## Why an associative layer beside structural graphs

Structural links (`Declared` in Intent/Plan/Knowledge Debt, `Observed` in
Scripts) capture explicit hierarchy and code imports, but miss cross-cutting
conceptual narratives that emerge across turns — for example, an early aesthetic
intent (`INT-001`), a deferred latency trade-off (`KD-002`), and a layout module
(`src/canvas_renderer.ts`) that repeatedly participate in the same design
questions.

Adapted from cognitive neuroscience and *HeLa-Mem* (Zhu et al., ACL 2026), PtM
adds an **Associative Layer** (`_aiHumanInteract/hebbian/associations.json`)
governed by three rules:

1. **Epistemic separation:** Associative synapses never overwrite or masquerade
   as `Declared` or `Observed` edges. Every synapse carries
   `"layer": "associative"` with its current weight $w_{ij} \in (0, 1]$ and
   co-activation count.
2. **Tiered on-device embeddings with deterministic fallback:**
   - **Primary (Apple Silicon laptop SOTA):** `mlx-embeddings` running
     `mlx-community/Qwen3-Embedding-0.6B-4bit-DWQ` locally on Metal GPU (~333 MB
     unified memory, 32K context, multilingual CJK/English + code).
   - **Secondary (Cross-platform local):** `fastembed` or `sentence-transformers`
     when installed.
   - **Fallback (Zero-dependency stdlib):** Deterministic L2-normalized
     character/word n-gram subword hashing so offline environments and CI tests
     always succeed without network or GPU packages.
   - Vectors are content-addressed by `model_id + sha256(text)` in
     `_aiHumanInteract/.cache/embeddings.json`.
3. **Hebbian plasticity and Dual-Path spreading retrieval:**
   - **Initial semantic seeding:** Node pairs whose cosine similarity exceeds
     $\theta_{\text{seed}}$ receive a weak prior synapse $w_0 = \gamma_{\text{seed}} \cdot \text{sim}(i, j)$ so newly encoded projects are not blind linear chains.
   - **Co-activation reinforcement ("fire together, wire together"):** When a set
     of nodes $\mathcal{K}_t$ is co-retrieved, co-edited in a turn, or revisited
     together via a Knowledge Debt bookmark, pairwise weights update with
     bounded Hebbian reinforcement and synaptic decay:
     $$w_{ij}^{(t+1)} = \min\!\left(1.0,\; (1 - \lambda)\, w_{ij}^{(t)} + \eta \cdot \mathbb{I}(v_i, v_j \in \mathcal{K}_t)\right)$$
   - **Dual-Path Ranking (`Base + Flip`):** Queries compute `S_base` (embedding
     similarity + concept/keyword match × valid ISO-date recency factor), spread
     activation across synapses above $\theta_{\text{spread}}$:
     $$S(v_j) = S_{\text{base}}(v_j) + \beta \sum_{i \in \mathcal{N}(j)} S_{\text{base}}(v_i)\, w_{ij}$$
     and return `Top-k(S_base) ∪ Top-m(S | v ∉ Top-k(S_base))` — surfacing
     associatively linked intents, plans, bookmarks, or scripts that literal
     query similarity alone would miss.
   - **Hub detection:** Nodes whose cumulative synaptic strength
     $D(v_i) = \sum_j w_{ij} > \delta_{\text{hub}}$ are surfaced as cross-project
     conceptual hubs for consolidation and portrait synthesis.

## Subagent portrait and `AGENTS.md` recovery

Context compaction summarizes away loaded skill instructions and dialogue history,
while `AGENTS.md` is re-injected by agent harnesses. PtM keeps two independent
marked blocks in `AGENTS.md`:

1. **Protocol & Entry Routing (`<!-- paths-to-modernity:protocol:start/end -->`)**
   — static, hash-verified by `adopt_project.py`: holds the core invariants and
   the entry routing paths for `intent/`, `plan/`, `knowledge-debt/`, `scripts/`,
   `studio/index.html`, and `state/active.md`.
2. **Project Portrait (`<!-- paths-to-modernity:portrait:start/end -->`)**
   — refreshed by an isolated **subagent** (either a harness subagent via
   `invoke_subagent` or the CLI `ptm portrait` subagent summarizer backed by an
   OpenAI-compatible lightweight model in `.env`, with deterministic extractive
   fallback when offline).

Keep the portrait block compact (under ~25 lines):

- **Intent Portrait:** 2–4 bullets capturing the active user intents, anchored
  concepts, and preserved experiential qualities;
- **Plan Portrait:** active focus across `LT/MT/ST/WP`, completed milestones, and
  immediate next pragmatic step;
- **Epistemic Watchlist:** open `KD-###` bookmarks and top Hebbian conceptual
  hubs;
- **Quick Recovery Commands:** one-line CLI pointers (`ptm status`, `ptm query`).
