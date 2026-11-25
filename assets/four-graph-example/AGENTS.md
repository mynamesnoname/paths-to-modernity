<!-- paths-to-modernity:protocol:start -->
<!-- schema-version: paths-to-modernity-protocol-v4 -->
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
- `specs/nodes/` (`specs/structure/graph.json`) — Spec Graph: standing invariants, glossary, standards & contracts
- `plan/` (`plan/structure/graph.json`) — Plan Graph v4 sources & views (pragmatic)
- `knowledge-debt/nodes/` (`knowledge-debt/structure/graph.json`) — Knowledge-debt bookmarks
- `scripts/structure/graph.json` — Scripts Graph AST dependencies & plan/spec coverage
- `hebbian/associations.json` — Embedding + Hebbian associative memory & hubs
- `studio/index.html` — Self-contained interactive three-stratum five-graph studio
- `state/active.md` — Active session checkpoint for recovery after compaction

After compaction, or in a new session, read the Project Portrait block (if
present) and `_aiHumanInteract/state/active.md` first, verify that pointers and
authorization still hold, and load only the neighborhood needed for the next step.
<!-- paths-to-modernity:protocol:end -->

<!-- paths-to-modernity:plan-graph:start -->
<!-- schema-version: paths-to-modernity-plan-graph-v4 -->
<!-- Installation template: this block governs the target project after adoption. -->
## Plan Management

Architecture and multi-stage work is governed by the visible, version-controlled
`_aiHumanInteract/plan/` directory. Markdown nodes under its level directories
are the only editable sources. Files under `_aiHumanInteract/plan/structure/`
are deterministic generated views and must not be edited by hand. Use
`_aiHumanInteract/plan/structure/graph.json` for programmatic discovery, require
`schema_version: paths-to-modernity-plan-graph-v4`, then follow a node's
`source` field relative to the repository root. Reject unsupported schema
versions.

Plans decompose through exactly four levels:

```text
long-term (LT-###) -> mid-term (MT-###) -> short-term (ST-###) -> work-package (WP-###)
```

A work package is the terminal, directly executable unit. It may span several
steps or files, but owns one coherent outcome and is independently acceptable.
IDs are globally unique, immutable, zero-padded, and never reused. Every active
non-work-package node must decompose through all remaining levels to a work
package. A node has at most one decomposition parent; every active non-root
node has exactly one; long-term roots set `parent: null`. Cross-cutting
relationships use typed edges.

Every node starts with YAML-style front matter in which each line maps a key
to a single-line JSON value, containing `id`, `title`, `level`, `status`,
`updated`, `parent`, `depends_on`, `enables`, `objective`, `deliverables`,
`acceptance`, `links`, and `evidence`.
Optional
typed references are `validates`, `supersedes`, and `conflicts_with`. Optional
planning details are `context` (problem, invariants, constraints, non-goals,
and success signals, including only useful members),
`qualities`, `tradeoffs`, `perspectives`,
`source_requirement`, `approach`, and `alternative_of`; omit them from ordinary
nodes that do not need them. These details are independently optional.
If present, `source_requirement` must resolve locally or identify an external
archive and must also be recorded in `links`. Work-package bodies contain
`Objective`, `Planned work`, `Decisions`, `Completion`, and `Evidence` sections.

Use `parent`/`decomposes_to` for hierarchy, `depends_on` for hard prerequisites,
`enables` for newly possible capability, `validates` for verification,
`alternative_of` for controlled sibling alternatives, and `supersedes` or
`conflicts_with` for lifecycle/design relationships. Decomposition, dependency,
alternative, and supersession graphs must be acyclic and contain no dangling IDs,
self-references, duplicate IDs, or orphaned active nodes.

Controlled alternatives must be sibling work packages sharing objective text,
invariant sets, and source requirements, with distinct non-empty approaches.
Record the common evaluation baseline and comparison decision in a linked
evaluation or Decisions section.

Local links are repository-relative without `..`. Every node links its own plan
and at least one intended or existing code, test, documentation, artifact, or
evaluation target. Planned links may be absent; links and evidence for `done` or
`superseded` nodes must exist or identify an external archive. Evidence must
also be recorded in links, in every status. External references have the form
`external:<non-empty archive identifier or URI>`. The validator checks their
syntax only; record who verified external completion evidence, when, and what
it establishes in the Evidence section or a linked evaluation.

Allowed statuses are `proposed`, `ready`, `in_progress`, `blocked`, `done`, and
`superseded`. Mark a work package `done` only when all acceptance criteria pass
and evidence is linked. Mark an ancestor `done` only when every descendant
work package is `done` or evidenced `superseded`.
Hard prerequisites must be `done` before work becomes `in_progress` or `done`.
Superseded plans retain evidence and must be referenced by a successor.

Before decomposing a materially ambiguous requirement, inspect available facts.
Ambiguity is material when two reasonable readings would change the outcome,
responsibility, acceptance, meaningful risk, or an irreversible
commitment. Distinguish evidence gaps from choices about value, responsibility,
authority, acceptable risk, and irreversible scope. The agent resolves
inspectable facts; it presents consequential boundary alternatives to the
decision owner (the authorized person or role). If the environment disables
interactive question tools, present the choice as plain conversational text
and stop for an answer; a missing prompt channel never turns a human choice
into a silent assumption. Record the selected inside/outside boundary,
affected interfaces, unresolved discoveries, retained qualities, and rationale
in a linked requirement or decision record. Keep the governing node
`proposed` until it is clear enough for the next responsible commitment; do not
delay a reversible discovery step merely to manufacture total certainty.

For deeper inquiry, planning-model guidance, or alternative comparison, use
the `paths-to-modernity` skill if available in the environment's skill catalog.
Start at its `SKILL.md` and follow the relevant reference links. These local
rules remain usable when the skill is unavailable; do not assume an absolute
installation path.

Before architecture implementation, locate the governing work package, confirm
its dependencies, and mark it `in_progress`; create one under the appropriate
parents if absent. At completion, link evidence, resolve the work package,
update eligible ancestors, rebuild, and run:

```bash
python3 -B _aiHumanInteract/plan/validate.py
python3 -B _aiHumanInteract/plan/build_graph.py
python3 -B _aiHumanInteract/plan/build_graph.py --check
python3 -B -m unittest discover -s _aiHumanInteract/plan -p 'test_*.py' -v
```

Commit source nodes and generated `graph.json`, `graph.md`, `graph.canvas`,
`graph.html`, and `review.md` together. Keep runtime/domain evidence graphs in a separate
namespace and connect them only through links.
<!-- paths-to-modernity:plan-graph:end -->

<!-- paths-to-modernity:portrait:start -->
<!-- generated: 2026-11-24 | synthesizer: subagent-llm:deepseek-flash -->
### Project Recovery Portrait (Generated — Do Not Hand-Edit)

- **意图画像 (Intent Portrait):** INT-001（已结晶）要科学光谱 Agent 像"拨动实体旋钮"般直接连贯，"更快"已定型为 IV-3；INT-002（已澄清）要求未懂技术走三态分拣＋知识债书签，选 IV-1"先记下来跑通原型"，绝不把沉默当背书。
  INT-003（探索中）跨会话同一谱峰可寻址与历史审计，概念"历史状态回放粒度"仍 ambiguous（IV-1）；INT-004 全黑盒代理已 superseded（保留 WP-003 为反例锚点）；INT-005 要求零弹窗回放验收（WP-006）。
- **常驻规范与术语 (Spec & Glossary Portrait):** SPEC-001 must_not：主画布禁阻断式技术弹窗，沉默/超时≠技术授权；SPEC-002 强制统一术语 `PeakHandle (PK-###)`，禁用 WaveItem/LineCursor/PeakIdx 同义词。
  SPEC-003 must：暖灰纸感低疲劳色板＋存储模块与分拣模块单向零循环依赖；SPEC-004 must：`classify_disclosure` 输入输出契约与知识债 open→affirmed|rejected 状态机后置条件。
- **规划与执行画像 (Plan & Scripts Portrait):** 计数 done 3 / in_progress 4 / ready 1 / proposed 2 / superseded 1；进行中 LT-001、MT-001、ST-001、ST-002，ready 为 WP-002（三态分拣闸门接知识债）。
  已完成 WP-001（谱峰直选画布+会话入口）、WP-004（轻量 KV 谱峰持久化）、WP-006（端到端契约验证）；核心代码枢纽 `src/workbench_api.py`(1.0)、`src/spectral_store.py`、`src/triage_gate.py`(0.9655)，测试 `tests/test_workbench.py`(0.5405)。
  缺口：`src/event_replay_audit.py` 仍为 planned_target（0.5405）未落地，对应 WP-005 不在活跃/完成列表。
- **认知书签与关联枢纽 (Epistemic Watchlist & Hubs):** KD-001 Hebbian 双路激活（open，not_understood_prototype）—触发：多跳召回噪声过多或固化突触衰减超参；KD-002 Append-Only 事件溯源（open）—触发：JSON 快照撑不住多协作者冲突回溯或动手写 `src/event_replay_audit.py`。
  KD-003 MLX 4-bit 端侧量化嵌入已 affirmed，触发：迁移无 Metal 的 Linux 容器时验降级通路。Hebbian 枢纽：WP-001(3.54)、SPEC-001(3.48)、SPEC-004(3.31)、MT-001(3.15)、WP-006(3.01)。

- **快速恢复入口 (Quick Routes):** 意图 `_aiHumanInteract/intent/structure/graph.json` · 规范 `_aiHumanInteract/specs/structure/graph.json` · 规划 `_aiHumanInteract/plan/structure/graph.json` · 知识债 `_aiHumanInteract/knowledge-debt/structure/graph.json` · 脚本 `_aiHumanInteract/scripts/structure/graph.json` · 工作台 `_aiHumanInteract/studio/index.html` · 会话断点 `_aiHumanInteract/state/active.md`
<!-- paths-to-modernity:portrait:end -->
