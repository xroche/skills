---
name: compact-text
description: Cut a long human-facing document to a target length, by default half, without losing a fact the reader acts on. Grades every point NEED, SHOULD or DROP against the decision it changes, rewrites each chunk to a hard word budget, then verifies with a failure-mode pass, mechanical gates and narrow-charter review agents. TRIGGER when a document is too long to be read, and when the user says "compact this", "cut this in half", "this RFC is too long", or asks to shorten an RFC, a design doc, a report or a wiki page. SKIP for code, for text short enough to rewrite in one pass, and for style-only work, which belongs to /humanizer.
user-invocable: true
argument-hint: <file path or pasted draft> [target, e.g. 50% or 3000 words]
---

# Compact text

A document nobody reads carries no facts. This skill cuts a long document to a target
length and keeps every fact its readers act on.

Write a ledger that grades every point. Rewrite each chunk to a hard word budget. Then
check the rewrite three ways. A failure-mode pass looks for lost instructions and
inverted rules. A script finds lost digits and identifiers. Narrow-charter agents find
what a diff cannot see. `EVIDENCE.md` holds the run this method came from and the
numbers behind each rule.

## What it costs

A full pass runs six agents per chunk. These are one rewrite (Appendix A), one
failure-mode check (Appendix D) and four verification charters (Appendix C). A
six-chunk document therefore needs about 36 agents. Tell the user that number before
you start.

Use the light pass when the document is under about 3,000 words or is a single chunk.
It runs the rewrite, the failure-mode check and the LOSS charter. Add BASELINE when
the document argues for something, such as a proposal or a self-review. Never skip the
failure-mode check or LOSS. On the reference run, the two failures they target produced
almost every blocking finding.

## Step 1: name the readers, their decisions and the target

Write down who reads the document and what each reader decides after reading it. Every
later cut is judged against that list, so a vague list produces vague cuts. Ask the user
for the list when the document does not state it. Do not infer it from the document's
own headings.

Take the target from the argument. Without one, the target is half the original. The
user may know how long the readers will spend on it. Then convert that time to words, at
about 200 words a minute.

## Step 2: split and set the budgets

Split the document into chunks of 600 to 3,500 words along its own top-level sections.
Put every file in one work directory. Name every chunk and use the name in each
file, because the gates and the charters expect this convention:

- `chunk-<name>.md` holds the original.
- `new-<name>.md` holds the rewrite.
- `class-<name>.md` holds the ledger.
- `checks-<name>.md` holds the failure-mode check from Step 4.
- `budgets.txt` and `gates.txt` hold the budgets and the gate report for all chunks.

Mark each collapsed or optional section, such as a `<details>` block or an appendix, as
`[FOLD: title]` ... `[/FOLD]`. The material outside folds is the visible reading path,
and most readers read only that part.

**The budget is a word count per chunk, not a percentage of the document.** Multiply
each chunk's word count by the target ratio and round to the nearest ten. Write one
`<name> <words>` line per chunk to `budgets.txt`. A brief that says
"compact this" returns a cut of about one tenth. A hard budget returns about half.

## Rules for every agent you launch

**A file's existence is not an agent's completion.** On the reference run the
coordinator saw a `new-<name>.md` file appear and started a second agent on that chunk.
The two agents wrote one file, and one round of work was lost. Wait for each agent's own
completion signal, and run two agents on one file one after the other.

**You own every cross-chunk decision.** A chunk agent told that another chunk covers a
fact will drop it, and two such decisions do not compose. On the reference run two
chunks dropped one requirement, each because the other stated it. Keep each fact in one
named chunk, and tell no chunk agent that another chunk covers a fact.

## Step 3: classify and rewrite

Run one agent per chunk with Appendix A. It writes the ledger first and the rewrite
second. The ledger has one line per point, because a grade nobody wrote down cannot be
checked.

| Grade | Test |
|---|---|
| NEED | The reader cannot take their decision, or takes a wrong one, without this fact. |
| SHOULD | It changes how much the reader trusts a NEED fact, or tells an implementer something they would otherwise get wrong. |
| DROP | Everything else. It is true but unusable, and a claim that only asserts the baseline belongs here too. |

**The negation test finds the baseline.** Negate the claim and ask what the reader does
with the negation. If the negation reads as a defect report rather than as news, the
claim asserts what the reader already expects. For example, "my reviews changed what
colleagues shipped" negates to "my reviews changed nothing", which is a defect report.
Grade such a claim DROP and tag it ` [BASELINE]`. Something specific usually hides under
it. When the chunk states that fact, it gets its own NEED or SHOULD line and replaces the
claim in the rewrite. Under that
review sentence sat three facts. Half the colleagues were outside the author's team. Two
changed a design rather than a line. Two were failures that would have reported success.

An admission of a setback is never baseline. Its negation is good news, so the test
acquits it.

**Tag every rule.** A point that states a rule, a condition or a guarantee gets ` [RULE]`
at the end of its ledger line. Step 4 walks those tags, because rules are the sentences
most likely to invert under compression.

**An overrun goes in the ledger.** A chunk that is mostly table can miss its budget
honestly. The rewriter lists each NEED fact that kept it over budget. If a chunk ends
more than 10% over budget without that list, run Appendix B on it.

**A rewriter's report of compliance is not evidence.** On the reference run five of six
agents reported hitting budget with no NEED fact dropped. Four NEED facts had gone anyway. The
budget is safe for the word count and not for the content, so Step 4 always runs.

## Step 4: the failure-mode check

Run one agent per chunk with Appendix D, before the gates. It looks for two failures
that no diff can see. Rewriters following the brief produced both.

**A kept reason whose instruction is gone.** The rewrite keeps why something matters and
deletes what to do. The text still reads as complete, because the reason is the part
that sounds like content. For example, one rewrite kept "deleting a record unlinks
neither its data directory nor its metadata file" and lost "needs an end-to-end probe".
Two named operator roles kept their titles and lost the halt procedure each owned.

**A condition that lost its consequence.** A rule's meaning can invert when the rule is
shortened. On the reference run one chunk produced five shapes of this:

- Two branches of a version rule merged, so a node not yet upgraded appeared to fail
  every request.
- The duration of an error moved from one node to the whole fleet.
- A silent no-op lost its condition "only when the value is already present", so the
  no-op became unconditional.
- A prohibition became a prediction with a backwards "so".
- A claim about a config file said a reload path exists, but the service has none.

When a rule will not fit the budget with its condition intact, keep the condition and
cut a different fact.

The check writes `checks-<name>.md`. Step 7 applies every UNMATCHED line and every
shifted rule in it.

## Step 5: the mechanical gates

```
python3 <skill_dir>/scripts/gates.py <work_dir> > <work_dir>/gates.txt
```

`<skill_dir>` is the directory that holds this file. The script compares each
`chunk-<name>.md` with its `new-<name>.md`. For each chunk, it reports the word count
against the budget. It lists the numbers, versions, ticket IDs, code spans, `file:line`
citations and URLs that went missing or appeared. It also reports lost fold and heading
titles, sentences over 25 words outside tables, and the banned constructions.

**The gates issue no verdict.** The script exits 0 whatever it finds, and a clean report
does not mean the rewrite is safe. On the reference run the gates reported none of the
81 charter findings. They test whether a fact is present and cannot test what a sentence
claims about it. The number 591 changed unit from tenants to tokens, and the gates could
not see it, because 591 was present in both texts.

Read every line before acting on it:

- `GONE` means absent from the rewrite in any form, and only `GONE` is a possible
  loss. Check each one against a DROP line in the ledger. A number that moved into a
  code span or a citation still counts as present. Other changes of form, such as a
  host and port spelled out in prose, show as `GONE`, because a false alarm costs less
  than a silent loss.
- `NEW` means the rewrite has a fact the source lacks. Check it for invention.
- `BROKEN` means the fold markers no longer pair up, and `banned` names a construction
  the rewrite charter forbids.
- `dedup` means the item is still present, but fewer times. That is usually the intended
  change.
- A `GONE` identifier can be a duplicate spelling that the rewrite collapsed. For
  example, routes spelled both `:id` and `{id}` become one spelling, which is a fix.
- The long-sentence list merges a list item that has no final period with the next
  one. It also merges a sentence with the next one when that one starts in lower
  case.

## Step 6: the verification charters

Run one agent per charter per chunk with Appendix C. Never ask one agent to "review the
rewrite", because that returns style notes. Give each agent the source chunk, the
rewrite, the ledger, the gate output and the reader list from Step 1. Forbid it to
re-report what the gates catch. A light pass runs LOSS only, plus BASELINE for a
document that argues for something.

The four charters are LOSS, HALLUCINATION, VERBOSE and BASELINE. Run BASELINE first on a
document that argues for something. A proposal asserts the practices any such change
would follow. A document arguing that work exceeded a standard asserts the standard.
The other three charters judge a sentence against the source or against itself, so they
pass a baseline claim. Whether a claim is worth making depends on what the reader
already assumes, and only BASELINE gets that as input.

Every charter defaults to refuting its own finding, and it reports a checked and killed
suspicion as REFUTED. That gives a suspicion somewhere to go other than the findings
list. **If the charters return no blocking finding on the first run, suspect the
charters rather than the rewrite.** The reference run found 22 blocking findings on a
text whose gate report named no missing fact. One chunk that skipped verification
returned 6 blocking findings when it was checked later, which was the highest rate of
any chunk.

## Step 7: apply the findings

Apply the charter findings and every UNMATCHED line and shifted rule in
`checks-<name>.md`. Raise the budget by the cost of the findings you accept, and say so. Every word you buy
back must restore a condition, an instruction or a figure from the source. If it does
neither, it is a rewrite, and a rewrite is judged against the budget again.

Record each rejected finding in the ledger with its reason, so the next reader sees the
decision.

## Step 8: the cross-chunk pass

No per-chunk agent can do this pass, so you do it. A fact can be cut from one chunk
while a surviving sentence in another chunk still refers to it. Grep the assembled text
for references by name and by number, such as "the ledger", "rule 3" and "the phase
table". Then confirm each target survives. On the reference run a sentence still
referred to a requirement that two chunks had both dropped.

## Step 9: report

Report three measurements:

- the words before and after, for the whole document and for the visible reading path
  outside folds
- the number of blocking findings the charters returned, the UNMATCHED lines and
  shifted rules in the checks files, and how many of each you fixed
- every NEED fact that kept a chunk over budget

Give the true percentage. If the target was unreachable without dropping a NEED fact,
say so and name the fact. An honest shortfall is fine, but a silent loss is not.

## Appendix A: the rewrite charter

Hand this to one agent per chunk, with the placeholders filled in.

> You are rewriting one chunk of a document that its readers refuse to read because it
> is too long. Its readers are <readers>. They read it to take <decisions>.
>
> Read `chunk-<CHUNK>.md`. If you cannot read it, stop and say so rather than guessing.
>
> **Your budget is <N> words. Hit it.** If only dropping a NEED fact would hit it, get
> as close as you can. Then list in the ledger every NEED fact that kept you over budget.
> Do not overshoot silently.
>
> **Step 1: classify.** For every paragraph, table row, list item and fold, list its
> distinct points and grade each one NEED, SHOULD or DROP. NEED means the reader cannot
> take their decision, or takes a wrong one, without this fact. SHOULD means it changes
> how much the reader trusts a NEED fact, or tells an implementer something they would
> otherwise get wrong. DROP means true but unusable: methodology, restatement of the
> code, self-correction narrative, hedges, and context the reader already has.
>
> A claim the reader already expects of anyone doing this work is DROP too. Negate it,
> and if the negation reads as a defect report rather than as news, it is the baseline.
> Tag that line ` [BASELINE]`. When your chunk states something sharper under it, give
> that fact its own NEED or SHOULD line and write it instead. Never invent one. An
> admission of a setback is never baseline.
>
> Tag every point that states a rule, a condition or a guarantee with ` [RULE]`.
>
> Write the ledger to `class-<CHUNK>.md`, one line per point, as
> `NEED|SHOULD|DROP <the point> [RULE] [BASELINE]`. A paragraph with no NEED and no
> SHOULD point disappears.
>
> **Step 2: rewrite** to `new-<CHUNK>.md`. Attack the words in this order:
> 1. Remove duplication between the visible path and a fold, or between a table and
>    prose. Keep the fact once, where the reader meets it first.
> 2. Cut the derivation after a rule. Keep the rule, its number, its order and the
>    mistake it prevents.
> 3. Split or cut sentences over 25 words. A table cell over about 15 words is prose
>    hiding in a table.
> 4. Cut the second example, unless it shows a different failure.
> 5. Cut any sentence that survives only because it is true.
>
> NEED facts are main clauses in short sentences, one idea each. SHOULD facts go in a
> subordinate clause or a trailing sentence. DROP facts do not appear. When a rule will
> not fit with its condition intact, keep the condition and cut a different fact.
>
> Follow these rules. Each one can be checked.
>
> 1. Every number, ticket ID, `code identifier`, file:line citation and URL appears in
>    your rewrite, unless its whole point is DROP in the ledger. Never alter a digit or
>    its unit.
> 2. Keep every `[FOLD: title]` and `[/FOLD]` with its exact title. Move content
>    between the visible path and a fold only if the ledger says so. Never fold away a
>    fact that a visible sentence refers to.
> 3. Invent nothing: no fact, number, mechanism, cause or consequence that is not in
>    your chunk. If two sentences contradict each other, keep both and flag it in the
>    ledger.
> 4. Do not renumber anything the text refers to by number.
> 5. Every sentence has a subject and a main verb. This outranks brevity, so delete a
>    whole fact rather than a subject or a verb.
> 6. Never join two statements with an em dash, a semicolon or a parenthesis. Name the
>    relation with a word: because, so, but, then, for example. A parenthesis may hold a
>    short noun phrase or a code citation.
>
> Then apply the `humanizer` skill to your rewrite, if it is available, with one change:
> cutting outranks its preserve-everything default. Skip any suggestion that adds words
> or fights a rule above.
>
> Return only these items:
> - your chunk name, the words before and after, and the budget
> - the NEED, SHOULD and DROP counts
> - any contradiction, and any NEED fact that kept you over budget

## Appendix B: the retry charter

Use this only for a chunk that ended more than 10% over budget without listing the NEED
facts that kept it there.

> Your chunk `new-<CHUNK>.md` is <W> words against a budget of <N>. Read it, with
> `chunk-<CHUNK>.md` and `class-<CHUNK>.md` beside it. Write over `new-<CHUNK>.md`, and
> append what changed to `class-<CHUNK>.md` under a `## Retry` heading.
>
> **Hit <N> words.** Attack the words in the order the first charter gave, and start
> with duplication. If a NEED fact keeps you over budget, list it in the ledger with the
> reason it is NEED. Every rule from the first pass still binds.
> <Facts the first pass lost that must come back, if any.>
>
> Return only these items:
> - the words before and after, and whether you hit the budget
> - what you restored, and any NEED fact that kept you over

## Appendix C: the verification charter

Run one agent per charter per chunk, with one CHARTER filled in per agent.

> A document was compacted because its readers refused to read it. Its readers are
> <readers>, and they read it to take <decisions>. You are verifying one chunk against
> ONE named charter. Do not report anything outside your charter, and do not
> rewrite the text.
>
> Read the original `chunk-<CHUNK>.md`, the rewrite `new-<CHUNK>.md`, the ledger
> `class-<CHUNK>.md` and the gate output `gates.txt`. If you cannot read a file, stop and
> say so.
>
> The gates already compared numbers, ticket IDs, code spans, citations, URLs, fold and
> heading titles and sentence lengths. **Do not re-report anything the gates catch.**
> Your value is in what a diff cannot see.
>
> **CHARTER=LOSS.** Find facts the reader needs that no longer reach them. For each one,
> quote the old sentence, name the decision the reader takes worse without it, and say
> whether the ledger marked it DROP. Look hardest for a kept reason whose instruction is
> gone. A fact moved into a fold is a finding only if a visible sentence refers to it. A
> fact the ledger justifies as DROP is a finding only if you can name the decision it
> breaks.
>
> **CHARTER=HALLUCINATION.** Find claims in the new text that the old text does not
> support. Look hardest for these shifts:
> - a cause or consequence now stated where the old text put two facts side by side
> - a dropped hedge that turned a maybe into a fact
> - a number whose unit or scope changed
> - a "because" that names the wrong reason
> - a consequence attached to the wrong branch of a condition
>
> Quote both
> versions for every finding.
>
> **CHARTER=VERBOSE.** Find text that still fails the brief, in this order:
> 1. sentences that carry no fact a reader acts on
> 2. facts stated twice
> 3. methodology or self-correction narrative that survived
> 4. hedges
> 5. sentences over 25 words in a table or a list, which the gates do not measure
>
> Give each one the sentence and either the shorter replacement or "cut". Also
> flag any fragment without a subject or main verb, and any parenthesis that joins two
> statements. The gates already report em dashes and semicolons.
>
> **CHARTER=BASELINE.** Find claims that assert what the reader already expects, so they
> move no decision. Read the reader list first, because it is your prior. Negate every
> claim in the new text. **If the negation reads as a defect report rather than as news,
> the claim is a finding.** Quote the claim, give its negation and name the decision it
> fails to move. Then name the specific fact hiding under it, or say "cut". Prefer the
> specific fact, because deleting a vague summary loses the sharp fact under it too.
> Report any `[BASELINE]` line from the ledger that the rewrite reintroduced in new
> words. Some baseline claims must stay, such as a precondition the reader must
> confirm or a scope boundary that prevents a wrong reading. Say REFUTED for those. An admission of a setback is never baseline.
>
> Rules for all charters: quote, never paraphrase. Default to refuting your own finding,
> because a finding you cannot support with a quote is not a finding. Say REFUTED for a
> suspicion you checked and killed. Say plainly when you find nothing, because an empty
> result is a real result. Propose a replacement for one sentence at a time, never for
> the whole chunk.
>
> Return a numbered list, most severe first, each finding in at most three lines: the
> quote, the problem, the fix. End with this line:
> `VERDICT: <n> findings, <k> of them blocking, <r> refuted`.

## Appendix D: the failure-mode charter

Run one agent per chunk, after the rewrite and before the gates.

> A chunk of a document was compacted to a hard word budget. You are checking it for two
> failure modes and nothing else. Do not rewrite the text.
>
> Read the original `chunk-<CHUNK>.md`, then the rewrite `new-<CHUNK>.md`, then the
> ledger `class-<CHUNK>.md`. The ledger grades every point NEED, SHOULD or DROP and tags
> every rule with `[RULE]`. If you cannot read a file, stop and say so.
>
> **Check 1: a kept reason whose instruction is gone.** Walk the ledger's NEED lines one
> at a time. For each one, quote the sentence in the rewrite that carries the
> instruction, which is what the reader must do. A surviving reason is not an
> instruction. Mark a line UNMATCHED rather than stretching a quote to cover it, because
> the unmatched lines are the output of this check.
>
> **Check 2: a condition that lost its consequence.** Walk the `[RULE]` lines. Read each
> rule in the rewrite against the original, clause by clause. Confirm the condition, the
> branch the consequence attaches to, the scope of the consequence and its duration. The
> tags are incomplete, so repeat the check on every bolded lead. Repeat it also on every
> sentence that contains "only", "unless", "when" or "because" and lost more than a third
> of its words.
>
> Write `checks-<CHUNK>.md` with two tables. Check 1 has the columns
> `NEED line | instruction sentence in the rewrite, or UNMATCHED`. Check 2 has the
> columns `rule | old clause | new clause | VERIFIED, or the shift you found`.
>
> Quote, never paraphrase. Default to refuting your own finding, because a finding you
> cannot support with a quote from both versions is not a finding.
>
> Return only these items:
> - how many NEED lines you walked, and how many are UNMATCHED
> - how many rules you checked, and how many shifted
> - the three worst findings, one line each
