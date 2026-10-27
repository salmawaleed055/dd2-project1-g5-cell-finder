import sys
import os

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import unittest
from src.aig import parse_aag
from src.cut_enumerator import CutEnumerator, verify_cut, Cut


class TestCutEnumerator(unittest.TestCase):
    def setUp(self):
        # 3-input synthetic AIG:
        # Inputs: 1, 2, 3 (lits 2, 4, 6)
        # Node 4 = 1 & 2 (lit 8 = 2 & 4)
        # Node 5 = 4 & !3 (lit 10 = 8 & 7)
        # Output: lit 10
        self.test_aag_path = "build/test_3inp.aag"
        os.makedirs("build", exist_ok=True)
        with open(self.test_aag_path, "w") as f:
            f.write("aag 5 3 0 1 2\n2\n4\n6\n10\n8 2 4\n10 8 7\n")

    def tearDown(self):
        if os.path.exists(self.test_aag_path):
            os.remove(self.test_aag_path)

    def test_cut_enumeration_and_simulation(self):
        aig = parse_aag(self.test_aag_path)
        enumerator = CutEnumerator(aig, max_cut_size=4)
        cuts = enumerator.enumerate_cuts()

        # Node 5 should have cuts including {1, 2, 3} and {4, 3}
        cuts_5 = cuts[5]
        self.assertGreaterEqual(len(cuts_5), 1)

        # Verify all cuts pass simulation
        for node, c_list in cuts.items():
            for c in c_list:
                self.assertTrue(verify_cut(aig, c))


if __name__ == "__main__":
    unittest.main()
