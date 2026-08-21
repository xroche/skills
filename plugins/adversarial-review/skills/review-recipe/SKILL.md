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

## Workflow

### Step 1: gather the diff and context

- Use `gh pr view <PR> --json headRefName,baseRefName,title,body` if a
  PR is named, then `gh pr diff <PR>`.
- Otherwise diff the branch against its merge base.
- Read any `CLAUDE.md` at repo root and in directories the diff touches.
- Skim the PR description / commit messages for the author's intent.

Capture: the diff, the touched paths, the project's coding rules, the
author's stated goal.

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
belongs, and a helper whose parameter names do not say what they hold.

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
> (a) duplicates a responsibility another component / service / module already
> owns -- name it, file:line; (b) belongs in a different component (e.g. an
> engine hard-coding vocabulary, strings, or a wire shape that the consumer
> already owns); (c) reinvents a schema or primitive instead of reusing the
> single source of truth. Check the change against the owning component and any
> spec / design doc. If the design is sound, say so plainly and why; if it is
> misplaced, lead with the concrete relocation. Do NOT accept the PR's own
> justification as the answer -- verify it.
>
> Stay under 500 words.

Never let a single agent's "NOVEL / justified / acceptable tradeoff" stand as
the verdict here. That phrasing is the tell that a design was rationalized, not
challenged. If it appears, verify against the owner before accepting.

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
condition buried after the command. A sentence two words over the limit
is a nit. Skip on a trivial diff that adds no comments and barely
touches the PR body.

Pass B's word limits, modal ladder and one-concept-one-term rule come
from ASD-STE100 (Simplified Technical English), the controlled language
aerospace maintenance manuals use. The full standard is a free download
at asd-ste100.org; the rules below are self-contained without it.

Two questions, in this order: does the text earn its place (rules 1-4),
and can a reader actually understand it (rules 5-9). Judge keep/drop
first, then apply the prose rules only to what survives -- there is no
point rewriting a comment that should be deleted.

> Review the comments the diff adds or changes, any comment attached to
> a line it changes, plus the PR description. Work in two passes.
>
> Pass A -- does the text earn its place? One principle: condense to the
> minimum that conveys the same information; when two versions say the
> same thing, the shorter wins.
>
> 1. Necessary -- flag any comment that states what the code already
>    makes obvious to a competent reader (paraphrases the next lines,
>    restates a well-named call). A comment earns its place only by
>    adding the *why*, an invariant, or a non-obvious constraint.
>    Obvious comments should be dropped, not reworded. Same for history
>    breadcrumbs ("moved to X", "was Y", "COPY OF ..."): git narrates
>    history. And flag an untouched neighbouring comment the diff has
>    made wrong -- it still describes the old behavior.
> 2. Altitude -- a comment should explain intent and the higher-level
>    logic, not narrate the mechanism the code lowers to. Flag "what"
>    comments; keep "why" comments.
> 3. Length -- one line unless a second line is load-bearing. Flag any
>    comment longer than its point requires.
> 4. PR description -- flag a body that restates the diff, pads with
>    rule-of-three or filler, or runs long where a few lines carry the
>    same information.
>
> Pass B -- can a reader understand it? Assume the reader is a competent
> engineer who is not a native English speaker, is new to this code, and
> may be from another team. Apply these to every comment that survives
> Pass A, and to the PR description.
>
> 5. Plain English. Short sentences, one idea each, active voice, common
>    words. Flag a rare or latinate word that has a plain equivalent
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
>
> When brevity and clarity pull apart, buy the clarity with word choice,
> not extra lines: swap the hard word for the easy one, usually shorter
> anyway. Pass B may not raise a comment's line count -- if word choice
> cannot carry it, the comment is doing too much, and the fix is to cut
> the *why* down rather than add a sentence.
>
> Every replacement you propose must itself satisfy rules 5-9. Do not
> hand back a suggestion that opens with a condition or leans on a word
> you just flagged.
>
> For each finding give `file:line` (or "PR body"), which rule it breaks,
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
BLOCKING.

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

### Step 6: aggregate

After the agents return, write a single report:

```
# Review verdict

## Scope of this review
Ran: correctness invariants, tests, verification surface, design/ownership,
module boundaries, design-doc/RFC requirement, comment/conciseness,
interface shape, local idiom, repo conventions / file list (list which
actually ran). NOT judged:
<anything not run -- e.g. performance, security posture beyond the invariants
checked, product fit>.

## Correctness — invariants checked
- <invariant 1>: PASS / P0 / inconclusive (one-line rationale)
  - if doubled: model agreement (both PASS / both flag X / disagree -> what you adjudicated)
- ...

## Tests
- N audited; M confirmation-biased: <file:line>.
- Behavior-bearing changes with NO test on the changed path: <list> (each BLOCKING).
- Tests that only run by touching internals -- fake exposing private state, log or
  metric read as a channel, assertion on state after a failed call: <list>
  (report as a design finding naming the missing seam, NOT as a scaffolding request).

## Verification surface
- High-risk areas touched: <list>. Only static coverage: <list>.

## Design & ownership
- <sound / misplaced>: <one line; if misplaced, where it belongs and why>.

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

## Comments & prose (BLOCKING on self-review)
- Earns its place: unnecessary / obvious comments <file:line -> drop>; "what"
  comments to lift to "why" <list>; over-long comments <list>; neighbouring
  comments the diff made wrong <file:line -> update or drop>.
- Readable: hard words / long sentences <file:line -> replacement>; unexpanded
  acronyms or gratuitous jargon <list>; one concept named two ways <list>;
  comments opening with context instead of the point <file:line -> rewrite>;
  a requirement stated as "should" <file:line -> must / plain fact>;
  AI-writing tells <list>.
- PR description: <concise and plain / what to cut and what to reword>.

## Verdict
- BLOCKING (must fix before merge): <list, or "none">.
- Non-blocking follow-ups: <list>.
- Correctness: <clean / has P0>.
- Approvable: <YES only if zero BLOCKING; else NO + shortest path to yes>.
```

The BLOCKING bar -- any one blocks approval: a P0 correctness violation; a
behavior-bearing change with no test on the changed path; a design/ownership
violation (duplicates or misplaces a responsibility another component owns); a
broken module boundary; an interface that only yields what a caller needs by
reading state left behind after a failed call (Step 5g); a NEEDS-DESIGN-DOC /
NEEDS-RFC verdict where a change's scale outran any agreed written design (Step
5f); on a self-review of your own PR, unfixed comment slop or a padded
description (Step 5e). A clean correctness pass is NEVER on its own an
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

**A suggested rename can carry a semantic change.** When a reviewer offers a name
via a suggestion block, check whether it means the same thing as the old one. An
inverted name (`isDamaged` for a field that meant `isValid`) needs the logic
inverted with it, or the name becomes a lie -- and the diff will look like a
harmless rename.

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
- Never accept "general correctness" as an invariant.
- Craft is in scope, not a bonus. Run Step 5g (interface shape) and Step 5h
  (local idiom) on any diff that adds a declaration. Correctness findings alone
  do not predict whether a maintainer will ask for changes.
- "It does work" never answers an interface-shape finding.
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
  cheaper model. It judges both whether the text earns its place and whether a
  non-native, non-local reader can understand it: plain English, no gratuitous
  jargon, point before context, unambiguous modals, no AI-writing tells. On a
  self-review of your own PR its ambiguity-bearing findings are BLOCKING -- fix
  the slop before pushing; a two-word overrun is a nit. Do not let it widen the
  correctness agents' charters.
- Readability never licenses vagueness: a precise domain term stays, and gets
  expanded on first use rather than swapped for an everyday approximation. Nor
  does it license length: the one-line default is a ceiling Pass B may not raise.
- A dedicated prose pass over the PR body (`/humanizer` or the equivalent) stays
  the gate, run before `gh pr create`; Step 5e's rule 8 is a second opinion on
  it, and the only pass that sees code comments.
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
