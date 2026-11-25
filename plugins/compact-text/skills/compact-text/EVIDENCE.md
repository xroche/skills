# Evidence: the run behind compact-text

`SKILL.md` is the procedure. This file holds the numbers behind its rules. They come from
one document, so read them as one data point and do not promise them to a user.

## The document

The document was an RFC of 8,398 words on a wiki. Staff engineers, an engineering
manager and a product director read it to take four decisions, and they had refused to
read it at full length. It was split into six chunks and compacted in September 2026.

Two instruments produced the word counts, and every figure below names its own. `wc -w`
over the chunk files counts fold markers and table pipes. The published page with its
markup stripped counts neither.

| Chunk | Original | Round 1 | Round 2 at budget | Published | Budget |
|---|---|---|---|---|---|
| 1-context | 1,231 | 1,123 | 774 | 890 | 620 |
| 2-goals | 761 | 626 | 379 | 409 | 380 |
| 3-proposal | 3,276 | 2,888 | 1,650 | 2,052 | 1,650 |
| 4-work | 1,238 | 1,129 | 620 | 862 | 620 |
| 5-crosscut | 1,029 | 939 | 520 | 520 | 520 |
| 6-infra | 863 | 623 | 430 | 486 | 430 |
| Total | 8,398 | 7,328 | 4,373 | 5,219 | 4,220 |

All figures in that table are `wc -w` over the chunk files. On the published page the
body went from 8,309 words to 5,190, a 38% cut. The visible reading path outside folds
went from 2,723 words to 1,958.

## A brief without a number fails

Round 1 told each agent "compact this, the readers refuse to read it". It returned a 13%
cut, and every agent reported success. Round 2 gave the same six chunks hard budgets and
returned a 47.9% cut. That is why `SKILL.md` gives the budget in the first charter and
keeps a retry charter only for a miss.

All six round 2 agents reported hitting budget with no NEED fact dropped. Four NEED facts
had gone anyway, and one ledger's claim of compliance was false in two places.

One chunk landed at 756 words against 620 and reported that its tables and titles were
304 of them. That is an honest overrun, and it is why an overrun belongs in the ledger.

## Where the words were

Duplication between a table, the visible prose and a fold was much the largest source.
The chunk that was 40% of the page was halved mainly by one move. Every fact the phase
table stated was deleted from the phase fold, so the table became the map and the fold
carried only the rest.

Seven rules cost 53 words each before the cut and 26 after. No rule lost its number, its
order or the mistake it prevents. Only the derivation went.

The ledgers held 123 DROP lines. Counting reason words over them gives floors rather than
exact counts, because a line can name a reason without using one of these words:

| Reason word | Occurrences |
|---|---|
| `restat` or `duplicat` | 39 |
| `methodolog` | 12 |
| `derivation` | 6 |

The figure has been misquoted three times in prose, so re-run it rather than copying it:

```python
import re, glob
rows = [l for f in sorted(glob.glob('class-*.md')) for l in open(f)
        if re.match(r'\s*(?:[-*|]\s*)?(?:\*\*)?drop(?:\*\*)?\b', l, re.I)]
txt = '\n'.join(rows)
len(re.findall(r'restat|duplicat', txt, re.I))
```

## What the charters found

The gate script reported none of these findings. Each was on text whose gate report
named no missing fact.

| Chunk | LOSS | HALLUCINATION | VERBOSE | Blocking |
|---|---|---|---|---|
| 1-context | 4 | 5 | | 2 |
| 2-goals | 5 | | | 0 |
| 3-proposal | 9 | 16 | | 7 |
| 4-work | | 16 | 1 | 5 |
| 5-crosscut | 8 | 11 | | 6 |
| 6-infra | 6 | | | 2 |
| Total | 32 | 48 | 1 | 22 |

That is 10 runs over 6 chunks, against the 18 that a full pass would then have needed.
BASELINE did not exist yet. One HALLUCINATION run reported 16 findings and refuted 12 of
its own suspicions, which is why every charter asks for REFUTED verdicts by name.

The chunk `5-crosscut` was published before it was verified. Its ledger claimed "no fact
dropped, only wording tightened", which was false in two places. Verifying it afterwards
returned 19 findings, 6 of them blocking, which was the highest blocking rate of any
chunk.

Two failure modes produced almost all 22 blocking findings. The first was a kept reason
whose instruction was gone. In four cases the rewriter's own ledger graded the fact NEED and
never listed it as dropped. The fact was gone from the text anyway. The second
was a rule whose consequence detached from its condition. The failure-mode check in
Appendix D was written after the run from those findings, so its own yield is not yet
measured.

## Why BASELINE is a separate charter

VERBOSE already looks for "sentences carrying no fact a reader acts on". It did not
catch a baseline claim on the second document the method ran on, which was a performance
self-review. The sentence was present, so LOSS had nothing to report. The source
supported it, so HALLUCINATION had nothing to report. It was fifteen words of clean
active prose, so VERBOSE passed it. In fact VERBOSE had proposed that wording while it
fixed the passive voice of the original.

The other three charters judge a sentence against the source or against itself. Whether
a claim is worth making depends on what the reader already assumes, so the charter
needs the reader list as input.

Its first run returned 6 findings, 2 of them blocking, on a text the other charters had
already passed. Every finding was a bullet lead that restated the role's own definition.
In five of the six, the sharper fact was in the same bullet or in the previous draft.

The same run produced the rule that a setback is never baseline. Without it, the charter
flagged every honest admission in the document.
