"""Tests for gates.py. Run: python3 -m unittest test_gates (from this dir)."""

import contextlib
import io
import os
import tempfile
import unittest
from unittest import mock

import gates

OLD = """# Rollout
The cap is 591 tenants, see PROJ-123 and `max_tenants` at src/limit.c:42.
Docs at https://example.com/x. The cap is 591 tenants again.
[FOLD: Details]
More detail.
[/FOLD]
"""


def run(old, new, budget=None):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        gates.report("a", old, new, budget)
    return out.getvalue()


class Gates(unittest.TestCase):
    def test_identical_text_reports_nothing_lost(self):
        out = run(OLD, OLD)
        self.assertNotIn("GONE", out)
        self.assertNotIn("dedup", out)
        self.assertNotIn("NEW", out)

    def test_every_fact_kind_is_reported_gone(self):
        out = run(OLD, "Nothing left.\n")
        for item in (
            "number 591",
            "ticket PROJ-123",
            "code `max_tenants`",
            "file:line src/limit.c:42",
            "url https://example.com/x",
            "heading Rollout",
            "fold Details",
        ):
            self.assertIn(f"GONE   {item}", out)

    def test_fewer_occurrences_is_dedup_not_gone(self):
        out = run("591 and 591.\n", "591 once.\n")
        self.assertIn("dedup  number 591 (2 -> 1)", out)
        self.assertNotIn("GONE", out)

    def test_digits_inside_url_or_citation_are_not_numbers(self):
        out = run("See src/a.c:42 and https://x.org/7.\n", "Gone.\n")
        self.assertNotIn("number 42", out)
        self.assertNotIn("number 7", out)

    def test_new_number_and_budget_overrun(self):
        out = run("Ten words " * 2 + "\n", "Now 600 things " * 4 + "\n", 5)
        self.assertIn("NEW    number 600", out)
        self.assertIn("OVER by", out)

    def test_banned_constructions_and_broken_fold(self):
        out = run(OLD, "It is robust — really; This ensures it.\n[FOLD: X]\n")
        for label in ("em dash", "semicolon", "filler opener", "promotion"):
            self.assertIn(f"banned {label}", out)
        self.assertIn("BROKEN fold markers", out)

    def test_table_rows_are_not_long_sentences(self):
        row = "| " + " ".join(["word"] * 40) + " |\n"
        self.assertNotIn("long", run(row, row))

    def test_main_reads_work_dir_and_budgets(self):
        with tempfile.TemporaryDirectory() as d:
            for name, text in (("chunk-x.md", OLD), ("new-x.md", "Short.\n")):
                with open(os.path.join(d, name), "w") as f:
                    f.write(text)
            with open(os.path.join(d, "budgets.txt"), "w") as f:
                f.write("x 10\n")
            out = io.StringIO()
            argv = ["gates.py", d]
            with contextlib.redirect_stdout(out), mock.patch("sys.argv", argv):
                gates.main()
            self.assertIn("budget 10, within", out.getvalue())
            self.assertIn("== total:", out.getvalue())


if __name__ == "__main__":
    unittest.main()
