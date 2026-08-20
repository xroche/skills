# skills

Claude Code skills I use and am willing to stand behind. One plugin so far.

```
/plugin marketplace add xroche/skills
/plugin install adversarial-review@xroche-skills
```

## adversarial-review

Two skills that share one idea: a reviewer told to *verify* will verify, so tell
it to refute instead, and give it one thing to refute at a time.

- **`/review-recipe`** attacks a diff. One reviewer per invariant, tests audited
  against the specification rather than against the code, and a set of gates for
  the things that generate review rounds without being bugs: interface shape,
  local convention, test scaffolding, module boundaries.
- **`/counter-check`** attacks a document before it is sent. A pull request body,
  an issue report, a reply to a maintainer, a bug filed against someone else's
  project.

`plugins/adversarial-review/RECIPE.md` and `COUNTER-CHECK.md` describe both in
harness-neutral terms if you want the ideas without the Claude Code specifics.
The `SKILL.md` files are canonical where they disagree.

## Why bother

Generic charters return generic findings. "Review this diff for bugs" surfaces
style nits and missing tests, and misses the bug the diff is structurally exposed
to, because nothing asked the reviewer to check a specific guarantee.

The sharper problem is that a model's confidence tracks its fluency rather than
its correctness. A wrong explanation arrives in the right register, cites a real
file and a real line, and reads as settled.

### What that looks like in practice

One session's worth, working on LLVM and a C++ library proposal. Almost every
measurement survived review. Almost no explanation did.

The exception is instructive. `sizeof(unsigned _BitInt(N)) == ceil(N/64)*8` is
true at every width I had measured and false below 48 bits, where I had not
looked. That was an inference wearing a measurement's clothes, which is the one
failure this method is worst at catching.

- I reported a missed optimisation and named the mechanism: a loop-invariant
  value being split across registers by one pass. Wrong pass, wrong mechanism.
  The real gate was a target-specific profitability predicate, found by a
  reviewer that went and read the lowering.
- I called the fix target-independent and free of backend work. Both false. The
  obvious version regressed a real subtarget by 11 instructions.
- I prototyped that fix. It passed all 5584 tests in the relevant suite and gave
  the motivating loop optimal code. A reviewer charged to find regressions found
  27, in shapes no test covered, because a single constant operand was enough to
  open the gate. See [llvm/llvm-project#217648](https://github.com/llvm/llvm-project/issues/217648),
  which reports the gap and the negative result instead of the patch.
- I drafted a paper issue asking for a function the paper already specified under
  a different name, resting on two claims about the reference implementation that
  were both false. It was never sent. What survived was an unrelated allocation
  bug in the same function: [eisenwave/std-big-int#341](https://github.com/eisenwave/std-big-int/issues/341).
- I wrote a test that passed. It passed because `CHECK-NOT: popcntq` matches
  inside `vpopcntq`, so the assertion I thought I was making was not the one
  being checked.
- I attributed a position to a maintainer that he had not taken, in his own
  thread, from a two-month-old post I had read earlier the same session.

Six for six, and none of them was a typo. Each was a confident, plausible,
specific claim. The recipe caught all of them before anything was sent, which is
the only reason this list is embarrassing rather than expensive.

## Requirements

Claude Code, and a harness that can run several subagents in parallel. Per-agent
model selection is used for doubling the hardest invariant and for running the
prose pass on something cheap; both degrade gracefully without it.

Some passes shell out to `gh` for the diff and for enumerating review comments.

## Licence

MIT. See `LICENSE`.
