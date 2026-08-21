# skills

Claude Code skills I use and am willing to stand behind. Three plugins.

```
/plugin marketplace add xroche/skills
/plugin install adversarial-review@xroche-skills
/plugin install pr-craft@xroche-skills
/plugin install what-could-go-wrong@xroche-skills
```

## adversarial-review

Two skills, one idea: a reviewer told to *verify* will verify, so tell it to
refute instead, and give it one thing to refute at a time.

- **`/review-recipe`** attacks a diff. One reviewer per invariant, tests audited
  against the specification rather than against the code, and separate passes for
  the things that cost review rounds without being bugs: interface shape, local
  convention, test scaffolding, module boundaries.

- **`/counter-check`** attacks a document before it is sent. A pull request body,
  an issue report, a reply to a maintainer, a bug filed against another project.

## Using it

Either as a slash command or by asking for it.

```
/review-recipe 4821
/review-recipe feat/retry-payments
/review-recipe 4821 -- "no request can be executed twice" "retries are bounded"
/counter-check drafts/cache-leak-report.md
/counter-check
```

> Let's `/review-recipe` PR 4821, the retry wrapper. The one thing I care about
> is that no request can be executed twice.

> Can you `/counter-check` the paper draft in `docs/rfc-0007.md` before I send it
> to the list? The section on eviction order is the part I am least sure of.

Naming the invariants yourself is the highest-leverage thing you can do. Given
none, it infers one to four from the diff and the project's conventions, which
works, but you usually know the property that matters and it does not.

With no argument at all, `/counter-check` takes the last thing drafted in the
conversation.

`RECIPE.md` and `COUNTER-CHECK.md` in the plugin directory describe both without
the Claude Code specifics. The `SKILL.md` files are what runs.

## pr-craft

The two places a pull request wastes people's time: the review, and the wait.

- **`/mechanical-refactor`** makes a large mostly-mechanical diff reviewable. The
  mechanical part comes out of a short migration script, committed before its own
  output, so the reviewer reads twenty lines of `sed` instead of a thousand lines
  of result. What the script could not produce is a separate commit, read
  normally.

- **`/babysit-ci`** diagnoses a red run: which leg, why, whether this PR caused
  it, and the fix. Then it pushes and returns. It does not loop waiting for
  green, because `gh pr merge --auto` already does that for free.

```
/mechanical-refactor convert the visitor callbacks to take a span
/babysit-ci 4821
```

## what-could-go-wrong

For the question a code review cannot settle by reading: *can this actually
happen?*

**`/what-could-go-wrong`** takes a worry about ordering, lifetime, concurrency or
state and answers it with a concrete interleaving and `file:line` anchors, or
with an honest "not found, and here is what I covered". It builds a small TLA+
model of the part that matters and checks it; the report is plain language, and
the model sits in an appendix for anyone who wants to audit it.

```
/what-could-go-wrong can the cleanup pass delete a cache entry a writer still holds?
```

It is explicit about what a bounded check on a hand-written model does and does
not buy you. `LIMITATIONS.md` in the plugin is the part to read before treating a
clean run as an answer.

## Why the reviews are adversarial

Generic charters return generic findings. "Review this diff for bugs" surfaces
style nits and missing tests, and misses the bug the diff is structurally exposed
to, because nothing asked the reviewer to check a specific guarantee.

The sharper problem is that a model's confidence tracks its fluency, not its
correctness. A wrong explanation arrives in the right register, cites a real file
and a real line, and reads as settled.

## What it caught

One session, working on a compiler backend. Four of my own claims, all confident,
all specific, none a typo:

- I reported a missed optimisation and named the mechanism. Wrong mechanism,
  wrong compiler pass. A reviewer sent to read the lowering found the real one.
- I called the fix target-independent. It regressed a different CPU target.
- I prototyped that fix. It gave the motivating case optimal code and passed all
  5584 tests in the relevant suite. A reviewer charged to find regressions found
  27, in shapes no test covered.
- I quoted a maintainer taking a position he had not taken, from a post in a
  thread I had already read.

The pattern held all session: the measurements survived, the explanations did
not. What went out was [a report of the gap and the negative
result](https://github.com/llvm/llvm-project/issues/217648) instead of a patch
that would have pessimised real code.

It has a blind spot. I published a formula that held at every input I had
measured and failed outside that range, because I had generalised from the
measured points without saying so. An inference wearing a measurement's clothes
survives a review that checks measurements.

## Requirements

Claude Code, and for the review skills a harness that can run several subagents
in parallel. Per-agent
model choice is used to double the hardest invariant and to run the prose pass on
something cheap; both degrade gracefully without it. Some passes shell out to
`gh`. `what-could-go-wrong` downloads TLA+ and a JRE on first use, into a cache
under your home directory.

## Author and licence

All of it written by Xavier Roche. MIT.
