"""
Broken cases for the Checkpoint 2 checks (overview, section 4.3, rule 3):

  * a mapped netlist with one cell swapped (nand2 -> nor2) must fail the
    mapping equivalence check (ABC dsec against the design before ABC);
  * an extended Liberty whose new cell has the wrong function must fail the
    Liberty check (verify_liberty_cells).
"""

import os
import re
import sys
import unittest

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
os.chdir(repo_root)

from src.equivalence import netlist_to_aig, run_cec, write_ff_models
from src.liberty_writer import cell_name, liberty_function, verify_liberty_cells, write_liberty
from src.table5 import WORK_DIR, NETLIST_DIR, map_design

TMP = "build/test_broken_cp2"
LIB = "given/hd_reduced.lib"


class TestBrokenMappedNetlist(unittest.TestCase):
    def test_swapped_cell_fails_cec(self):
        row = map_design("cpu8", "cpu8", LIB, "brk", "A")
        self.assertEqual(row["cec"], "pass", "the unbroken netlist must pass first")
        os.makedirs(TMP, exist_ok=True)
        with open(f"{NETLIST_DIR}/cpu8_brk_A.v", 'r', encoding='utf-8') as f:
            good = f.read()
        bad = re.sub(r"sky130_fd_sc_hd__nand2_1 ", "sky130_fd_sc_hd__nor2_1 ", good, count=1)
        self.assertNotEqual(good, bad)
        with open(f"{TMP}/cpu8_bad.v", 'w', encoding='utf-8') as f:
            f.write(bad)
        ff_v = f"{TMP}/ff.v"
        ff = write_ff_models(LIB, ff_v)
        netlist_to_aig(f"{WORK_DIR}/cpu8_brk_A_pre.v", "cpu8", LIB, ff_v, ff, f"{TMP}/gold.aig")
        netlist_to_aig(f"{TMP}/cpu8_bad.v", "cpu8", LIB, ff_v, ff, f"{TMP}/bad.aig")
        ok, out = run_cec(f"{TMP}/gold.aig", f"{TMP}/bad.aig")
        self.assertFalse(ok, "dsec must reject the broken netlist:\n" + out[-500:])
        print("PASS: dsec rejected the netlist with nand2 swapped for nor2.")


class TestBrokenNewCellFunction(unittest.TestCase):
    def test_wrong_function_is_flagged(self):
        os.makedirs(TMP, exist_ok=True)
        cell = {"name": cell_name(0x077F), "tt": 0x077F,
                "function": liberty_function(0x077F, ""), "area": 8.7584, "stages": 1}
        broken = dict(cell, function="!((A&B)|(C&D))")   # a22oi, not maj4n
        write_liberty(LIB, [broken], f"{TMP}/bad.lib")
        problems = verify_liberty_cells(f"{TMP}/bad.lib", [cell])
        self.assertTrue(problems, "a new cell with the wrong function must be flagged")
        print("PASS: Liberty check flagged the new cell with the wrong function.")


if __name__ == "__main__":
    unittest.main()
