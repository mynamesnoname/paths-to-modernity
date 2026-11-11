# Human inquiry and boundary formation

Read this reference when ambiguity could materially change what a successful
outcome would mean, who or what the plan is responsible for, which harms or
costs are acceptable, which person or role has authority to decide, or whether
an irreversible commitment is justified.
The aim is sufficient shared orientation for the next responsible step, not the
elimination of every uncertainty.

## Clarify choices before writing the plan

A polished summary can conceal an unmade decision. Form the plan brief
after distinguishing facts the agent can discover from meanings,
decisions, and obligations that only a person can authorize. Treat the person's
wording, hesitation, refusal, emphasis, and desired character as evidence of
direction without pretending that any single phrase is already a complete
specification.

The agent contributes attention, synthesis, alternatives, and consequence
mapping. The person retains choices about value, responsibility, acceptable
risk, and irreversible scope. Neither party should be reduced to a form field.

## Diagnose the ambiguity

Classify only the uncertainties that could change the plan:

| Kind                 | Typical question                                      | Default treatment                                               |
| -------------------- | ----------------------------------------------------- | --------------------------------------------------------------- |
| Evidence gap         | What is true in the code, system, or world?           | Inspect, measure, or create a discovery task.                   |
| Intent gap           | Which outcome or quality actually matters?            | Ask the person; do not infer a preference from convenience.     |
| Boundary gap         | Does adjacent responsibility belong inside this plan? | Render a small set of boundaries and their consequences.        |
| Authority gap        | Who may accept this cost, risk, or external effect?   | Identify the decision owner before commitment.                  |
| Productive ambiguity | Which openness carries the desired character?         | Preserve it in the desired qualities and tradeoffs until resolution is useful. |

Do not ask the person to answer questions that repository inspection, available
tools, or ordinary professional inference can settle safely. Do not treat a
reversible implementation detail as a strategic dilemma.

Use this threshold: ambiguity is **material** when two reasonable
interpretations would change the outcome, responsibility, acceptance,
meaningful risk, or an irreversible commitment.
For example, whether a plan owns detection only or detection plus recovery is
material; the provisional name of a reversible internal file normally is not.
If evidence can settle the difference, investigate it. If it cannot and the
difference crosses this threshold, ask the decision owner. Otherwise state the
reversible assumption and continue.

A **decision owner** is the person or role authorized to make a choice and
accept responsibility for its consequences. The current user may identify that
owner without necessarily being that owner.

Use precise boundary terms: **scope** says which outcomes are included;
**responsibility** says who owns decisions and consequences; **interfaces**
describe interactions with people or systems outside that ownership.

## Inquiry loop

This loop is the detailed form of steps 2–4 of the planning workflow in
[SKILL.md](../SKILL.md).

The four steps describe what has to happen, not an order that runs once. Treat
them as a control loop: observe, interpret, resolve or preserve, assess
readiness, and then either advance or reopen what the answer just undermined.
Decomposition, comparison, and review routinely show that the first reading of
the scope or the outcome was wrong. Returning to an earlier step is the loop
working, not the loop failing.

### 1. Observe before asking

Read the raw request, applicable instructions, existing plans, relevant code,
and decision history. Separate direct evidence, reasonable inference, and
unknowns. Notice contradictions and emotionally or normatively weighted words;
they often indicate a boundary or quality rather than a technical requirement.

### 2. Offer a provisional reading

Demonstrate understanding before requesting labor from the person:

```text
My current reading is that the desired change is A because B. I am treating C
as outside the plan for now. The material uncertainty is whether D belongs
inside the responsibility boundary.
```

Make assumptions visible. A provisional reading is revisable and must not be
presented as a decision already made.

### 3. Render the smallest meaningful contrast

#### Before asking: whose information is this?

Materiality says a question is worth asking. It does not say the person is the
one who can answer it. Sort the question first:

| Kind of question | What to do |
|---|---|
| A fact the code, data, or tools can settle | Find it; do not outsource it |
| A reversible technical choice inside an already granted scope | Decide it, record why, and report it |
| A question of intent, value, experience, or acceptable responsibility | Ask the decision owner |
| A technical claim that lacks evidence | Design a test or prototype, not a vote |

Then translate. A question earns a human answer only if the answer supplies
something the agent cannot obtain: what the person wants, what they will accept,
or who bears the consequence. If the answer would only ratify the agent's own
reasoning, no question has been found — only a decision the agent should be
taking itself.

Compare: "Should we use event sourcing for auditable recovery?" asks for a
verdict on a mechanism. "Do you need to replay past state and trace who changed
what, and is a migration cost acceptable?" asks for an outcome. Someone who has
never heard of event sourcing can answer the second, and it still carries the
whole decision.

When the target project already governs this kind of choice, and an existing
pattern with its tests answers the question, do not make the person pick between
equivalent libraries.

When a human answer is genuinely needed but the person cannot yet evaluate it,
[knowledge debt](knowledge-debt.md) describes how to record the gap and keep
reversible work moving without pretending the gap is closed.

A grant to proceed and an understanding of what will be done are two questions
with opposite defaults: permission must be given, while an unclaimed
understanding may be recorded as absent. Silence can supply the second, never
the first.

When a human choice is necessary, show two or three materially different
boundaries, not a catalogue of possibilities. For each one state the consequence
that matters: responsibility, affected or excluded people, operational burden,
reversibility, cost, risk, or preserved quality. Recommend an option when
evidence supports one, while keeping the decision genuinely open.

Prefer a focused question such as:

```text
I recommend keeping C outside because including it makes this team responsible
for recovery as well as detection. Should this plan own detection only, or the
full recovery loop?
```

Avoid `Please clarify the requirements`, long questionnaires, and questions
whose answers would not alter scope, invariants, acceptance, sequencing, or
authorization. Ask the single highest-leverage question, and say what you are
deferring and why this one comes first: a person who can see the queue is not
ambushed by it later. Put at most two questions in one round, and only when
neither can be judged without seeing the other. A numbered list of
recommendations invites agreement, not deliberation.

Deliver the question through whatever channel the environment provides. When
interactive question tools are disabled or unavailable — for example in
autonomous or auto-approval modes — present the contrast as plain
conversational text, end the turn, and wait for the person's answer. A missing
structured channel never converts a human-owned choice into an agent
assumption; only genuinely reversible assumptions may proceed without an
answer.

#### Keep a material decision frontier

Hold, in working memory rather than in a file, the unresolved choices that could
still change the next responsible commitment. For each, know its consequence,
what must be settled before it can be asked, and whose decision it is.

Recompute after every answer. Some choices unblock, some are reframed, some
vanish because the answer changed what the plan is about. Ask only what is
answerable now, and resolve the factual prerequisites yourself rather than
handing them to the person.

Do not persist this set. Frontier structure and question dependencies are
scaffolding for one conversation; written down, they become a second planning
graph that no validator checks. Persist the decisions and the residue of open
questions instead, as the next step describes.

#### Interpretive variants are not alternatives

A contrast can be about meaning. The same words may name different outcomes:
"faster" can mean lower latency, higher throughput, or less human review, and
those are three goals rather than three routes to one goal. Present them to
discover what is meant; do not score them against a shared baseline, because
they do not have one yet.

Once the outcome is agreed, choosing between ways to reach it is a different act
under different rules; see [alternatives](alternatives.md).

### 4. Record the chosen boundary and the residue

Capture:

- **inside** — what this plan promises to change;
- **outside** — nearby work it deliberately refuses;
- **interfaces** — affected people, systems, contracts, and handoffs not owned;
- **unknowns** — unresolved facts and how they will be discovered;
- **decision owners** — who can close each value or authority question;
- **reversibility** — which assumptions may safely remain provisional;
- **retained ambiguity** — qualities or tradeoffs intentionally left open;
- **decisions** — the chosen boundary, rationale, accepted cost, and date.

Preserve this in the project's requirement or decision record and link it
from the governing plan when the target planning system supports traceability.
Record the resulting non-goals and invariants in the plan brief. Do not
copy the entire conversation into every plan item.

## Readiness gate

A plan is ready for its next responsible commitment only when:

- the intended outcome is intelligible enough to distinguish success from mere
  production of deliverables;
- hard invariants and material non-goals are visible;
- the inside/outside boundary and affected interfaces are sufficient for the
  next commitment;
- no value, authority, responsibility, or irreversible choice has been silently
  made by the agent;
- remaining evidence gaps have an owner and a discovery or validation path;
- retained experiential ambiguity is represented as a quality or open tradeoff
  rather than falsely converted into acceptance evidence.

In a system with an explicit status lifecycle, passing this gate moves a
governing plan from `proposed` to `ready`; see the Plan Graph lifecycle in
[plan-graph.md](plan-graph.md#relationships-and-lifecycle).

Readiness is proportional to the next action. Do not demand architectural
certainty before a reversible experiment. Conversely, do not use a provisional
assumption to cross an irreversible boundary.

If the gate fails:

- keep the plan provisional when the shape of the work remains negotiable;
- create a bounded discovery work package only when the investigation itself
  has a known objective, deliverable, and acceptance criterion;
- ask the decision owner when the missing fact is actually a value or
  authority decision in disguise;
- identify the exact commitment that cannot responsibly proceed.

## Handoff

Inquiry produces a working boundary and durable decisions; it does not
prescribe a storage schema. Hand those results to the target project's planning
model, using [the planning model](model.md) when a structure is needed.
Use [alternatives](alternatives.md) only after they share the same human-confirmed
outcome and invariants. Do not copy conversational states into every plan item
or mistake a polished transcript for an executable plan.
