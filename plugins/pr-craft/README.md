# pr-craft

Two Claude Code skills for the two places a pull request wastes people's time:
the review, and the wait.

**`/mechanical-refactor <description>`** turns a large mostly-mechanical diff
into a PR a human can actually review. The mechanical part is produced by a
short migration script, committed on its own before its output, so the reviewer
reads twenty lines of `sed` and skims the thousand lines it generated. What the
script could not produce lands in a separate commit and is reviewed normally.

**`/babysit-ci [PR]`** diagnoses a red run: which leg failed, why, whether this
PR caused it, and the fix. It pushes and returns. It does not sit in a loop
waiting for green, because `gh pr merge --auto` already does that for nothing.

## Why the script, and not just a big diff

A reviewer cannot tell a mechanical change from a subtle one by reading the
output, so they either read all of it or none of it, and both are bad. Reading
the script instead is bounded work: it says what the change does, and the diff
that follows is only the evidence that it did it.

The constraint that makes it work is the length cap: at most about twenty `sed`
commands. A script that grows a case per file has stopped being a claim and
become the diff again. Anything that needs a special case belongs in the
non-mechanical commit.
