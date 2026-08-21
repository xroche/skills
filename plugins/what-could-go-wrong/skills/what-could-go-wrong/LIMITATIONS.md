# Known limitations

Honest gaps. Update as the skill improves.

- **Bounded, not proven.** TLC checks a small hand-chosen size. A clean run is not a proof about all
  sizes or about the real binary. The confidence footer states this on every report; do not let a
  green result be read as a guarantee.
- **Model-code gap.** The model abstracts the code by hand. Fidelity rests on the file:line anchors,
  which a developer must be willing to audit. The skill cannot detect on its own when an anchor has
  gone stale after a refactor.
- **Only exercised on Linux x86-64 so far.** The tooling setup is written for macOS arm64 and Linux
  x86-64, but the macOS path (Gatekeeper quarantine, `Contents/Home` JRE layout) has not been run
  end to end. Verify on a Mac and record the result here.
- **Repo-agnosticism is argued, not demonstrated broadly.** The modeling and tooling are
  language-neutral, since anchors are just `file:line` and the model abstracts behavior rather than
  syntax, and the method has run end to end on both C++ and Go codebases. But ecosystems with their
  own concurrency shapes (Rust async, JS event loop, Python asyncio) are unexercised, and nothing here
  has been run on a codebase the operator did not already know well.
- **A hit rate is a property of your search, not of the code — and the skill invites the wrong
  inference.** Run the skill over N worries in repo A and M in repo B, and the ratio of live findings
  says almost nothing about which codebase is more correct. It is dominated by where the candidate
  worries came from: sweep one repo's ticket tracker and not the other's, and the swept one looks
  worse. Two further confounders when comparing an old system with a young one. Age buys a long trail
  of recorded pain, which makes candidates *easier to find* rather than more numerous. And age also
  means the loud failures were fixed years ago, so what survives is silent, which is exactly the
  profile this tool is best at. On top of that, a defect family deliberately fit-gated out to
  ThreadSanitizer never enters the count at all. **Never present a per-repo tally as a quality
  comparison**, and if a write-up groups findings by component, say what the grouping measures.
- **Property selection is the hard part and is not automated.** Picking the one right property still
  needs judgement in phase 4. A wrong property yields a confidently useless model. The pattern
  library helps but does not replace the judgement.
- **Liveness works, but it is expensive and the fairness choice is a trap.** It is in scope:
  `reference/04-modeling-guide.md` has the mechanics for checking "a node that starts waiting
  eventually stops", which finds permanent hangs that safety cannot see. Two real limits. Cost:
  per-message fairness contributes one condition per possible message and TLC's liveness checking
  degrades badly as those multiply — a 5.7M-state safety run finished in under a minute while a
  temporal property over a smaller space never finished. The documented fallback is an `ENABLED`-based
  invariant asking whether the bad state is a dead end, which answers permanence but not duration.
  Trap: fairness stated per actor instead of per message produced a liveness violation on a **healthy
  control**, i.e. a fabricated finding with a plausible trace. The control run is the only thing that
  catches this, which is why running it first is a rule in SKILL.md rather than advice.
- **No automatic state-space sizing.** The modeler chooses constants by hand. Very large real
  systems may need a size the checker cannot finish; the skill will say when it truncated, but does
  not yet suggest an optimal size.
- **Single-file models only.** No refinement mappings or multi-module composition. The
  assume-guarantee decomposition is done on paper; the model checks one flattened property at a time.
- **Fix suggestions are directional.** The model validates that some guard closes the hole. The exact
  code fix (lock choice, grace period, ref count) is left to the developer, and may differ from the
  model's guard.
- **No worked examples ship with it.** The upstream version carried six runnable investigations; they
  were dropped on import because they anchored into codebases not available here. The smoke test in
  `reference/03-tooling-setup.md` is the only runnable model, and it is deliberately tiny. Expect to
  build the first real model without a full-size reference to copy from.
