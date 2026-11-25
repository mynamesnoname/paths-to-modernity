# Intent Graph and epistemic inquiry

Read this reference when decomposing user dialogue into explicit intents and
concepts, designing epistemic prototypes ("physical rotation"), or maintaining
repository-local intent records under `_aiHumanInteract/intent/`.

## Epistemic action vs. pragmatic action

Following Kirsh & Maglio (1994), actions in human–agent project design serve two
distinct functions:

- **Epistemic actions** change the shared informational and cognitive state
  $S_{\text{info}}$ of the human and agent: reducing working-memory load (space
  complexity), mental simulation steps (time complexity), and misinterpretation
  risk (unreliability). Clarifying concepts, contrasting interpretive variants,
  inspecting curated graphs, and building throwaway visual sketches or demos are
  epistemic actions.
- **Pragmatic actions** directly advance the deliverable state $S_{\text{phys}}$
  (writing production code, wiring APIs, migrating schemas, running builds). Once
  intent boundaries and technical disclosures are settled, pragmatic actions
  belong primarily to the agent and deterministic tooling.

### Physical rotation via epistemic prototypes

In Kirsh & Maglio's Tetris experiments, physically rotating a piece on screen
takes ~100 ms whereas mentally rotating it takes 800–1200 ms and fills working
memory. In project design, asking a person to evaluate abstract verbal options
forces expensive **mental rotation**. Building a quick, reversible **epistemic
prototype** — an SVG comparison, an interactive HTML/UI widget, a mocked CLI
trace, or a minimal runnable demo — acts as **physical rotation**: even an
imperfect prototype lowers cognitive friction and reveals what the person
actually wants or rejects.

Prefer an epistemic prototype over purely verbal questioning whenever:

- a choice governs visual layout, interaction feel, narrative tone, or pacing;
- the person says "I won't know until I see it"; or
- two variants or alternatives sound plausible in prose but feel different in use.

## Hierarchy of meaning: Utterance → Intent → Concept → Variants / Alternatives

A single conversational turn often bundles multiple goals, and a single goal
rests on several terms whose meanings are not yet shared:

```text
Dialogue Turn (preserved verbatim in raw_utterance / utterances/UTT-###.md)
  └── Intent (INT-###) — one coherent desired change or design direction
        ├── Concept 1 — e.g. "Scientific Agent" (domain/subject anchor)
        └── Concept 2 — e.g. "Faster" (ambiguous quality/outcome concept)
              ├── Interpretive Variant IV-1: Lower single-query latency
              ├── Interpretive Variant IV-2: Higher batch compute throughput
              ├── Interpretive Variant IV-3: Fewer human review interruptions
              └── Interpretive Variant IV-4: Code-level algorithmic speedup
        └── Implementation Alternatives (after shared variant is chosen)
              ├── IA-1: Deterministic confidence gate (reversible rule baseline)
              └── IA-2: Learned triage classifier (higher recall, opaque threshold)
```

Keep the two comparison layers separate:

1. **Interpretive variants** interpret what a concept *means* as an outcome.
   They imply different goals and cannot be scored against one shared baseline.
   Present concise contrasts (or quick visual/behavioral probes) so the decision
   owner selects or synthesizes the intended meaning.
2. **Implementation alternatives** are distinct technical or experiential ways to
   achieve an already confirmed intent. Compare them under [alternatives](alternatives.md),
   using interactive choice tools, side-by-side SVG/UI prototypes, or technical
   disclosure triage.

## Repository layout and source contract

When a project persists its Intent Graph, store editable Markdown nodes under
`_aiHumanInteract/intent/`:

```text
_aiHumanInteract/
  intent/
    utterances/          Optional verbatim multi-turn snapshots (UTT-###.md)
    prototypes/          Optional SVG / HTML / demo artifacts for physical rotation
    nodes/               Editable intent source nodes (INT-###.md)
    structure/           Generated views (graph.json, graph.md, graph.canvas)
```

Each `_aiHumanInteract/intent/nodes/INT-###.md` uses the same stdlib-parseable
single-line JSON front-matter convention as Plan Graph v4:

```yaml
---
id: "INT-001"
title: "Make the scientific workbench feel immediate"
status: "clarified"
updated: "2026-11-24"
raw_utterance: "让科学 Agent 更快，不要每次分析都卡在人工点确认上。"
utterance_ref: "_aiHumanInteract/intent/utterances/UTT-001.md"
parent: null
depends_on: []
enables: []
validates: []
supersedes: []
conflicts_with: []
alternative_of: null
refines: []
branches_from: []
constrains: []
concepts: [{"name": "科学 Agent", "role": "subject", "status": "anchored", "definition": "光谱特征交互分析智能体"}, {"name": "更快", "role": "outcome", "status": "resolved", "selected_variant": "IV-3", "interpretive_variants": [{"id": "IV-1", "meaning": "降低单次推理端到端延迟"}, {"id": "IV-2", "meaning": "提高后台批处理吞吐"}, {"id": "IV-3", "meaning": "减少低信息量的人工审批中断"}]}]
implementation_alternatives: [{"id": "IA-1", "approach": "可逆范围预授权 + 三态技术分拣面板", "selected": true, "prototype": "_aiHumanInteract/intent/prototypes/triage-demo.svg"}, {"id": "IA-2", "approach": "基于风险评分的全自动静默放行", "selected": false}]
plan_refs: ["LT-001", "WP-001"]
knowledge_debt_refs: ["KD-001"]
qualities: ["直接操作科学对象而非反复弹窗审批"]
---
```

### Allowed statuses and relationships

- **Statuses:**
  - `exploring` — concepts or interpretive variants are still under epistemic inquiry;
  - `clarified` — core concepts and interpretive variant are settled enough to seed pragmatic plans;
  - `crystallized` — backed by active or completed Plan Graph nodes and validated through prototype/use;
  - `reopened` — reopened because prototype feedback or a rejected Knowledge Debt invalidated an earlier reading;
  - `superseded` — replaced by a newer intent node (preserving history).
- **Declared intent edges (aligned with Plan Graph's agent-maintained relations):**
  - `parent` (`decomposes_intent`) — hierarchical parent/children shown directly on the graph canvas;
  - `depends_on` (`prerequisite_for`), `enables`, `validates` — directional dependencies, capabilities, and validations inspected in the node detail sidebar;
  - `supersedes`, `conflicts_with`, `alternative_of` — lifecycle replacement, incompatibility, and alternative framing stamped via icon badges/watermarks on counterpart cards and listed in the sidebar;
  - `refines`, `branches_from`, `constrains` — optional epistemic aliases preserved for nonlinear exploration.

### Body sections

Intent node Markdown bodies remain concise and human-readable:

- `## Raw Utterance` — exact quote and conversational context;
- `## Concept Decomposition` — key concepts, interpretive variants considered, and why the chosen reading won;
- `## Epistemic Probes & Alternatives` — prototypes, SVG sketches, or concrete comparisons shown to the user;
- `## Pragmatic Handoff` — linked Plan Graph IDs (`LT/MT/ST/WP`) and any Knowledge Debt bookmarks (`KD-###`) recorded during technical disclosure.
