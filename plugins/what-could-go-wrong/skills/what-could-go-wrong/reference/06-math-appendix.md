# Math appendix: how the model checker works

This file is optional. The plain-language report stands on its own, and nothing in the skill requires you to read this. It is here for the reader who wants to know what the machine is doing when it turns a suspicious piece of concurrent code into a counterexample.

## A program as a state machine

Think of a running program as a point moving through a space of states. A state is just the current value of every variable that matters: the counter is 3, the lock is held, the queue holds two items. A step is one atomic action that changes the state, for example incrementing the counter from 3 to 4. A behavior is a sequence of states, each reached from the previous one by a single step:

```
s0 -> s1 -> s2 -> s3 -> ...
```

TLA+ describes which behaviors are allowed using two pieces of logic. `Init` is a predicate that says which states are legal starting points. The next-state relation, written `Next`, is a predicate over a pair of states (the current one and the one after) that says which single steps are allowed. A behavior is allowed when its first state satisfies `Init` and every adjacent pair satisfies `Next`. That is the whole formalism. Everything else is convenience on top of it.

## PlusCal versus TLA+

Writing `Init` and `Next` as raw logic is precise but tedious for anything with control flow. PlusCal is an imperative pseudocode layer that reads like a normal program and compiles down to that TLA+ math for you. It has processes, `while`, `if`, `await`, assignment, and labels. Here is a fragment:

```
process worker \in 1..2
  variables tmp = 0;
{
  read:  tmp := counter;
  write: counter := tmp + 1;
}
```

The words `read:` and `write:` are labels. A label marks a boundary between atomic steps. Everything between one label and the next happens as a single indivisible action. So this worker takes two steps: first it copies `counter` into its local `tmp`, then, as a separate step, it writes `tmp + 1` back. Splitting the read from the write at a label boundary is exactly what lets a second worker slip in between them. Where you place labels is where you decide the grain of atomicity, and that grain is usually the crux of a concurrency bug.

## Interleaving

With two workers, each sitting between labels, the checker does not pick one order and run it. It considers every order in which the processes could take their next step. Worker 1 might do `read`, then worker 2 does `read`, then both `write`. Or worker 1 runs both its steps before worker 2 starts. Each distinct ordering is a different behavior, and the checker walks all of them.

This is why concurrency bugs are hard to find by hand and easy to find here. The bug lives in one specific interleaving out of many, often one you would never think to test. It is also why the state space explodes. With P processes and roughly L steps each, the number of orderings grows faster than any product you would want to enumerate on paper, and adding a third process or a larger data domain multiplies it again. So we keep models tiny on purpose: two or three processes, a data domain of two or three values. The smallest model that can express the bug is almost always enough to trigger it, and it stays fast to check.

## Safety versus liveness

Properties come in two flavors. A safety property says nothing bad ever happens. "The counter is never negative." "Two workers never hold the lock at once." A safety property is an invariant: a predicate that must hold in every state the program can reach. It can be checked one state at a time, because a single bad state is already a violation.

An invariant, stated plainly, is a condition on a single state that you claim is true of every reachable state. Not every state you can imagine, only the ones actually reachable from `Init` by legal steps.

A liveness property says something good eventually happens. "Every request eventually gets a response." Liveness is about whole infinite behaviors, not single states, and it only makes sense under fairness assumptions that rule out a process being starved forever. Checking it needs temporal operators and costs more. This skill is almost always safety-only. We assert an invariant and ask whether any reachable state breaks it. That covers the bugs we care about here: lost updates, torn reads, illegal combinations of component states.

## What TLC actually does

TLC is the explicit-state model checker for TLA+. It performs a breadth-first search of the reachable state graph. It starts from every state satisfying `Init`, then repeatedly takes each frontier state, computes every successor allowed by `Next`, and checks the invariant on each new state before adding it to the queue. It remembers states it has already seen so it never revisits one.

When it reaches a state that violates the invariant, it stops and prints the path from an initial state to that bad state: the counterexample trace. Because the search is breadth-first, the first violating state it reaches is at minimum distance from the start, so the trace it prints is the shortest possible. That is what makes it a good bug report. There is no incidental noise, no unrelated steps padding it out. Every step in the trace is necessary to reach the failure, so reading it top to bottom tells you the exact interleaving that breaks the design, and nothing else.

## Assume-guarantee reasoning, briefly

Real systems are built from components, and you would like to reason about each one on its own. Assume-guarantee (also called compositional) reasoning does that. Each component is proved correct against its own contract, assuming that its neighbors honor their contracts. Component A guarantees a certain output behavior provided its inputs meet certain assumptions. Component B assumes A behaves that way. The interesting bugs live at the discharge points: the places where you must show that A's guarantee actually implies B's assumption. When that implication quietly fails, both components can be correct in isolation while the composition is broken.

Be honest about a limitation here. An explicit-state checker like TLC does not discharge composition for free. It does not prove the assume-guarantee obligations as a theorem. What the toy models in this skill do instead is concrete: model the neighbor, then deliberately weaken or drop the guarantee we suspect is not really upheld, and let TLC explore. If the missing guarantee matters, the checker exhibits a reachable state where the next component's assumption is violated, and prints the trace. You get a demonstration of the gap rather than a proof of its absence.

## What this proves and what it does not

A counterexample is trustworthy in one direction. When TLC prints a trace, that behavior is genuinely allowed by the model, so it is a real flaw in the abstraction you wrote. If the abstraction faithfully captures the part of the system you meant to capture, you have found a real design bug, and the trace tells you how to hit it.

A clean run is weaker. "No error found" means only that no reachable state within this bounded model violates the invariant. It says nothing about states outside the bounds you chose, and it is not a proof about the actual source code. Between the model and the code there is a gap: the model is an abstraction, and it can omit exactly the detail where the real bug hides. A green result raises your confidence. It does not close the case. The report's confidence footer restates this every time, so a reader never mistakes a passing model for a verified program.
