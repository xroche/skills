# Writing style for the report

Read at phase 9, before returning any prose. The report has to be clear and free of the tells that make
text read as machine-generated. **If a `humanizer` skill is available, run the drafted report through it
and return what it gives back** — that is the authority, and the rules below are the subset that matters
most here, for the passes where invoking it is not warranted.

## Hard rules

- No em-dashes or en-dashes. Use a period, a comma, a colon, or parentheses, or restructure.
- Lead with the answer. The first sentence says whether the bad thing can happen. Detail follows.
- Plain nouns in the body. Say "the copy" and "the cleanup job", not the model names, until the
  appendix.
- Vary sentence length. Some short. Some longer when the point needs it. Avoid an even, mid-length
  drone.
- Cut filler openers: "Currently,", "It is important to note that", "In order to". State the thing.

## Patterns to avoid (they read as AI slop)

- Promotional adjectives: comprehensive, robust, seamless, powerful, significant. Describe behavior,
  not marketing.
- Fake-depth "-ing" tails: "..., ensuring correctness", "..., enabling safety", "..., highlighting
  the risk". Make it a real clause or cut it.
- Rule of three: forcing ideas into groups of three for rhythm. Use the real number of items.
- Bolded inline-header lists (`**Label:** text`) as a crutch. Prefer prose or a real table.
- Copula avoidance: "serves as", "stands as", "acts as". Use "is" and "has".
- Hedging stacks: "it could potentially possibly". Say "may" once, or state the condition.
- Signposting: "Let's dive in", "Here's what you need to know". Just say the thing.
- Vague authority: "experts say", "studies show". Name the evidence or drop the claim.

## Honesty rules specific to this report

- Never call a clean run a proof. A found counterexample is a real flaw in the model; "no
  counterexample at size N" is weak evidence, and the report must say so.
- Do not overstate how often the bug fires. State the conditions that make the interleaving possible,
  not a made-up frequency.
- When the model's fix differs from the likely code fix, say it plainly rather than implying they are
  identical.
- Keep the top half readable by someone who has never seen code. Jargon lives in the appendix.

## Quick self-check before returning

Read the top section aloud in your head. If it sounds like a press release, or every sentence is the
same length, or you spot an em-dash or a "comprehensive", rewrite it.
