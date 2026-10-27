import sys
import os

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import unittest
from src.redundancy import RedundancyChecker, parse_hd_library, eval_lib_expr
from src.classification import get_p_class, depends_on_all_4


class TestRedundancy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.checker = RedundancyChecker("given/hd_usable.lib")

    def test_hd_cells_come_out_as_exists(self):
        """Rule (Section 5): Every combinational HD cell, fed to it as a candidate, must come out as Exists."""
        cells = parse_hd_library("given/hd_usable.lib")
        self.assertGreaterEqual(len(cells), 264)
        for c in cells:
            classification = self.checker.classify_hd_cell_dict(c)
            self.assertEqual(classification, "Exists", f"HD cell {c['name']} must be classified as Exists")

    def test_table4_reference_counts(self):
        """Validates all reference counts from Handout Table 4."""
        counts = self.checker.run_self_test()
        self.assertEqual(counts["Exists"], 24, "Exists count mismatch")
        self.assertEqual(counts["Exists with an inverter"], 20, "Exists with inverter count mismatch")
        self.assertEqual(counts["Contained"], 38, "Contained count mismatch")
        self.assertEqual(counts["New"], 3822, "New count mismatch")
        self.assertEqual(counts["New, and one static CMOS stage"], 9, "New one stage count mismatch")
        self.assertEqual(counts["New, one stage, at most 3 transistors in series and at most 12 transistors"], 5, "New 3-series 12-tx count mismatch")
        self.assertEqual(counts["One stage with every input used once"], 8, "Simplest cells count mismatch")
        self.assertEqual(counts["One stage with every input used once, Exists"], 6, "Simplest cells Exists mismatch")
        self.assertEqual(counts["One stage with every input used once, Contained"], 2, "Simplest cells Contained mismatch")


if __name__ == "__main__":
    unittest.main()
