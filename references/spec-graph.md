# Spec Graph (`_aiHumanInteract/specs/`)

Read this reference when crystallizing standing invariants, canonical domain
terminology, engineering/aesthetic standards, or verifiable contracts under
`_aiHumanInteract/specs/`, or when analyzing the blast radius of changing a
specification (`ptm.py spec impact`).

## Why Spec Graph exists alongside Intent, Plan, KD, and Scripts

Each graph in Paths to Modernity governs a distinct epistemic or temporal role:

| Graph | Question answered | Temporal lifecycle |
|---|---|---|
| **Intent Graph** (`INT-###`) | *What experience or goal does the user want, and why?* | Exploratory → clarified → crystallized (or reopened) |
| **Knowledge Debt** (`KD-###`) | *Which technical mechanism did the user defer understanding while prototyping?* | Provisional bookmark (`open` → `affirmed` \| `rejected`) |
| **Spec Graph** (`SPEC-###`) | ***What standing rules, terms, standards, and contracts MUST hold across all work?*** | **Standing law (`enforced` until formally superseded/deprecated)** |
| **Plan Graph v4** (`LT..WP`) | *What delta work steps will we execute next?* | Consumable delta (`proposed` → `in_progress` → `done`) |
| **Scripts Graph** (`SCR:...`) | *What does the codebase actually contain and import right now?* | Observed current state (may satisfy or violate a Spec) |

Without a **Spec Graph**, completed Work Packages (`done`) accumulate into an
historical log of finished tasks, forcing future sessions to archaeology-mine
dozens of closed plans just to learn which redlines, schemas, or naming rules
cannot be broken. `SPEC-###` separates **timeless standing obligations** from
**one-off execution deltas**.

## The Four Pillars of Spec (`kind`)

Every `SPEC-###` node belongs to one of four normative pillars:

1. **`invariant` — Mandatory Redlines & Behavioral Invariants (*Do / Do NOT*)**
   - Unconditional truths and prohibitions that hold across every feature and
     refactoring (e.g., *"Never block the primary canvas with modal approval
     queues"*, *"Never execute external side effects without explicit owner
     authorization"*).
   - Uses `do_rules` and `dont_rules` arrays for scannable enforcement.
2. **`glossary` — Controlled Domain Vocabulary (*Ubiquitous Language*)**
   - Once an ambiguous `Concept` in an `Intent` is clarified and anchored, its
     canonical name, identifier pattern, definition, and **forbidden aliases**
     (`canonical_term`, `forbidden_aliases`) are promoted here so frontend,
     backend, docs, and dialogue never drift into competing synonyms (e.g.,
     enforcing `PeakHandle` / `PK-###` and banning `WaveItem` or `LineCursor`).
3. **`standard` — Engineering, Architectural & Aesthetic Standards**
   - Cross-cutting conventions: module layering, error-handling envelopes,
     testing discipline, visual design tokens (such as palette constraints), or
     worldbuilding canon in creative works.
4. **`contract` — Verifiable Interface, Schema & State-Machine Contracts**
   - Exact input/output signatures, JSON/DB schemas, or legal state transitions
     (`signature_or_schema`, `postconditions`) paired directly with automated
     tests or validators (`verified_by_scripts`).

## Source-of-Truth Layout

Editable Markdown records live in `_aiHumanInteract/specs/nodes/SPEC-###.md` using
single-line JSON-value front matter (matching Plan Graph v4 and Intent Graph).
Generated views (`structure/graph.json`, `graph.md`, `graph.canvas`, schema
`paths-to-modernity-spec-graph-v1`) are outputs of `scripts/ptm.py build` and
must never be hand-edited.

```yaml
---
id: "SPEC-002"
title: "统一谱峰可寻址标识与术语规范 (PeakHandle)"
kind: "glossary"
status: "enforced"
enforcement: "canonical_term"
updated: "2026-11-24"
summary: "全栈代码、UI 与对话统一使用 PeakHandle (PK-###) 指代可寻址光谱特征，严禁混用非标别名。"
parent: "SPEC-001"
depends_on: []
enables: ["SPEC-003"]
validates: []
supersedes: []
conflicts_with: []
canonical_term: "PeakHandle (PK-###)"
forbidden_aliases: ["WaveItem", "LineCursor", "PeakIdx"]
do_rules: ["所有跨会话谱峰持久化与 UI 选中句柄必须携带 PK-### 格式 ID"]
dont_rules: ["严禁以数组下标或裸波长浮点数充当谱峰唯一主键"]
intent_refs: ["INT-003"]
plan_refs: ["MT-002", "WP-004"]
knowledge_debt_refs: []
governs_scripts: ["src/spectral_store.py", "web/SpectralCanvas.ts"]
verified_by_scripts: ["tests/test_workbench.py"]
---
```

### Field Contract

- **Required fields:** `id` (`SPEC-###`), `title`, `kind`
  (`invariant | glossary | standard | contract`), `status`
  (`draft | enforced | deprecated | superseded`), `enforcement`
  (`must | must_not | should | canonical_term`), `updated` (`YYYY-MM-DD`),
  `summary`.
- **Intra-graph explicit relations (7 standard families):**
  - `parent` → `decomposes_spec` (drawn as structural tree lines on the canvas)
  - `depends_on` → `prerequisite_for` (sidebar)
  - `enables` → `enables` (sidebar; must not duplicate `depends_on`)
  - `validates` → `validates` (sidebar)
  - `supersedes` → `supersedes` (bidirectional `↓ / ↑` icon stamps + sidebar;
    target must have `status: "superseded"`)
  - `conflicts_with` → `conflicts_with` (symmetric `✕` icon stamps + sidebar)
  - `alternative_of` → `alternative_of` (bidirectional `◎ / ⇄` icon stamps + sidebar)
- **Kind-specific optional facets:**
  - `canonical_term` (`str`), `forbidden_aliases` (`list[str]`)
  - `do_rules` (`list[str]`), `dont_rules` (`list[str]`)
  - `signature_or_schema` (`str`), `postconditions` (`list[str]`)

## How Spec Graph Interlocks with the Other Four Graphs

1. **Intent ↔ Spec (`crystallizes_into`):**
   - `SPEC.intent_refs` (and optional `INT.spec_refs`) link exploratory intents
     and resolved concepts to the standing `SPEC-###` rules they crystallized
     into.
2. **Plan ↔ Spec (`implements_spec`):**
   - `SPEC.plan_refs` and Plan Graph v4 `links.spec`
     (`["_aiHumanInteract/specs/nodes/SPEC-###.md"]`) connect one-off `LT/MT/ST/WP`
     work packages to the permanent specs they implement or amend, without
     altering Plan Graph v4's validator.
3. **Knowledge Debt ↔ Spec (`questions_spec`):**
   - `SPEC.knowledge_debt_refs` and `KD.spec_refs` link provisional technical
     bookmarks to any tentative spec or contract (`status: "draft"` or
     `"enforced"`). If a user later resolves a `KD-###` as `rejected`,
     `compute_kd_rejection_impact` surfaces affected specs under
     `amend_or_review_specs`.
4. **Scripts ↔ Spec (`governs_script` & `verifies_spec`):**
   - `SPEC.governs_scripts` binds standing obligations directly to production
     modules (`SPEC-### --governs_script--> SCR:path`), even for planned modules
     not yet created on disk;
   - `SPEC.verified_by_scripts` binds test suites or static validators that
     enforce the spec (`SCR:test_path --verifies_spec--> SPEC-###`). Both appear
     automatically on Script nodes (`governed_by_specs`, `verifies_specs`).

## Spec Amendment Impact Analysis

Before amending, deprecating, or superseding an `enforced` spec, inspect its
cross-graph blast radius:

```bash
python3 -B scripts/ptm.py spec impact /path/to/repo SPEC-002
```

This reports child/dependent specs, originating intents, implementing plans,
linked knowledge-debt bookmarks, governed production scripts, and verification
test suites that must be updated or re-run together.
