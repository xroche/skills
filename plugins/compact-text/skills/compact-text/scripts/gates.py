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

# Order matters: each match is cut from the text before the next kind runs,
# so the digits of a URL or a citation are not listed again as numbers.
FACT_PATTERNS = {
    "url": r"https?://[^\s)>\]<`\"']+",
    "code": r"`[^`\n]+(?:\n[^`\n]+)?`",
    "file:line": r"\b[\w./-]+\.\w+:\d+\b",
    "ticket": r"\b[A-Z][A-Z0-9]+-\d+\b",
    "number": r"(?<![\w.])v?\d{1,3}(?:,\d{3})+(?:\.\d+)?%?"
    r"|(?<![\w.])v?\d+(?:\.\d+)*%?",
}
URL_TAIL = ".,;:!?*_"

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
    with open(path, encoding="utf-8") as f:
        return f.read()


def prose(text):
    """Return the text without fenced code blocks and table rows."""
    text = re.sub(r"^```.*?^```", "", text, flags=re.S | re.M)
    return "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("|")
    )


def norm(text):
    """Collapse whitespace, drop thousands separators, spell percent as %."""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", text)
    return re.sub(r"(?<=\d) ?percent\b", "%", text)


def facts(text):
    """Return a Counter of (kind, value) for every fact in the normalized text."""
    found = Counter()
    rest = norm(text)
    for kind, pattern in FACT_PATTERNS.items():
        for m in re.finditer(pattern, rest):
            value = m.group(0)
            value = value.rstrip(URL_TAIL) if kind == "url" else value
            found[(kind, value.rstrip(","))] += 1
        rest = re.sub(pattern, " ", rest)
    return found


def token_in(value, text):
    return re.search(rf"(?<![\w-]){re.escape(value)}(?![\w-])", text)


def present(kind, value, text, found):
    """Is this fact still in the text, as itself or in a form that keeps it?

    Strict by default, because a silent loss costs more than a false GONE.
    """
    if (kind, value) in found:
        return True
    of = {k: [v for (kk, v) in found if kk == k] for k in FACT_PATTERNS}
    if kind == "number":
        return any(token_in(value, v.strip("`")) for v in of["code"]) or any(
            v.rsplit(":", 1)[1] == value for v in of["file:line"]
        )
    if kind == "code":
        inner = value.strip("`")
        return any(token_in(inner, v.strip("`")) for v in of["code"])
    if kind == "file:line":
        path, line = map(re.escape, value.rsplit(":", 1))
        forms = rf"{path},? line {line}\b|\bline {line} (?:of|in) {path}"
        return bool(re.search(forms, text))
    if kind == "ticket":
        return token_in(value, text)
    return re.search(re.escape(value) + r"(?![\w/?=&%#~+-])", text)


def report(name, old, new, budget):
    w_old, w_new = len(old.split()), len(new.split())
    cut = 100 * (w_old - w_new) / w_old if w_old else 0
    line = f"== {name}: {w_old} -> {w_new} words ({cut:.1f}% cut)"
    if budget:
        status = "within" if w_new <= budget else f"OVER by {w_new - budget}"
        line += f", budget {budget}, {status}"
    print(line)

    f_old, f_new = facts(old), facts(new)
    n_old, n_new = norm(old), norm(new)
    for (kind, value), n in sorted(f_old.items()):
        if not present(kind, value, n_new, f_new):
            print(f"  GONE   {kind} {value}")
        elif 0 < f_new[(kind, value)] < n:
            print(f"  dedup  {kind} {value} ({n} -> {f_new[(kind, value)]})")
    for kind, value in sorted(f_new):
        if not present(kind, value, n_old, f_old):
            print(f"  NEW    {kind} {value}")

    for label, pattern in (("fold", FOLD), ("heading", HEADING)):
        gone = set(pattern.findall(old)) - set(pattern.findall(new))
        for title in sorted(gone):
            print(f"  GONE   {label} {title}")
    if new.count("[FOLD:") != new.count("[/FOLD]"):
        print("  BROKEN fold markers do not pair up")

    body = re.sub(r"\s+", " ", prose(new))
    for s in re.split(r"(?<=[.!?])\s+(?=[A-Z`*\[(])", body):
        if len(s.split()) > LONG:
            print(f"  long   {len(s.split())}w: {s.strip()[:100]}")
    for label, pattern in BANNED.items():
        for m in re.finditer(pattern, body):
            context = body[max(0, m.start() - 40) : m.end() + 40]
            print(f"  banned {label}: ...{context}...")


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
