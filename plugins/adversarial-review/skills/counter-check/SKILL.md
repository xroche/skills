---
name: counter-check
description: Adversarially verify an artifact before it leaves. One agent per claim, each charged to refute it, verifying by building and measuring rather than by reading. Use before any push, issue report, review reply, or draft shown for approval.
user-invocable: true
argument-hint: <path to draft, or a description of what is about to be sent>
---

# Counter-check

Run this on anything that is about to spend someone else's attention: a pull
request, an issue report, a reply to a maintainer, a bug report against someone
else's project, a design note, or a draft you are about to show for approval.

It is the sibling of `review-recipe`. That one attacks a diff. This one attacks
a document, and the claims inside it.

Given a path, work on that file. Given a description, work on what it names.
Given nothing, work on the most recent draft in the conversation, and say which
artifact you picked before starting so a wrong guess is cheap to correct.

## Why this exists

A draft written by a model is confident in proportion to how fluent it is, not
how correct it is. The failure mode is not sloppy prose. It is a claim that
reads as established, is stated in the right register, cites a real file and a
real line, and is wrong.

Measured on one project over two sessions: essentially every *argument* in a set
of drafted notes was refuted or narrowed, while essentially every *measurement*
survived. The pattern repeated across unrelated artifacts. Explanations,
mechanisms, and proposed fixes were wrong at a high rate. Numbers taken from a
compiler or a test run were almost always right.

That asymmetry is the whole design. Attack the reasoning, keep the data.

## The mechanism

Not "review this draft". A generic charter returns generic findings.

### 1. One agent per claim

Enumerate the load-bearing claims first. A claim is load-bearing if the artifact
would have to change when it turns out to be false. Give each agent exactly one,
stated as a sentence it can try to break.

Skip the claims that carry nothing. Three agents on the three claims that matter
beats ten on everything.

### 2. Charge each agent to refute

Tell it to default to "wrong" or "overstated" on thin evidence, and to say so
plainly when it cannot break the claim. Confirmation bias is the failure mode
being defended against, so a charter that says "verify" gets verification.

### 3. Verify by building and measuring, not by reading

Wherever a claim admits it, the agent must compile, run, or measure. Reading the
code and reasoning about it is how the wrong explanation got written in the first
place.

For a claim about a test, have the agent construct a fake fix and check whether
the test still passes. A test that a fake fix satisfies is a weak test.

### 4. Pre-empt the obvious rebuttal

If a finding rests on an unusual build configuration, a flag, or a
platform, prove that configuration is supported before reporting it. "That
configuration is not supported" is the cheapest way for a report to die.

### 5. Separate measurements from inferences

State measurements plainly. Mark reads and guesses as such. Do not hedge a
reproduction that ran identically on two toolchains; false modesty makes a report
easier to dismiss.

Watch specifically for a number that measures one thing being used as evidence
for another. A speedup that comes from vectorizing at all is not evidence about
the specific gate you are proposing to change.

### 6. Record verdicts

CONFIRMED, NARROWED, or REFUTED per claim, plus a list of claims that did not
survive, kept in the working notes so a later session does not revive them.

## Doubling

For the one or two claims whose failure would be most expensive, run the same
charter on two different models in parallel and compare.

- Both confirm independently: much stronger than one agent. A single model can
  rationalize a broken path; two rarely rationalize the same one.
- Both flag the same problem: treat it as real.
- They disagree: inconclusive. Do not average. Read the cited path yourself and
  adjudicate. The disagreement usually points straight at the subtle case, and
  the more conservative verdict is usually the right one.

Do not double a mechanical claim. It only doubles cost.

## Agent isolation is part of the mechanism

Never give more than one write-capable agent the same working tree. Two reviewers
pointed at one checkout with permission to build will edit it concurrently, each
will end up reviewing the other's prototype, and the findings become unusable.

Either run reviewers strictly read-only, saying so explicitly and forbidding
builds and any `git checkout`, `git stash` or `git apply`, or give each its own
tree.

Where agents need to compare a patched build against an unpatched one, build both
yourself first and hand them the two binaries. They then need no build at all,
and the comparison is reproducible.

After any agent batch that builds or runs tests, sweep for orphaned processes. A
detached test binary whose launching shell exited gets reparented and can spin at
full CPU indefinitely.

## Verify the setup of a negative check

A discrimination check that reports "this fails without the fix" may be testing
the fixed code. Expect the specific failure, and treat its absence as a reason to
doubt the harness before doubting the finding.

The same applies to any comparison across configurations. Confirm that the knob
you are varying is the knob that changed, and that nothing upstream pins it.

## Hard rules

- Enumerate claims before spawning anything. No agent gets "check this over".
- Every agent is charged to refute, and is told that failing to break a claim is
  a useful result worth reporting plainly.
- A claim that can be measured must be measured. An explanation that cannot be
  measured is marked as an inference in the artifact itself.
- Doubling means the same charter on two models, not two models with looser
  charters.
- Reviewers are read-only unless each has its own tree.
- Record what did not survive. An unrecorded refutation comes back.
- The artifact does not leave until every load-bearing claim has a verdict.

## What good output looks like

A short list of claims, each with a verdict, the evidence, and for anything
refuted, the narrower statement that is actually true. Then the edits that
follow.

If a draft loses its central argument, that is a success, not a setback. The cost
of finding out here is a few agent runs. The cost of finding out after sending is
the credibility of everything else in the document.

---

From [xroche/skills](https://github.com/xroche/skills). Written by Xavier Roche, MIT licensed.
