import sys
import os
import unittest

# Add repo_template and workspace root to path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from src.aig import parse_aag
from src.cut_enumerator import Cut, verify_cut, CutVerificationError


class TestBrokenCutTruthTable(unittest.TestCase):
    def setUp(self):
        # A simple AIG with an AND gate: node 3 = 1 & 2
        import os
        self.test_aag_path = "build/test_broken_aig.aag"
        os.makedirs("build", exist_ok=True)
        with open(self.test_aag_path, "w") as f:
            f.write("aag 3 2 0 1 1\n2\n4\n6\n6 2 4\n")
        self.aig = parse_aag(self.test_aag_path)

    def tearDown(self):
        import os
        if os.path.exists(self.test_aag_path):
            os.remove(self.test_aag_path)

    def test_corrupted_truth_table_fails_simulation(self):
        """
        True truth table for node 3 = inp1 & inp2 is:
        (0,0)->0, (1,0)->0, (0,1)->0, (1,1)->1 => 0x8 in 2-variable space (or 0x8888 in 16-bit).
        We deliberately corrupt bit 0 (change 0 to 1).
        verify_cut MUST catch the corruption and raise CutVerificationError.
        """
        correct_tt = 0x8888
        corrupted_tt = correct_tt ^ 0x0001  # Flip bit 0

        bad_cut = Cut(node=3, inputs=(1, 2), truth_table=corrupted_tt)

        with self.assertRaises(CutVerificationError) as ctx:
            verify_cut(self.aig, bad_cut)

        self.assertIn("Cut simulation mismatch", str(ctx.exception))
        print("PASS: verify_cut successfully caught the corrupted truth table.")


if __name__ == "__main__":
    unittest.main()
