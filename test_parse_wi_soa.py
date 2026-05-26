#!/usr/bin/env python3
"""Test parse_wi_soa against all known PDF/CSV pairs in validated/."""

import os
import unittest

from parse_wi_soa import parse_forms, ParseError
from validate import find_pairs, make_test_case

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "validated")

for _name, _pdf, _csv in find_pairs(FIXTURES_DIR):
    globals()[f"Test_{_name}"] = make_test_case(_name, _pdf, _csv)


class TestParseErrors(unittest.TestCase):
    def test_not_an_soa_form(self):
        with self.assertRaises(ParseError) as ctx:
            parse_forms("just some random text")
        self.assertIn("column headers", str(ctx.exception))

    def test_multi_page_rejected(self):
        with self.assertRaises(ParseError) as ctx:
            parse_forms("page one\fpage two")
        self.assertIn("single-page", str(ctx.exception))

    def test_missing_municipality_header(self):
        header_line = "  ".join(f"(Col. {c})" for c in "ABCDEF")
        with self.assertRaises(ParseError) as ctx:
            parse_forms(f"STATEMENT OF ASSESSMENT\n{header_line}")
        self.assertIn("municipality header", str(ctx.exception))

    def test_source_appears_in_error(self):
        with self.assertRaises(ParseError) as ctx:
            parse_forms("not a form", source="myfile.pdf")
        self.assertIn("myfile.pdf", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
