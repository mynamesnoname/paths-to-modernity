# Planning model

Use this reference to structure a complex plan or review its scope, outcomes,
and assumptions. Adapt names and nesting to the target project's existing model.

## Preserve intent and decisions

Keep the original request or a stable reference to it. When meaning or
responsibility is unsettled, use [inquiry](inquiry.md) first. Record the agreed
scope, affected interfaces, unresolved questions, decision owners, and rationale
in the project's requirement or decision record.

A requirement or decision record can be as small as:

```yaml
inside: "Explain routing decisions"
outside: "Automate recovery"
interfaces: ["Existing routing engine", "Operator workflow"]
unknowns:
  - question: "Which inputs are needed to reproduce a decision?"
    owner: "Implementation team"
    next_step: "Inspect the routing code"
decisions:
  - decision: "Keep recovery outside this plan"
    decided_by: "Operations lead"
    rationale: "Recovery needs separate authority and operational support"
```

Keep this durable record linked from the plan. Do not copy dialogue into every
work item or add unsupported fields to a project's strict schema.

## Plan brief

A plan brief explains the desired outcome and the context needed to judge it:

- **Outcome:** what will be true when the work succeeds.
- **Problem:** the condition that calls for change.
- **Invariants:** properties every acceptable solution must preserve.
- **Constraints:** current limits on resources, time, compatibility, or authority.
- **Non-goals:** nearby work deliberately excluded.
- **Success signals:** observations that would indicate the intended result.

Include the context that changes decisions. An invariant defines acceptable
solutions; a constraint limits available routes. A deliverable can exist without
achieving an outcome, so specify both the expected result and how to judge it.

## Decomposition and dependencies

Decompose around capabilities and coherent outcomes before files or people.
Each executable work package owns an outcome, prerequisites, deliverables,
acceptance criteria, and an expected evidence location.

Hierarchy answers “part of what?” Dependency answers “must follow what?”
Keep these relationships distinct. Use the target project's levels and storage
format; the planning method does not require a four-level hierarchy.

## Desired qualities and tradeoffs

Qualities describe how an acceptable result should feel or behave in use.
Examples include “easy to understand under pressure” and “forgiving to a
first-time operator.” Tradeoffs describe competing aims, such as speed versus
explanation detail; they may remain deliberately unresolved until useful
evidence or a decision becomes available.

Record either when technically acceptable solutions could still differ in a
way that matters. Preserve the person's wording. Keep acceptance tests
separate, and introduce measurable proxies only when they represent the
quality meaningfully. A stated quality alone is not completion evidence.

When unsure where an observation belongs: a quality describes the desired
character of the result, a tradeoff holds competing aims that stay open, and a
perspective (next section) is a viewpoint used to examine the plan.

## Perspectives

A perspective is a stakeholder or analytical viewpoint that can reveal a
different constraint, failure mode, or acceptance need. Names are free text,
not an enumeration. Use a label whose review question is clear in context:

| Perspective | Review question |
|---|---|
| Operator | Can someone understand and act on the result under pressure? |
| Runtime | Does the design change latency, failure handling, or resource use? |
| Evidence | Can another person reproduce and check the result? |

Choose only useful viewpoints. Record findings that change scope, context,
acceptance, decomposition, or a decision in the plan's review or Decisions
section. Applying another perspective does not create another plan.

## Example and handoff

A compact brief might state:

> Operators cannot explain slow-path routing. The outcome is a reproducible
> explanation of each decision. Existing routing behavior must remain unchanged,
> and automated recovery is outside scope. The explanation should stay easy to
> understand under pressure.

Decompose that outcome into schema definition and replay verification, with
verification depending on the schema. Add an alternative only if a consequential
choice of approach remains; use [alternatives](alternatives.md) to compare it.

When using the optional repository implementation, the
[Plan Graph field mapping](plan-graph.md#concepts-and-fields) defines exactly
how these concepts are stored. Other projects can represent them differently.

## Common problems

- An objective combines background, implementation, and acceptance into one paragraph.
- Deliverables name activities without an expected result.
- Dependencies mean “related to” rather than a real prerequisite.
- A quality is copied into acceptance without explaining how it will be judged.
- Several documents can independently change the same decision.
- Optional fields are filled merely to complete a template.
