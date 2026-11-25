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

    def test_clean_text_raises_no_flag(self):
        out = run(OLD, OLD)
        for flag in ("banned", "BROKEN", "long"):
            self.assertNotIn(flag, out)

    def test_fact_that_changed_form_is_not_gone(self):
        for old, new in (
            ("Set 3 retries.", "Set `retries=3`."),
            ("See line 42 of foo.c.", "See foo.c:42."),
            ("PROJ-9 (https://j.io/browse/PROJ-9)", "https://j.io/browse/PROJ-9"),
            ("See src/a.py:42.", "See line 42 of src/a.py."),
            ("About 1,231 words.", "About 1231 words."),
            ("Up 50%.", "Up 50 percent."),
            ("Cap 591, then stop.", "Cap 591 then stop."),
            ("At **https://x.com/a**.", "At https://x.com/a now."),
            ('Read "https://x.com/a".', "Read https://x.com/a."),
        ):
            with self.subTest(old=old):
                self.assertNotIn("GONE", run(old, new))

    def test_real_loss_is_not_hidden_by_lookalikes(self):
        for old, new in (
            ("Retry 3 times. Fixed in PROJ-3.", "Fixed in PROJ-3."),
            ("Retry 3 times.", "See https://x.org/pull/3 and v3."),
            ("Run `id` now.", "It did run."),
            ("Run `make` now.", "It makes sense."),
            ("See src/a.py:42.", "src/a.py changed, see b.py:42 for 420 rows."),
            ("Docs at https://e.com/docs today.", "Docs at https://e.com/docs/v2."),
            ("Use ?id=1 at https://e.com/?id=1 now.", "Use https://e.com/?id=12 now."),
            ("Fix PROJ-1 now.", "Fix PROJ-12 now."),
        ):
            with self.subTest(old=old):
                self.assertIn("GONE", run(old, new))

    def test_versions_are_whole_facts(self):
        self.assertIn("GONE   number v38", run("Ship v38.", "Ship it."))
        self.assertIn("GONE   number 2.1.224", run("Use 2.1.224.", "Use 2.1.225."))
        self.assertIn("NEW    number 2.1.225", run("Use 2.1.224.", "Use 2.1.225."))

    def test_wrapped_code_span_still_tracks_the_next_one(self):
        out = run("Use `foo\nbar` and `baz` here.", "Use `foo bar` here.")
        self.assertIn("GONE   code `baz`", out)
        self.assertNotIn("GONE   code `foo", out)

    def test_long_sentence_is_reported_and_short_ones_are_not(self):
        self.assertIn("long   26w", run("x.\n", " ".join(["w"] * 26) + ".\n"))
        self.assertNotIn("long", run("x.\n", ("A " + "a " * 19 + "b. ") * 2))

    def test_every_banned_spelling(self):
        for text, label in (
            ("Ok. Currently, b", "Currently opener"),
            ("a -- b", "em dash"),
        ):
            self.assertIn(f"banned {label}", run("x", text))

    def test_budget_boundary_and_overrun_amount(self):
        self.assertIn("within", run("a b c", "a b c", 3))
        self.assertIn("OVER by 2", run("a b c", "a b c d e", 3))

    def test_main_reports_missing_rewrite(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "chunk-y.md"), "w") as f:
                f.write(OLD)
            out = io.StringIO()
            with contextlib.redirect_stdout(out), mock.patch(
                "sys.argv", ["gates.py", d]
            ):
                gates.main()
            self.assertIn("MISSING new-y.md", out.getvalue())

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
            self.assertIn("== total: 27 -> 1 words (96.3% cut)", out.getvalue())
            self.assertIn("== total:", out.getvalue())


if __name__ == "__main__":
    unittest.main()
