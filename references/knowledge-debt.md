# Knowledge debt

Read this reference when a person cannot independently evaluate a technical
recommendation that affects their work, or asks for a gap to be recorded.

## What a knowledge debt is

A technical concept, rationale, premise, or doubt influences a real choice; the
person cannot verify it yet; and they do not want to learn it before reversible
work continues. Record the gap, the decision it touches, the evidence behind it,
and what would make it matter again.

This is not a claim that the recommendation is untrustworthy, and not a
deficiency in the person. It is permission to defer understanding without
manufacturing the appearance of shared understanding.

## What it is not

- **Not a substitute for evidence.** A missing test is a verification task.
  Noting the gap does not discharge it.
- **Not an authorization.** A recorded gap never widens the scope of what may be
  done, and never upgrades provisional work to production.
- **Not a glossary.** Do not create a file per unfamiliar term, and do not turn
  an admission of not-knowing into a curriculum.
- **Not a gate.** Nothing requires the debt to be settled before reversible work
  continues.

## Four things that must not be confused

| Kind | Question it asks |
|---|---|
| Concept | What is this thing? |
| Reasoning gap | Why does this approach serve the goal better? |
| Comparison gap | Why this one rather than that one? |
| Evidence gap | Has anyone actually shown that it works? |

One concept underlies several decisions, and one decision rests on several
concepts. A gap does not invalidate a decision, and missing evidence is not
repaired by recording it.

## Capture on request, revisit on trigger

Capture when the person says they do not understand something that matters, or
asks for it to be written down. Do not infer ignorance, and do not build a term
inventory unasked.

One exception: a choice that constrains the future may be recorded without being
asked about, when the person has not claimed to understand it. Record those, and
no others.

Reopen the record when the person asks, when the concept becomes a major premise
again, when new evidence contradicts the earlier judgement, when the scope or
risk grows, or when reversible work is about to become a production commitment.

## Acceptance has three modes

- **Informed acceptance** — the trade-offs were understood and accepted.
- **Provisional acceptance** — the consequences were partly understood; the
  person authorized reversible progress inside a stated scope and is relying on
  the agent's reasoning for the rest.
- **Unsupported assent** — agreement given without the information needed to
  judge it. Record it as such; never present it as reviewed.

Absence of objection is none of these. Authorization must be given, not inferred
from silence. It can be given once for a defined scope, which is how reversible
work proceeds without asking at every step; what silence cannot do is extend
that scope.

## Reporting technical choices

Two different situations arise when a round of work introduces unfamiliar
technology, and they carry opposite defaults.

**Inside an authorization already granted** — continue and report. Do not ask
for the same permission twice. State what the work rests on:

- the technical choices that shape the result, and what each costs if it turns
  out wrong;
- the boundary the authorization covers — reversible, local, no external
  effect, no production data;
- what falls outside that boundary, and would need a separate grant.

**Opening a new scope** — ask once, explicitly. Silence is not a grant.

### List the choices, then sort comprehension

When a round introduces technology the person will have to live with, list it
before continuing, and ask them to sort it rather than approve it:

1. **Understood and agreed** — informed acceptance.
2. **Understood and disagreed** — say why; the approach changes.
3. **Not understood, proceed anyway** — provisional acceptance, plus a
   knowledge debt.

Offer all three per item, one line each. These two questions may share a round:
what the person understands, and whether to begin. Neither reframes the other.

Cap the list at three to five items, and choose them by one test: would the
approach change if the person disagreed? Report consequences, not mechanisms —
lock-in, migration cost, operating burden. A long list of unfamiliar techniques
is not information; it is a decision the person was never equipped to make, and
a list nobody reads makes every recorded acceptance meaningless.

Comprehension may default downward; authorization never defaults upward. After
the person says to begin, anything left unsorted is recorded as not claimed as
understood and treated as provisional. Before they say so, nothing proceeds and
nothing is recorded as accepted.

Ask once per batch, not per item, whether any of it should be written down.
Offer; do not diagnose, and do not turn the batch into a curriculum.

## Recording

Prefer the project's existing glossary, ADRs, or decision records. Create a
directory only when none exists and the person agrees. Name it for the debt,
not for knowledge: these records hold gaps, and a `knowledge/` directory invites
the glossary this rule exists to prevent.

```text
_aiHumanInteract/
  knowledge-debt/
    <topic>.md
```

Keep each record short, and link it from the governing decision record so the
path runs both ways: from a choice to the gap behind it, and from a gap to the
choice that depended on it. The decision record remains the single authoritative
source for the decision; the knowledge record explains what is not yet understood
about it.

```markdown
# <topic>

**Understanding gap:** what is not understood, in the person's own words.
**Agent explanation:** a summary of the reasoning. Not independent verification.
**Related decision:** a link to the decision record that depends on it.
**Current treatment:** what is being done while the gap stays open.
**Scope:** what this covers, and what it explicitly does not.
**Revisit when:** the trigger that would make this matter again.
**Evidence needed:** the test or reference that would settle it.
```

Do not copy the decision's rationale into the knowledge record; a second copy
will drift. Link instead.
