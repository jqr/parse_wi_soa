#!/usr/bin/env python3
"""Test parse_wi_soa against all known PDF/CSV pairs in validated/."""

import os
import unittest

from validate import find_pairs, make_test_case

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "validated")

for _name, _pdf, _csv in find_pairs(FIXTURES_DIR):
    globals()[f"Test_{_name}"] = make_test_case(_name, _pdf, _csv)

if __name__ == "__main__":
    unittest.main()
