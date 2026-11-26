# Episodic Dialogue Disentanglement & Embedded SQLite Memory (`memory.sqlite`)

Read this reference when ingesting raw human–agent conversation turns, searching
past dialogue nuances that were not yet promoted into graph nodes, linking
`INT-###` / `SPEC-###` / `WP-###` / `KD-###` nodes to their originating
conversation threads, or folding completed discussion threads to save active
context tokens.

## Why Flat Turn Storage and Contiguous Episodes Both Fail

In complex engineering and research projects, a single conversational turn
frequently bundles **multiple independent topics in parallel** (e.g., *"1. How
should explicit relations render? 2. What does reorganization granularity mean?
3. Let's also add a Spec Graph"*), and those parallel topics interleave across
several turns before settling at different times.

- **Flat `Turn` indexing** embeds all 5 topics into one muddled vector and dumps
  80% irrelevant text on playback.
- **Contiguous `Episode` chunking** assumes turns `1..k` belong to one topic,
  shattering when topics interleave within each turn.
- **Forcing live UI session branches on the human** fragments conversational flow,
  multiplies prefix tokens by $N\times$, and blocks mid-stream cross-pollination
  (e.g., *"Wait — the answer to #2 also solves #4!"*).

Paths to Modernity solves this with **Single-Stream Interaction, Virtual Thread
Demultiplexing (`Physical Turn → Atomic Span → Virtual Thread`)**: the human
converses naturally in one stream while an embedded SQLite engine disentangles
multi-topic turns in the background.

---

## Architecture: Two-Tier Storage & Three-Layer Disentanglement

### 1. Portable Log vs. Derived Embedded SQLite Store

| Artifact | Path | Tracked in Git? | Role |
|---|---|---|---|
| **Portable Turn Stream** | `_aiHumanInteract/episodes/turns.jsonl` (+ optional `thread_state.json`) | Optional (small append-only JSONL) | Reconstructible source log of physical turns and folded thread capsules |
| **Embedded Memory & Vector DB** | `_aiHumanInteract/.cache/memory.sqlite` | **No** (`.cache/` gitignored; auto-rebuilt on `ptm.py build`) | Concurrent `WAL`-mode SQLite database unifying `turns`, `spans`, `spans_fts` (`FTS5`), `threads`, graph-node links, and **IEEE-754 `float32` binary embedding BLOBs** |

Storing 1024-dimensional embeddings as packed little-endian `float32` BLOBs
(`4,096` bytes/vector) cuts disk footprint by ~70% compared to JSON decimal
arrays, eliminates full-file JSON rewrites via `O(1)` indexed upserts, and allows
concurrent reads/writes across the main agent and isolated perspective subagents
via SQLite `WAL` mode — using **100% Python standard library (`sqlite3`, `struct`)**
with zero external database daemon.

### 2. The `Turn → Span → Thread` Data Model

1. **`turns` (Immutable Physical Layer — Cold Audit Ground Truth)**
   - Stores verbatim `turn_id` (`TURN-0001`), `session_id`, `turn_index`,
     `timestamp`, `user_text`, `assistant_text`, and `content_sha256`.
   - Never mutated; guarantees exact historical reproducibility.
2. **`spans` (Sub-Turn Atomic Semantic Slices — Primary Vector & FTS5 Unit)**
   - Each physical turn is split along structural and discourse boundaries
     (numbered items `1. / 2. / ①`, markdown headings `###`, and explicit
     topic-shift cues such as `关于第2点` / `另外` / `顺便问`), pairing each user
     sub-question `(user_char_start, user_char_end)` with its corresponding
     assistant answer slice `(asst_char_start, asst_char_end)` into `SPAN-0001.1`,
     `SPAN-0001.2`, etc.
   - Each `Span` receives its own pure **single-topic embedding vector** and is
     indexed into `spans_fts` (`FTS5` `unicode61` BM25 full-text index).
3. **`threads` (`THR-###` — Virtual Single-Topic Timelines)**
   - `Spans` across multiple turns that discuss the same topic are woven into a
     clean virtual `Thread` (`THR-001`, `THR-002`, ...) using discourse
     back-references (`关于第1点`), embedding cosine similarity against thread
     centroids, and identifier/concept anchor overlap.
   - `thread_spans` is **many-to-many**: if a later span synthesizes two earlier
     threads, it attaches to both and records a `thread_cross_refs` bridge.
   - `thread_node_links` binds `THR-###` to crystallized graph nodes (`INT-###`,
     `SPEC-###`, `WP-###`, `KD-###`, `EVAL-###`).

---

## Per-Thread Selective Context Folding (Solving Context Bloat)

Instead of waiting for global session compaction to indiscriminately crush active
and finished topics alike:

- **`active` threads** retain their full verbatim `Span` Q&A slices in working
  context queries (`ptm.py memory context`).
- **`folded` / `crystallized` threads** (topics whose decisions have settled or
  been promoted into `INT` / `SPEC` / `WP` nodes) collapse in active context into
  a **one-line Thread Capsule** (`capsule_summary` + graph node pointers),
  shrinking context consumption by 80–90% while keeping every underlying `Span`
  instantly retrievable in `memory.sqlite` via `ptm.py memory show THR-###` or
  `ptm.py memory search`.
- **Epistemic vs. Pragmatic branching rule:** Keep *epistemic* multi-topic
  dialogue unified for the human and virtually demultiplexed into `THR-###`;
  spawn true isolated subagent sessions (`invoke_subagent`) when *pragmatic*
  coding or context-separated `EVAL-###` review begins.

---

## CLI Workflow (`scripts/ptm.py memory ...`)

```bash
# 1. Log a turn (automatically splits multi-topic items into Spans & weaves into THR-###)
python3 -B scripts/ptm.py memory log /path/to/repo \
  --user "1. 让画布操作零弹窗；2. 不懂的算法先记入知识债" \
  --assistant "1. 采用主画布谱峰直选；2. 引入三态技术分拣闸门"

# 2. Import an existing JSONL chat transcript (idempotent by content_sha256)
python3 -B scripts/ptm.py memory import-jsonl /path/to/repo /path/to/transcript.jsonl

# 3. Hybrid FTS5 + dense vector search across atomic Spans & Threads
python3 -B scripts/ptm.py memory search /path/to/repo "WaveItem 谱峰命名统一"

# 4. List virtual threads or inspect one pure single-topic thread timeline
python3 -B scripts/ptm.py memory threads /path/to/repo
python3 -B scripts/ptm.py memory show /path/to/repo THR-001

# 5. Fold a settled thread into a compact capsule linked to crystallized graph nodes
python3 -B scripts/ptm.py memory fold /path/to/repo THR-001 \
  --nodes INT-001,SPEC-001,WP-001 \
  --capsule "确认消除模态审批队列，采用主画布谱峰直选与侧栏非阻塞声明（已固化为 INT-001 / SPEC-001）。"

# 6. Render selective working context (full spans for active threads + 1-line capsules for folded threads)
python3 -B scripts/ptm.py memory context /path/to/repo
```
