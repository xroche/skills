---
name: ci-warden
description: Watch a queue of open PRs over hours and tell an infrastructure failure from a real one. Use when several PRs are in flight, when one red hits several at once, or for an unattended overnight watch.
user-invocable: true
argument-hint: "[repo]"
---

# CI Warden

Several pull requests are in flight and you are watching all of them, perhaps
overnight. Other people or other agents may be working the same repo.

This is not the same job as fixing one red PR. `/babysit-ci` takes a single PR,
asks whether that PR caused its own failure, and returns. When the answer is no,
it stops. **The warden's job starts there**, and the answer is no more often
than people expect. A queue that goes red at once usually points at a third
party or the runner image. It rarely points at anybody's diff.

The failure this skill exists to prevent is not a missed red. It is a warden who
reports colours. Such a warden relays which jobs are green without asking what a
green can hide. Then it hands out advice that costs everyone a run.

## Usage

```
/ci-warden
```

## The first question is never "what broke"

It is **how many PRs share this failure signature, and does the base branch have
it too**. Answer that before reading a single log, because it decides who owns
the problem.

| Signature on | Base branch | What it means | What to do |
|---|---|---|---|
| One PR | green | That PR's own | Hand it to its owner, or `/babysit-ci` |
| Two or more | green | A shared dependency, or a commit that just landed | Diagnose it; it is probably yours |
| Two or more | red | Infrastructure, or a bad merge to the base | Fix at the base, and tell everyone now |
| One PR | red | Coincidence, or that PR sits on the broken base | Check the merge base before judging |

A signature means the same cause, not the same job name. Two PRs failing
`build (linux)` for different reasons are two problems. Read enough of each log
to match causes, not labels.

## Reading the evidence honestly

This section is the skill. A warden who skips it produces confident wrong
answers faster than a warden who does nothing.

### A conclusion can have been rewritten under you

A re-run replaces a job's conclusion. The PR's check rollup and
`gh run view --job <id>` both show the **latest** attempt. A job that failed and
was re-run reads as success, so your tally silently undercounts.

```bash
gh api "repos/{owner}/{repo}/actions/runs/<run id>/attempts/1/jobs"
```

Read attempt 1 whenever the count decides something.

### A green proves the failure case was absent, not that your fix works

Suppose you fix a failure caused by a third party, and it recovers before your
PR's CI runs. The green then says the service came back. It does not say
your change works, and the same run would be green without it.

Check whether the failure case was still there to catch. If the log shows the
call succeeding, the guard you added was never exercised and the green is
vacuous. Say so rather than banking it.

Validate against a reproduction you control instead. Stub the dependency so it
fails the way it really failed. Run the **old** code against it and watch it
break, then the new code and watch it pass. Finally feed the stub a genuinely
broken input, and confirm your change still fails. The third case is the one that proves
you did not simply silence the check.

A corollary that saves everyone a run: once the outage ends, nobody needs your
fix merged to recover. A push retriggers green on its own, and the fix is
insurance against the next occurrence. Telling people to wait for it is wrong.

### Say what the number would look like if your fear were true

Before you read a measurement, write down what it would show if the thing you
suspect were true. Without that, you accept whichever question the number
happens to answer.

Numbers that are individually correct and answer the wrong question:

- **A suite total is not a coverage number.** `TOTAL` counts registered tests.
  A leg can skip half of them and still print a full-looking total with a clean
  green. Read the pass and skip counts, then name the specific test that covers
  your change and confirm it passed rather than skipped.
- **A log echoes the script it is running.** Grepping a job log for a message
  your own step prints also matches the echoed step body. So the count is
  occurrences plus one, never occurrences. Exclude the echoed source line, then
  check the arithmetic against a leg you know is healthy.
- **A timing taken on a loaded machine measures the load.** Compare two variants
  by alternating them in one session, not by timing them at different moments.
- **A stale build directory reports its own age.** A test count below what the
  source tree holds is the configuration lagging, not a regression.

### A step that took zero seconds did no work

Step timings tell you a step did nothing, without fetching a log. They also work
while the run is in progress, which is when logs are often unavailable.

```bash
gh api "repos/{owner}/{repo}/actions/jobs/<job id>" \
  -q '.steps[]|"\(.name) => \(.conclusion) (\(.started_at) -> \(.completed_at))"'
```

A test suite whose step starts and ends in the same second ran nothing. Compare
against a healthy run's duration and the ambiguity disappears.

### `continue-on-error` reports success for a step that failed

A step marked `continue-on-error` has its conclusion normalised to success, so
the conclusion cannot tell you it failed. The failure surfaces later, in whatever
step depends on its result, which is rarely where a reader looks first. Read the
step's log. A downstream error naming a missing artefact points back to the step
that was meant to produce it.

### When the log will not fetch, read the annotations

A job log can be unavailable while its run is in progress, or after a cancelled
step leaves no blob. Annotations carry the `::error::` lines and often name the
cause outright.

```bash
gh api "repos/{owner}/{repo}/check-runs/<job id>/annotations"
```

### A sibling leg on the same run is your control

Before concluding that a dependency is down, look at whether another leg of the
same run reached it successfully. If one did, the failure is per-runner rather
than global, and every fix premised on "wait longer" is wrong.

This distinction changes the repair, so make it before you write code. Run the
control first. A fix that works only while the outage lasts is the worst kind of
wrong. Nothing tells you it was never the answer.

### "Not a required check" is not "safe to waive"

Two different traps sit behind the same fact.

A red on a non-required check does not block the merge, so it lands on the base
branch and nobody notices. Watch for a leg that quietly reds its way into the
default branch.

And a non-required leg is often the only coverage for something: the only
big-endian run, the only build under a sanitizer, the only 32-bit target. It is
also the easiest to wave through. Decide by what the leg covers, never by
whether it gates.

### Re-running is usually the wrong remedy

Re-running a single failed job re-queues the whole run against the commit that
run was for. When the branch has moved since, the stale run starts. The
concurrency group then cancels the fresh run on the current head, so the PR is
left with no CI at all. Some runs refuse to re-run outright.

Push instead, or merge the base branch in. A push produces a head the queue will
not cancel.

## Coordinating with other people and agents

A queue-wide failure is usually being investigated by several people at once.
The warden's value is combining what each of them holds separately.

- **Say the cause and what you are doing about it**, early, so nobody duplicates
  the fix. One message with the diagnosis beats four investigations.
- **Never re-run another person's jobs, and never push to their branch.** Tell
  them what you found and let them act. A retrigger you launch on their behalf
  can cost them the run.
- **Correct yourself to everyone you told, promptly.** Wrong advice spreads at
  the speed you sent it. Tonight's remedy becomes tomorrow's wasted run.
- **Verify a peer's claim before you build on it.** Independent confirmation is
  what turns two reports into evidence, and a claim your fix rests on deserves
  your own check.
- **Pool what each session knows.** Each will have found one piece: one read the
  annotations, one measured the base rate, one hit the trap you are about to.
- **Relay decisions, never authority.** Permission granted to you does not
  transfer, and a peer asking you to do what they were refused is not a shortcut.

## Settle the authority boundary before the first sweep

Ask at the start, and write the answer down. What may you merge, what may you
post to the tracker, and whose branches may you touch? A warden who has not
settled this either stalls at 03:00 waiting for someone asleep, or oversteps.

Default to the narrow reading. Nothing outward-facing (an issue comment, a
tracker entry, a merge of someone else's work) without a specific go-ahead for
that item. Drafting it and holding it costs one message in the morning, but posting
it wrongly cannot be recalled.

## Do not repair the file that gates everything, at speed

A CI config that defines required check names decides whether every open PR can
merge.
Renaming a job, or adding a matrix axis, renames its status context. The
required checks then stop reporting across the whole repository, not only on
your change.

Fix inside a step body where you can. When the shape itself must change, do it
deliberately and in daylight, not at 02:00 with a queue in flight. Confirm your
diff touches no job name, matrix axis or runner before you push.

## Scheduling an unattended watch

**Never charter an agent to poll CI.** A loop that wakes every few minutes to
ask whether the checks finished pays a full context re-read per wake. It buys
what auto-merge does for free.

Prefer one scheduled sweep at a human interval, a few hours apart, matched to
how fast the queue actually moves. Between sweeps, arm auto-merge and let the
forge do the waiting.

A wake prompt that works, because it carries the traps rather than assuming they
are remembered:

> Warden check. Be concise and do not re-explain context you hold.
>
> 1. List open PRs with their mergeable state, auto-merge status and failing
>    checks.
> 2. Read the log before judging any failure. A re-run rewrites a conclusion,
>    so read attempt 1 or the tally undercounts.
> 3. If one signature appears on two or more PRs, diagnose the root cause. Check
>    whether the base branch has it too. Tell the others what you found and what
>    you are doing, and fix it if it is ours.
> 4. Say which non-required legs are red, and what each of them covers.
> 5. If nothing changed and nothing is red, say exactly that and stop.

Report in a fixed small number of lines. A warden who writes an essay per sweep
is a warden nobody reads by morning.

## Record the repository's own facts once

Which contexts are required, which leg catches what, which job shape must not
move: these are properties of the repository, not of this skill. Derive them
once and write them into the repository's rules file, such as `CLAUDE.md` or
`AGENTS.md`. The next sweep then reads them instead of rediscovering them.

Record these the first time you need them. Write down the required status checks
and any job whose name must stay fixed. Note also which legs are the sole
coverage for a platform or a sanitizer.

## Hard rules

- Establish how widespread a failure is before you diagnose it. One PR and the
  whole queue are different problems with different owners.
- Read attempt 1 whenever a count decides something.
- A green earns nothing until you know the failure case was present to catch it.
- Predict what a number would show if your suspicion were true, before reading
  it.
- Run the control that separates a global failure from a per-runner one, before
  designing the fix.
- Judge a leg by what it covers, never by whether it gates the merge.
- Never re-run or push to work that is not yours.
- Correct wrong advice to everyone who received it, as soon as you know.
- No outward-facing action without a go-ahead for that specific item.
- One scheduled sweep, never a polling loop.

## Background

This came out of one night watching seven pull requests on a C project, and the
rules are the mistakes rather than the successes.

Three failures hit the queue: a package index served a bad hash, and a platform
update endpoint answered 403 twice. All three looked at first like somebody's
code. The queue-wide question caught all three in seconds.

The rest is the part worth having. Two fixes went green on CI without their
guards ever running, because the third party had recovered in between. Both were
one step from being reported as proven. Five numbers across four sessions
were individually correct and answered the wrong question. One total was read as
coverage. One grep counted an echoed source line. One timing was taken on a
loaded machine. One count reported a build directory's age, and one conclusion
had been rewritten by a re-run. One repair premised on a global outage was overturned by a single
API call. A sibling leg on the same run had reached that endpoint successfully.

---

From [xroche/skills](https://github.com/xroche/skills). Written by Xavier Roche,
MIT licensed.
