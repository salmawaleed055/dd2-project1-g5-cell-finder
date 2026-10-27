import sys
import os
import unittest

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from src.runner import runner


class TestBrokenCEC(unittest.TestCase):
    def test_abc_cec_rejects_inequivalent_netlists(self):
        """Runs ABC cec on netlist_spec.v and netlist_broken.v and asserts non-equivalence."""
        spec_file = os.path.join("tests", "broken", "netlist_spec.v")
        if not os.path.exists(spec_file):
            spec_file = os.path.join("repo_template", "tests", "broken", "netlist_spec.v")

        broken_file = os.path.join("tests", "broken", "netlist_broken.v")
        if not os.path.exists(broken_file):
            broken_file = os.path.join("repo_template", "tests", "broken", "netlist_broken.v")

        spec_clean = spec_file.replace("\\", "/")
        broken_clean = broken_file.replace("\\", "/")

        res = runner.run_cmd(["yosys-abc", "-c", f"cec {spec_clean} {broken_clean}"])
        output = res.stdout + res.stderr
        self.assertTrue(
            "NOT EQUIVALENT" in output or res.returncode != 0,
            f"ABC CEC should have rejected equivalence!\nOutput:\n{output}"
        )
        print("PASS: ABC CEC successfully rejected inequivalent netlists.")


if __name__ == "__main__":
    unittest.main()
