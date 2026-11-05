"""
Checkpoint 3 tests: greedy selection, real-cell responses, the Liberty
function parser, the 30% Liberty edit, the new-cell Verilog models and the
gate-level testbench flow.
"""

import json
import os
import sys
import unittest

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
os.chdir(repo_root)

from src.final_flow import greedy_select, run_testbench, scaled_liberty
from src.liberty_writer import (cell_group, cell_name, imported_cell_count, liberty_function,
                                verilog_models, write_liberty)
from src.redundancy import eval_cell_truth_table, parse_hd_library
from src.responses import check_response, read_cell, truth_table
from src.runner import runner
from src.table5 import map_design

TMP = "build/test_final"


def make_cell(tt: int, area: float = 8.7584) -> dict:
    return {"name": cell_name(tt), "tt": tt, "function": liberty_function(tt, ""),
            "area": area, "stages": 1}


def make_response(tt: int, d: str, status: str = "pass", function: str = None,
                  extra_group: bool = False):
    """A request and a response in the Appendix A format, with its Liberty file."""
    c = make_cell(tt)
    req = {"request_id": "G5-001", "name": c["name"], "inputs": ["A", "B", "C", "D"],
           "output": "Y", "expression": c["function"], "truth_table": f"0x{tt:04X}",
           "sizing": "hd", "estimated_area_um2": c["area"]}
    lib = os.path.join(d, f"{c['name']}.lib").replace("\\", "/")
    text = cell_group(dict(c, function=function or c["function"]))
    if extra_group:
        text += "\n" + cell_group(dict(c, name=c["name"] + "_copy"))
    with open(lib, 'w', encoding='utf-8') as f:
        f.write(text + "\n")
    resp = {"request_id": "G5-001", "status": status, "reason": None if status == "pass" else "lvs",
            "cell": c["name"], "stages": 1, "transistors": 12, "width_sites": 7,
            "area_um2": c["area"], "files": {"liberty": lib}}
    return req, resp


class TestGreedySelection(unittest.TestCase):
    def test_keeps_only_cells_that_lower_the_total(self):
        pool = [{"name": n, "p_class": n, "rank": i, "occurrences": 1, "area": 1.0,
                 "est_saving_um2": 1.0} for i, n in enumerate("abcd", 1)]
        effect = {"a": -10.0, "b": +5.0, "c": -3.0, "d": 0.0}

        def evaluate(cells):
            return 100.0 + sum(effect[c["name"]] for c in cells), {
                "new_cell_instances_A": 0, "new_cell_instances_B": 0}

        chosen, log = greedy_select(pool, evaluate, 100.0)
        self.assertEqual([c["name"] for c in chosen], ["a", "c"])
        self.assertEqual([r["kept"] for r in log], [True, False, True, False])
        self.assertEqual(log[-1]["total_after_um2"], 87.0)

    def test_stops_at_max_cells(self):
        pool = [{"name": str(i), "p_class": "", "rank": i, "occurrences": 1, "area": 1.0,
                 "est_saving_um2": 1.0} for i in range(15)]
        chosen, log = greedy_select(pool, lambda cells: (100.0 - len(cells), {
            "new_cell_instances_A": 0, "new_cell_instances_B": 0}), 100.0, max_cells=10)
        self.assertEqual(len(chosen), 10)
        self.assertEqual(len(log), 10)


class TestLibertyFunctions(unittest.TestCase):
    def test_parser_agrees_with_hd_functions(self):
        """Every combinational reduced-HD function, parsed independently, gives the same table."""
        n = 0
        for c in parse_hd_library("given/hd_reduced.lib"):
            pins = tuple(c["inputs"])
            self.assertEqual(truth_table(c["function"], list(pins)),
                             eval_cell_truth_table(c["function"], pins), c["name"])
            n += 1
        self.assertGreater(n, 100)

    def test_full_liberty_operator_set(self):
        ab = ["A", "B", "C"]
        self.assertEqual(truth_table("A'B + C", ab), truth_table("(!A&B)|C", ab))
        self.assertEqual(truth_table("A*B+!C", ab), truth_table("(A&B)|(!C)", ab))
        self.assertEqual(truth_table("A B", ab), truth_table("A&B", ab))
        self.assertEqual(truth_table("!A^B", ab), truth_table("(!A)^B", ab))


class TestResponses(unittest.TestCase):
    def test_good_response_is_accepted(self):
        os.makedirs(TMP, exist_ok=True)
        req, resp = make_response(0x077F, TMP)
        problems, text = check_response(resp, req)
        self.assertEqual(problems, [])
        self.assertEqual(read_cell(text)["name"], req["name"])


class TestLibertyEdits(unittest.TestCase):
    def test_30pct_smaller_cell_loads_in_yosys(self):
        os.makedirs(TMP, exist_ok=True)
        cells = [make_cell(0x077F, 10.0096), make_cell(0x011F, 8.7584)]
        write_liberty("given/hd_reduced.lib", cells, f"{TMP}/ext.lib")
        a = scaled_liberty(f"{TMP}/ext.lib", cells[0]["name"], 0.7, f"{TMP}/ext30.lib")
        self.assertAlmostEqual(a, 7.0067, places=4)
        got = {c["name"]: c["area"] for c in parse_hd_library(f"{TMP}/ext30.lib")}
        self.assertAlmostEqual(got[cells[0]["name"]], 7.0067, places=4)
        self.assertAlmostEqual(got[cells[1]["name"]], 8.7584, places=4)
        res = runner.run_cmd(["yosys", "-p", f"read_liberty -lib {TMP}/ext30.lib"])
        self.assertEqual(imported_cell_count(res.stdout), 191)


class TestVerilogModels(unittest.TestCase):
    def test_models_match_the_truth_tables(self):
        """Simulates every generated model on all 16 inputs."""
        os.makedirs(TMP, exist_ok=True)
        tts = [0x077F, 0x011F, 0x82EB, 0x0009]
        cells = [make_cell(tt) for tt in tts]
        verilog_models(cells, f"{TMP}/models.v")
        tb = ["module tb;", "  reg [3:0] i;", "  integer k;"]
        tb += [f"  wire y{n}; {c['name']} u{n}(.A(i[0]), .B(i[1]), .C(i[2]), .D(i[3]), .Y(y{n}));"
               for n, c in enumerate(cells)]
        tb += ["  initial begin", "    for (k = 0; k < 16; k = k + 1) begin",
               "      i = k; #1;",
               "      $display(\"%0d " + " ".join("%b" for _ in cells) + "\", k, "
               + ", ".join(f"y{n}" for n in range(len(cells))) + ");",
               "    end", "  end", "endmodule"]
        with open(f"{TMP}/tb.v", 'w', encoding='utf-8') as f:
            f.write("\n".join(tb) + "\n")
        res = runner.run_cmd(["iverilog", "-o", f"{TMP}/tb", f"{TMP}/tb.v", f"{TMP}/models.v"])
        self.assertEqual(res.returncode, 0, res.stderr)
        out = runner.run_cmd(["vvp", "-n", f"{TMP}/tb"]).stdout.split("\n")
        got = [0] * len(cells)
        for line in out:
            parts = line.split()
            if len(parts) == len(cells) + 1 and parts[0].isdigit():
                for n, b in enumerate(parts[1:]):
                    got[n] |= int(b) << int(parts[0])
        self.assertEqual(got, tts)


class TestGateLevelSimulation(unittest.TestCase):
    def test_spm_baseline_passes_its_testbench(self):
        src = "designs/tutorials/spm/SPM.v designs/tutorials/spm/CSADD.v designs/tutorials/spm/TCMP.v"
        row = map_design("spm", "SPM", "given/hd_reduced.lib", "test", "A", src=src)
        self.assertEqual(row["cec"], "pass")
        ok, out = run_testbench("SPM_tb", "designs/tutorials/spm/SPM_tb.v",
                                "results/netlists/spm_test_A.v", None, work=f"{TMP}/gls")
        self.assertTrue(ok, out[-800:])


if __name__ == "__main__":
    unittest.main()
