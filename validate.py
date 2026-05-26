"""Shared validation logic for SOA PDF/CSV pairs."""

import csv
import glob
import os
import unittest

from parse_wi_soa import extract_text, parse_forms, HEADER


def find_pairs(directory):
    pdfs = sorted(glob.glob(os.path.join(directory, "*.pdf")))
    pairs = []
    for pdf in pdfs:
        csv_path = os.path.splitext(pdf)[0] + ".csv"
        if os.path.exists(csv_path):
            name = os.path.splitext(os.path.basename(pdf))[0]
            pairs.append((name, pdf, csv_path))
    return pairs


def make_test_case(name, pdf_path, csv_path):
    class Case(unittest.TestCase):
        def setUp(self):
            with open(csv_path) as f:
                reader = csv.reader(f)
                self.expected_header = next(reader)
                self.expected_rows = list(reader)
            text = extract_text(pdf_path)
            self.actual_rows = list(parse_forms(text))

        def test_header_matches(self):
            self.assertEqual(HEADER, self.expected_header)

        def test_row_count(self):
            self.assertEqual(len(self.actual_rows), len(self.expected_rows))

        def test_each_row_matches(self):
            for i, (actual, expected) in enumerate(zip(self.actual_rows, self.expected_rows)):
                with self.subTest(line=i + 1):
                    self.assertEqual(actual, expected)

    Case.__name__ = Case.__qualname__ = f"Test_{name}"
    return Case


def run_validations(directory):
    pairs = find_pairs(directory)
    if not pairs:
        print(f"No PDF/CSV pairs found in {directory}")
        return False

    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    for name, pdf, csv_path in pairs:
        case = make_test_case(name, pdf, csv_path)
        suite.addTests(loader.loadTestsFromTestCase(case))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()
