import sys
import os

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import unittest
from src.redundancy import RedundancyChecker


class TestBrokenRedundancy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.checker = RedundancyChecker("given/hd_usable.lib")

    def test_hd_cell_must_flag_as_exists(self):
        """
        Takes sky130_fd_sc_hd__nand4_1 (function: !(A & B & C & D), TT = 0x7FFF).
        Verifies that it flags as 'Exists'.
        Also verifies that claiming this HD cell as 'New' fails an assertion.
        """
        nand4_tt = 0x7FFF
        result = self.checker.classify(nand4_tt)
        self.assertEqual(result, "Exists")

        # Simulate a broken claim: if an algorithm claimed nand4 is 'New', catch it
        def claim_candidate_is_new(candidate_tt: int) -> bool:
            return self.checker.classify(candidate_tt) == "New"

        self.assertFalse(
            claim_candidate_is_new(nand4_tt),
            "Broken check: sky130_fd_sc_hd__nand4_1 was falsely flagged as New!"
        )
        print("PASS: Redundancy check correctly identified HD cell as Exists and rejected fake New claim.")


if __name__ == "__main__":
    unittest.main()
