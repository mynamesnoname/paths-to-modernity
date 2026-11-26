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
2. **Dual-interface embeddings (Local Apple Silicon MLX + OpenAI-compatible API) with deterministic fallback:**
   - **Local On-Device (`--embedding-backend mlx` / `local`):** `mlx-embeddings` running
     `mlx-community/Qwen3-Embedding-0.6B-4bit-DWQ` (or `PTM_EMBEDDING_LOCAL_MODEL`) on
     Apple Silicon Metal GPU via `.venv` (`PTM_EMBEDDING_LOCAL_PYTHON` override supported).
   - **OpenAI-Compatible API (`--embedding-backend openai` / `api`):** Remote or local
     `/embeddings` endpoints (DashScope `text-embedding-v4` / `qwen3.7-text-embedding`,
     OpenAI, Ollama, vLLM) configured via `PTM_EMBEDDING_BASE_URL`,
     `PTM_EMBEDDING_MODEL`, `PTM_EMBEDDING_API_KEY`, and optional
     `PTM_EMBEDDING_DIMENSIONS`. Explicit opt-in only (`auto` never triggers billed API calls)
     with loud HTTP/dimension validation.
   - **Fallback (`--embedding-backend hash`):** Deterministic L2-normalized
     character/word n-gram subword hashing (`ptm-stdlib-ngram-384`) so offline environments
     and CI tests always succeed without network or GPU packages.
   - **Strict model-namespace isolation in SQLite:** Vectors are content-addressed by
     `<effective_model_id>:<sha256(text)>` (`mlx:<model>`, `openai:<model>:<dim>`, or
     `ptm-stdlib-ngram-384`) and stored as compact IEEE-754 little-endian `float32` binary
     BLOBs inside `_aiHumanInteract/.cache/memory.sqlite` (`WAL` mode, shared with the
     [Episodic `Turn → Span → Thread` store](episodic-memory.md)). Switching between `mlx`
     and `openai` preserves both caches without ever computing cross-model dot products.
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
4. **Deterministic lexical & structured anchors (why PtM omits per-turn LLM keyword calls):**
   - *HeLa-Mem* (§3.1.1 / §3.4) pairs `all-MiniLM-L6-v2` with an online LLM call
     (`llm_extract_keywords`) on every write and every query to compensate for
     weak proper-noun recall. PtM intentionally **keeps the lexical bonus term**
     $\alpha \cdot \text{keyword\_match}$ inside $S_{\text{base}}$ (for exact
     code symbols, IDs, and abbreviations that dense vectors blur), **but drops
     per-turn LLM keyword extraction**:
     1. Calling a remote LLM on every `query`/`related` probe would add seconds
        of network latency, break offline operation, and fail across bilingual
        synonyms (e.g., `"Event Sourcing"` vs. `"事件溯源"`), which
        `Qwen3-Embedding-0.6B` already aligns natively;
     2. Unlike unstructured chat transcripts, PtM's federated graphs already
        expose curated high-signal anchors at zero API cost: **Intent
        `concepts[].name`**, **Knowledge Debt `term`**, and **Scripts AST
        `classes` / `functions`**.

## Agent-facing reverse lookup (`ptm.py related` & `ptm.py query`)

Agents can inspect embedding similarity and Hebbian associations directly via
`scripts/ptm.py` (read-only by default unless `--reinforce` is passed):

```bash
# 1. Inspect an existing Plan, Intent, KD bookmark, or Script (reuses full cached vector)
python3 -B scripts/ptm.py related /path/to/repo WP-002
python3 -B scripts/ptm.py related /path/to/repo --node INT-003 --per-graph 5

# 2. Probe an uncommitted draft file BEFORE writing it into _aiHumanInteract/plan/
python3 -B scripts/ptm.py related /path/to/repo --draft-file /tmp/draft_WP007.md

# 3. Probe a draft idea in plain text to discover candidate dependencies, conflicts, KDs, and scripts
python3 -B scripts/ptm.py related /path/to/repo --text "实现轻量 JSON 谱峰快照导出替代事件溯源"

# 4. Run Dual-Path Retrieval (also auto-resolves exact node IDs)
python3 -B scripts/ptm.py query /path/to/repo "谱峰标注无弹窗交互" --no-reinforce
```

`ptm.py related` returns:
- `declared_links`: relationships already explicitly recorded in source files;
- `novel_discoveries`: top unlinked nodes surfaced by embedding similarity and
  Hebbian spreading activation (candidate `depends_on`, `conflicts_with`,
  `alternative_of`, `knowledge_debt`, or `links.code` targets);
- `by_graph`: top ranked matches grouped cleanly into `intent`, `plan`,
  `knowledge_debt`, and `scripts`.

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
