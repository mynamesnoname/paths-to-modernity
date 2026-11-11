---
name: paths-to-modernity
description: Clarify materially ambiguous requirements with the decision owner, define scope and outcomes, structure complex plans, and compare consequential alternatives. Use for roadmaps, architecture decomposition, plan review, or repository-local plan graphs. Do not use for routine one-step tasks, status reports, or execution of an already-governed plan unless replanning is needed.
---

# Paths to Modernity

Turn uncertain intent into clear, traceable plans. Work with people to define
what matters, preserve meaningful qualities, review different perspectives,
and compare alternatives against shared outcomes.

The user participates in forming the plan. The agent investigates facts,
proposes interpretations, and explains consequences. Choices about values,
responsibility, and acceptable consequences belong to the authorized person
or role, called the **decision owner**. The current user may be that owner or
identify another one.

## Establish context

The **target project** is the repository, product, organization, or planning
system to which the plan applies. Read its applicable instructions, existing
plans, and decision history. Use an existing coherent structure and terminology.
The four-level Plan Graph described below is one optional implementation.

The **skill root** is the directory containing this loaded `SKILL.md`.
Resolve the links below relative to it, regardless of where the skill is
installed. The **repository root** is the target project's top-level directory;
it may be different from the skill root.

Planning alone does not authorize implementation. Deliver the planning or
review artifact requested by the user.

## Read the needed detail

| Resource | Read when |
|---|---|
| [Inquiry](references/inquiry.md) | Two reasonable interpretations could change the outcome, responsibility, acceptance, meaningful risk, or an irreversible commitment |
| [Planning model](references/model.md) | Defining a plan's objective, context, decomposition, qualities, or review perspectives |
| [Alternatives](references/alternatives.md) | Consequential alternatives need comparison under a shared outcome and evaluation baseline |
| [Plan Graph](references/plan-graph.md) | The project uses a plan graph — look for `_aiHumanInteract/plan/structure/graph.json` with a `schema_version` field — or the user asks to establish repository-local planning infrastructure |
| [Knowledge debt](references/knowledge-debt.md) | A person cannot evaluate a technical recommendation that affects their work, or asks for the gap to be recorded |
| [Worked example](assets/plan-graph/example/README.md) | First learning how the Plan Graph's source plans and generated views fit together |

## Planning workflow

Use the depth needed for the next decision; omit steps that add no value.

1. Preserve the raw requirement or a faithful link so later summaries cannot
   silently change intent.
2. Inspect evidence before asking questions. Ambiguity is material when two
   reasonable readings change the outcome, responsibility, acceptance,
   meaningful risk, or an irreversible commitment;
   [inquiry](references/inquiry.md) owns this threshold and its treatment.
   Investigate factual gaps;
   bring unresolved human choices to the decision owner. Otherwise continue
   on a visible, reversible assumption.
3. Establish scope, responsibility, and affected interfaces. Record what is
   inside, outside, unknown, reversible, and deliberately left open, together
   with the decisions and their owners.
4. Write a concise plan brief: the desired outcome plus the problem,
   invariants, constraints, non-goals, and success signals that matter. Keep
   solution preferences separate from the problem being solved.
5. Decompose by coherent outcomes and capabilities. Specify interfaces,
   prerequisites, deliverables, acceptance, and expected evidence. Hierarchy
   describes what work belongs to; dependencies describe what must precede it.
6. Preserve desired qualities when acceptable implementations can differ in
   character. Keep them separate from acceptance tests; use a metric only
   when it meaningfully represents the quality.
7. Review perspectives that could change the plan. Incorporate findings into
   its source record. Compare alternatives only when a consequential choice
   remains, with a shared baseline, budget, and stopping condition.
8. Hand off a plan with traceable decisions, implementation or activity
   targets, acceptance criteria, and completion-evidence expectations.

The steps describe what a complete plan accounts for, not a pass to execute
once. Decomposition, comparison, and review can show that the scope or the
outcome was misread; revise it rather than defend the first reading.
Interpretations that imply different goals are not alternatives to compare:
agree on the outcome before comparing ways to reach it.

## Repository-local Plan Graph

Inspect applicable `AGENTS.md` files and existing planning tools. Follow a
compatible local contract and its validation commands. Do not impose this
skill's schema on other planning systems.

When the user asks to establish or upgrade planning infrastructure, follow the
[installation procedure](references/plan-graph.md#installation-and-removal).
Include the governance fragment (`assets/plan-graph/AGENTS.plan-management.md`,
added by the installer's `--update-agents` option) when that request includes
adopting project planning rules and no equivalent local contract exists.
Existing authorization continues to apply; do not ask again for routine steps
within that scope. The installer supports preview, conflict checks, and
ownership-based removal.

## Working principles

- Keep one editable source for each decision; generate indexes and views.
- Ask for judgments the person can make, not for endorsement of technical
  reasoning they cannot assess. Decide reversible technical choices yourself,
  record why, and report what they rest on.
- Ask questions only when the answer can change the plan, and ask the most
  consequential one first, naming what you are deferring; batch only choices
  that cannot be judged apart. Use whatever channel the environment offers.
  When interactive prompts are disabled, ask in plain conversational text and
  pause for the answer. Readiness is relative to the next commitment, so a
  bounded discovery task can proceed before the larger design is settled.
- Preserve constraints, provenance, and people's choices when shortening prose.
- Add context, qualities, perspectives, or alternatives independently when
  useful; do not fill fields merely to complete a template.
- Keep influential rejected alternatives and the reasons for resolving them.
  End comparison when further exploration cannot change the decision.
