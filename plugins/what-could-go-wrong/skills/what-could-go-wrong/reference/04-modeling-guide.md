# Building a small honest model

Read at phases 6 and 7. The aim is the smallest PlusCal model that can still exhibit the worry, with
every part traceable back to the code. The skeletons in `02-patterns.md` are the starting shapes; the
smoke model in `03-tooling-setup.md` is a complete runnable one, small enough to read in a minute.

## Start as small as possible

Two of each thing is almost always enough: 2 jobs, 2 directories, 1 worker. A race needs at most two
actors contending for one resource; ordering needs at most two operations. Grow only when a
specific interleaving you care about needs a third. Small models check in under a second and produce
short, readable counterexamples. Large models explode and give traces no one wants to read.

## The annotation rule (non-negotiable)

Every state variable and every action carries a comment naming the exact `file:line` it abstracts.
This is the only defense against the model drifting from the code. A reviewer validates the model by
opening each cited line and confirming the abstraction still matches. If an action has no honest code
anchor, it does not belong in the model; that is a sign you are modeling something the code does not
do.

```
variables
  inFlight   = {},                     \* the scheduler-admitted set, Scheduler.c:412
  dirMarker  = [d \in Dirs |-> TRUE];  \* does the dir still carry its liveness marker? Builder.c:853/930
```

## Three parts of a model

1. **State** the few facts that matter. Resist adding fields; each one multiplies the state space and
   usually does not change whether the bug exists.
2. **Actions**, one per real step, split at the points where another actor could interrupt. In
   PlusCal, labels are those interruption points. Put a label exactly where the code yields (releases
   a lock, does I/O, returns to a loop) so the checker considers an interleaving there.
3. **The invariant**: the "X must never happen" from phase 4, written as a predicate over the state.

## The precondition must be an action, never an assumption

The most expensive modeling mistake is to bake the answer into the setup. If the worry is "two writers
can collide", do not write a model with two writers running freely: that assumes the concurrency whose
reachability is the actual question, and the model can then only tell you what happens *given* the bug.

Make the enabling condition an action with a switch, and add the guard that normally prevents it:

```
\* WRONG: both rounds simply exist, so overlap is assumed
Read(r) == pc[r] = "read" /\ ...

\* RIGHT: a second round may start only if something deposed the first
Read(r) == /\ pc[r] = "read"
           /\ \A o \in Rounds \ {r} : ~InFlight(o) \/ stale[o]
Flip    == MODEL_FLIP /\ ~flipped /\ stale' = [r \in Rounds |-> IF InFlight(r) THEN TRUE ELSE stale[r]] /\ ...
```

Now the no-flip configuration is checkable, and that run is usually the most valuable one in the whole
report. On one leader-transfer worry it came back green on every invariant, which turned a vague "this
design is broken" into the far more useful "this design is correct until leadership moves mid-operation, and
nothing stops the old leader." It also gave fencing something to act on: with the precondition assumed
rather than modelled, a fence knob had *no effect at all* and looked useless.

Rule of thumb: if your model has no configuration that comes back green on today's code, ask whether
you have modelled the system or modelled the bug.

## Designing the invariant: two failure modes

**Too strong.** An invariant that forbids a legitimate state reddens unrelated paths and buries the real
finding. `NoSilentLoss == dropped => applied` looked right and was wrong: the system legitimately hands a
task from a queue file to a stored job directory, so every retry path went red for a reason that had
nothing to do with the defect. The fix was to name what actually must hold: a durable copy exists in
*either* place.

    Durable(t)  == t \in queued \/ (\E j : slot[j] = t)
    Recoverable == \A t : t \notin applied => Durable(t)

Before trusting a red result, ask: is this state genuinely forbidden, or merely surprising?

**Alone.** Most safety invariants have a cheap degenerate solution, and a single-invariant check will
happily bless it. "Never lose an operation" is satisfied by refusing all work; "never corrupt data" is
satisfied by never writing. Pair the invariant with its counterweight and check both:

| invariant | degenerate cheat it permits | counterweight |
|---|---|---|
| nothing is lost | refuse everything, stall | a legitimate retry is never refused |
| no duplicate work | never start work | work eventually starts |
| no stale read | block all readers | readers make progress |

Check them in **separate runs**. Several `INVARIANT` lines in one config make TLC stop at the first
violation and hide whether the others also broke.

## A repair pass is not a guard: check liveness too, or you will misprice it

Candidate fixes come in two shapes, and a safety invariant can only judge one of them. A **guard**
prevents the bad state from being entered; safety is the right lens. A **repair pass** — a reconciler,
a periodic resync, a retry sweep — lets the bad state happen and then leaves it. Against a safety
invariant that says "never be stale", a repair pass is *always* red, because the checker finds the
state before the sweep runs. Reporting that as "this fix does not work" is wrong, and the mistake is
easy: the run genuinely comes back RED.

Price it on liveness instead. Add the two-state pair and fairness on the repair action only:

    Stale == status = "SETTLED" /\ table < truth
    Fresh == table >= truth
    EventuallyFresh == Stale ~> Fresh
    FairSpec == Spec /\ WF_vars(Ev_Reconcile)

with `SPECIFICATION FairSpec` / `PROPERTY EventuallyFresh` in the config. Now the two options separate
cleanly, and the pair of results is the actual finding:

| candidate | safety (`NoStale`) | liveness (`EventuallyFresh`) | verdict |
|---|---|---|---|
| guard at the transition | green | green | the fix |
| periodic repair pass | RED | green | a backstop, not a substitute |
| today | RED | **RED** | stale *permanently*, not transiently |

The `today` row is worth the extra run on its own: a liveness violation on today's code is the formal
statement that the bad state is permanent rather than a window, which is usually the difference between
"annoying" and "a user waits forever". That row is what once turned "the routing table can lag" into
"nothing will ever correct it except a process restart".

Note the runner must detect this outcome. TLC prints `Temporal properties were violated`, not
`Invariant ... is violated`, so a result-classifying script that greps only for the latter scores a
liveness violation as a pass.

## Checking liveness properly: fairness granularity, and what it costs

Once you write a liveness property you have to say which actions the system is assumed to keep
performing. That choice is part of the model, it is easy to get wrong, and **getting it wrong fabricates
findings rather than hiding them**.

**State fairness per message, not per actor.** The natural-looking form is one condition per node:

    Recv(n) == \E m \in net : m.to = n /\ Handle(n, m)
    FairSpec == Spec /\ \A n \in Nodes : WF_vars(Recv(n))       \* WRONG

Weak fairness on a disjunction only promises that *some* step of it happens. A node can therefore
discharge its obligation forever by repeatedly handling one message while never touching another that
is sitting there for it. In a ring leader-election model that produced a liveness violation on the
**healthy full-mesh control**: a node kept re-handling a circulating token and never once picked up the
announcement addressed to it. Entirely an artifact. The honest form quantifies over messages:

    RecvOne(n, m) == m \in net /\ m.to = n /\ Handle(n, m)
    FairSpec == Spec /\ \A m \in Messages : WF_vars(RecvOne(m.to, m))

which says "a message left in flight is eventually delivered" — what a real per-connection thread does.
The control went green immediately.

The general lesson is about the control, not about fairness: **the control run catches broken models,
not only absent bugs.** A session that had checked only the suspicious configuration would have shipped
an invented liveness bug with a plausible trace attached. Run the healthy configuration first, every
time, and treat a red control as a modelling defect until proven otherwise.

**Guard the receive action with `m \in net`.** A handler written as `net' = (net \ {m}) \cup {...}` is
satisfiable for an `m` that was never sent, so without the membership guard the model invents messages.
This hides while fairness is per-actor (the `\E m \in net` supplies the guard) and bites the moment you
quantify over all messages.

**Do not make the environment fair.** Message loss, crashes, network changes are things that *may*
happen, not things that keep happening. Put them under a counter (`drops < MaxDrops`) and leave them
out of the fairness conjuncts. Forcing them to recur refutes every protocol ever written, which is a
result about your model rather than about the code.

**Liveness checking does not scale like safety, and you need a fallback.** Per-message fairness
contributes one condition per possible message — 27 at three nodes with three message types — and TLC's
liveness checking degrades badly as those multiply. In that same model a safety run over 5.7M states
finished in under a minute while the temporal property on a smaller space never finished at all and was
killed at 100s.

When that happens, ask the sound half as an invariant: **is the bad state a dead end?**

    TwoMasters          == \E n1, n2 \in Nodes : n1 # n2 /\ believes[n1] /\ believes[n2]
    TwoMastersHasEscape == TwoMasters => \E n \in Nodes : ENABLED Escape(n)

If that holds, every bad state has an exit available, and weak fairness on `Escape` takes it. This is
cheap, and it answers the question that usually matters — permanent split versus transient window.
Two duties keep it honest. Say what it does not cover: it shows the state is escapable, not how long it
lasts, and for a window the duration is exactly where the damage is. And **mutate it** — switch the
escape action off and confirm the invariant goes red, or the green is vacuous in the usual way.

## A fix you cannot model

Some fixes, expressed in the model, *are* the invariant. "Only import what was confirmed" as a model
action makes `NoUnconfirmedApply` true by construction, so the run comes back green and proves nothing.
Recognise the shape and say so: the model's job ends, and the fix's cost has to be judged in code (an
extra file plus fsync per item, a rename, a schema change). Reporting that green as evidence is the same
error as a vacuous check, one level up.

## Modeling a lock as a toggle

Most concurrency worries turn on whether a lock actually covers the check and the mutation it is
meant to protect. Model the lock as one boolean variable, `locked`, with a plain acquire/release pair
bracketing the labels it guards. Keep the check and the mutation in **separate** labels between the
acquire and release, so the checker can try to slip another process in between them; the lock is what
forbids that.

```
Acq:   await ~locked; locked := TRUE;                  \* the queue lock, Scheduler.c:115
Check: with (c \in Queue) { ... conflict scan ... };   \* Scheduler.c:525-529 / Job.c:211-240
Ins:   inFlight := inFlight \union {picked};           \* Scheduler.c:276-277 (insert + clear the slot)
Rel:   locked := FALSE;
```

This makes the mutation test one edit: replace the acquire with `skip` (or delete the `await
~locked`) so the two labels are no longer mutually exclusive. If the lock is load-bearing, TLC now
finds the interleaving (a double-pick, a lost update); restore the acquire and it goes green. A lock
that changes nothing between the two runs was not protecting the invariant you modeled, which is
itself a finding.

## The mutation test (mandatory, phase 7)

A green run only means something if the model could have gone red. Before trusting any "no problem
found", prove the model can reach the bad state:

1. Build the model with the guard or protection you are testing **removed or commented out**.
2. Run TLC. It must report the invariant violated, with a trace. This is the proof that the check is
   not vacuous, and it is usually the actual finding.
3. Now add the guard back. Re-run. If it goes green, you have shown both that the danger was real and
   that the guard removes it.

If step 2 does not produce a violation, the model is vacuous: it cannot reach the danger, so its
green result proves nothing. Fix the model (usually a missing action or an over-strong precondition)
before reporting anything.

### Mutate toward the refuted design, not only toward broken

When the model picked design A over design B, the tests and the model must both fail if the code were
B. Mutating toward "obviously broken" does not check that: it leaves the plausible wrong design
untested, which is the one someone will actually propose in review.

This caught a real hole. A model refuted comparing payload sizes in favour of comparing identities, the
code compared identities, and every test still passed when the comparison was switched back to sizes,
because the fixture varied identity and payload together. The tests pinned "something differs" rather
than the property that survived the model. The repair is to build the off-diagonal cases explicitly:

| | same identity | different identity |
|---|---|---|
| same payload | must stay silent | **must report** |
| different payload | **must stay silent** | must report |

The two bold cells are the ones a size-based check gets wrong, and the ones a fixture that co-varies the
two dimensions can never reach. Whenever a decision has two candidate signals, cross them.

### Mechanics: never let a mutation run lose its own baseline

Mutation runs edit real source files, so treat the restore as the load-bearing part.

- One mutant per step, each with its own restore. A loop that applies several mutants leaves the tree
  mutated the moment any step exits early.
- Never `set -u` plus `source <build-env>` inside a shell function: an unbound variable in the sourced
  script exits the whole script, skipping the restore.
- **Never overwrite the pristine copy from a re-run.** A script that starts with `cp $SRC $BAK` poisons
  its own backup the second time it runs on an already-mutated tree.
- Verify by grepping for the mutation marker afterwards, not by trusting the script's exit code. On one
  session a mutant reached the staging area and was caught only by that grep.

### Mutation test when the worry is refuted

Sometimes the faithful model is green: the code is safe and the worry does not hold. The mutation
test still applies, but its shape flips. There is no guard in the real model to remove, because the
safety comes from the code's structure (two operations sharing one lock, an increment that precedes
the read). So instead, **encode the worry's own hypothesis as a separate model** — the split or the
missing guard the asker feared — and confirm TLC finds the race there. That red run is the proof the
green one is not vacuous: it shows the model can express and catch this exact class of bug, and that
the real structure is what prevents it. Keep the hypothesis model in a clearly named companion file
(`<Name>_hyp.tla`) with a header saying it is deliberately not the real code. A refutation without
this companion is as weak as a "no problem found" without a mutation test.

### Re-open every anchor before trusting the model

The annotation rule only protects you if you actually read the cited lines. A plausible lock
structure taken from a design doc, a research note, or the asker's own framing of the worry is not
the code. Before the first run, open each `file:line` and confirm the ordering you modeled — which
lock is held where, which step precedes which — matches. One investigation built its first model around
a two-lock split ("commit under lock A, ref-count later under lock B") that the worry described but the
code did not have: both steps were in one critical section. Re-reading the anchors turned a false "yes"
into a correct "refuted". The summary was wrong; the lines were right.

## Self-validating fix (phase 9)

Never suggest a guard you have not tested. Encode the proposed fix in the model as an `await` or an
extra precondition on the dangerous action, re-run, and confirm the violation disappears. Report the
before and after. For a delete-in-flight worry the fix is one line in the reclaimer:

```
await ~ \E j \in inFlight : Dest[j] = d ;   \* skip a dir an in-flight job still targets
```

Be honest when the model's fix differs from the likely code fix. That model expresses a "skip
in-flight" guard, where the shipped code fix may well use a grace period on the directory's
modification time instead. Both close the hole; a clockless toy cannot express mtime crisply. Say so
rather than implying the model's exact fix is the one to write.

## Reading TLC output

- `Invariant Safe is violated` followed by `State 1 ... State N`: a counterexample. Each state prints
  the full variable values and the program counters. The last state is the bad one; the path to it is
  the bug. It is the shortest such path, which makes it a clean minimal reproduction.
- `Model checking completed. No error has been found`: no violation at this size. Only meaningful
  after the mutation test. Always report the size checked and the state count.
- A parse or semantic error: usually a PlusCal typo. Fix and rerun `pcal.trans`.

## Common PlusCal gotchas

- Rerun `pcal.trans` after every edit to the algorithm block; TLC reads the generated TLA+, not your
  PlusCal.
- Two assignments to the same variable in one label are illegal unless combined with `||`. Split into
  separate labels, or assign different variables.
- Within one label, statements run in order and later ones see earlier assignments; the whole label is
  still one atomic step to other processes.
- A `with (x \in S)` over an empty set disables the action; the process waits. That is often the
  intended effect of a guard, not a bug.
- Use `-deadlock` so a legitimately waiting guarded process is not reported as a deadlock.
- Model values as strings ("j1", "d1") keep the config trivial: no `CONSTANTS` assignments needed,
  and the counterexample prints readable names.
- "Missing label at line N" usually means a blocking `await` sits inside an `if`/`else` branch, or a
  statement follows an `if` whose branch ends in `goto`. PlusCal cannot hoist a conditional guard.
  Fix by giving the awaited step its own label, or restructure so control falls through the loop
  instead of using `goto`. When a per-process lock is uncontended in the abstraction (only its owner
  touches it, and the owner is sequential), drop the lock variable and make the guarded region one
  atomic step instead — same behavior, no label headache.

## Sizing up when a first model finds nothing

If the mutation test passes (the unguarded model does reach the danger) but the guarded model is
green, that is a real result: report it. If the mutation test itself found nothing, the worry may not
be reachable in the modeled shape; widen the model by one actor or one resource, or revisit phase 4,
you may have named the wrong property. Record what you tried; a genuine "cannot make it break at size
N" is a finding worth stating plainly, with its limits.
