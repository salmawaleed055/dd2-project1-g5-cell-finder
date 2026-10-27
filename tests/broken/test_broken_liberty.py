import sys
import os
import unittest

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from src.runner import runner


class TestBrokenLiberty(unittest.TestCase):
    def test_yosys_rejects_broken_liberty(self):
        """Runs Yosys read_liberty on broken_liberty.lib and asserts rejection (non-zero return code)."""
        broken_lib = os.path.join("tests", "broken", "broken_liberty.lib")
        if not os.path.exists(broken_lib):
            broken_lib = os.path.join("repo_template", "tests", "broken", "broken_liberty.lib")
        broken_lib_clean = broken_lib.replace("\\", "/")

        res = runner.run_cmd(["yosys", "-q", "-p", f"read_liberty {broken_lib_clean}"])
        # Must fail with non-zero return code
        self.assertNotEqual(res.returncode, 0, f"Yosys should have failed on broken_liberty.lib!\nOutput: {res.stdout}\n{res.stderr}")
        print("PASS: Yosys successfully rejected broken_liberty.lib.")


if __name__ == "__main__":
    unittest.main()
