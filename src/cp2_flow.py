"""
Checkpoint 2 flow: steps 6 to 9 of handout section 4.

    python src/run_step.py 6   area model fitted to HD x1 cells
    python src/run_step.py 9b  baseline mapping (hd_reduced.lib), both scripts, with cec
    python src/run_step.py 7   candidates costed, checked against HD and ranked
    python src/run_step.py 8   requests and extended Liberty (top N candidates)
    python src/run_step.py 9   extended mapping with cec and Table 5 (estimated areas)

Step 7 needs the baseline areas, so `make all` runs 9b before 7.
"""

import json
import sys

from src.area_model import AreaModel
from src.candidates import rank_candidates, write_candidate_reports
from src.liberty_writer import (cells_from_candidates, imported_cell_count,
                                verify_liberty_cells, write_liberty, write_requests)
from src.runner import runner
from src.table5 import map_all, write_baseline, write_table5

TOP_N = 10
BASE_LIB = "given/hd_reduced.lib"
EXT_LIB = "libs/hd_extended_est.lib"
BASE_ROWS = "results/table5_baseline_rows.json"
EXT_ROWS = "results/table5_extended_rows.json"


def step_6() -> None:
    m = AreaModel()
    m.write_report()
    c0, c1, c2 = m.coef
    print(f"sites = {c0:.3f} + {c1:.3f} x transistors + {c2:.3f} x (stages - 1)")
    for g, s in m.error_summary().items():
        print(f"  {g:12s} {s['cells']:3d} cells: mean error {s['mae_sites']:.2f} sites "
              f"({s['mape_pct']:.1f}%), max {s['max_sites']:.2f}")


def step_9_baseline() -> None:
    rows = map_all(BASE_LIB, "baseline")
    with open(BASE_ROWS, 'w', encoding='utf-8') as f:
        json.dump(rows, f, indent=1)
    write_baseline(rows)
    _require_cec(rows)


def step_7() -> None:
    rows = rank_candidates()
    write_candidate_reports(rows, TOP_N)
    kept = [r for r in rows if r["kept"]]
    print(f"{len(rows)} classes, {len(kept)} kept, "
          f"{sum(1 for r in kept if r['est_saving_um2'] > 0)} with a positive estimated saving")


def step_8() -> None:
    cells = cells_from_candidates("results/candidates.csv", TOP_N)
    write_liberty(BASE_LIB, cells, EXT_LIB)
    write_requests(cells)
    problems = verify_liberty_cells(EXT_LIB, cells)
    res = runner.run_cmd(["yosys", "-p", f"read_liberty -lib {EXT_LIB}"])
    n = imported_cell_count(res.stdout)
    print(f"Yosys: Imported {n} cell types (expected {189 + len(cells)})")
    if problems or n != 189 + len(cells):
        print("\n".join(problems))
        sys.exit(1)


def step_9() -> None:
    with open(BASE_ROWS, 'r', encoding='utf-8') as f:
        base = json.load(f)
    ext = map_all(EXT_LIB, "extended")
    with open(EXT_ROWS, 'w', encoding='utf-8') as f:
        json.dump(ext, f, indent=1)
    cells = cells_from_candidates("results/candidates.csv", TOP_N)
    write_table5(base, ext, cells, "Table 5 (first version, estimated areas)")
    _require_cec(ext)


def _require_cec(rows) -> None:
    bad = [f"{r['design']} {r['library']} {r['script']}" for r in rows if r["cec"] != "pass"]
    if bad:
        print("Equivalence check FAILED for: " + ", ".join(bad))
        sys.exit(1)
