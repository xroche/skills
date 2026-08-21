---
name: mechanical-refactor
description: Large mechanical refactoring workflow with migration script and 4-commit split for reviewable PRs
user-invocable: true
argument-hint: <description of the refactoring>
---

# Large Mechanical Refactoring

When a refactoring produces a large diff that is mostly mechanical (find-and-replace,
signature changes, pointer-to-reference conversions, etc.), follow this workflow
to make the PR reviewable.

Refactoring to perform: $ARGUMENTS

## Step 1: Write a migration script

Write a self-contained bash script that reproduces the mechanical changes from
a clean base branch state using `sed`. The script must:
- Start with `set -euo pipefail` and `cd "$(git rev-parse --show-toplevel)"`
- Be deterministic (running it twice produces the same result)

## Step 2: Keep the script short

**At most ~20 `sed` commands.** Rules:
- Use broad `sed` patterns applied to file arrays, not per-file replacements.
- Never add a `sed` for a single-occurrence replacement. Move it to commit 4.
- Prefer a few general regexes over many precise ones.
- Accept that the script won't cover everything. Commit 4 handles the rest.
- If it exceeds ~20 seds, refactor: find broader patterns or remove single-occurrence replacements.
- Use bash brace expansion (`{7..14}`, `{a,b,c}`) when it reduces verbosity over listing items individually.

## Step 3: Split into commits

1. **Commit 1 (script only):** Add the migration script (e.g., `tools/migrate-xxx.sh`).
   Lets the reviewer read it before seeing the diff.
2. **Commit 2 (large, mechanical):** Output of running the script, formatted with
   the repo diff-scoped formatter. Reviewer reads the script from commit 1
   instead of this diff. Message: `<scope>: apply migration script` (commit 1
   already describes the change).
3. **Commit 3 (cleanup):** Remove the migration script.
4. **Commit 4 (non-mechanical):** Everything the script couldn't produce.
   Reviewed as a normal diff. Skip if nothing to add.
5. **Commit 5+ (CI-dependent data, optional):** Golden files, generated output,
   or other data that can only be obtained after CI runs. Add as needed after
   each CI iteration. Mark as "skim only" in the PR description.

To produce the split:
1. Add the script file, commit as "commit 1"
2. Run the script, format the touched lines only, commit as "commit 2"
3. Remove the script file, commit as "commit 3"
4. Apply non-mechanical changes, commit as "commit 4" (skip if none)
5. If CI reveals golden file mismatches, extract correct data and commit as "commit 5"

## Step 4: PR description format

```markdown
## Review

1. Commit 1 (1 file) -- migration script. Read this first.
2. Commit 2 (N files) -- script output. Review the script instead.
3. Commit 3 (1 file) -- removes the script.
4. Commit 4 (P files) -- non-mechanical fixes. Review normally.
5. Commit 5 (Q files) -- golden files from CI. Skim only.
```

Omit commits 4 and 5 if not needed.
