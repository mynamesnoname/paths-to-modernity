# Controlled plan alternatives

Read this reference only when the user requests alternatives or when a
consequential design uncertainty cannot be resolved through ordinary analysis.
An alternative is a different approach to a shared outcome, with a comparison
that can change the decision.

This reference begins after the outcome is settled. If the disagreement is about
which outcome is meant — such as what "faster" or "simpler" in user requests actually refers to — those
are interpretive variants, not alternatives, and they have no shared baseline to
compare against. Resolve them with [inquiry](inquiry.md) first, then return here.

## Admission test

Create alternatives only when all of the following hold:

- the alternatives serve the same canonical outcome and invariants;
- they can be evaluated against the same evidence or scenario;
- they differ in a named approach or responsibility boundary;
- choosing between them would materially change implementation or risk;
- the comparison has an explicit budget and decision point.

If the alternatives have different outcomes, they are separate plans. If one
alternative merely adds detail, it is decomposition. If both can be combined
without tension, synthesize them instead of manufacturing a contest.

## Minimal alternative contract

This is a conceptual comparison record, not strict node front matter:

```yaml
alternative_of: "stable canonical plan identifier"
approach: "the meaningful difference"
shared:
  - "source requirement"
  - "outcome and invariants"
  - "evaluation baseline"
evaluation:
  - "criteria and evidence to compare"
stop_when: "condition that ends exploration"
```

Keep the canonical plan and alternatives under the same planning scope when the
target project's model supports hierarchy; the Plan Graph contract requires
sibling work packages. Alternative and supersession relationships should be
acyclic.

For repository-local storage, use the [Plan Graph contract](plan-graph.md).
Keep the shared evaluation baseline, budget, and stopping rule in a linked
evaluation or Decisions record; do not add these conceptual keys to node
front matter.

## Compare fairly

Use criteria derived from the plan brief rather than preferences
discovered after seeing results. A compact comparison usually covers:

| Dimension | Question |
|---|---|
| Outcome fit | Does it achieve the same intended result? |
| Invariants | Which invariants are protected or endangered? |
| Evidence | Can the claim be tested with the shared baseline? |
| Reversibility | How difficult is retreat or migration? |
| Complexity | What permanent conceptual or operational cost is added? |
| Qualities | What desired character is preserved or lost? |
| Failure modes | What does this approach make newly possible to fail? |

Do not average away a hard invariant. An alternative that violates one is
inadmissible regardless of its aggregate score.

## Resolve the comparison

End with one of three outcomes:

- **select** one alternative and record why;
- **synthesize** compatible parts into a new canonical design;
- **defer** only when a named missing fact prevents a responsible decision.

Preserve a rejected alternative when it affected the decision. Mark it with the
target project's resolved or superseded status, identify its successor, retain
the comparison evidence, and remove it from active execution queues. Do not
delete the history or leave rejected alternatives looking like unfinished work.

## Stop conditions

Stop generating alternatives when one admissible option clearly dominates,
the comparison budget is exhausted, additional alternatives repeat existing
approaches, or the remaining uncertainty requires implementation evidence
rather than more planning.
