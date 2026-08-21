# Checkpointing an investigation

A full investigation (grounding agents, several model runs, a written report) fills context fast, and
quality drops once it is tight: earlier facts fall out of view and the model starts re-deriving what it
already established.

Whatever context and subagent-lifecycle rules are already in force take precedence over this file, and
so does a `checkpoint` skill if one exists — invoke it. What follows is what is specific to *this* skill:
which facts an investigation must not lose, and where to put them.

## When

At a clean boundary, meaning after a verified result and never mid-model. Grounding done plus one full
model run is usually the right moment. Checkpointing mid-model saves a state nobody can resume from,
because the interesting part (does it go red, and why) is exactly what is not yet known.

## What to write

A `CHECKPOINT.md` in the investigation workspace, next to the model files, so the models are runnable
immediately with the recipe in `03-tooling-setup.md`.

```markdown
# Checkpoint — <the worry, one line>

## Where we are
Phase reached: <e.g. phase 7, mutation test done>.

## The property under check
<"X must never happen", in one sentence.>

## Files
- Model: <path to the .tla / .cfg>
- Grounding map: <path or a 5-line summary of components + shared state + protection>
- Report so far: <path, or "not started">

## Findings so far
- <bug found + shortest trace, OR "no violation at size N (mutation test passed)">
- Key code anchors: <file:line list the model cites, with the ref they were read at>

## Next steps
1. <the very next action>
2. <...>
```

Short and factual. The test is whether a fresh session can open this one file and pick up in under a
minute.

## After writing it

Say where it is, then give a **restart sentence**: one copy-pasteable line naming the file to read
first and the next action, e.g. `Resume the <worry> investigation — read CHECKPOINT.md in <dir>, then
<next step>`. One sentence; the fresh session gets its detail from the file, not from that line.

The checkpoint is a safety net, not a stop sign. If there is context left, keep going.
