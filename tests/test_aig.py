import sys
import os

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import unittest
from src.aig import AIG, parse_aag, simulate_node


class TestAIG(unittest.TestCase):
    def setUp(self):
        # Create a simple synthetic AIG:
        # Inputs: 1 (lit 2), 2 (lit 4)
        # AND node 3 (lit 6) = 1 & !2 (lits 2, 5)
        # Output: lit 6
        self.test_aag_path = "build/test_simple.aag"
        os.makedirs("build", exist_ok=True)
        with open(self.test_aag_path, "w") as f:
            f.write("aag 3 2 0 1 1\n2\n4\n6\n6 2 5\n")

    def tearDown(self):
        if os.path.exists(self.test_aag_path):
            os.remove(self.test_aag_path)

    def test_parse_and_simulate(self):
        aig = parse_aag(self.test_aag_path)
        self.assertEqual(aig.max_var, 3)
        self.assertEqual(aig.num_inputs, 2)
        self.assertEqual(aig.num_outputs, 1)
        self.assertEqual(aig.num_ands, 1)
        self.assertEqual(aig.inputs, [1, 2])
        self.assertEqual(aig.outputs, [6])
        self.assertEqual(aig.and_nodes[3], (2, 5))

        # Test simulation: 3 = inp1 & ~inp2
        # (0, 0) -> 0 & 1 = 0
        self.assertEqual(simulate_node(aig, 3, {1: 0, 2: 0}), 0)
        # (1, 0) -> 1 & 1 = 1
        self.assertEqual(simulate_node(aig, 3, {1: 1, 2: 0}), 1)
        # (0, 1) -> 0 & 0 = 0
        self.assertEqual(simulate_node(aig, 3, {1: 0, 2: 1}), 0)
        # (1, 1) -> 1 & 0 = 0
        self.assertEqual(simulate_node(aig, 3, {1: 1, 2: 1}), 0)


if __name__ == "__main__":
    unittest.main()
