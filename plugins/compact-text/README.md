# compact-text

**`/compact-text`** cuts a long document to a target length, by default half, and keeps
every fact its readers act on. It works on an RFC, a design doc, a report or a wiki page
that people refuse to read at full length.

```
/compact-text docs/rfc-0012.md
/compact-text docs/rfc-0012.md 3000 words
```

It asks who reads the document and what each reader decides. Each chunk then gets a
ledger that grades every point against those decisions, and a hard word budget. After
the rewrite, agents look for two failures that no diff shows. One is a kept reason
whose instruction is gone. The other is a rule whose consequence no longer matches its
condition.
`scripts/gates.py` catches lost numbers, identifiers and URLs.

A full pass costs about six agents per chunk. The light pass costs three per chunk, for
documents under about 3,000 words. `EVIDENCE.md` holds the numbers from the run the
method came from.

The rewrite charter uses the `humanizer` skill when it is installed, and works without
it.
