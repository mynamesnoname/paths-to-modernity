# Knowledge debt and technical disclosure triage

Read this reference when a project introduces unfamiliar technical choices to a
bounded-technical decision owner, when recording or revisiting a `KD-###`
bookmark, or when a resolved knowledge debt triggers Intent / Plan reorganization.

## Bounded-technical decision owners and the right to know

In most creative and engineering projects, the decision owner holds authority
over outcomes, user experience, values, and acceptable risk, and has **the right
to know** what architecture, frameworks, data structures, or algorithms pragmatic
execution will rely on — without necessarily having deeper technical expertise
than the agent on every mechanism.

Asking such an owner *"Should we use X? (Recommended: Yes)"* produces the
**Agree Problem**: uninformative assent that transfers anxiety without adding
control. Conversely, hiding technical choices erodes agency and prevents later
course correction when understanding matures in practice.

## Pre-execution technical declaration & three-way triage

Before entering a new pragmatic implementation scope, declare the consequential
technical choices (cap at 1–5 items whose rejection would actually change the
implementation, architecture, lock-in, or user-observable behavior). Describe
each item in terms of **what it does, what it costs if wrong, and whether it is
reversible**.

Have the user classify each item into one of **three explicit choices** (via the
harness's structured choice UI when available, or concise structured text):

1. **`understood_agreed` — Understood and agreed (Informed acceptance)**
   The user understands the technical trade-off and explicitly endorses using it.
2. **`not_understood_prototype` — Not understood yet, proceed with prototype (Provisional acceptance + Knowledge Debt bookmark)**
   The user chooses not to spend cognitive friction learning the mechanism right
   now, authorizes proceeding within a bounded, reversible prototype, and
   bookmarks the item in `_aiHumanInteract/knowledge-debt/` linked to the
   relevant Intent and Plan nodes.
3. **`disagreed_counterproposal` — Disagreed, propose own technical view (Rejection & plan revision)**
   The user rejects the proposed mechanism and supplies an alternative technical
   constraint or preference; the agent revises the Plan (and re-examines Intent
   if needed) before executing.

### Orthogonal invariants

- **Silence is never authorization.** No pragmatic execution begins until the
  scope is explicitly authorized.
- **Already-authorized prototype scopes do not re-block every turn.** Within a
  granted reversible prototype scope, routine internal details proceed without
  repeated triage; trigger a new declaration only when introducing a choice with
  lasting architectural or external consequences.
- **Not a substitute for evidence.** Recording a Knowledge Debt bookmark never
  discharges a required test, benchmark, or safety check.
- **Not a curriculum.** Do not create unrequested encyclopedia entries for minor
  terms or require the user to study before building a reversible prototype.

## Four kinds of gaps that must not be confused

| Kind | Core question |
|---|---|
| `concept` | What does this technical or domain term mean in our project? |
| `reasoning_gap` | Why does this architecture/algorithm fit our goal? |
| `comparison_gap` | Why approach A rather than approach B? |
| `intuitive_doubt` | "This feels over-engineered or fragile, though I cannot prove why yet." |
| `evidence_gap` | Has this claim been verified by a test or measurement? *(Requires verification, not just explanation.)* |

## Bookmark lifecycle and graph reorganization

Understanding develops through concrete practice (as shown in *DesignerlyLoop*):
seeing a working prototype often clarifies whether an abstract technical choice
was right or wrong. Each Knowledge Debt node (`_aiHumanInteract/knowledge-debt/nodes/KD-###.md`)
follows a three-state lifecycle:

```text
open (bookmarked during prototype)
  ├──► affirmed  (user now understands & endorses the choice → plan stands as informed acceptance)
  └──► rejected  (user now understands, rejects the choice & states new view → triggers reorganization)
```

### Reorganizing Intent and Plan Graphs on `rejected`

When a user cancels an `open` Knowledge Debt with `rejected` and states a new
technical or experiential view:

1. Record the resolution (`status: "rejected"`, `resolution_note`, `resolved_at`)
   on `KD-###.md`.
2. Run impact analysis (`ptm kd resolve` / `ptm kd impact KD-###`) to trace:
   - **Direct Plan targets (`plan_refs`)** and their downstream `prerequisite_for`
     dependents → transition superseded `WP-###` nodes to `superseded` and create
     successor work packages reflecting the user's new technical direction;
   - **Linked Intent nodes (`intent_refs`)** → if the rejection reveals that the
     underlying concept or desired quality was misread (not merely its technical
     mechanism), transition `INT-###` to `reopened`, update the chosen variant or
     constraint, and propagate to the Plan Graph.

## Source contract (`_aiHumanInteract/knowledge-debt/nodes/KD-###.md`)

When using the structured multi-graph bundle, store bookmarks with single-line
JSON front matter:

```yaml
---
id: "KD-001"
term: "Hebbian Spreading Activation (Base + Flip)"
kind: "reasoning_gap"
status: "open"
triage_mode: "not_understood_prototype"
updated: "2026-11-24"
intent_refs: ["INT-002"]
plan_refs: ["WP-002"]
script_refs: ["scripts/ptm_hebbian.py"]
revisit_when: "原型检索出现不相关的联想节点干扰，或准备固化长期记忆权重参数时"
resolution_note: null
---
```

Body sections:

- `## Understanding Gap` — what remains unfamiliar or uncertain, in plain words;
- `## Technical Declaration & Cost if Wrong` — concise plain-language mechanism,
  lock-in/failure cost, and reversibility boundary;
- `## Revisit Trigger & Evidence Needed` — observable prototype behavior or test
  that makes revisiting worthwhile;
- `## Resolution & Graph Impact` — filled when `affirmed` or `rejected`.

Projects without the multi-graph bundle may still keep lightweight narrative
files `_aiHumanInteract/knowledge-debt/<topic>.md` linked from decision records.
