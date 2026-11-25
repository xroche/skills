#!/usr/bin/env python3
"""Compare chunk-<name>.md with new-<name>.md and print what a diff can see.

Usage: gates.py <work_dir>

Optional <work_dir>/budgets.txt holds one "<name> <words>" line per chunk.
It always exits 0: the output is evidence for the charters, not a verdict.
"""

import glob
import os
import re
import sys
from collections import Counter

FACT_PATTERNS = {
    "url": r"https?://[^\s)>\]]+",
    "code": r"`[^`\n]+`",
    "file:line": r"\b[\w./-]+\.\w+:\d+\b",
    "ticket": r"\b[A-Z][A-Z0-9]+-\d+\b",
    "number": r"(?<![\w.])\d[\d,]*(?:\.\d+)?%?",
}

BANNED = {
    "em dash": r"—|\s--\s",
    "semicolon": r";",
    "filler opener": r"\bThis (?:enables|ensures|lets|allows)\b",
    "Currently opener": r"(?:^|\. )Currently,",
    "promotion": r"\b(?:robust|seamless(?:ly)?|powerful|crucial|vital|"
    r"comprehensive|cutting-edge|leverag(?:e|es|ing))\b",
}

FOLD = re.compile(r"\[FOLD:\s*([^\]]+)\]")
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.M)
LONG = 25


def read(path):
    """Return the whole file at path as text."""
    with open(path, encoding="utf-8") as f:
        return f.read()


def prose(text):
    """Return the text without fenced code blocks and table rows."""
    text = re.sub(r"^```.*?^```", "", text, flags=re.S | re.M)
    return "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("|")
    )


def facts(text):
    """Return a Counter of (kind, value) for every fact-bearing token."""
    found = Counter()
    rest = text
    for kind, pattern in FACT_PATTERNS.items():
        for m in re.finditer(pattern, rest):
            found[(kind, m.group(0).rstrip(".,"))] += 1
        # A URL or code span must not also count its digits as numbers.
        rest = re.sub(pattern, " ", rest)
    return found


def sentences(text):
    """Yield (word count, sentence) for prose sentences over LONG words."""
    flat = re.sub(r"\s+", " ", prose(text))
    for s in re.split(r"(?<=[.!?])\s+(?=[A-Z`*\[(])", flat):
        n = len(s.split())
        if n > LONG:
            yield n, s.strip()


def budgets(work_dir):
    """Read budgets.txt into {name: words}, or return {} when it is absent."""
    path = os.path.join(work_dir, "budgets.txt")
    if not os.path.exists(path):
        return {}
    out = {}
    for line in read(path).splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].isdigit():
            out[parts[0]] = int(parts[1])
    return out


def report(name, old, new, budget):
    """Print the gate report for one chunk."""
    w_old, w_new = len(old.split()), len(new.split())
    cut = 100 * (w_old - w_new) / w_old if w_old else 0
    line = f"== {name}: {w_old} -> {w_new} words ({cut:.1f}% cut)"
    if budget:
        verdict = "within" if w_new <= budget else f"OVER by {w_new - budget}"
        line += f", budget {budget}, {verdict}"
    print(line)

    f_old, f_new = facts(old), facts(new)
    for (kind, value), n in sorted(f_old.items()):
        if (kind, value) not in f_new:
            print(f"  GONE   {kind} {value}")
        elif f_new[(kind, value)] < n:
            print(f"  dedup  {kind} {value} ({n} -> {f_new[(kind, value)]})")
    for kind, value in sorted(set(f_new) - set(f_old)):
        print(f"  NEW    {kind} {value}")

    for label, pattern in (("fold", FOLD), ("heading", HEADING)):
        gone = set(pattern.findall(old)) - set(pattern.findall(new))
        for title in sorted(gone):
            print(f"  GONE   {label} {title}")
    if new.count("[FOLD:") != new.count("[/FOLD]"):
        print("  BROKEN fold markers do not pair up")

    for n, s in sentences(new):
        print(f"  long   {n}w: {s[:100]}")
    body = re.sub(r"\s+", " ", prose(new))
    for label, pattern in BANNED.items():
        for m in re.finditer(pattern, body):
            context = body[max(0, m.start() - 40) : m.end() + 40]  # noqa: E203
            print(f"  banned {label}: ...{context}...")


def main():
    if len(sys.argv) != 2:
        print(__doc__.strip())
        return
    work_dir = sys.argv[1]
    limits = budgets(work_dir)
    chunks = sorted(glob.glob(os.path.join(work_dir, "chunk-*.md")))
    if not chunks:
        print(f"no chunk-*.md files in {work_dir}")
    total_old = total_new = 0
    for path in chunks:
        base = os.path.basename(path)
        name = base.removeprefix("chunk-").removesuffix(".md")
        new_path = os.path.join(work_dir, f"new-{name}.md")
        if not os.path.exists(new_path):
            print(f"== {name}: MISSING new-{name}.md")
            continue
        old, new = read(path), read(new_path)
        total_old += len(old.split())
        total_new += len(new.split())
        report(name, old, new, limits.get(name))
    if total_old:
        cut = 100 * (total_old - total_new) / total_old
        print(f"== total: {total_old} -> {total_new} words ({cut:.1f}% cut)")


if __name__ == "__main__":
    main()
