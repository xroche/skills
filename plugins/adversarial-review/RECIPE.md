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

Two techniques inside those patterns produced most of the signal. The doubling
pass below holds the mechanics of the first, and the test-necessity pass holds
the second.

**Double one invariant across two models.** Agreement between two models is
itself the evidence, because two models rarely rationalise the same broken path.

**Build a mutation matrix over the clauses of one guard.** The off-diagonal
passes are the payload, because they prove that each test fails for its own
clause and that no test stands in for another test's coverage.

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

**Legibility, first.** Read each file the change adds or grows, whole, the way
its next maintainer will, rather than hunk by hunk. Ask whether each name
carries the distinction it exists to express, whether each argument's meaning is
guessable at the call site, and whether a doc comment gives a caller the
contract inside about ten lines plus one line for each parameter and return
value. Count what a reader must hold at the file's worst line, meaning live
variables, in-flight state and locally defined helper contracts, where six or
more is a finding. A block you had to read twice is a finding whatever its
sentence lengths.

This pass goes first because it gates the value of every pass after it. A change
a maintainer cannot follow does not get reviewed. It gets skimmed, approved on
trust, or left to rot, and the correctness passes then certify code nobody can
change safely. Use the strongest model available, because this simulates a
reader's comprehension rather than matching a rule list. Name the single edit
that buys the most comprehension per line changed, and let that one block.

**A witness for each addition.** Every other charter proves the change preserves
an invariant. An element that does nothing preserves every invariant, so it is
invisible to all of them. For each guard, branch, bound, parameter, config
value, handler, log line, assertion, wait, fixture or comment the change adds,
produce the concrete input, state, caller or reader under which it changes an
outcome. Report it as witnessed, dead, unresolvable, or cannot-decide, and say
where you stopped. Skip the pass on a change that only edits existing logic.

A dead element inside a test blocks, because an assertion that cannot fail or a
wait already satisfied at entry makes a test report coverage that does not
exist. Asking whether an element is correct can never answer whether it is
needed.

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

**Test necessity.** More tests do not mean a better change. Every other pass
pushes toward adding a test, and none of them asks whether the set that came out
earns its size. Enumerate every test the change adds, across every file at once
rather than file by file, counting each row of a table as a test. Name the
mutation that turns each one red, then record every test that same mutation
turns red. Two tests dying to the same mutation set are one test wearing two
names. One set contained in another is redundant unless you can name a mutation
only it catches.

Two exceptions survive that rule. A test whose mutation set is empty still earns
its place when it pins a precondition the new code relies on, and the simplest
case in a table still earns its place when a reader uses it to read the rest.

State the invariant that makes each fold safe, because every mutation that
turned some test red before the fold must still turn some test red after it.
Refuse any fold that buys its lower count by widening an assertion, for example
a specific error becoming any error. That trades coverage for tidiness, and a
test count does not show it.

**Verification surface.** For each high-risk area the diff touches, ask whether
the tests include something that would catch wrong behaviour at runtime, rather
than only a static or shape check.

**Reinvention.** For each helper, constant, or table the diff adds, search for
the primitive that already does it. Report duplicate, near-miss, or novel with
the search trail so the gap is auditable.

**Design and ownership.** One reviewer whose whole job is to argue the change
should not land as written: that it duplicates a responsibility another component
owns, belongs somewhere else, or reinvents a schema instead of reusing the source
of truth. A dump written for a person to read is still a schema once a program
parses it, so count it. Do not let its own justification stand as the answer.

Two questions belong here. Is the fix in the right repository and layer? Ask
whether the change would be deleted once the upstream defect is fixed, because
an answer of yes makes it a mitigation rather than a fix, and a mitigation says
so and names an upstream ticket somebody has checked exists. Ask it per defect
and not per file, because most consumer-side fixes are real fixes. Then, who
produces the input the change parses, and can we change them? A parser's
complexity should be inversely proportional to that control, so text from a
program in the same organisation earns a machine-readable mode in the producer
rather than a parser in the consumer. When the format also carries data the
producer does not control, the parser is an injection surface and it blocks.

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

**Scope.** The craft passes above push one way. Interface shape asks for a type
where an out-parameter sits, legibility asks for a name where a bare literal
sits, and both add named entities, so something has to push back. Read the
requirement from the ticket, then walk the change hunk by hunk and judge scope
against that requirement rather than against taste.

Report the hunks the requirement does not need, the renames and moves the
feature did not have to make, each abstraction whose only call site arrives in
the same change, and the generality nothing asked for. Count the named entities
introduced against the number the requirement needs, and state in lines the
smallest change that delivers the same behaviour. Report what to delete, never a
replacement design, because proposing one is the failure mode this pass exists
to catch.

Where this pass contradicts interface shape or legibility, the smaller change
wins, unless the flagged shape is a correctness hazard rather than a taste
question. Say which craft finding was traded away.

**Prose.** The one style pass. Does each added comment earn its place, and can a
reader who is new to the code and not a native English speaker understand it.
Comment slop is the most reliable sign of machine authorship and the cheapest
thing to fix.

## The bar

Any one of these blocks approval:

- the named highest-value legibility edit, where the change introduced or
  worsened the problem
- a dead element inside a test
- a correctness violation
- a behaviour-bearing change with no test on the changed path
- a change that duplicates or misplaces a responsibility another component owns
- a mitigation for a defect upstream that neither says so nor names an upstream
  ticket somebody has checked exists
- a hand-written parser for a format one of our own programs produces, where
  that format also carries untrusted data
- a broken module boundary
- an interface that only yields what a caller needs by reading state after a
  failed call
- a change whose scale outran any written, agreed design
- a hunk the stated requirement does not need, or a change whose product lines
  run more than roughly twice the smallest version that would deliver the same
  behaviour
- unfixed comment slop or a padded description, on a self-review of your own
  change

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

A construct added because a reviewer or an earlier round asked for it gets the
same audit as any other line. That a review suggested it is a provenance, not
evidence, and it is exactly where an element that does nothing hides.

A round that changes the test harness re-opens every test an earlier round
added. A round often adds a test to work around something the harness cannot
see, and a later round fixes the harness itself. The workaround is dead from
that moment, and nothing looks at it again, because a cleared list is a cache
with no invalidation rule. So put those tests back through the necessity pass.

## Two traps that no charter catches

Neither of these is a defect in the change under review, so no pass above finds
them, and both nearly shipped something wrong.

**A tool that opens a pull request can succeed when the push did not.** The
request then shows stale code while you believe it shows the change you just
reviewed. Compare the pushed head against the local head before you trust what
a pull request contains.

**Never relay a reviewer's finding as fact without checking it.** One charter
reported a test making a real network call, and the mock was in fact registered
and intercepting it. Another reported an unpushed commit, and what it had
misread was a rebase. Read the cited lines yourself before a finding leaves the
session.

## Machine-generated changes get a stricter bar

When the change is machine-generated, especially from another team, treat the
description and every comment as an unverified claim. The missing-test gate stops
being negotiable, the design gate becomes mandatory, and a single reviewer saying
"justified" is never sufficient. Models produce confident justifications for
weak code, and a model reviewer will accept them unless told to attack them.
