# Fit triage, and what to use when TLA+ is the wrong tool

Read this at phase 1. Its job is to keep the skill honest: TLA+ is powerful for a specific shape of
question and useless for others. Recommending the right different tool is a successful run.

## The one-question triage

Ask: is the worry about *when things happen relative to each other*, or about *whether a computation
is correct or fast*?

- Timing, ordering, who-touches-what-when, can-these-interleave: **good fit, continue.**
- Is the result correct for this input, is it fast enough, is the number right: **poor fit, route
  and stop.**

A useful sharper test: could you describe the bug as "step A and step B happened in a bad order" or
"two things touched the same thing at once"? If yes, model it. If the bug would show up even with a
single thread running start to finish and no interruption, it is not a concurrency/ordering bug and
this is the wrong tool.

## Good-fit shapes (model these)

- Race on shared state: two operations touch the same resource concurrently with no lock.
- Lost update: read-modify-write where a concurrent writer's change is silently overwritten.
- Delete-in-flight / use-after-free: one path reclaims a resource another path is still using.
- Ordering / sequencing: "operations for the same target must apply in submission order."
- Resource lifecycle: a state machine (created, ready, draining, gone) where a transition is illegal
  from some state but reachable anyway.
- Small protocols and handshakes: two or three parties exchanging messages, where a message can be
  lost, reordered, or duplicated.
- Cache or replica coherence at a small scale: does a reader ever observe a state that should be
  impossible.

## Poor-fit shapes, and the tool that actually fits

TLA+ checks *design-level* behavior over an abstraction you write by hand. It does not run the code.
So it is the wrong tool for anything where the difficulty is in the concrete code, the data values,
or the numbers. Route these:

| The worry is really about | Use this instead | Why |
|---|---|---|
| Is this function correct for many inputs | Property-based testing (e.g. rapidcheck for C++, Hypothesis for Python) | Exercises the real code over generated inputs; no hand model to drift from |
| Does the real multithreaded code have a data race | ThreadSanitizer, then stress tests | Instruments the actual binary; catches races TLA+ can't see because they live below the abstraction |
| Explore real interleavings of real code deterministically | Systematic concurrency testing: Shuttle or Loom (Rust), Coyote (C#), rr for record/replay debugging | Drives the actual code through many schedules; closes the model-code gap TLA+ leaves open |
| Is this concurrent data structure or log linearizable | A linearizability checker: Jepsen/Knossos, Porcupine, Elle | Purpose-built to check histories against a sequential spec |
| Does it stay correct when disk/network/process fails midway | Fault injection plus a decode/validation oracle | Corruption and torn writes leave no clean "history"; a checker that assumes clean operations is blind to them |
| Is it fast enough, does it scale | Benchmarks, profiling, load tests | Performance is not a safety property |
| Is the arithmetic / algorithm result correct | Unit tests, or a proof assistant for real proofs | Functional correctness of a computation, not an ordering question |
| Is the deep protocol provably correct, not just bug-free at small size | Apalache (symbolic, via Quint) for inductive proofs, or TLAPS / Ivy for machine-checked proofs | Explicit-state TLC only checks a bounded size; these prove for all sizes but cost far more effort |

## The important nuance about "no bug found"

TLC exploring a small model and finding nothing is weak evidence, not a proof. It means "no violation
exists at this size." Two failure modes to guard against:

- **State explosion**: the real system is too big to check exhaustively, so you shrank it; the bug
  might need three of something you modeled with two. Say the size you checked.
- **Vacuity / false green**: the model passed because it could not even reach the interesting state.
  The mutation test in `04-modeling-guide.md` exists precisely to catch this. Never report a green
  result without it.

## "My model cannot price this option" is a task, not a caveat

When you compare candidate fixes, you will hit variants your abstraction cannot judge — a per-node
allocator when the model has no per-node state, a cost that lives in latency or disk, anything whose
harm is invisible at your level of detail. Saying so is honest and correct. The trap is what happens
next: an admitted blind spot reads as reassurance. "The model reports it green while hiding the
divergence" gets written up two paragraphs later as "the cheap option, worth trying first", and the
option that was never evaluated becomes the recommendation.

The rule: **the variant the model cannot price is the one to prototype in code.** Not model harder —
prototype. Ten lines in the working tree plus two throwaway probe tests against the real class will
usually settle it in under an hour, and it can refute what your model structurally cannot see. One such
unpriceable variant turned out to convert a single silently dropped task into a fully stalled pipeline:
a single-node, no-contention failure that a single-node *model* had no way to express, because the harm
ran through code the abstraction had collapsed away.

Write the refutation next to the option, with the measured numbers. "Cheaper alternative, cost unknown"
invites a reviewer to pick it.

## Where TLA+ sits in the larger toolbox

Think of two tiers. Design correctness asks "is there a guard in the design at all, and does adding
this guard close the hole?" That is TLA+ and Quint: cheap, exhaustive over your abstraction.
Implementation correctness asks "does the real code actually implement that guard on every path?"
That is ThreadSanitizer, stress tests, fault injection, systematic concurrency testing. The tiers are
complementary. A finished investigation often ends with "the design gap is real (shown here), now add
a test at the implementation tier to keep it fixed."
