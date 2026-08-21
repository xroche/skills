# Worry patterns with ready skeletons

Read at phase 4. Match the worry to a pattern to get a modeling head start. Each pattern gives the
plain worry, the state to keep, the invariant, a PlusCal skeleton, and where to put the mutation
(the guard to remove for the reachability test). Model values are strings so configs stay trivial.
Adapt names to the real code and keep the file:line anchors.

## Pattern A — Race on a shared resource (delete-in-flight, use-after-free)

Worry: one path reclaims or frees a resource another path is still using. State: which resources are
in use, and a per-resource status that a reclaimer keys on. Invariant: never reclaim a resource that
is in use.

```
Safe == \A r \in reclaimed : ~ \E u \in inUse : Target[u] = r
\* mutation: the reclaimer picks any "looks-dead" resource with NO in-use check.
\* guard (fix): await ~ \E u \in inUse : Target[u] = r
```

## Pattern B — Lost update (read-modify-write)

Worry: two writers read a value, each computes a new one, and one write silently overwrites the
other. State: the shared value, plus each writer's local snapshot. Invariant: the final value
reflects every committed update (often modeled as a counter that must equal the number of commits).

```
w0: local := shared;              \* read
w1: shared := local + 1;          \* modify-write; the gap between w0 and w1 is the race
Safe == shared = Cardinality(committed)   \* no update was lost
\* mutation: no lock around read..write. guard (fix): a lock/CAS making w0..w1 atomic.
```

## Pattern B2 — Dedup on an unstable identity (dropped work)

Worry: a component skips work it believes it has already done, and is wrong. Whenever code decides
"already seen / already applied / duplicate" and then *discards* something, ask the two questions
that make or break this pattern:

1. **What identity does the check key on?** A name, a content hash, a client-supplied task ID, a
   server-assigned sequence number, an offset, a timestamp.
2. **Is that identity stable for the lifetime of the work?** Retries, re-sends, reconnects,
   re-elections, and re-queues frequently *re-assign* server-side sequence numbers while the caller's
   own identifier stays fixed. A watermark over a re-assignable identity silently covers work that
   was never done.

A high-water mark (`id <= latestSeen`) is the usual shape, and it is only sound when ids are assigned
once. State: the mark, plus a separate flag for whether the work was *actually* performed. Keeping
those two facts distinct in the model is the whole trick — collapsing "mark is past it" into "it is
done" builds the bug into the model and hides it.

```
\* the mark and the truth are DIFFERENT variables
Drop == id <= mark                    \* what the code checks (unstable id)
Safe == \A w \in started : done[w]     \* what must hold (stable identity)
\* mutation: key the check on the stable id instead; or forbid the mark from
\* advancing past un-done lower ids. Either going green localizes the defect.
```

Two field notes. A correct dedup on the stable identity often already exists *elsewhere in the same
codebase* (a different layer keying on the caller's ID) — finding it both confirms the diagnosis and
names the fix. And the evidence for re-assignment usually is not in the code, which rarely says "ids
get reused"; it is in **logs**, where the same stable ID appears twice under different sequence
numbers. Read the incident logs before modeling, not just the ticket summary: this pattern has produced
a first model that was plausible, anchored, red, and blaming the wrong mechanism entirely.

## Pattern C — Ordering / sequencing

Worry: operations for the same target must apply in submission order, but a faster path or a retry
reorders them. State: per-target the sequence applied so far. Invariant: applied order is a prefix of
submission order for each target.

```
Safe == \A t \in Targets : IsPrefix(appliedSeq[t], submittedSeq[t])
\* mutation: allow applying op n+1 before op n. guard (fix): await appliedSeq[t] length = n-1.
```

## Pattern D — Resource lifecycle (illegal transition)

Worry: a state machine (created, ready, draining, gone) reaches a transition that should be illegal
from its current state. State: per-resource status. Invariant: only legal transitions occur; a
forbidden pair never appears.

```
Legal == { <<"created","ready">>, <<"ready","draining">>, <<"draining","gone">> }
Safe == \A r \in Res : <<prev[r], status[r]>> \in Legal \/ prev[r] = status[r]
\* mutation: an action that jumps to "gone" from "ready". guard (fix): require "draining" first.
```

## Pattern E — Deadlock / stuck waiting

Worry: two parties each wait for the other and neither proceeds. This is one of the few liveness-ish
checks worth doing here, and TLC's built-in deadlock check does it for free. Do NOT pass `-deadlock`
for this pattern (that flag disables the check). Model each party taking a lock then waiting on the
other; TLC reports a deadlock state if one exists.

```
\* run WITHOUT -deadlock so TLC reports a genuine stuck state.
\* two processes acquiring locks in opposite order is the classic reproduction.
```

## Pattern F — Small protocol / handshake

Worry: a two or three party exchange breaks when a message is lost, duplicated, or reordered. State:
each party's phase, plus an in-flight message set (a bag if duplicates matter). Invariant: no party
reaches "done" believing an agreement the other never made.

```
\* model the channel as a set (reorder/loss) or a bag (duplicates);
\* an environment action may drop or duplicate a message.
Safe == done1 => agreed2      \* no false belief of agreement
```

## Pattern G — Deposed owner keeps acting (missing fence)

Worry: a role is held by one party at a time (leader, lock owner, primary), the role moves, and the
former holder finishes an operation it started under the old authority. This is the classic missing
fencing token, and it hides well because the ordinary path is genuinely single-owner, so every test and
every day of production looks fine.

Two questions decide it, and both are code questions rather than model questions:

- Is the authority re-checked between the point it was read and the point the operation takes effect? A
  check at the start of a multi-phase operation is not a fence.
- Does the message that takes effect carry the authority (a term, an epoch, a generation), and does the
  receiver validate it? A payload with no term cannot be fenced, whatever the sender believes.

Model the role transfer as an action so the no-transfer control exists (see the modeling guide), and give
the fence its own switch:

```
Depose      == MODEL_FLIP /\ ~flipped /\ stale' = [r \in Owners |-> IF InFlight(r) THEN TRUE ELSE stale[r]]
Act(r)      == /\ pc[r] = "act"
               /\ ~(FENCE /\ stale[r])          \* the fence: a deposed owner does nothing
               /\ ...
FencedOut(r) == FENCE /\ pc[r] = "act" /\ stale[r] /\ pc' = [pc EXCEPT ![r] = "dead"]
```

Two traps found the hard way. A fence on the *outbound message* is not enough if the owner also acts on
itself locally: instrument both paths. And fencing alone can be insufficient when the operation has
already had a partial effect before the transfer, so check the fence knob together with whatever makes the
effect atomic; each was red alone and only the pair was green.

Watch for a nearby timing guard that looks like a fix and is not: a "wait N seconds after the role moves"
delay on the *new* owner protects nothing if the old owner's operation is short, and such guards often
carry a first-iteration exemption that fires exactly when the role moves because the new owner restarted.

## If nothing matches

The scope is broad: you can model any safety invariant over state even if it fits no pattern here.
Keep the method identical: smallest state that exhibits the worry, one invariant, the mutation test
to prove reachability, the annotation rule throughout. Add the new shape to this file afterward if it
is likely to recur.
