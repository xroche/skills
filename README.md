# skills

Claude Code skills I use and am willing to stand behind. One plugin so far.

```
/plugin marketplace add xroche/skills
/plugin install adversarial-review@xroche-skills
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

`RECIPE.md` and `COUNTER-CHECK.md` in the plugin directory describe both without
the Claude Code specifics. The `SKILL.md` files are what runs.

## Why

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

Claude Code, and a harness that can run several subagents in parallel. Per-agent
model choice is used to double the hardest invariant and to run the prose pass on
something cheap; both degrade gracefully without it. Some passes shell out to
`gh`.

## Licence

MIT.
