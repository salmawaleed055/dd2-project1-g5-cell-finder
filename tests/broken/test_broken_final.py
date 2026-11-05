"""
Broken cases for the Checkpoint 3 checks (overview, section 4.3, rule 3):

  * cell responses that must not be used in a mapping: status fail, a
    function that differs from the requested truth table, and a Liberty file
    with two cell groups;
  * a mapped SPM netlist with one cell swapped must fail Tutorial 4's
    gate-level testbench;
  * a mapped multiplier netlist (no flip-flops, so checked by `cec`
    instead of `dsec`) with one cell swapped must fail the check;
  * a candidate that raises the total area must not be kept by the greedy
    selection.
"""

import os
import re
import sys
import unittest

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
os.chdir(repo_root)
sys.path.insert(0, os.path.join(repo_root, "tests"))

from test_final import make_response  # noqa: E402
from src.final_flow import greedy_select, run_testbench  # noqa: E402
from src.responses import check_response  # noqa: E402
from src.equivalence import netlist_to_aig, run_cec, write_ff_models  # noqa: E402
from src.table5 import WORK_DIR, map_design  # noqa: E402

TMP = "build/test_broken_final"


class TestBrokenResponses(unittest.TestCase):
    def setUp(self):
        os.makedirs(TMP, exist_ok=True)

    def test_failed_cell_is_rejected(self):
        req, resp = make_response(0x077F, TMP, status="fail")
        problems, text = check_response(resp, req)
        self.assertIsNone(text)
        self.assertTrue(any("not pass" in p for p in problems))
        print("PASS: a response with status fail was rejected.")

    def test_wrong_function_is_rejected(self):
        req, resp = make_response(0x077F, TMP, function="!((A&B)|(C&D))")
        problems, text = check_response(resp, req)
        self.assertIsNone(text)
        self.assertTrue(any("not the requested" in p for p in problems), problems)
        print("PASS: a response whose function differs from the truth table was rejected.")

    def test_two_cell_groups_are_rejected(self):
        req, resp = make_response(0x077F, TMP, extra_group=True)
        problems, text = check_response(resp, req)
        self.assertIsNone(text)
        self.assertTrue(any("not exactly one" in p for p in problems), problems)
        print("PASS: a response Liberty file with two cell groups was rejected.")


class TestBrokenGateLevel(unittest.TestCase):
    def test_swapped_cell_fails_the_testbench(self):
        src = "designs/tutorials/spm/SPM.v designs/tutorials/spm/CSADD.v designs/tutorials/spm/TCMP.v"
        map_design("spm", "SPM", "given/hd_reduced.lib", "brk", "A", src=src, check=False)
        with open("results/netlists/spm_brk_A.v", 'r', encoding='utf-8') as f:
            good = f.read()
        # Swap the first two-input XOR or XNOR for its complement.
        bad, n = re.subn(r"sky130_fd_sc_hd__xor2_1 ", "sky130_fd_sc_hd__xnor2_1 ", good, count=1)
        if n == 0:
            bad, n = re.subn(r"sky130_fd_sc_hd__xnor2_1 ", "sky130_fd_sc_hd__xor2_1 ", good, count=1)
        if n == 0:
            bad, n = re.subn(r"sky130_fd_sc_hd__nand2_1 ", "sky130_fd_sc_hd__nor2_1 ", good, count=1)
        self.assertEqual(n, 1, "no cell to swap in the SPM netlist")
        os.makedirs(TMP, exist_ok=True)
        with open(f"{TMP}/spm_bad.v", 'w', encoding='utf-8') as f:
            f.write(bad)
        ok, out = run_testbench("SPM_tb", "designs/tutorials/spm/SPM_tb.v", f"{TMP}/spm_bad.v",
                                None, work=f"{TMP}/gls")
        self.assertFalse(ok, "the testbench must fail on the broken netlist")
        # It must fail because the products are wrong, not because it did not compile.
        self.assertIn("ERROR:", out, out[-800:])
        print("PASS: SPM_tb reported wrong products on the netlist with one cell swapped.")


class TestBrokenCombinationalCec(unittest.TestCase):
    def test_swapped_cell_in_the_multiplier_fails_cec(self):
        """The multiplier has no flip-flops, so it is checked by cec, not dsec."""
        lib = "given/hd_reduced.lib"
        row = map_design("mul", "mul", lib, "brk", "A", src="designs/tutorials/mul/mul.v")
        self.assertEqual(row["cec"], "pass", "the unbroken netlist must pass first")
        with open("results/netlists/mul_brk_A.v", 'r', encoding='utf-8') as f:
            good = f.read()
        bad, n = re.subn(r"sky130_fd_sc_hd__(xor2|xnor2|nand2|nor2)_1 ",
                         lambda m: {"xor2": "sky130_fd_sc_hd__xnor2_1 ", "xnor2": "sky130_fd_sc_hd__xor2_1 ",
                                    "nand2": "sky130_fd_sc_hd__nor2_1 ",
                                    "nor2": "sky130_fd_sc_hd__nand2_1 "}[m.group(1)], good, count=1)
        self.assertEqual(n, 1)
        os.makedirs(TMP, exist_ok=True)
        with open(f"{TMP}/mul_bad.v", 'w', encoding='utf-8') as f:
            f.write(bad)
        ff_v = f"{TMP}/ff.v"
        ff = write_ff_models(lib, ff_v)
        netlist_to_aig(f"{WORK_DIR}/mul_brk_A_pre.v", "mul", lib, ff_v, ff, f"{TMP}/mul_gold.aig")
        netlist_to_aig(f"{TMP}/mul_bad.v", "mul", lib, ff_v, ff, f"{TMP}/mul_bad.aig")
        ok, out = run_cec(f"{TMP}/mul_gold.aig", f"{TMP}/mul_bad.aig")
        self.assertFalse(ok, out[-500:])
        self.assertIn("NOT EQUIVALENT", out.upper())
        print("PASS: cec rejected the multiplier netlist with one cell swapped.")


class TestBrokenGreedy(unittest.TestCase):
    def test_candidate_that_raises_area_is_dropped(self):
        pool = [{"name": "worse", "p_class": "", "rank": 1, "occurrences": 999, "area": 1.0,
                 "est_saving_um2": 1e6}]
        chosen, log = greedy_select(pool, lambda cells: (100.5, {
            "new_cell_instances_A": 5, "new_cell_instances_B": 5}), 100.0)
        self.assertEqual(chosen, [])
        self.assertFalse(log[0]["kept"])
        print("PASS: the greedy selection dropped a candidate that raised the total area.")


if __name__ == "__main__":
    unittest.main()
