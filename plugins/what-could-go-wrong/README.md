# what-could-go-wrong

One Claude Code skill, for the question a code review cannot settle by reading:
*can this actually happen?*

**`/what-could-go-wrong <the worry>`** takes a worry about ordering, lifetime,
concurrency or state. Can the cleanup pass delete an entry a writer still holds,
can these two callbacks interleave, can a retry run the operation twice. It
answers with a concrete interleaving and `file:line` anchors, or with an honest
"not found, and here is what I covered".

It builds a small TLA+ model of the part that matters and model-checks it. The
report is plain language; the model and the math sit in appendices for anyone
who wants to audit them. The reader needs no formal methods, and neither does
the person asking.

It says so and stops when the question is not its kind: pure functional
correctness, performance, and numerical questions are not what a model checker
answers.

## Reading order

`skills/what-could-go-wrong/SKILL.md` is what runs. `LIMITATIONS.md` is the part
worth reading before trusting a green result: a bounded check on a hand-written
model is not a proof about the binary, and the skill is explicit about which of
those two you are getting.

## Provenance

Written by me. It ran on private codebases before this one and was de-identified
on the way out, which is why it ships without worked examples: the six it had
went with the code they anchored into. The modeling method is standard TLA+
practice, not novel work.
