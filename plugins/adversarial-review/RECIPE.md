# The review recipe

A harness-neutral description of narrow-charter code review. The executable
version, with concrete tool names, is `skills/review-recipe/SKILL.md`, and that
one is canonical when the two disagree.

Use this when correctness matters more than style and a wrong-shape change would
be expensive to walk back. Skip it for style-only changes, comment fixes,
documentation rewrites, and refactors that move code without changing behaviour.

## The problem it solves

"Review this diff for bugs" returns style nits, missing tests, and comment
quality. It misses the correctness bugs the diff is structurally exposed to,
because nothing in the charter asks the reviewer to verify a specific guarantee.

Two patterns fix that.

**One agent, one invariant, one verdict.** Hand a reviewer a single property the
change must preserve, ask it to construct adversarial cases against that
property, and take a yes or no.

**Tests audited against the spec, not against the code.** A test whose
assertions were derived from observed behaviour locks that behaviour in, bugs
included. The useful question is "construct a code path where this test passes
but the specification is violated".

## Requirements

A harness that can run several reviewers in parallel, each with its own charter,
each able to read the repository and run builds or tests. Per-reviewer model
selection helps but is not required. Isolated working trees are required if more
than one reviewer can write.

## The passes

Not all of these apply to every change. Scale to the diff: a one-line fix needs
none of the added gates.

**Gather.** The diff, the touched paths, the project's own conventions, and the
author's stated intent.

**Name the invariants.** One to four, each a sentence, each with an example of
what would violate it. The example matters because it constrains the search. If
you cannot name one invariant, stop and ask. "General correctness" is the charter
this method exists to replace.

**Correctness, one reviewer per invariant.** Each constructs concrete violating
inputs, cites the lines they would land on, and distinguishes "definitely
violates" from "cannot tell". Any violation is a stop-and-report.

**Double the hardest invariant.** For hostile input, concurrency, memory model,
ABI or layout, crypto, or anything expensive to walk back, run the same charter
on two different models and compare. Agreement is the signal. Disagreement means
read the cited path yourself.

**Test design.** For each test the diff adds, construct a buggy implementation
that the test would still pass. Also ask what the test had to touch in order to
run: a fake that exists only to expose internals, a log line read as a channel,
an assertion on state left behind by a call that failed. Those are design
findings, not test findings. Name the missing seam.

**Verification surface.** For each high-risk area the diff touches, ask whether
the tests include something that would catch wrong behaviour at runtime, rather
than only a static or shape check.

**Reinvention.** For each helper, constant, or table the diff adds, search for
the primitive that already does it. Report duplicate, near-miss, or novel with
the search trail so the gap is auditable.

**Design and ownership.** One reviewer whose whole job is to argue the change
should not land as written: that it duplicates a responsibility another component
owns, belongs somewhere else, or reinvents a schema instead of reusing the source
of truth. Do not let its own justification stand as the answer.

**Module boundaries.** Only if the diff adds a dependency edge, widens
visibility, or places a type across a boundary.

**Interface shape.** For each function or type added, and each signature changed:
out-parameters where a return would do, absence encoded as a sentinel, a boolean
whose name does not say which way is true, a function returning less than its only
caller needs. An interface that is safe only because today's callers avoid the
wrong path is a finding.

**Local idiom.** Compare each new declaration against its immediate neighbours
rather than against a written style guide. Most conventions in a mature tree are
written down nowhere; they live in the lines next to the change. Then read the
history of the touched files for feedback the same maintainer has already given.

**Prose.** The one style pass. Does each added comment earn its place, and can a
reader who is new to the code and not a native English speaker understand it.
Comment slop is the most reliable sign of machine authorship and the cheapest
thing to fix.

## The bar

Any one of these blocks approval: a correctness violation; a behaviour-bearing
change with no test on the changed path; a change that duplicates or misplaces a
responsibility another component owns; a broken module boundary; an interface
that only yields what a caller needs by reading state after a failed call; a
change whose scale outran any written, agreed design.

A clean correctness pass is never on its own an approval. Report correctness and
approvability separately, and never write "safe to ship" from invariants alone.

## Craft is the deliverable, not a bonus

A change can be correct, well placed, and inside its module, and still cost the
author three rounds of review over interface shape, local convention, and test
scaffolding.

Measured on one real pull request: across two review rounds a maintainer raised
fourteen comments and none was a correctness defect. Three were interface shape,
five test maintainability, three local convention, two scope.

A pass tuned only to find what is wrong will systematically under-report what is
merely worse than it should be, and that is what generates the rounds.

## After a human review round

Enumerate the comments from the API, never from memory and never from a guessed
time window. A query bounded by a guess silently drops comments.

Then turn each comment into a rule and sweep the whole diff for other instances.
A reviewer points at the line they happened to read; the same mistake is usually
elsewhere in the same change.

Check the fix against the rule the reviewer just stated. Code written to satisfy
a review comment is the likeliest place to break the same principle again, and
new test code is the likeliest of all.

## Machine-generated changes get a stricter bar

When the change is machine-generated, especially from another team, treat the
description and every comment as an unverified claim. The missing-test gate stops
being negotiable, the design gate becomes mandatory, and a single reviewer saying
"justified" is never sufficient. Models produce confident justifications for
weak code, and a model reviewer will accept them unless told to attack them.
