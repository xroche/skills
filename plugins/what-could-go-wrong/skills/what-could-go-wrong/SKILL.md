---
name: what-could-go-wrong
description: Investigate a worry about how some code behaves under concurrency, ordering, or state changes, then find a concrete failing scenario (or report none found, honestly) and explain it in plain language with a suggested fix. Builds a tiny TLA+ model behind the scenes; the math is always optional. Works on any codebase. TRIGGER when someone asks "can X ever happen?", "is there a race here?", "could these two things step on each other?", "what could go wrong with this?", or wants to check an ordering / lifecycle / protocol / lost-update / use-after-free style property. For pure functional correctness, performance, or numerical questions, the skill will say so and stop.
user-invocable: true
argument-hint: <the worry to investigate, e.g. "can the cleanup pass delete a cache entry a writer still holds?">
---

# What Could Go Wrong

Turn a worry about code behavior into a concrete answer. The skill grounds itself in the real code,
builds a small honest model of the part that matters, checks whether the bad thing can happen, and
reports back in plain language with a concrete example and a suggested fix. The reader does not need
to know any formal methods. The TLA+ model and the math live in optional appendices for anyone who
wants them.

The worry to investigate: $ARGUMENTS

## What this is good for, and what it is not

Good fit: questions about *timing, ordering, and who-touches-what-when*. Races on shared state,
lost updates, use-after-free or delete-in-flight, ordering and sequencing guarantees, resource
lifecycle, small protocol handshakes, "can these two operations interleave badly?".

Poor fit: is the arithmetic correct, is it fast enough, is the output right for a given input.
Those are functional, performance, or numerical questions. TLA+ will not help, and the honest move
is to say so. `reference/01-fit-and-alternatives.md` covers how to recognize a poor fit and what to
recommend instead (property-based testing, fault injection, ThreadSanitizer, systematic concurrency
testing, linearizability checking, or just a unit test). Read it during phase 1.

Scope setting for this instance: **broad**. Attempt any safety invariant over state, not only the
classic concurrency shapes. Still run the fit triage first and still bail with a plain explanation
when the question is genuinely functional, performance, or numerical.

## The workflow

Run these phases in order. Each names the reference file with the detail. Do not inline those files
here; read them when you reach the phase so the context stays small.

### Phase 1 — Triage: is this the right tool?
Decide in plain terms whether the worry is about timing/ordering/state (good fit) or about
functional/perf/numerical correctness (poor fit). If poor fit, explain why in one or two sentences,
point to the better tool from `reference/01-fit-and-alternatives.md`, and stop. A clear "this is the
wrong tool, here is the right one" is a successful outcome, not a failure.

### Phase 2 — Understand who is asking
Infer how much the asker wants to see: someone who will audit the anchors line by line, or someone who
needs the answer and the impact and nothing else. This only tunes how the final report reads. When
unsure, ask one short question. Keep the model work identical either way.

### Phase 3 — Ground in the code
Find the components involved, the shared state, and how each piece of state is protected: a real
lock with a clear owner, or a convention that everyone is trusted to follow. Fan out with agents
for anything broad (see the agent/model guidance below). Produce a short map: components, shared
state, protection mechanism, and the one thing nobody clearly owns. This map is the raw material
for the model.

**Establish the ref before reading a single line, and say so out loud.** A model anchored to a stale
checkout can be internally perfect and still describe a bug that was fixed months ago — or miss the one
the fix introduced. Three commands, once, at the top of phase 3:

```bash
git rev-parse --abbrev-ref HEAD && git rev-parse --short HEAD
git fetch -q origin <default-branch>
git merge-base --is-ancestor HEAD origin/<default-branch> \
  && echo "behind or current" || echo "DIVERGED"
```

Then the check that actually matters, which is **per-file, not per-repo**: once you know which files
you will anchor, run `git diff --stat HEAD origin/<default-branch> -- <those files>`. "Behind by 400
commits" is noise if none of them touched your files; one commit that rewrote the function you are
modeling is fatal.

Investigating from a fresh worktree cut off the just-fetched default branch removes most of this at the
source, and is the right default. When instead you are reading a checkout somebody else owns and it is
not current, **say so plainly and early, before presenting any finding, and do not move it for them**:
they may be mid-work on that branch. Carry the ref and its staleness in the model header and in the
report's confidence footer, and name which anchors sit in files upstream has since changed.

A diverged feature branch is the dangerous case, not one merely behind: it can hold local work *and*
miss upstream fixes, and nothing in the diff says which lines are which. Recording the sha is necessary
and not sufficient — `git log -1` tells you what you are reading, not whether it is what ships. This has
inverted a verdict in practice: the modeled hole was real on the branch and already closed on the
default branch, and the commit that closed it had introduced a different defect.

**Read every primary artifact to completion, and write down its size.** Ticket descriptions, incident
write-ups and log dumps are routinely much longer than the first screenful, and a model built on an
excerpt will be confidently wrong. Record "description: 12,431 chars, read in full" in the map. If you
are working from a summary — including your own from an earlier session — re-open the source. Modeling
on a partial read costs a full analysis cycle each time it happens.

**If the incident is asymmetric across supposedly identical replicas, "why this one and not its peers"
is a mandatory question, answered before modeling.** Nodes in the same cluster running the same binary
are not interchangeable in practice: one may be the elected master, or the only one that never fell
back to a slower path. That asymmetry usually *is* the arming condition, and it is often answerable in
a single metric query. Ask it first; it reframes everything downstream.

### Phase 4 — Pick exactly one property
From the map, name a single safety property to check, phrased as "X must never happen." Identify the
seam where it could break (often: one component assumes a protection that another component does not
actually provide). Confirm it back to the asker in one plain sentence before building anything.
`reference/02-patterns.md` has named worry-patterns (race on shared resource, lost update, ordering,
delete-in-flight, deadlock, handshake, deposed owner) with ready PlusCal skeletons; match the worry to a pattern to
get a head start.

Then name the property's **counterweight** and check both. Almost every safety property has a cheap
degenerate solution the checker will bless: "nothing is lost" is satisfied by refusing all work, "no
duplicate work" by never starting any. One invariant alone cannot tell a fix from a stall. Check them in
separate runs, because several `INVARIANT` lines in one config make TLC stop at the first violation and
hide the rest. `reference/04-modeling-guide.md` has the pairing table and the two ways an invariant goes
wrong (too strong, or alone).

### Phase 5 — Set up the tooling
Ensure a Java runtime and `tla2tools.jar` are available, cached, no admin rights needed on the first
attempt. Follow `reference/03-tooling-setup.md` exactly (system Java first, portable JRE second, shared
cache so repeat runs are instant), including its smoke test. Quint is the fallback if someone prefers
readable syntax; same file covers it.

### Phase 6 — Build the smallest honest model
Write PlusCal at the smallest size that can still exhibit the worry (usually 2 of each thing). Follow
`reference/04-modeling-guide.md`. The non-negotiable rule: **every state variable and every action
carries a `file:line` anchor into the code it abstracts.** An action with no honest anchor does not
belong in the model. This is the only thing that lets a reviewer trust the model against the code.

Second rule, equally load-bearing: **the enabling condition goes in as an action, never as an
assumption.** If the worry needs two writers to overlap, model what lets them overlap and put the normal
guard in; do not start from two free-running writers. Otherwise the model can only describe the bug it
was built to contain, the without-it control cannot be run, and a candidate fix aimed at the precondition
will appear to do nothing.

**Run the control configuration first, and treat a red control as a broken model.** The healthy setup
catches modelling defects, not only absent bugs. A healthy full-mesh control has gone red on liveness
purely because fairness was stated per actor instead of per message; a session that had only run the
suspicious configuration would have shipped an invented bug with a plausible trace attached.
`reference/04-modeling-guide.md` has that trap and the rest of the liveness mechanics.

### Phase 7 — Verify, and prove the check is not vacuous
Translate and run TLC. Then run the mandatory **mutation test**: remove the guard or the assumed
protection and confirm the checker *can* reach the bad state. A "no problem found" result is
meaningless unless you have shown the model could have found a problem. Report both runs.
`reference/04-modeling-guide.md` has the exact commands and how to read the output.

When the model chose between two candidate designs, also **mutate toward the design it refuted**, not
only toward obviously-broken. The plausible wrong design is the one a reviewer will propose, and a
fixture that varies two signals together will pass with either. Same file has the cross-product table.

### Phase 8 — Map the result back to the code
If a counterexample was found, walk its steps and map each to the real `file:line` it came from.
Turn it into a short concrete story: "first this, then this, and now the directory is gone while the
copy is still writing to it." If no counterexample was found, state precisely what was checked and
at what size, and that this is not a proof about the real binary.

### Phase 9 — Explain and suggest a fix, then self-validate the fix
Write the report from `reference/05-report-template.md`: plain-language first, the concrete scenario,
the suggested fix, and the confidence-and-scope footer. When you suggest a fix, encode it in the
model and re-run to show it closes the hole. Never suggest a guard without demonstrating it works in
the model.

**Then read your own "what this model drops" list back, as a risk register.** Finding a bug and
validating a fix are different jobs, and the same abstraction cannot serve both. The abstraction was
chosen to *expose* the bug: everything irrelevant to that one property was dropped on purpose. A fix
edits real code, including the parts that were dropped — so the model is blind to exactly the region
the fix is most likely to disturb. Walk the dropped list item by item and ask "does the fix touch
this?" For each yes, you need evidence the model cannot give you.

This is not hypothetical. A fix once went green on both the property and its counterweight and then
shipped a production incident: the model's own header said it dropped "background enqueues, exception
capture", and the defect was precisely an enqueue failing and being swallowed by that exception
handler, which committed the claim and then reported failure to the caller. Two independent
code-review agents found it in minutes. The model could not have, at any size.

So: **a green model is a validated design, never a reviewed change.** Put the diff through a
narrow-invariant code review before recommending it, and say in the report which invariants the model
checked and which only the review covered. Keep the report readable: apply `reference/07-writing-style.md` to all prose before
returning it. Offer, but never force, the optional appendix `reference/06-math-appendix.md` for
anyone who wants to understand the model and the math.

## Guardrails (these are what make the result trustworthy)

- **Fit-gate** (phase 1): do not model a functional/perf/numerical question. Route it and stop.
- **Fresh-checkout gate** (phase 3): establish the ref, and the per-file diff against the default
  branch, *before* reading code. A stale checkout does not merely shift line numbers — it can invert
  the verdict, and no amount of care downstream recovers from it.
- **Mutation test** (phase 7): a green result is worthless if the model could not reach the danger.
  Always demonstrate reachability first. This is the formal version of "a test that can never fail
  is a no-op."
- **No vacuous invariant** (phase 7): **every** invariant, including the counterweight, must go RED in
  at least one cell of the matrix. An invariant that is green everywhere is not evidence of safety, it
  is an invariant that cannot fail — and TLC will never tell you, because it is answering correctly
  about the model you wrote. Apply this per rule, not once per model: the counterweight is the one that
  slips through, since attention goes to the property. Corollary: **check the invariant against a patch
  somebody already tried.** Encode a real rejected fix as a configuration; if the invariant goes green
  on it, the invariant is keyed on the symptom (an exception, a log line, an alert) rather than on the
  state, and it will bless anything that silences the symptom.
- **Annotation rule** (phase 6): every action anchored to `file:line`, or it does not ship.
- **Confidence footer** (phase 9): every report distinguishes "found a concrete counterexample"
  (strong) from "no counterexample in a small bounded model" (weak, not a proof), and states the
  model-code gap. Enforced by the template.
- **Self-validating fix** (phase 9): a suggested guard is shown to close the hole in the model. Its
  limit: a fix that, written in the model, *is* the invariant comes back green by construction and proves
  nothing. Recognise that shape, say so, and price the fix in code instead.
- **Dropped-list re-read** (phase 9): before recommending a fix, walk the model's own list of what it
  abstracted away and ask whether the fix touches each item. The abstraction was built to expose the
  bug, so it is blind precisely where a fix does its work — a green model plus an unreviewed diff is
  how a validated design ships an incident. Pair every fix with a narrow-invariant code review, and
  state in the report which invariants the model covered and which only the review did.
- **Precondition as an action** (phase 6): the condition that enables the worry is modelled and
  switchable, so the without-it run exists. A model with no green configuration on today's code is
  usually a model of the bug rather than of the system.
- **Repro gate** (phase 9): a model counterexample is a *conditional* result until something in the
  real system arms it. Before claiming a root cause, say explicitly which of the three rungs below the
  evidence reaches. Skipping this rung is how a model turns into a confident wrong answer.
- **Stay local**: never send someone else's source to an external service. All modeling and checking
  runs locally.

### The proof ladder — where does the evidence actually stop?

A counterexample proves "**if** the system can reach state S, **then** the bad thing follows." The
"if" is the whole question, and a model cannot discharge it. Grade every finding on this ladder and
put the rung in the report:

1. **Mechanism shown** — TLC exhibits the interleaving in the abstraction. Cheap, and the weakest
   rung. It proves the *modeled* mechanism is unsafe, not that it is the mechanism that fires.
2. **Precondition reachable** — a code-level artifact reaches the dangerous state through legitimate
   API calls, no hand-forcing. This is the rung that converts "conditional" into "real."
3. **Repro** — a test that fails on today's code for the bug's own reason, and passes under the
   proposed fix. **Always pair it with a control**: the same test body with the trigger removed, which
   must pass before *and* after. This is the code-level twin of the "precondition as an action" rule
   above, and it earns its keep the same way — a red test on its own proves that *something* is broken,
   never that the trigger is what broke it, and a reviewer cannot tell the difference from the diff.
   While you are checking the harness, neuter each fixture the repro needed (a mock knob, an injected
   ordering) and confirm the test then fails: a fixture that changes nothing is dead weight claiming a
   necessity it does not have. That check has exposed a mock knob that was inert until an assertion was
   added which actually depended on it.

**Rung 3 is about a mechanism, not about the incident.** These are two different claims and the ladder
does not connect them: a test can genuinely reproduce a real defect that is *not* the one that fired in
production. When the work started from a specific incident, carry a separate verdict — does the
reproduced mechanism match the incident's **signature** (the actual timestamps, identifiers, node, and
ordering from the logs)? If it does not, say "rung 3 on a defect of the same class; incident cause still
open," ship the fix on its own merits, and keep the investigation open. Do not let a green repro close
an incident it does not explain. A rung-3 test and a shipped fix can legitimately coexist with an
unexplained incident; conflating them closes the ticket wrongly.

Rung 3 is the goal; **say so plainly when you only have rung 1.** Three traps to check for by name:

- **Begging the question.** A test that reaches the bad state by *directly setting* the variable whose
  reachability is in doubt (writing the watermark, injecting the flag) demonstrates rung 1 with extra
  steps. It is not rung 2. Ask: "did I construct this state, or did the system?"
- **Already-covered mechanism.** Before writing a repro, search the existing suite for the branch. If
  a passing test already exercises it, the mechanism was never in doubt and a new test adds nothing —
  the open question is the arming, one level up. Worse, an existing test may encode the suspect
  behavior as *expected*, which is itself a finding: it means the contract, not just the code, is
  written in the wrong terms.
- **Unreachable state.** Before writing a repro, go find the code that would have to *permit* the
  dangerous state and read it. A guard you had not noticed can make the whole hypothesis impossible,
  and a test written anyway will either be forced (rung 1 dressed up) or quietly assert the wrong
  thing. A single line enforcing that a counter only advances by exactly one has refuted a hypothesis
  that had already survived a full write-up, found by asking "what code lets this happen?" instead of
  "how do I test this?"

When rung 2 cannot be reached — the precondition is a cross-node, cross-process, or timing state a
unit test cannot construct, and no single-component code path produces it — that is a legitimate and
publishable result: **"narrowed to one predicate, arming not established."** Name the cheapest
instrument that would settle it (an integration test at the right scope, or production forensics such
as the on-disk counters and surrounding logs at incident time). Do not inflate it to a root cause, and
do not discard it as nothing: a defect localized to one predicate plus a named next instrument is
often the most valuable thing a hard investigation produces.

**Rung 2 has a measured variant, and it can demote your own argument.** Reading the code to argue a
precondition is reachable is rung 2 by inference; *measuring* the window is rung 2 by observation, and the
two can disagree. A code argument that a stalled peer widens a dangerous window died against production
timings showing the window is ~40ms against a 10s guard, with the slow part of the operation happening
after the point that mattered. Measure before defending a reachability argument, and when the measurement
contradicts the argument, mark the argument weakened in the document that contains it rather than quietly
editing it. Beware the reverse error too: a measured rate can be far too low to explain the observed
incident count, and that gap is a finding ("frequency unexplained"), not licence to pick whichever
conclusion you preferred.

**Calibrate the instrument to the hypothesis before running it, not after.** Write down the effect size
the hypothesis predicts, then check the instrument can resolve it. A metric sampled every 20 seconds
cannot see a 30-unit discontinuity in a series that legitimately moves by 1,300 in that time; querying
it anyway produces a clean, confident, worthless negative — and a negative result reads as evidence,
so it does real damage. State the predicted magnitude and the instrument's resolution side by side in
the report. If they do not overlap, the honest output is "not measurable with this instrument," never
"not observed."

Corollary worth stating in the report: if a log line or metric is emitted on **both** the healthy and
the buggy path, it is not diagnostic. Verify that before treating its presence in an incident as
evidence — an existing passing test that emits the same line is proof it is ambiguous.

## Using agents and model tiers

Phase 3 (grounding) fans out well: one agent per subsystem or per source, on a cheaper/faster model,
each returning a small structured map. Phase 4 (picking the property) and phase 8 (explaining the
trace) are the judgement-heavy steps; use a stronger model there. Keep total fan-out bounded; this
skill should feel quick. Request tool installs (a JRE, `tla2tools.jar`, optionally Quint) when a
phase needs them, preferring the no-admin path in `reference/03-tooling-setup.md`.

## Long runs and context

An investigation fills context fast: grounding agents, several model runs, then the report. Follow
whatever context and subagent-lifecycle rules are already in force; they take precedence over anything
here. What is specific to this skill is *what* to preserve, and that lives in
`reference/08-context-and-checkpoint.md`: a `CHECKPOINT.md` next to the model files carrying the
property, the anchors, the run results so far, and the next action. Write it at a clean boundary (after
a verified result, not mid-model), never as a rushed dump once the context is already gone.

---

From [xroche/skills](https://github.com/xroche/skills). Written by Xavier Roche, MIT licensed.
