# The counter-check

A harness-neutral description of adversarial verification before sending. The
executable version is `skills/counter-check/SKILL.md`, and that one is canonical
when the two disagree.

Run it on anything that is about to spend someone else's attention: a pull
request, an issue report, a reply to a maintainer, a bug filed against someone
else's project, a design note, or a draft about to be shown for approval.

`RECIPE.md` attacks a diff. This attacks a document, and the claims inside it.

## The problem it solves

A draft written by a model is confident in proportion to its fluency, not its
correctness. The failure mode is not sloppy prose. It is a claim that reads as
established, sits in the right register, cites a real file and a real line, and
is wrong.

Measured across two sessions on one project: essentially every *argument* in a
set of drafted notes was refuted or narrowed, while essentially every
*measurement* survived. Explanations, mechanisms and proposed fixes were wrong
at a high rate. Numbers taken from a compiler or a test run were almost always
right.

That asymmetry is the whole design. Attack the reasoning and keep the data.

## The mechanism

**Enumerate the load-bearing claims first.** A claim is load-bearing if the
artifact would have to change when it turns out to be false. Skip the rest. Three
reviewers on the three claims that matter beats ten on everything.

**One reviewer per claim, charged to refute it.** Told to default to "wrong" or
"overstated" on thin evidence, and to say so plainly when it cannot break the
claim. A charter that says "verify" gets verification.

**Verify by building and measuring, not by reading.** Reading the code and
reasoning about it is how the wrong explanation got written in the first place.
For a claim about a test, construct a fake fix and check whether the test still
passes; a test a fake fix satisfies is a weak test.

**Pre-empt the obvious rebuttal.** If a finding rests on an unusual
configuration, a flag or a platform, prove that configuration is supported before
reporting it. "That configuration is not supported" is the cheapest way for a
report to die.

**Separate measurements from inferences.** State measurements plainly, mark
reads and guesses as such, and do not hedge a reproduction that ran identically
on two toolchains. Watch specifically for a number that measures one thing being
offered as evidence for another.

**Record verdicts.** Confirmed, narrowed or refuted per claim, plus a list of
what did not survive, so a later session does not revive it.

## Doubling

For the one or two claims whose failure would be most expensive, run the same
charter on two different models and compare. Independent agreement is much
stronger than one reviewer, because a single model can rationalise a broken path
and two rarely rationalise the same one. Disagreement is inconclusive: do not
average, read the cited path yourself, and prefer the more conservative verdict.

Do not double a mechanical claim.

## Isolation

Never give more than one write-capable reviewer the same working tree. Two
reviewers with permission to build will edit it concurrently, each will end up
reviewing the other's prototype, and the findings become unusable. Run them
read-only, explicitly forbidding builds and any working-tree or branch changes,
or give each its own tree.

Where reviewers need to compare a patched build against an unpatched one, build
both yourself and hand them the binaries. They then need no build at all, and the
comparison is reproducible.

Sweep for orphaned processes after any batch that builds or runs tests.

## Verify the setup of a negative check

A check reporting "this fails without the fix" may be testing the fixed code.
Expect the specific failure, and treat its absence as a reason to doubt the
harness before doubting the finding. The same applies to any comparison across
configurations: confirm the knob you are varying is the one that changed, and
that nothing upstream pins it.

## What good output looks like

A short list of claims, each with a verdict and its evidence, and for anything
refuted, the narrower statement that is actually true. Then the edits that
follow.

If a draft loses its central argument, that is a success. The cost of finding out
here is a few reviewer runs. The cost of finding out after sending is the
credibility of everything else in the document.
