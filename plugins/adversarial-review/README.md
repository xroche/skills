# adversarial-review

Two Claude Code skills.

**`/review-recipe <PR or branch> [-- invariant ...]`** reviews a diff. It names
the invariants the change must preserve, gives each to its own reviewer, and asks
each to construct violations rather than to look for problems. It then runs the
passes that catch what is not a bug but still costs review rounds: test design,
interface shape, local convention, module boundaries, reinvention, and whether
the change needed a written design before it was written.

**`/counter-check <draft>`** reviews a document before it is sent. It enumerates
the load-bearing claims, gives each to a reviewer charged to refute it, requires
that anything measurable be measured rather than read, and records what did not
survive.

## Reading order

`RECIPE.md` and `COUNTER-CHECK.md` are harness-neutral write-ups of both ideas.
`skills/review-recipe/SKILL.md` and `skills/counter-check/SKILL.md` are what
Claude Code actually executes, and they win where the two disagree.

## The two rules that make it work

**Charge the reviewer to refute, not to check.** "Verify this" gets
verification. "Default to wrong or overstated on thin evidence" gets the
counterexample.

**Break the check on purpose before trusting a clean run.** A harness that
cannot fail is not evidence. This applies to the review itself: a discrimination
check reporting "fails without the fix" may be testing the fixed code.

## Cost

Real. A thorough run is several parallel subagents, each reading code and often
building. Use it where a wrong-shape change is more expensive than a slow review,
and skip it for style, comments, docs, and behaviour-preserving refactors.
