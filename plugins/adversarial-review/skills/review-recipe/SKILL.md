---
name: review-recipe
description: Narrow-charter PR review for correctness-critical code. Spawns one agent per invariant (not "find bugs"), audits tests against spec instead of against code, and flags risk-area changes that lack runtime probes. Use when a wrong-shape PR is more expensive than a slow review.
user-invocable: true
argument-hint: <PR number or branch> [-- invariant1 invariant2 ...]
---

# Review Recipe

A narrow-charter PR review. Use it when correctness matters more than style
nits and a wrong-shape change would be expensive to walk back.

Inputs: `$ARGUMENTS` is one of:
- A PR number on the current repo's default remote (e.g. `199351`).
- A `owner/repo#NNN` reference (e.g. `llvm/llvm-project#199351`).
- A local branch name (review the diff against the merge base).
- Optionally, `--` followed by one or more invariant names to focus on.

## Why this exists

Generic "review the diff for bugs" charters tend to surface generic
findings: style, missing tests, comment quality. They miss correctness
bugs the diff is structurally exposed to, because the charter does not
ask the agent to verify a specific guarantee.

Two patterns that catch what generic review misses:

1. **One agent, one invariant, one verdict.** Hand the agent a single
   property the diff must preserve, ask it to construct adversarial
   cases against that property, report yes/no.
2. **Tests audited against spec, not against code.** A test whose
   assertions are derived from observed code behavior locks the code
   in, bugs included. Adversarial test review asks "construct a code
   path where this test passes but the spec is violated."

This skill drives both patterns plus a risk-area verification-surface
check.

## The two techniques that produced the most signal

Reach for these two first, instead of rediscovering them halfway through a
review.

**Double one invariant across two models.** Run the same charter on two
different models and compare the verdicts, because the agreement is itself the
evidence. Two models rarely rationalise the same broken path, so an independent
double PASS is worth far more than one agent's PASS. Step 3 holds the mechanics
and the rule that a disagreement is inconclusive.

**Build a mutation matrix over the clauses of one guard.** Mutate each clause of
the guard on its own, then record which tests turn red for each mutation. The
off-diagonal passes are the payload, because they prove that each test fails for
its own clause and that no test is standing in for another test's coverage. Step
4b holds the method.

## Workflow

### Step 1: gather the diff and context

- Use `gh pr view <PR> --json headRefName,baseRefName,title,body` if a
  PR is named, then `gh pr diff <PR>`.
- Otherwise diff the branch against its merge base.
- Read any `CLAUDE.md` at repo root and in directories the diff touches.
- Skim the PR description / commit messages for the author's intent.
- Split the added lines into test and product with `git diff --numstat
  <base>...<head>`, counting a `_test` suffix, a `test/` path, `testdata/` and
  any golden file as test. Record both numbers, because Step 5j's trigger and
  the report both read them.

Capture: the diff, the touched paths, the project's coding rules, the
author's stated goal, and the added test and product line counts.

### Step 2: identify invariants

The user may have passed invariants after `--`. If not, infer 1-4
invariants from:

- Risk-area heuristics (Step 4) -- if the diff touches an ABI / wire
  format / public API / concurrency primitive, that area has known
  invariants.
- Domain conventions in any `CLAUDE.md` or repo docs ("we always X",
  "Y must hold").
- The PR description's claims (if the author says "this preserves Z",
  Z is an invariant).

If you cannot name 1 invariant, ask the user. Do not proceed with
"general correctness" as the charter; that is the failure mode this
skill exists to avoid.

For each invariant, write a one-sentence statement of the property
*and* an example of what would violate it. The example matters: it
constrains the agent's adversarial search.

### Step 2b: reader legibility (one agent, strongest model, FIRST)

Run this before the invariant agents, and run it on any diff that adds a file or a
function, or grows a file by more than about thirty lines.

It goes first because it gates the value of everything after it. A diff a
maintainer cannot follow does not get reviewed; it gets skimmed, approved on
trust, or left to rot, and the correctness passes below then certify code nobody
will be able to change safely. Measured on a real PR: this skill ran four times
over about fifteen agents and reported the diff clean each time, and the human
reviewer's first and strongest comment was "the tests are really hard to parse
... they were already structurally hard before". Every comment in that diff
passed the prose pass individually. The file did not, because the defects were
aggregate.

Use the strongest model available (`fable`, else `opus`). Never a cheap model
here. This is not pattern matching against a rule list, it is simulating a
reader's comprehension, and a cheap agent asked "is this readable" returns
generic nits, which is the bikeshedding this step must avoid.

> Read each file the diff adds or grows, whole, top to bottom, the way its next
> maintainer will. Do NOT review the diff hunk by hunk. Answer each probe with
> file:line and a concrete fix:
>
> - Does each name carry the distinction it exists to express? A file that
>   contrasts two things and calls them `A` and `B` stores the contrast in the
>   reader's memory instead of on the page. Propose the rename or the label.
> - Is each argument's meaning guessable at the call site alone? Cover the
>   helper's definition and read the call. A sentinel with silent meaning (an
>   empty string that means "the admin key") fails; propose the readable
>   spelling.
> - Can a reader tell what the file asserts without opening another file? Where
>   expectations live in a golden or a fixture, judge whether the label alone
>   says what a wrong answer would look like. A label naming the behaviour
>   passes; a label naming a row number in a document outside the repo fails.
> - What must be held in working memory at the file's worst point? Count live
>   variables, in-flight state and locally defined helper contracts at that line.
>   Name the line and the count. Six or more is a finding.
> - Is there a shorter shape that says the same thing? If a sibling file in the
>   same directory already has the better shape, cite it as the target.
> - Read every doc comment the diff puts on a declaration you would have to
>   understand to use it. Answer two questions about each block, and answer the
>   first one before you count anything.
>   - Did you have to read the block twice before you could state what the
>     declaration guarantees? Report that honestly, because your own re-read is
>     the only instrument this probe has. A block you re-read is a finding
>     whatever its sentence lengths and whatever its ratio to the body, and when
>     you name THE single highest-value edit below, a re-read block outranks
>     every finding that rests on a word count or a line count.
>   - How many lines does the block spend? A doc comment on a declaration exists
>     to give a caller the contract, so it earns about ten lines of prose, plus
>     one line for each parameter and return value it documents. Ten lines is
>     roughly what a reader takes in before the declaration itself scrolls off
>     the screen, and the per-parameter lines are contract rather than
>     explanation, so they do not compete with it. A block past that cap is a
>     finding, and so is a block longer than the body it describes, which catches
>     the small case the cap lets through. Give both counts, the comment's and
>     the body's, because a block can sit at a quarter of the body's length and
>     still be three times the cap.
>
>   Then say where the material over the cap should go. A threat model, a
>   rationale, a history or a list of alternatives belongs in the PR body or the
>   ticket, and an invariant the caller must respect stays in the comment.
>   Propose the cut, not a rewrite of equal length. Never propose splitting one
>   long sentence into several short ones, because that keeps every fact and adds
>   lines, so it makes the block worse against both questions above.
>
> Tag each finding DIFF (the diff introduced or worsened it) or PRE-EXISTING
> (the file was already hard and the diff added to the pile). Report
> PRE-EXISTING findings, because that is a verdict a human reviewer will reach,
> but mark them advisory.
>
> Then name THE single edit that buys the most comprehension per line changed,
> with its line estimate. Rank at most three findings by that ratio and drop the
> rest. Do NOT propose a rewrite, a new abstraction, or any edit whose line
> count you cannot justify in one sentence. Do NOT restyle code the diff never
> touched. If the file reads fine, say so in one line and stop.
>
> Do NOT comment on correctness, on the wording of a single sentence, on
> signature shape or on idiom conformance; those are other steps. Judging whether
> a doc comment is worth its length IS yours. Stay under 500 words.

The single named highest-value DIFF finding is BLOCKING. Illegible code you
wrote is yours to fix now, when you are the only person who has read it, and
that holds on any review, not only a self-review. A doc block that failed the
one-read question is a DIFF finding, so it blocks whenever it is the named
highest-value edit. The other DIFF findings are
craft findings with the standing of Step 5g, so Step 5j's precedence rule
applies to them, and a rename beats a new named entity only one call site would
use. PRE-EXISTING findings never block
and never mandate a cleanup commit: they go to the human, who decides whether
this PR pays the debt down.

**Why no word count could have caught this, and why these rules are not
redundant with the word limits.** Numeric sentence limits were once the whole
comment rule here, and they let a 36-line doc block through five prose passes on two
models before the human reviewer called it "long as a book". Every sentence in
it was inside the 25-word limit, because one earlier pass had split a 59-word
sentence into four short ones and reported that as a fix, which left the block
longer than it found it. The block was about a quarter of the length of the
134-line function under it, so the longer-than-the-body rule never fired either.
A word count measures the sentence a writer produced. It cannot measure whether
a reader can hold the block in one pass, and it cannot see that the same
explanation is already written in three other artifacts. So keep the one-read
question, the line cap and Step 5e's cross-artifact search even when every
sentence passes its limit, because those three are what the counting rules are
blind to. Do not delete them as duplicates of the word limits.

Two probes overlap neighbours, so ownership is fixed here. When the fix to a
call-site argument is a signature change, Step 5g owns it; this step owns it
only when the fix is a name or the spelling at the call site. On comments, this
step owns the verdict on length and on whether a reader can act on the block at
all, and Step 5e owns the sentence-level rules applied to whatever survives.
Step 5e also owns the search for the same prose in the PR body, the ticket and
the project docs, because it is the step that already has the PR body open.
Step 5h asks
whether a name matches its neighbours, this step asks whether it carries meaning
at all: `A` and `B` pass 5h when every sibling file uses them, and fail here.

### Step 2c: witness check (one agent, strong model, if the diff adds elements)

Skip on a diff that only edits existing logic. Run it when the diff adds a guard,
branch, bound, parameter, config value, handler, log line, test, wait, fixture or
comment.

Every other charter here proves the diff PRESERVES an invariant. An element that
does nothing preserves every invariant, so it is invisible to all of them: a
guard that cannot be false, an assertion that cannot fail, a flag nothing reads,
a comment whose referent exists only in the author's notes. This step carries the
converse burden. An addition must show its witness.

This gap is not theoretical. On a real PR an earlier round of this skill
*suggested* adding a wait, a later round certified that wait as sound, and a
human then pointed out it returned on its first poll and synchronised nothing.
Asking "is it correct?" can never catch "is it needed?".

> For each element the diff ADDS -- guard, branch, retry or timeout bound,
> parameter, config value or flag, error handler, log line, assertion, wait or
> poll, fixture, comment, identifier -- produce its witness: the concrete input,
> state, caller or reader under which that element changes an outcome or resolves
> for a reader of this repository. Cite it: file:line for a caller or state, a
> repo path for a referenced concept or document. Report each as one of:
>
> - WITNESSED -- give the witness.
> - DEAD -- no witness exists: the condition cannot be false, the assertion
>   cannot fail, the bound cannot be reached, nothing reads the value, every
>   caller passes the same argument, the awaited state holds at entry, no
>   assertion uses the fixture. Show why.
> - UNRESOLVABLE -- a comment or identifier names a concept a reader of this repo
>   cannot find. List where you searched.
> - CANNOT-DECIDE -- reachability depends on code more than one hop from the
>   diff. Say where you stopped.
>
> A deliberately dead element (a defensive guard, an invariant assert, a
> parameter reserved for a stacked PR) is still DEAD unless the code states the
> reason where a reader will see it. A justification that lives only in the PR
> body does not count. Do NOT comment on correctness, style, placement or test
> adequacy. Stay under 500 words.

A DEAD element inside a test is BLOCKING: an assertion that cannot fail, a wait
satisfied at entry or a fixture nothing checks makes Step 4 report coverage that
does not exist, which is a missing test wearing a passing test's clothes. A DEAD
product element or an UNRESOLVABLE reference is a change request, like a
DUPLICATE in Step 5b, and BLOCKING on a self-review. CANNOT-DECIDE is reported,
never dropped.

### Step 3: spawn narrow agents (one per invariant)

In one message, spawn the agents in parallel. Per-agent charter shape:

> Given invariant <STATEMENT>, verify the diff preserves it for every
> code path. For each path that might violate the invariant, construct
> a concrete example showing the inputs, the resulting behavior, and
> whether it violates the invariant. If you find ANY violation, that
> is a P0 -- report it loudly, lead with the minimal repro, and stop.
>
> Do NOT comment on style, tests, comments, or anything outside this
> invariant. Stay under 600 words.
>
> Return ONCE and stop. Do not arm a watcher, do not re-notify, and do
> not leave a sleep or wait timer that can outlive your return.

The agent must:
- Construct adversarial cases, not just read the code top-down.
- Cite specific lines / paths where each case would land.
- Distinguish "definitely violates" from "possibly violates / can't tell".

#### Never leave a timer running past the return

Every charter carries the "return once" line above, verbatim. A report-length
budget caps what an agent *writes*; it does not reach a `sleep` the agent armed
for its own pacing, which fires long after the verdict is delivered and costs a
full re-read of the parent's context to say "that was only my timer". It is a
hard charter line rather than advice. Stop any agent that notifies with nothing
new.

#### Double the model on complex invariants

For a high-stakes or complex invariant -- hostile-input parsing, concurrency
/ memory model, ABI / struct layout, crypto, anything where a missed bug is
expensive to walk back -- run the *same* charter on two different models in
parallel (set the Agent tool's `model`, e.g. one `opus` and one `sonnet`) and
compare their verdicts. The signal is in the agreement:

- Both say PASS independently -> much stronger than one agent; a single model
  can rationalize a broken path, two rarely rationalize the *same* one.
- Both flag the same violation -> rules out a single-model hallucination;
  treat it as real and lead with it.
- They disagree -> inconclusive. Do not average. Read the cited path yourself
  and adjudicate; the disagreement usually points straight at the subtle case.

Don't double trivial or mechanical invariants -- it just doubles cost. Reserve
it for the one or two invariants whose failure is the reason you're running
this skill. (Borne out in practice: on a hostile-input network diff, doubled
Opus+Sonnet agents independently agreed on every PASS and both caught the same
unbounded-read hang.)

### Step 4: test-design audit (one agent)

Charter:

> For each new or modified test in the diff, ask: "if the code were
> buggy in way X, would this test catch it?" Construct one such buggy
> code path per test. For each test where you can construct a buggy
> path the test would pass, that is a confirmation-biased test --
> report it with the constructed buggy path. Also report any test
> whose assertions look derived from observed IR / output rather than
> from a spec invariant.
>
> Stay under 400 words.

**A confirmation-biased test takes six shapes.** Across three consecutive
rounds on five branches, every single finding was a test that passed for a reason
other than the one it advertised, and not one finding was a wrong behaviour in
product code. So hunt these shapes by name rather than only stating the
principle:

- An assertion cannot tell two states apart, for example a NULL and an epoch
  zero that are read back through the same cache.
- A table passes against a wrong implementation, because no row distinguishes the
  wrong implementation from the right one.
- A check accepts any error, where the identity of the error is what decides the
  behaviour.
- A race's check missed its own injected bug in eighteen runs out of twenty.
- A request asserts only that it did not error.
- A test name claims a consequence that no assertion in the test checks.

The class recurs, so the audit has to recur with it. These shapes turned up in
tests that were written to satisfy an earlier round's finding, which means a
construct added because a review asked for it needs the same audit as any other
line.

Then apply the testing bar, which is a GATE, not a note. A behavior-bearing
change -- especially one that alters a serialized / wire / on-disk /
cross-service format --
with no test that exercises the *changed path* is a BLOCKING finding. "The
harness can't force this path" is a reason to add a test seam, not a reason to
waive the test. Also flag brittle docs: comments that narrate a call site, the
surrounding flow, or the diff instead of the contract -- they rot when the
caller moves and are a common LLM tell.

**Cover the path, then ask what the coverage cost.** This gate creates real
pressure to reach an awkward path by any means available, and the cheapest means
are the ones reviewers reject: driving a fake or mock so the object under test
can be poked from inside, asserting on a log line as a side channel, reaching
into private state, or asserting on an object *after* a call that failed. A test
that needs any of those is evidence about the *design*, not a test to be
congratulated. Report it as a design finding: name the seam that is missing and
the smaller unit that wants extracting, so the test becomes ordinary. Prefer
"extract this predicate into a free function and test it directly" over "add a
harness that can force the private path". A demand for coverage that is satisfied
by scaffolding trades one review round for another.

So for each test in the diff, answer both questions and report both: does it
catch the bug (adequacy), and what did it have to touch to run (shape). Flag
specifically: assertions on state left behind by a failed or throwing call, a
log or metric read as a test channel, a fake whose only purpose is to expose
internals, a bare literal repeated across assertions where a named constant
belongs, and a helper whose parameter names do not say what they hold. Propose
that constant only inside the file the test lives in. Retiring a lint
suppression across other files is a refactor of its own, and Step 5j owns it.

**A wait is a test of the schedule; audit it like one.** For each wait, poll,
retry or barrier the diff adds, name the state before the operation and the state
the poll waits for. If the predicate already holds beforehand, the poll succeeds
on its first call and the wait waits on nothing: report it, and either delete it
or replace it with a single asserted probe. A comment conceding the state never
changes ("refuses throughout") is the tell, not a justification. The question is
not "is this wait sound?" but "under what schedule does its first attempt fail?"
If you cannot construct that schedule, the line should not exist. Measure rather
than argue where you can: record what the first poll actually sees.

### Step 4b: test necessity and folding (one agent, after the test-design audit)

More tests do not mean a better PR. Every other step in this skill pushes toward
adding a test, and none of them asks whether the set that came out earns its
size. Run this after Step 4, because it works from Step 4's mutations.

Charter:

> Enumerate every test the diff adds across every file of the diff at once,
> never file by file, and count each row of a table-driven test as a test of its
> own. A new test file commonly re-pins a function an existing table already
> drives through a caller, and that overlap is invisible to a per-file walk.
> For each one, name the mutation of product code that turns it red, then record
> every test that same mutation turns red. Build the matrix of mutations against
> tests and report:
>
> - Two or more tests die to exactly the same mutation set. They are one test
>   wearing two names, so say which one survives.
> - One test's mutation set is a subset of another test's. Report it as redundant
>   unless you can name a mutation that only it catches. Two exceptions. A test
>   whose mutation set against this diff is empty is not redundant when it pins a
>   precondition the new product code relies on, so name the reliance with
>   file:line and keep the test. The simplest case in a table is not redundant
>   when a reader uses it to read the rest, even where a busier case subsumes it.
> - Separate test functions walk the same path with different data. They want to
>   be rows in one table, so propose the table.
> - A test whose named subject is a function in a package the diff does not
>   touch. Say so and give the path. A mutation matrix marks such a test
>   necessary the moment it uniquely kills a mutation, so the matrix rewards
>   scope creep instead of catching it, and only this bullet reports it. Where
>   it does kill a mutation of that untouched code, it is real coverage sitting
>   in the wrong package: say it belongs in that package's own test file, and
>   never propose deleting it.
>
> For every fold you propose, state the invariant that makes it safe. Every
> mutation that turned some test red before the fold must still turn some test red
> after it. When you cannot state that for a fold, do not propose the fold.
>
> Do NOT propose a fold that keeps the count down by widening an assertion, for
> example a specific error becoming any error, or an exact value becoming a range.
> That trades coverage for tidiness, and a test count does not show it.
>
> Then take every product function the added tests call, including functions the
> diff does not modify, mutate each clause separately, and give the full matrix.
> Record for each mutation every test it turns red, including tests already on
> master, because a duplicate of an existing test is only visible from there.
> The off-diagonal passes are what you are after, because they show that each
> test fails for its own clause and that no test is standing in for another
> test's coverage.
>
> Do NOT comment on correctness, style or design. Stay under 500 words.

A duplicate or a foldable pair is a change request on a self-review of your own
PR, and advisory otherwise, because the author picked the shape. A fold that has
already been applied by widening an assertion is a coverage loss, so it carries
the testing bar's severity from Step 4 rather than the advisory standing of the
rest of this step.

### Step 5: verification-surface check (one agent)

Charter:

> Check whether the diff touches any of these high-risk areas without
> matching runtime / property / contract tests:
>
> - Size / length / index arithmetic on attacker-controlled values.
> - ABI, calling convention, struct layout, memory model.
> - Concurrency primitives, atomics, locking order.
> - Wire format, network protocol, on-disk cache format, serialization.
> - Public API contract, backward compatibility.
> - Cryptographic primitives or security-sensitive paths.
>
> For each area the diff touches, report whether the test set in the
> diff includes a runtime / property test that would catch a wrong
> behavior, not just a static / unit / IR-shape check. Flag any area
> with only static coverage.
>
> Stay under 300 words.

The list above is the default baseline. Extend it per project from
CLAUDE.md or repo docs if they name additional risk areas.

### Step 5b: reinvention check (one agent, only if the diff adds code)

Skip this when the diff only edits existing functions. Run it when the
diff introduces a new function, helper, constant, lookup table, or a
non-trivial inline block of logic.

Charter:

> For each new function / helper / constant / table / non-trivial logic
> block the diff ADDS, search the codebase and its already-linked
> libraries for an existing primitive that already does this. Grep the
> name, the literals it would contain, and a synonym or two; this tree
> is old and wide, so the primitive you need often already exists under
> a different name. For each addition, report one of: (a) DUPLICATE --
> name the existing symbol (file:line) it should reuse; (b) NEAR-MISS --
> an existing helper covers most of it, note what differs; (c) NOVEL --
> no existing equivalent found, list where you looked so the gap is
> auditable. Prefer reuse, or an explicit reason not to. Do NOT comment
> on correctness, style, or tests.
>
> Stay under 400 words.

Treat a DUPLICATE as a change request, not a nit: reinvented primitives
drift from the original (missing bounds checks, different edge-case
handling) and double the maintenance surface. NEAR-MISS is a judgment
call -- surface it so the author decides. NOVEL with a stated search
trail is the clean pass.

### Step 5c: design & ownership gate (one agent)

Correctness says the code does what it does without crashing. It does NOT say
the change should exist as built. This is the step that stops a correctness pass
from masquerading as an approval. Run one adversarial agent whose whole job is to
argue AGAINST the change:

> Argue this change should not land as written. Make the strongest case that it
> (a) works around a defect that lives upstream, in another repository or
> another layer, instead of fixing it where it is -- name the upstream defect and
> the layer that owns the information the fix needs; (b) duplicates a
> responsibility another component / service / module already
> owns -- name it, file:line; (c) belongs in a different component (e.g. an
> engine hard-coding vocabulary, strings, or a wire shape that the consumer
> already owns); (d) reinvents a schema or primitive instead of reusing the
> single source of truth. A dump written for a person to read is still a schema
> once a program parses it, so count it. Check the change against the owning component and any
> spec / design doc. If the design is sound, say so plainly and why; if it is
> misplaced, lead with the concrete relocation. Do NOT accept the PR's own
> justification as the answer -- verify it.
>
> Stay under 500 words.

Never let a single agent's "NOVEL / justified / acceptable tradeoff" stand as
the verdict here. That phrasing is the tell that a design was rationalized, not
challenged. If it appears, verify against the owner before accepting.

**Is this fix in the right repository and the right layer?** This is the same
question one layer out, so ask it of every fix. Are we working around a bug in
the upstream component inside the consumer, when the root cause should be fixed
upstream instead?

One worked case shows what the question buys. One service prints a list of
records as a text dump meant for a person to read, and several fields of each
record are free text supplied by a third party. Another service parses that
text. One pull request hardens the parser so it refuses a dump whose shape its
own header does not vouch for. That hardening is worth having, because it turns
silent corruption into a refusal. It is still not the fix. The format stays
ambiguous, and the case that proves it is a stored value containing a comma,
which the dump prints exactly like a separator, so the parse gives that record
one field too many and silently drops the last one. No reader can recover from
that, because the information is already lost by the time the reader sees it.
The root cause is the format, in the other repository, and the durable fix is a
machine-readable output mode whose precedent already exists in the same tree for
a sibling tool.

The test to apply is one question. Ask whether this change would be deleted once
the upstream defect is fixed. When the answer is yes, the change is a mitigation
and not a fix, so three things follow. Say that in the PR body in one sentence.
Name the upstream ticket there. Then check that the upstream ticket really
exists, rather than assuming somebody will file it. A mitigation that does not
announce itself gets read as the fix, the root cause never gets scheduled, and
that is how a workaround becomes permanent.

One caution keeps the rule from being over-applied. A fix in a consumer is not
automatically a workaround. Of five pull requests in one day only one was, and
the other four corrected defects that genuinely lived where they were fixed,
including one in the very same function as the workaround. So ask the question
per defect and not per file, and the discriminator is whether the information
needed to behave correctly is available at that layer at all.

**Who produces this input, and do we control them?** Ask this of every parser the
diff adds. A parser's complexity should be inversely proportional to the
reviewer's control over the producer. Input from a third party earns a defensive
parser, because the format is not ours to change. Input from a program in the same
organisation earns none, because changing the producer to emit a machine-readable
form is available and it is cheaper than every parser that would otherwise be
written against the text. Hand-writing a parser for a format we choose is a
decision to keep the wrong choice. Run this as its own agent whenever the diff
parses, scans or pattern-matches text it did not construct:

> The diff parses input it did not construct. Trace that input back to the program
> that produces it, and name the repository that owns the producer. Then answer
> whether the organisation reviewing this diff can change that producer, and give
> the evidence for the answer, meaning the producer's path and its repository,
> rather than an assumption.
>
> Search for a precedent before you judge the parser. Does a sibling tool in the
> producer's own package, or an adjacent code path in the consumer, already emit or
> consume a structured form of the same or similar data? Name it with file:line.
> That precedent is the cheapest evidence that the machine-readable mode belongs in
> the producer.
>
> Then report every tell that the diff is rebuilding structure a serialiser would
> have carried for free:
>
> - A line matched by prefix anywhere in the stream, which is position-independent
>   parsing of a positional format.
> - A version check on the input, which means the producer already versions the
>   format, so the format is a wire format in denial.
> - A separator, heading or banner string compared byte for byte.
> - Records counted to detect truncation.
> - Structure reconstructed from indentation, blank lines or headings.
>
> Last, say whether the format carries data from a source the producer does not
> control, such as customer-supplied free text printed verbatim. Name those fields
> and show where they enter the stream.
>
> Return one of: (a) PRODUCER-OWNED, so the parser should not exist and the fix
> belongs in the producer, naming the output mode to add and the precedent you
> found; (b) PRODUCER-OWNED-AND-UNTRUSTED, the same verdict plus the structure a
> hostile value can forge, with the forged record spelled out; (c) THIRD-PARTY, so
> a defensive parser is correct here, naming the producer and why it cannot be
> changed. Do NOT comment on the parser's correctness, on style or on tests. Stay
> under 500 words.

A PRODUCER-OWNED verdict is a change request with the standing of a DUPLICATE in
Step 5b, and it is BLOCKING on a self-review of your own pull request.
PRODUCER-OWNED-AND-UNTRUSTED is BLOCKING on any review, because a hand-written
parser over untrusted data is an injection surface rather than technical debt. A
value carrying an injected newline forges the structure the parser trusts, so the
parser can be made to report a record nobody created, or to stop early and report
success. THIRD-PARTY is an honest pass and it has to stay available, because a
defensive parser is the right answer for a format we do not own.

The worked case above is this one, and one further fact belongs to this
question. Two parsers of that dump grew inside the consuming service, and they
disagreed about what to refuse.

This question and the upstream-defect rule above fire from opposite directions, so
run both. This one fires on sight, because the tells sit in the added lines and the
producer question needs only the diff and a grep. The upstream-defect question
fires later, once somebody has already named the format as the defect. Step 5b
substitutes for
neither, because it reports NOVEL on the first parser of a format, correctly, and
that reads as a clean pass.

### Step 5d: module-boundary / layering gate (one agent, if the diff moves types or adds deps)

Skip for a diff contained to one module's internals. Run it when the diff adds a
dependency edge, adds a public header / symbol, or places a type across a module
boundary.

> Does the diff add a dependency edge a module should not have, place a domain
> type in a module that does not own the concept (e.g. a domain type parked in a
> transport / low-level module to dodge a dependency, then pulled into other
> modules to reach it), or widen visibility (public where private would do)?
> Report each with the CMake / header evidence and where the symbol should live.
> A misplacement is a finding even when it is not a hard cycle.
>
> Stay under 400 words.

### Step 5e: comment & prose pass (one agent, cheaper model)

The one style pass this skill runs, because comment slop is the most
reliable AI tell and the cheapest to fix. Run it on a cheaper model
(`sonnet`) -- it is mechanical prose judgment, not correctness
reasoning. On a self-review of your own PR, its findings are BLOCKING:
slop comments and a padded description are yours to fix before pushing,
not a follow-up to defer. What blocks is the ambiguity-bearing subset:
a comment a reader can misread, a requirement stated as a wish, a
condition buried after the command. A block of prose that is also written in the
PR body, the ticket or a project doc blocks as well, because those copies
diverge and the code copy is the one that goes stale. A sentence two words over
the limit is a nit. Skip on a trivial diff that adds no comments and barely
touches the PR body.

**Run this pass on your own text, and run it before you publish.** Five PR
bodies went out at 241, 256, 269, 286 and about 450 words, and the reviewer's
verdict was that they were long and unreviewable. The rewrite carried the same
facts at 85, 91, 112, 121 and 152 words. The reviewer then asked "did you run
the latest rules on conciseness", and the answer was no, because the pass had
been run on the ticket text and never on the PR bodies, while a review charter
had been told to check those same bodies. Running a style pass on someone else's
text while skipping your own is the mistake to name and avoid. The word budget
in rule 4 is therefore a gate that runs before publishing, not a note collected
afterwards.

Pass B's word limits, modal ladder and one-concept-one-term rule come
from ASD-STE100 (Simplified Technical English), the controlled language
aerospace maintenance manuals use. The full standard is a free download
at asd-ste100.org; the rules below are self-contained without it.

Two questions, in this order: does the text earn its place (rules 1-4),
and can a reader actually understand it (rules 5-13). Judge keep/drop
first, then apply the prose rules only to what survives -- there is no
point rewriting a comment that should be deleted.

Run the mechanical pass FIRST, on the PR body and on any prose file the
diff touches: `~/.claude/bin/check-prose.py FILE`. It reports
noun-phrase fragments, punctuation carrying logic, over-long sentences
and promotion words, which is the subset an eye pass misses. Hand its
output to the agent as a starting list, not as the finding set: it
cannot see whether a fact earns its place, and it does not read code
comments out of a diff. A clean run is not a passing review.

> Review the comments the diff adds or changes, any comment attached to
> a line it changes, plus the PR title, the commit titles and the PR
> description. Work in two passes.
>
> Pass A -- does the text earn its place? Name the reader and the action
> they are about to take: approve this diff, schedule the work, decide a
> design, unblock a build. Keep the facts that change what they do, and
> cut the rest, however true and however hard-won -- effort spent is not
> a reason to keep a fact. Of two versions carrying the same facts, the
> shorter wins.
>
> 1. Necessary -- flag any comment that states what the code already
>    makes obvious to a competent reader (paraphrases the next lines,
>    restates a well-named call). When a comment explains a helper call,
>    open the helper's own doc comment: a call-site comment that restates
>    it is the same finding, because the explanation lives once, on the
>    helper. A comment earns its place only by adding the *why*, an
>    invariant, or a non-obvious constraint. Obvious comments should be
>    dropped, not reworded. Same for history breadcrumbs ("moved to X",
>    "was Y", "COPY OF ..."): git narrates history. And flag an untouched
>    neighbouring comment the diff has made wrong -- it still describes
>    the old behavior.
>
>    The explanation lives once across the whole set of artifacts, and not only
>    once inside the code. Before you accept any comment longer than about three
>    lines, go and look for the same content in the PR body, in the linked
>    ticket, and in any project documentation this repository points at, such as
>    a `CLAUDE.md`, an `AGENTS.md`, a page under `doc/`, or a design note the
>    ticket links. Report where you found each copy, naming the artifact and the
>    line, and write "searched, found nowhere else" when that is the answer,
>    because a silent pass here reads exactly like a skipped one. Prose that
>    already exists in another artifact is cut from the code, and the code keeps
>    a bare pointer at most. The failure mode is divergence. The same
>    explanation maintained in four places drifts apart as each copy is edited on
>    its own, and the copy in the code is the one nobody comes back to update, so
>    it is the copy that ends up lying to the next reader.
> 2. Altitude -- a comment explains intent and the higher-level logic,
>    not the mechanism the code lowers to. Flag "what" comments; keep
>    "why" comments. The same filter runs one level up, on the document
>    itself: identifiers and line numbers belong in a PR, not in an RFC;
>    business impact belongs in the epic, not in a commit message. A
>    fact at the wrong altitude is cut here and raised there, not
>    reworded.
> 3. Length -- one line unless a second line is load-bearing. Flag any
>    comment longer than its point requires. A doc comment on a declaration has
>    a line cap, stated in Step 2b. Apply that cap here when Step 2b did not run
>    on this diff, and stay off it when Step 2b did run, because re-reporting its
>    finding buys nothing. When two comments say the same
>    thing, name which one survives AND shorten it: deleting the copy while
>    leaving the original untouched does not discharge the finding, and the
>    original is usually the longer of the two. Then judge the file, not only
>    each comment: when the same mechanical pattern (a wait, a flush, a
>    retry) carries a multi-line comment at every occurrence, keep one and
>    cut the rest, or move the explanation to the helper. A file the
>    comments make hard to scan is a finding even when each comment
>    survives alone. Prose longer than the body it documents is a finding
>    on sight: eleven lines of Doxygen on a one-line function is not
>    defensible.
> 4. PR description -- flag a body that restates the diff, carries a
>    fact its reader cannot act on, pads with rule-of-three or filler,
>    or runs long where a few lines carry the same information. Flag a
>    body that narrates the investigation: "master moves, the round
>    fails, the queue is re-submitted" is a chronology dressed as an
>    explanation, and it opens with events instead of with what breaks.
>    Where two texts say the same thing, name the survivor and shorten
>    that one; deleting the copy and leaving the original discharges
>    nothing, and the original is usually the longer one. Flag a list of
>    findings that does not close with what the reader should do about
>    them, and a link the reader is left to infer: what is obvious from
>    inside the work is not obvious from outside it. Length has a number
>    here, so count the words of the body and report the count. A Summary
>    earns about 120 words. A body covering several distinct defects may
>    reach 150. Past that, the body needs a reason you can state in one
>    line, and "the change was large" is not one.
>
> Pass B -- can a reader understand it? Assume the reader is a competent
> engineer who is not a native English speaker, is new to this code, and
> may be from another team. Apply these to every comment that survives
> Pass A, and to the PR description. Never re-edit wording a human
> wrote: leave their redundancies alone, and confine every finding to
> text this diff adds or changes.
>
> 5. Plain English. Short sentences, one idea each, active voice, common
>    words. FIRST check every sentence has a subject and a main verb: a
>    noun-phrase fragment is a defect regardless of length, and the fix is to
>    restore the subject and verb even though that adds words. Fragments are what
>    compression produces when the author is cutting to a word budget, so expect
>    them wherever the text is densest. Flag a rare or latinate word that has a plain equivalent
>    (utilize -> use, leverage -> use, prior to -> before, in order to ->
>    to, subsequent -> later, in the event that -> if), three or more
>    chained clauses, a double negative, and any idiom or metaphor that
>    does not survive translation. Flag a comment left in another
>    language in code the diff touches; translate it. Sentence limits:
>    20 words for a line the reader executes (a step, a warning), 25 for
>    everything else. Count backticked code, an identifier, and a number
>    with its unit as one word each -- a comment full of
>    `long_symbol_names` is shorter than it looks.
> 6. Plain terms over jargon. Flag an acronym never expanded, and jargon
>    used where an everyday word says the same thing. Do NOT flag the
>    codebase's real vocabulary: type names, field names, protocol and
>    domain terms are precise and must stay. Never propose replacing a
>    precise domain term with a vague everyday one -- expand it on first
>    use instead. What you are hunting is gratuitous jargon, not
>    necessary vocabulary. One concept, one term: flag a diff that calls
>    the same thing a job here and a task there, and say which to keep.
> 7. Point first, context second. The opening clause must state what the
>    code does, or why it exists. Conditions, scene-setting and history
>    come after, or not at all. Flag any comment or paragraph that opens
>    with a setup ("When foo exists and bar does not...", "Currently,
>    ...", "In the case where...") or with the identifier's own name
>    ("fooKey is the..."). Rewrite as action-then-reason:
>    "Handle the damaged case where foo exists without bar, because ...".
>    One exception: in a line the reader executes, a required condition
>    comes first, with a comma -- "If the build fails, read the log."
>    Point-first governs everything else.
> 8. AI-writing tells. Flag: an "-ing" clause tacked on for fake depth
>    ("ensuring X", "enabling Y", "reducing Z"); "this enables / ensures /
>    allows / makes it possible to" filler; promotional words
>    (comprehensive, robust, seamless, significant, powerful); hedges and
>    vague attribution ("it could be argued", "generally speaking",
>    "some may note"); negative parallelism ("not only X but also Y",
>    "it's not just X -- it's Y"); rule-of-three padding where the real
>    count is two or four; em dashes where a period or comma works; a
>    bolded inline-header list (`**Label:** text`) where prose works;
>    "Currently, ..." openers; "and/or" (pick one, or write "X, or Y, or
>    both"); "as needed" / "as necessary" where the condition should be
>    stated; "gracefully handles" and other claims carrying no fact (say
>    what it does: retries three times, then stops).
> 9. Modals say what they mean. In a comment stating a requirement or an
>    invariant, "should" hides whether the code enforces it -- flag it,
>    and write "must" when it is required or state the fact plainly when
>    it is not. Rewrite "may" / "might" / "could" to "can" for plain
>    possibility. Leave a genuine unknown alone; the target is a rule
>    dressed up as a suggestion.
>10. References resolve inside this repository. For every pointer a
>    comment makes -- a row, a table, a section, a document, a numbering
>    scheme -- check that a reader holding only this repo can follow it,
>    by grepping for the target. Flag any reference that resolves only in
>    the author's notes, a private spreadsheet or an unlinked document:
>    "Row 13" of a table that exists nowhere in the tree is the canonical
>    case. Fix by inlining the fact the reference carried, committing the
>    target, or dropping the pointer. A ticket link is the one exception,
>    and only as added context. Introduce every reference on first use: a
>    log string is "the log line `X`", not a bare quoted phrase. A date
>    earns its place only with the reason it matters.
>11. Grammar floor. Brevity is bought with facts, never with grammar.
>    Cutting a whole claim is right; cutting the subject or the verb out
>    of a claim that stays saves three words and makes every reader
>    rebuild the missing subject, so the effort goes up as the word count
>    goes down. Flag any noun-phrase fragment. Doc-comment summaries are
>    where they hide, because the opener looks like a convention:
>    `/// Whether the cache is warm.` and `/// How many hosts are needed.`
>    are both fragments. Write a predicate as the question it answers,
>    question mark and all -- `/// Should this host publish its own copy?`
>    -- and when its conditions are necessary and sufficient, say `iff`
>    and put them in a bullet list under `Returns true iff:`, one per
>    line, because a list shows the boolean structure that prose makes
>    the reader assemble. On a small predicate, give the contract and
>    stop.
>12. Punctuation carries no logic. Flag an em dash, a semicolon, a colon
>    or a parenthesis joining two statements: each one leaves the reader
>    to infer cause, contrast, example or explanation, and that inference
>    is where they go wrong. Name the relation with a word instead --
>    because, so, but, then, rather than, for example -- or split the
>    sentence. A dash separating a section title from its subtitle is
>    fine, because a title is not a spliced statement.
>
>13. Titles name the change in the maintainer's own words. Review the PR
>    title and every commit title. A title must name the change with the
>    domain noun and the verb the codebase already uses for it, never with a
>    clever paraphrase. A title that describes the input instead of the
>    change reads as a riddle. The reviewer rejected "fix(import): refuse
>    a dump a third party can add lines to" with "makes absolutely no
>    sense", because it names the input and never the change. Grep
>    the touched files for the noun and the verb they use, then build the
>    title out of those.
>
> When brevity and clarity pull apart, buy the clarity with word choice,
> not extra lines: swap the hard word for the easy one, usually shorter
> anyway. Pass B may not raise a comment's line count -- if word choice
> cannot carry it, the comment is doing too much, and the fix is to cut
> the *why* down rather than add a sentence.
>
> Every replacement you propose must itself satisfy rules 5-13, and must
> be SHORTER than what it replaces. Count both, and report the real
> figure: an equal-length rewrite has not discharged a length finding,
> and if the text cannot shrink without dropping a fact, say so and name
> the fact. Do not hand back a suggestion that opens with a condition or
> leans on a word you just flagged. Re-judge any prose the author already
> rewrote to satisfy an earlier review comment, because a pass that adds
> the requested fact and keeps everything already there is exactly where
> length grows back.
>
> For each finding give `file:line` (or "PR body", "PR title", "commit title"),
> which rule it breaks,
> the offending text, and the replacement -- or "drop". Do NOT comment on
> correctness, tests, or design; those are other agents' jobs.
>
> Stay under 600 words.

### Step 5f: design-document / RFC requirement gate (one agent, conditional)

Correctness and design-fit judge the code *as written*. This gate judges
whether the change should have been written *at all* before a design was
agreed. Run it when either trigger holds:

- No tracker item with stated goals backs the PR -- a GitHub issue, a Jira or
  Linear ticket -- so the intent lives only in the diff and the PR prose.
- The PR is LLM-generated, or comes from an outside contributor or another team
  (per the detection in "LLM-generated PRs get stricter review" below), so
  nobody who maintains the code has vouched for the approach.

Skip it when a linked issue or ticket names the goal AND the change is contained
(bug fix, mechanical refactor, an increment inside an already-agreed design).

Charter:

> Decide whether this change is large or far-reaching enough that it should
> not land without a written design first -- a design doc for a scoped change,
> or a full RFC for a cross-cutting one. Weigh the SCALE and BLAST RADIUS, not
> the line count: does it change or add a public / REST API surface, a wire or
> serialized format, a cross-process or cross-service contract, a storage,
> cache or index format, a concurrency or deployment model, or introduce a new
> subsystem / dependency / ownership boundary? Does it commit the team to a direction that is expensive
> to reverse once shipped? Check whether a linked issue, ticket or design doc already
> states the goal and the agreed approach. Return one of: (a) NEEDS-RFC --
> cross-cutting or hard-to-reverse, name what it touches, what has to be agreed
> first, and who signs off where the project names owners;
> (b) NEEDS-DESIGN-DOC -- scoped but still needs a written, reviewed design;
> (c) NONE -- goal is clear, scale is contained, cite the linked issue or
> ticket. Do
> NOT accept the PR body as the design doc: a description of what the code does
> is not an agreed design. Do NOT comment on correctness, tests, or style.
>
> Stay under 400 words.

A NEEDS-RFC or NEEDS-DESIGN-DOC verdict is BLOCKING: the design must be written
and reviewed before the implementation is approved, however clean the code is.
Lead with what the change touches and why it exceeds "just merge it" scope, and
point the author at the RFC / design-doc process rather than reviewing the
implementation in a vacuum.

### Step 5g: interface & signature shape (one agent)

Run this whenever the diff adds a function, method, or type, or changes an
existing signature. Steps 5c and 5d ask *where* code lives; this asks whether the
thing a caller has to hold is well made. It is the gate that catches the review
comments of the form "this works, but nobody will be able to maintain it".

Charter:

> For each function, method, or type the diff adds, and each signature it
> changes, judge the shape of the interface. Assume the code is correct -- that
> is another agent's job. Report each of:
>
> - An out or in-out parameter where a return value would do. Flag the
>   `bool f(T *out)` / `bool f(T& out)` shape by name: it forces the caller to
>   declare the output
>   before the call and to know which failure left it half-written.
> - State a caller can only obtain by reading an object *after* the call failed
>   or threw. Name the field, say what the function should return instead. This
>   is the highest-severity finding in this pass.
> - Absence, failure, or "not applicable" encoded as a sentinel, a
>   default-constructed value, or a bool flag sitting beside the data, where an
>   optional, a result type, or a variant would model it in the type itself. In
>   C, the same finding is a yes/no query handing back a raw errno or -1 the
>   caller has to decode.
> - A bool parameter or field whose name does not say which way is true, or whose
>   polarity makes readers negate it mentally at the use sites. Check every use
>   site, not the declaration alone.
> - A function returning less than its only caller needs, so the caller
>   recomputes or re-reads something the function already had.
> - Missing const, a must-check return a caller can silently drop (no
>   `nodiscard` on a pure query), a large type passed or returned by value where
>   a pointer, reference or view would do, or a non-owning pointer or view whose
>   backing store may not outlive it.
>
> For each finding give file:line, the current signature, the proposed signature,
> and the concrete maintenance hazard a future caller hits. If a shape is
> defensible, say so and why. Do NOT comment on correctness, placement, tests, or
> naming beyond bool polarity. Stay under 500 words.

An interface that is safe only because today's callers happen to avoid the wrong
path is a finding, not a nit. "It does work" does not answer this pass. An
interface that requires reading an object's state after a failed call is
BLOCKING. Step 5j holds the tie-break for everything else in this pass, so a
finding whose fix adds a named entity for a single call site loses to the smaller
shape.

### Step 5h: local idiom conformance (one agent, cheaper model)

Skip only when the diff adds no new declaration. Cheap model: this is pattern
matching against neighbouring code, not reasoning.

Most conventions in a mature tree are written down nowhere. They live in the
lines next to the change, so a style guide read in Step 1 cannot catch a
violation of them.

Charter:

> For every declaration the diff adds, compare it against its immediate
> neighbours -- the sibling declarations in the same class, file, or directory --
> and NOT against a written style guide. Read the surrounding declarations of the
> same kind, then report where the new code breaks a pattern its peers follow:
>
> - A name prefix or suffix every peer carries and this one does not, especially
>   one that encodes a contract (for example a suffix marking that the caller
>   must already hold a lock).
> - A comment marker that differs from every sibling declaration.
> - Parameter order, parameter passing, or error-reporting style that differs
>   from the neighbours doing the same job.
> - Test naming, fixture choice, or assertion helper that differs from the other
>   tests in the same file.
>
> Then check history: run `git log` on the touched files and look for review
> feedback the same maintainer has already given on this code. If a pattern was
> asked for once, it will be asked for again.
>
> Report each as: the new declaration, the peer pattern with file:line, and which
> of the two should change. If the diff is consistent with its neighbours, say so
> plainly. Do NOT comment on correctness, design, or tests. Stay under 400 words.

A deviation from the local idiom is a finding even when the written guide is
silent. When the written guide and the neighbouring code disagree, report the
conflict and let the author choose -- do not silently pick one and do not
"fix" the neighbours.

### Step 5i: repo-convention / file-list gate (one agent, cheaper model, always)

Every other gate reads the code. This one reads the FILE LIST, and catches the
class where each changed line is defensible but the file should not have been
touched by this PR at all. Nobody owns that question otherwise: it is not an
invariant of the diff, and the prose pass judges comment quality, not whether a
file belongs in the change.

Charter:

> Derive the repo's process conventions from its `CLAUDE.md`, `AGENTS.md`,
> `CONTRIBUTING.md` and the git history of each changed file, then judge the
> PR's FILE LIST against them. Do not review the code. For each changed file ask:
> who normally touches this file, and in what kind of change? `git log --oneline
> -- <file>` answers it -- if every prior commit to a file is a release, a version
> bump or a packaging change, a feature PR touching it is the finding.
> Watch for: release notes / changelog entries written ahead of the release that
> curates them; version or ABI values bumped outside a release; generated build
> output committed; a new test not registered with the runner; a file whose merge
> semantics make parallel edits collide (check `.gitattributes`). For each
> finding, name the convention, cite the evidence you derived it from, and say
> what should have happened instead. Return NONE if the file list is consistent
> with how the repo works. Stay under 300 words.

Two findings from this gate deserve a blocking verdict: committing generated
output, and editing a file another open PR is editing the same way (a duplicate
release-notes block conflicts on merge, or lands twice). The rest are advisory.

When a convention turns out to be real but unwritten, say so in the report: the
fix is to write it into the repo's rules file, not just to fix this PR. An
implicit convention will be violated again by the next author who reads the rules
literally.

### Step 5j: scope & over-engineering (one agent)

Run this whenever the feature is small and the diff is not, and always when the
diff adds more than about 150 lines, or more test lines than twice its product
lines. Step 1 recorded both counts, so the trigger is read off a number. Left as
a judgement about whether a feature "feels" small, it fires only for a reviewer
who has already reached this step's conclusion.

The craft steps push one way. Step 5g asks for a struct returned by value in
place of an in-out parameter, and Step 2b asks for a name where a bare literal
sits at a call site. Both add named entities, and until this step no charter
pushed the other way, so the skill only ever asked for more. Measured on a real PR whose feature
was reading one command-line flag: three rounds guided by these steps produced a
parse function returning a result type, a struct to carry its output, a helper
wrapping a single error message, a usage printer lifted out of an inline block, a
rename of `argv` and `argc` through the whole function body, span plumbing, a
vector copy of the argument tail, three spellings of the flag where one was
wanted, and the option name written three times in three forms, once as a named
constant and twice as a bare literal. The reviewer's verdicts were "the PR is
unreviewable", "STOP OVER ENGINEERING" and "the goal was to SIMPLIFY the PR, not
to make it bad". Every addition was defensible on its own, and several came out
of this skill's own craft steps. This step is the counterweight.

> Read the feature's requirement from the ticket or the PR body, then walk the
> diff hunk by hunk. Judge scope against that requirement and never against
> taste. Report:
>
> - For each hunk, does the requirement need it? A hunk that would survive if the
>   feature were dropped is a refactor riding along, so it belongs in its own PR.
>   List those hunks with their line counts. One exception, and check it before
>   you list any test hunk: a change to a fixture, a harness, an assertion helper
>   or a shared table that makes existing tests able to fail buys coverage rather
>   than spending lines. It is the cheapest coverage in the diff and never a
>   refactor riding along, however unrelated to the requirement it looks. Say what
>   it now catches, and move on.
> - Renames and moves of code the feature did not have to touch. Name each one,
>   because a rename inflates the line count without changing behaviour, which is
>   the cheapest way to make a diff unreviewable.
> - An abstraction whose only call site arrives in the same diff: a type, a
>   helper, a wrapper around one error message, a function lifted out of a block
>   that had one reader. Name it and say what inlining it would cost.
> - Generality nothing asks for: a second flag spelling, a config value, an
>   accepted enum value, a parameter that no caller in the tree and no line of the
>   requirement needs. A parameter every product caller passes the same way is
>   generality only when the tests do not need it either. A parameter the tests
>   need is a seam and not generality, whatever it carries: an injected clock, a
>   fixed random source, a supplied hostname or build id. It stays, and you say
>   so rather than listing it, because silence reads as an oversight and invites
>   the next reviewer to delete it.
> - An abstraction the diff introduces and then does not use consistently, for
>   example a named constant for a string that also appears twice as a bare
>   literal. That inconsistency is evidence the name was carrying nothing.
> - Count the named entities the diff introduces, meaning types, functions,
>   constants and renamed locals, then state how many the requirement needs. Give
>   both numbers, because a number is harder to argue with than an adjective.
> - The counterfactual: state in lines the smallest diff that delivers the same
>   behaviour, and put the actual diff's product line count beside it. Compare
>   product against product, because tests deliver no behaviour and belong in the
>   ratio below instead.
> - The test lines the diff adds against the product lines it adds, fixtures and
>   golden files counting as test. Give both numbers. Past about two to one, rank
>   the added tests by lines spent per assertion and report the ranking.
> - For each test at the top of that ranking, the shorter shape that keeps every
>   case: a row in a table the diff or the file already has, a direct assertion in
>   place of a one-row table, a literal in place of a helper with one call site,
>   one fixture in place of two that differ only in fields the path under test
>   never reads. Propose deleting lines, never cases.
>
> Report what to DELETE, with file:line. Do NOT propose a rewrite, a redesign or
> a replacement abstraction, because proposing one is itself the failure mode this
> step exists to catch. Do NOT comment on correctness, on whether a test asserts
> the right thing, or on naming quality. Test code IS in scope here: judge the
> lines a test spends, never the cases it covers.
> Stay under 400 words.

A hunk the requirement does not need is BLOCKING, and so is an actual diff more
than roughly twice its counterfactual. The test-to-product ratio is reported
with both numbers and is advisory on its own, because a test-only PR and a
one-line fix carrying a large regression table both read high for good reasons.
What blocks is a named line to delete whose deletion removes no case.

**Precedence over the craft steps.** This step contradicts Step 5g and Step 2b on
real diffs, so the tie-break is fixed here and not left to the reader.

- A craft finding whose fix introduces a new named entity for a single call site
  does not justify that entity by itself. Prefer the smaller shape and a name
  that states the hazard.
- The craft step wins when the shape it flags is a correctness hazard rather than
  a taste question, for example a signature that leaves a caller reading state
  after a failed call.
- When the two genuinely conflict, the smaller diff wins, and the report tells
  the reviewer which craft finding was traded away for it.

### Step 6: aggregate

After the agents return, write a single report:

```
# Review verdict

## Scope of this review
Ran: reader legibility, witness check, correctness invariants, tests, test
necessity and folding, verification surface, design/ownership, module boundaries,
design-doc/RFC requirement, scope & over-engineering, comment/conciseness,
interface shape, local idiom, repo conventions / file list (list which actually
ran). NOT judged:
<anything not run -- e.g. performance, security posture beyond the invariants
checked, product fit>.

## Legibility
- Highest-value edit: <the one change, line estimate> (BLOCKING when DIFF-tagged).
- Other DIFF findings: <list>. PRE-EXISTING (advisory): <list>. Or "reads fine".
- Doc comments on declarations: <per block, the comment's and the body's line
  counts against the ten-line cap, and whether the block had to be read twice
  before its contract was clear>.

## Witness check (if elements were added)
- DEAD in tests: <list> (each BLOCKING). DEAD in product code: <list>.
- Unresolvable references: <list>. Cannot-decide: <list>.

## Correctness — invariants checked
- <invariant 1>: PASS / P0 / inconclusive (one-line rationale)
  - if doubled: model agreement (both PASS / both flag X / disagree -> what you adjudicated)
- ...

## Tests
- Test lines added: <N> against <M> product lines (<ratio>). Past about 2:1, the
  ranking by lines per assertion: <list>. Lines to delete without losing a case:
  <file:line> (the ratio is advisory, a named deletable line is Step 5j's and
  BLOCKING).
- N audited; M confirmation-biased: <file:line>.
- Behavior-bearing changes with NO test on the changed path: <list> (each BLOCKING).
- Tests that only run by touching internals -- fake exposing private state, log or
  metric read as a channel, assertion on state after a failed call: <list>
  (report as a design finding naming the missing seam, NOT as a scaffolding request).
- Tests that die to the same mutation set, or whose set is a subset of another's:
  <list, with the fold and the invariant that keeps the coverage>.
- Tests whose named subject the diff does not touch: <file:line -> owning
  package>.
- On a later round: tests an earlier round added, what each was working around,
  and whether this round's harness changes have made any of them dead: <list, or
  "first round">.

## Verification surface
- High-risk areas touched: <list>. Only static coverage: <list>.

## Design & ownership
- <sound / misplaced>: <one line; if misplaced, where it belongs and why>.
- Right repository and layer: <fix / mitigation for an upstream defect -- name the
  upstream defect and its ticket, and say whether the ticket exists>.
- Parsed input, if the diff parses text it did not construct: <PRODUCER-OWNED /
  PRODUCER-OWNED-AND-UNTRUSTED / THIRD-PARTY>: <the producer and its repository,
  the structured precedent found, the tells, and for an untrusted format the
  record a hostile value forges> (PRODUCER-OWNED-AND-UNTRUSTED is BLOCKING).

## Design-doc / RFC requirement (if the gate ran)
- <NONE / NEEDS-DESIGN-DOC / NEEDS-RFC>: <what it touches; if needed, what has to be agreed first and who signs off> (a NEEDS-* verdict is BLOCKING).

## Module boundaries
- <clean / smell>: <dependency edge or misplaced type, with evidence>.

## Interface shape
- <clean / findings>: <file:line, current signature -> proposed, the hazard>.
- State readable only after a failed call: <list> (each BLOCKING).

## Local idiom
- <consistent / deviations>: <new declaration vs peer pattern file:line, which should change>.
- Written guide disagrees with the neighbours: <list, or "none">.

## Repo conventions / file list
- <consistent / findings>: <file, the convention and its evidence, what should have happened>.

## Reinvention (if code was added)
- Duplicates: <symbol to reuse, file:line>. Near-misses: <list>.

## Scope & over-engineering
- Named entities introduced: <N>, against <M> the requirement needs.
- Counterfactual: <lines> for the smallest diff, against <lines> actual (more
  than roughly 2x is BLOCKING).
- Hunks the requirement does not need: <file:line -> delete> (each BLOCKING).
- Single-call-site abstractions, unasked generality, and names the diff uses
  inconsistently: <list>.
- Craft findings traded away for the smaller diff: <list, or "none">.

## Comments & prose (BLOCKING on self-review)
- Earns its place: unnecessary / obvious comments <file:line -> drop>; "what"
  comments to lift to "why" <list>; over-long comments <list>; neighbouring
  comments the diff made wrong <file:line -> update or drop>.
- Written elsewhere: <for each comment over about three lines, the artifacts
  that hold the same content, naming artifact and line for the PR body, the
  ticket and each project doc, or "searched, found nowhere else">.
- Readable: hard words / long sentences <file:line -> replacement>; unexpanded
  acronyms or gratuitous jargon <list>; one concept named two ways <list>;
  comments opening with context instead of the point <file:line -> rewrite>;
  a requirement stated as "should" <file:line -> must / plain fact>;
  AI-writing tells <list>.
- PR description: <word count, against about 120 words, or 150 when it covers
  several distinct defects; what to cut and what to reword>.
- PR title and commit titles: <the maintainer's own words / the proposed rewrite>.

## Verdict
- BLOCKING (must fix before merge): <list, or "none">.
- Non-blocking follow-ups: <list>.
- Correctness: <clean / has P0>.
- Approvable: <YES only if zero BLOCKING; else NO + shortest path to yes>.
```

The BLOCKING bar -- any one blocks approval: the named highest-value legibility
change on a DIFF-tagged finding (Step 2b); a DEAD test element from Step 2c; a
P0 correctness violation; a behavior-bearing change with no test on the changed
path; a design/ownership violation (duplicates or misplaces a responsibility
another component owns); a mitigation for an upstream defect that neither says
so in the PR body nor names an upstream ticket that exists; a hand-written
parser for a format one of our own programs produces, where that format also
carries untrusted data (Step 5c); a broken module boundary; an interface that
only yields what a caller needs by
reading state left behind after a failed call (Step 5g); a NEEDS-DESIGN-DOC /
NEEDS-RFC verdict where a change's scale outran any agreed written design (Step
5f); a hunk the stated requirement does not need, or a diff more than roughly
twice its counterfactual (Step 5j); on a self-review of your own PR, unfixed
comment slop or a padded description (Step 5e). A clean correctness pass is
NEVER on its own an
approval. Report correctness and approvability separately, and never write "safe
to ship" from correctness alone. Lead with any BLOCKING finding.

**Craft findings are the deliverable, not a bonus round.** A diff can be correct,
well placed, and inside its module, and still cost the author three rounds of
review over interface shape, local idiom and test scaffolding. Measured on a real
PR: across two review rounds a maintainer raised 14 comments and *none* was a
correctness defect -- 3 were interface shape, 5 test maintainability, 3 local
convention, 2 scope. A pass tuned only to find what is *wrong* will
systematically under-report what is merely *worse than it should be*, and that is
what generates the rounds. Never close a review with "correctness clean" and no
craft verdict.

### Step 7: when the user gives feedback, challenge it (don't just absorb it)

If the user interjects a claim, doubt, or hunch during the review --
"doesn't this also fire for X?", "I think the lock is held here",
"this gate looks too broad" -- treat it as a one-line invariant and
spawn a dedicated adversarial agent to **challenge or confirm it**,
rather than reasoning about it inline or taking it at face value.

The charter shape: state the user's claim, instruct the agent to treat
it as *likely true* and try hard to prove it with a concrete
counterexample, then -- separately -- decide whether (if true) it makes
the diff WRONG (P0) or is harmless / cosmetic. The two questions are
distinct: a gate firing more broadly than its name suggests can still
be correct everywhere it fires. Make the agent answer both.

Why spawn instead of answer inline: the user's doubt is exactly the
high-value, possibly-subtle case the skill exists to nail, and an
inline answer from the main thread tends to rationalize the code you
just read. A fresh adversarial agent that is told the user suspects a
problem searches harder for one. Use a strong model and don't soften
the charter -- "if it's just imprecise wording, say so plainly; if you
find real breakage, lead with it." Fold the verdict back into the
report (confirm / refute, P0 / cosmetic, with the counterexample).

### Step 8: after a human review round, sweep every comment as a pattern

Run this when a human reviewer has commented and the author is fixing. One round
of fixes must not manufacture the next one, which is what happens when each
comment is treated as a single line to patch.

**Enumerate the comments from the API, never from a timestamp and never from
memory.** List the unresolved threads and read every one. A query bounded by a
guessed time window silently drops comments -- that has happened: a `> 12:00`
filter hid a comment posted at 11:58, and it turned out to be the only one
needing a real design decision. Count the threads, and reconcile the count
against what you think you are answering.

**Then turn each comment into a rule and sweep the whole diff for other
instances.** A reviewer points at the line they happened to read; the same
mistake is usually elsewhere in the same diff. For each comment write the rule it
implies -- "a bool's name says which way is true", "no assertion on state after a
failed call", "a literal repeated across assertions gets a name", "a method
needing a held lock carries the suffix" -- then grep the diff for every other
place that rule applies. On a real PR this sweep found four more instances of a
complaint the reviewer had raised once.

Report per comment: instances found, instances fixed, instances deliberately left
and why.

**Check the fix against the rule the reviewer just stated.** Code written to
satisfy a review comment is the likeliest place to break the same principle
again, and new *test* code is the likeliest of all. On a real PR a test added to
prove a reviewer's blocking fix violated the very principle that comment
asserted, and a full review pass ran in between without noticing.

A construct added because a reviewer or an earlier review round asked for it gets
the same audit as any other line: verify it is load-bearing, not merely sound.
"A review suggested it" is a provenance, not evidence. This holds for this
skill's own rounds and not only for a human's, so run it in every round of a
multi-round self-review.

**A round that changes the test harness re-opens every test an earlier round
added.** A round often adds a test to work around something the harness cannot
see, and a later round fixes the harness itself. The workaround is dead from that
moment and nothing looks at it again, because a cleared list is a cache with no
invalidation rule. Measured on a real PR: round 3 added a 58-line test that
counted mock consumption by hand, round 4 gave the shared table the assertion
that proves the same thing, and the workaround shipped anyway. So when a round
changes a fixture, a harness, a shared table or an assertion helper, put every
test an earlier round added back into Step 4b's input and report which ones
survived.

**A suggested rename can carry a semantic change.** When a reviewer offers a name
via a suggestion block, check whether it means the same thing as the old one. An
inverted name (`isDamaged` for a field that meant `isValid`) needs the logic
inverted with it, or the name becomes a lie -- and the diff will look like a
harmless rename.

## Two process traps

Both of these nearly shipped something wrong in a single day of using this skill,
and neither is a code defect, so no charter above catches them.

**`gh pr create` succeeds even when the push did not.** The command reports a
created pull request after a rejected `git push`, and the pull request then shows
stale code while you believe it shows the diff you just reviewed. Compare the
pushed head against the local head before you trust what a PR contains.

**Never relay an agent's finding as fact without checking it.** Two findings went
to the user before anyone verified them, and both were wrong. A charter reported
a test making a real network call to localhost, and the mock was in fact
registered and intercepting the call. A peer reported an unpushed commit, and
what it had misread was a rebase. Read the cited lines yourself before a finding
leaves the session.

## LLM-generated PRs get stricter review

Detect it: the PR body carries a generation marker (e.g. "Generated with Claude
Code"), the user says it is AI-generated, or the diff shows the slop tells
(comments that narrate the diff or a call site, reinvented primitives, confident
PR prose that just restates the code). When any holds, raise the bar:

- The testing bar (Step 4) defaults to BLOCKING -- no benefit of the doubt on a
  missing test.
- The design/ownership gate (Step 5c) is MANDATORY, not optional, and run on a
  strong model.
- The design-doc / RFC requirement gate (Step 5f) is MANDATORY when the PR comes
  from an outside contributor or another team: nobody who maintains the code has
  vouched for the approach, so a
  cross-cutting or hard-to-reverse change needs a written design before the
  implementation is reviewed.
- Treat the PR description and every code comment as an unverified claim; confirm
  against the code, the spec, and the owning component. LLMs produce confident
  justifications for slop, and an LLM reviewer will rationalize them unless told
  to attack them.
- A single agent's "NOVEL / justified" is never sufficient -- require the
  adversarial challenge (Step 5c) to try and fail to refute the design before you
  accept it.

## Hard rules

- Never widen an agent's charter to "find any bugs." One agent, one
  invariant.
- Legibility runs FIRST and its named highest-value change blocks. A diff a
  maintainer cannot follow does not get reviewed, it gets approved on trust, so
  certifying its correctness first wastes the pass.
- An addition owes a witness. "Is it correct?" never answers "is it needed?", and
  a test element that cannot fail is a missing test in disguise, inheriting the
  testing bar's BLOCKING severity.
- Never let this skill's own suggestions escape the witness check. A construct
  added because an earlier round asked for it is exactly where a no-op hides.
- Never accept "general correctness" as an invariant.
- More tests do not mean a better PR. Run Step 4b after the test-design audit,
  fold tests that die to the same mutation set, and refuse any fold that buys its
  lower count by widening an assertion.
- Ask of every fix whether it belongs in this repository and this layer, or
  whether it works around a defect the upstream component owns. A change that
  would be deleted once the upstream defect is fixed is a mitigation, so it says
  so in the PR body and names an upstream ticket you have checked exists. Ask
  this per defect and not per file, because most consumer-side fixes are real
  fixes.
- Ask who produces every input the diff parses, and whether we control them. A
  parser's complexity should be inversely proportional to that control, so text
  from a program in our own organisation earns a machine-readable mode in the
  producer instead of a parser in the consumer. When that format also carries
  untrusted data, the parser is an injection surface and the finding is BLOCKING.
  Step 5b cannot catch this, because the first parser of a format is NOVEL and
  reads as a clean pass.
- Craft is in scope, not a bonus. Run Step 5g (interface shape) and Step 5h
  (local idiom) on any diff that adds a declaration. Correctness findings alone
  do not predict whether a maintainer will ask for changes.
- "It does work" never answers an interface-shape finding.
- The craft steps ratchet upward, so Step 5j pushes back. A hunk the stated
  requirement does not need belongs in its own PR, and an abstraction whose only
  call site arrives in the same diff is not yet an abstraction. When a Step 5g or
  Step 2b fix would add a named entity for one call site, the smaller shape wins
  unless the flagged shape is a correctness hazard, and the report says which
  craft finding was traded.
- When a change is hard to test, that is a design finding, not a licence to build
  scaffolding. Name the missing seam; do not bless a fake, a log-as-channel, or
  an assertion on state after a failed call just because it reaches the path.
- After a human review round, run Step 8: enumerate the comments from the API
  (never from a timestamp), turn each into a rule, and sweep the whole diff for
  other instances.
- A clean correctness pass is NOT an approval. Report correctness and
  approvability separately; never emit "safe to ship" from invariants alone.
- Missing test on a behavior-bearing change is BLOCKING, not a follow-up.
- Challenge the design, don't rationalize it: when reinvention or a debatable
  design choice appears, the default is the Step 5c adversarial gate, not inline
  acceptance. LLM-generated PRs get the stricter bar above, not a laxer one.
- Scale to diff size: a typo / comment / one-line change needs none of the added
  gates -- don't run 5c/5d/5f on trivial diffs, and 5g/5h only bite once a
  declaration appears.
- Run the design-doc / RFC gate (Step 5f) when no issue or ticket states the
  goal, or the PR is LLM-generated / from an outside contributor or another
  team. Judge blast radius, not line count: an API / wire / storage /
  cross-process / cross-service / concurrency change that outruns any
  agreed written design is BLOCKING until the design doc or RFC exists -- the
  code being correct does not waive it.
- The comment/prose pass (Step 5e) is the ONE style pass allowed and runs on a
  cheaper model. It judges both whether the text earns its place -- named
  reader, named decision, right altitude for the document -- and whether a
  non-native, non-local reader can understand it: plain English, no gratuitous
  jargon, point before context, unambiguous modals, no AI-writing tells. On a
  self-review of your own PR its ambiguity-bearing findings are BLOCKING -- fix
  the slop before pushing; a two-word overrun is a nit. Do not let it widen the
  correctness agents' charters.
- Run the prose pass on your OWN text before publishing, not only on the author's.
  The PR body has a number. A Summary earns about 120 words, a body covering
  several distinct defects may reach 150, and anything past that needs a stated
  reason. Five bodies published at 241 to about 450 words were called "horrible
  and unreviewable", and the same facts fitted in 85 to 152 words.
- A title names the change in the words the code's maintainer already uses. Take
  the domain noun and the verb from the touched files instead of paraphrasing,
  and never describe the input where the change belongs.
- Confirmation-biased tests come in six shapes (Step 4), and they recur inside
  tests written to satisfy an earlier round. Audit a construct a review asked for
  exactly like any other line.
- Verify an agent's finding yourself before relaying it, and check the pushed
  head against the local head before trusting what a PR shows.
- Readability never licenses vagueness: a precise domain term stays, and gets
  expanded on first use rather than swapped for an everyday approximation. Nor
  does it license length: the one-line default is a ceiling Pass B may not raise.
- A dedicated prose pass over the PR body (`/humanizer` or the equivalent) stays
  the gate, run before `gh pr create`; Step 5e's rule 8 is a second opinion on
  it, and the only pass that sees code comments.
- A doc comment on a declaration earns about ten lines of prose, plus one line
  per parameter and return value, and a block you had to read twice is a finding
  whatever its sentence lengths and whatever its ratio to the body. Splitting one
  long sentence into four short ones is not a fix, because every fact stays and
  the line count grows. Move the threat model, the rationale and the history to
  the PR body or the ticket, and keep the caller's contract in the comment.
- A comment rewritten to satisfy a review finding is re-judged like any other
  line, and the bar is that it got SHORTER. Prose edited in response to a finding
  is where length grows: each pass adds the fact it was asked for and keeps
  everything already there. Measured on a real PR: a doc block was flagged as too
  long, rewritten twice across two rounds in response to that finding, grew each
  time, and the human reviewer then blocked the PR on it, calling it extremely
  hard to read and asking for a rewrite without an LLM.
- Deleting a duplicated comment is not the same as fixing a long one. When the
  same text sits in two places, the reflex is to keep the canonical copy and
  delete the other; if the canonical copy is the unreadable one, that resolution
  leaves the defect exactly where the reviewer will find it. Look for the copies
  outside the code as well, in the PR body, the ticket and the project docs. A
  threat model written in all four is four copies that will diverge, and the code
  copy is the one nobody updates. One such block shipped because no charter had
  been told to go and read the other three artifacts.
- Never skip Step 4 (test-design) if the diff includes new tests --
  test-design bugs are the cheapest to introduce and the most likely
  to lock in the actual code bug.
- Do NOT post anything to the PR. Output goes to the user; the user
  decides what to post.
- If the diff is small enough that one invariant covers it entirely,
  one agent is fine. Don't pad with redundant agents.
- Doubling means the *same* invariant on two models, not two models with
  looser charters. A second model with a "find bugs" charter is just the
  generic review this skill exists to avoid.
- When the user pushes back with a claim or hunch, spawn an agent to
  challenge it (Step 7) instead of answering inline -- and always ask
  the separate question "if true, is it P0 or merely cosmetic?"
- When the diff adds a new function / helper / constant / table, run the
  reinvention check (Step 5b): grep for an existing primitive before
  accepting the addition. Skip it for edits to existing code.

## When to skip this skill

- Style-only changes, comment-only changes, documentation rewrites.
- Trivial refactors that move code without changing behavior.
- Reviews where the project has no specs / contracts / invariants to
  protect (rare; ask the user before deciding).

## Background

This skill exists because two earlier "code-review" passes on the
same diff missed a fundamental ABI-aliasing miscompile. The diff
asserted the broken IR as expected behavior; both passes accepted the
test. A single narrow-charter agent given the C ABI rule for by-value
parameters caught it instantly. That experience produced these three
patterns: narrow-charter agents, spec-driven test audit, verification-
surface check.

---

From [xroche/skills](https://github.com/xroche/skills). Written by Xavier Roche, MIT licensed.
