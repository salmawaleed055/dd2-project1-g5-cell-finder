"""
Checkpoint 2 tests: CMOS costing, area model, Liberty writer, netlist repair
and the mapping equivalence flow.
"""

import os
import sys
import unittest

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
os.chdir(repo_root)

from src.area_model import AreaModel, SITE_AREA_UM2
from src.cmos_cost import cmos_cost
from src.liberty_writer import (cell_name, imported_cell_count, liberty_function,
                                timing_sense, tt_from_expr, verify_liberty_cells, write_liberty)
from src.netlist_repair import repair_netlist
from src.runner import runner
from src.table5 import map_design

TMP = "build/test_cp2"


class TestCmosCost(unittest.TestCase):
    def test_textbook_gates(self):
        """Transistor counts of gates whose CMOS form is standard."""
        cases = {0x5555: (2, 1), 0x7777: (4, 1), 0x1111: (4, 1), 0x8888: (6, 2),
                 0x6666: (12, 2), 0x077F: (12, 1)}
        for tt, (tx, st) in cases.items():
            c = cmos_cost(tt)
            self.assertEqual((c["transistors"], c["stages"]), (tx, st), hex(tt))

    def test_every_class_has_a_cost_with_at_most_3_in_series(self):
        for tt in range(1, 0xFFFF, 97):
            c = cmos_cost(tt)
            self.assertGreater(c["transistors"], 0)
            self.assertLessEqual(c["max_series"], 3)


class TestAreaModel(unittest.TestCase):
    def test_fit_and_rounding(self):
        m = AreaModel()
        self.assertGreaterEqual(len(m.rows), 50)
        self.assertGreater(m.coef[1], 0.0, "more transistors must mean more width")
        a = m.area(cmos_cost(0x077F))
        self.assertAlmostEqual(a / SITE_AREA_UM2, round(a / SITE_AREA_UM2), places=6)


class TestLibertyWriter(unittest.TestCase):
    def test_function_and_unateness(self):
        self.assertEqual(tt_from_expr(liberty_function(0x077F, "")), 0x077F)
        self.assertEqual(timing_sense(0x7777, 0), "negative_unate")
        self.assertEqual(timing_sense(0x8888, 1), "positive_unate")
        self.assertEqual(timing_sense(0x6666, 0), "non_unate")

    def test_yosys_reads_extended_library(self):
        os.makedirs(TMP, exist_ok=True)
        cells = [{"name": cell_name(tt), "tt": tt, "function": liberty_function(tt, ""),
                  "area": 8.7584, "stages": 1} for tt in (0x077F, 0x011F)]
        lib = f"{TMP}/ext.lib"
        write_liberty("given/hd_reduced.lib", cells, lib)
        self.assertEqual(verify_liberty_cells(lib, cells), [])
        res = runner.run_cmd(["yosys", "-p", f"read_liberty -lib {lib}"])
        self.assertEqual(imported_cell_count(res.stdout), 189 + len(cells))


class TestNetlistRepair(unittest.TestCase):
    def test_wrong_pin_name_is_resolved(self):
        pins = {"sky130_fd_sc_hd__o311ai_1": ["A1", "A2", "A3", "B1", "C1", "Y"]}
        net = ("\n  sky130_fd_sc_hd__o311ai_1 _1_ (\n    .\\$abc$1$new_n5 (a),\n    .A1(b),"
               "\n    .A2(c),\n    .A3(d),\n    .B1(e),\n    .Y(y)\n  );")
        fixed, alias = repair_netlist(net, pins)
        self.assertEqual(alias, {"\\$abc$1$new_n5": "C1"})
        self.assertIn(".C1(a)", fixed)


class TestMappingEquivalence(unittest.TestCase):
    def test_cpu8_baseline_mapping_passes_cec(self):
        row = map_design("cpu8", "cpu8", "given/hd_reduced.lib", "test", "A")
        self.assertEqual(row["cec"], "pass")
        self.assertGreater(row["area"], 0.0)


if __name__ == "__main__":
    unittest.main()
