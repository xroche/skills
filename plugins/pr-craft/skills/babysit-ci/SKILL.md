---
name: babysit-ci
description: Diagnose a red CI run on a PR, fix what the PR itself broke, push, and return once. Waiting for green belongs to auto-merge, not to a polling loop.
user-invocable: true
argument-hint: "[PR number]"
---

# Babysit CI

A PR's checks are red. Find out why, fix what this PR broke, push, return.

The name says babysit, but the job is diagnosis. An agent that wakes every few
minutes to ask whether CI has finished pays a full re-read of its context per
wake, and buys what `gh pr merge --auto` does for free. Arm auto-merge, return,
and come back when something is actually red.

## Usage

```
/babysit-ci [PR number]
```

With no argument, use the current branch's PR.

## Workflow

1. Get on the PR's own branch, and up to date with it:
   `gh pr view <PR> --json headRefName -q .headRefName`, then checkout and pull.
   A fix committed on the wrong branch looks identical to a fix that worked.
2. `gh pr checks <PR>` for the failing jobs. The output is TAB-separated, and a
   PR with zero checks reported is usually mergeable-state CONFLICTING, not an
   outage.
3. For each failure, fetch the job log
   (`gh api repos/{owner}/{repo}/actions/jobs/<id>/logs`), find the first real
   error rather than the last line, and decide one thing: did this PR cause it?
   Check the same job on the base branch before concluding it did.
4. Fix only what this PR broke. Build and run the tests locally, including the
   leg that would catch your change.
5. Push a follow-up commit, arm auto-merge, and return.

## Cancel the run in flight before you push

Otherwise the stale run holds the queue while the new one waits behind it.

```bash
run_id=$(gh run list --branch <branch> -L 1 --json databaseId -q '.[0].databaseId')
# gh run cancel sometimes hangs; the API force-cancel does not
gh api "repos/{owner}/{repo}/actions/runs/${run_id}/force-cancel" -X POST
git push
```

## Build the repo's failure map once

Which leg went red is most of the diagnosis, and that mapping is a property of
the repo, not of this skill. Derive it once from the workflow files (which job
builds what, which builds under a sanitizer, which packages, which lints, which
checks formatting or sign-off) and write it into the repo's own rules file, such
as `CLAUDE.md` or `AGENTS.md`. The next run reads it instead of rediscovering
it.

Two legs are worth knowing generically:

- **A sanitizer or fuzzer failure is a real bug, never flakiness.** ASan, UBSan,
  MSan and TSan report on the run whose heap layout happened to expose the bug.
  Do not retry it, skip it, or mark it allow-failure. Reproduce it and fix the
  cause.
- **A formatting job usually checks changed lines only.** Format against the
  branch's merge base, not the whole file and not the current default branch, or
  you will "fix" lines that only differ because the base moved.

## Rules

- Fix what this PR broke. A failure that is already red on the base branch is
  not yours, and saying so is a complete answer.
- Follow-up commits, not `--amend`: the branch is pushed, and rewriting it
  requires a force-push that may be denied and that breaks anyone tracking it.
- Sign off if the repo enforces DCO.
- Same error three times in a row: stop and report. The fourth attempt is
  guessing.
- Return once. Do not arm a watcher, and do not leave a sleep or wait timer that
  can outlive the return.
