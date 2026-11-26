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
<!-- generated: 2026-11-26 | synthesizer: deterministic -->
### Project Recovery Portrait (Generated — Do Not Hand-Edit)

- **意图画像 (Intent Portrait):** `INT-001` 让科学光谱 Agent 交互更快且具备直接操作感 (`crystallized`) · `INT-002` 对未理解技术采用三态分拣与可回溯知识债书签 (`clarified`) · `INT-003` 跨会话保持谱峰特征可寻址与历史审计 (`exploring`) · `INT-004` 备选意图：对用户完全隐藏底层算法与数据策略 (`superseded`)；核心体验品质：恢复上下文轻快透明，不引入笨重的运维负担；操作科学对象应像拨动实体仪器一样直接连贯，不退化为管理弹窗；用可运行原型和回归用例说话。
- **常驻规范与术语 (Spec & Glossary Portrait):** `SPEC-001` [invariant] 核心光谱画布零模态阻塞与显式授权铁律 · `SPEC-002` [glossary] 统一谱峰可寻址标识词典 (PeakHandle)（标准词：`PeakHandle (PK-###)`） · `SPEC-003` [standard] 建筑极简柔和视觉与模块单向解耦开发标准 · `SPEC-004` [contract] 三态技术分拣闸门与知识债状态机契约。
- **规划与验证画像 (Plan, Scripts & Verification Portrait):** 状态分布（done=3, in_progress=4, proposed=2, ready=1, superseded=1）；当前焦点：LT-001 (交付低摩擦、可追溯的科学光谱协同工作台), MT-001 (建立直接画布交互与认知分拣闸门), ST-001 (落地直接操作画布与三态技术分拣核心), WP-002 (采用显式三态技术分拣闸门连接知识债书签)；核心代码枢纽：`src/workbench_api.py`, `src/spectral_store.py`, `src/triage_gate.py`；待落地脚本：`src/event_replay_audit.py`；形式验证：1/1 用例通过且 SHA-256 指纹保鲜。
- **评鉴关注、认知书签与关联枢纽 (Evaluations, Watchlist & Hubs):** 评鉴关注：`EVAL-003`(concerns · 科研多协作者数据可靠性与可审计视角) · `KD-001` Hebbian Spreading Activation (Base + Flip 双路激活检索)（触发重审：当多跳检索召回过多无关联想节点，或准备固化突触衰减超参数时）；`KD-002` Append-Only Event Sourcing 状态事件溯源存储（触发重审：当普通 JSON 快照无法满足多协作者谱峰标注冲突回溯，或准备编写 src/event_replay_audit.py 时）；赫布高连接枢纽：`SPEC-001`(3.58), `WP-001`(3.56), `WP-006`(3.50)。

- **快速恢复入口 (Quick Routes):** 意图 `_aiHumanInteract/intent/structure/graph.json` · 规范 `_aiHumanInteract/specs/structure/graph.json` · 规划 `_aiHumanInteract/plan/structure/graph.json` · 知识债 `_aiHumanInteract/knowledge-debt/structure/graph.json` · 脚本 `_aiHumanInteract/scripts/structure/graph.json` · 工作台 `_aiHumanInteract/studio/index.html` · 会话断点 `_aiHumanInteract/state/active.md`
<!-- paths-to-modernity:portrait:end -->
