"""
Area model fitted to HD's own x1 cells (Option 2 handout, section 4, step 6).

HD cells are 2.72 um tall and a whole number of 0.46 um sites wide, so the
model predicts the width in sites:

    sites = c0 + c1 * transistors + c2 * (stages - 1)

fitted by least squares on every single-output combinational x1 cell of HD
with at most 4 inputs (the size of every candidate), using the transistor and
stage counts of src/cmos_cost.py, so that a candidate and the HD cells it is
compared with are costed the same way.  The estimated width is rounded up to a
whole site.  The fit is reported cell by cell, split into single-stage and
multi-stage cells, with the mean and maximum error.
"""

import csv
import math
import os
from typing import Dict, List, Tuple

from src.cmos_cost import cmos_cost
from src.redundancy import parse_hd_library, eval_cell_truth_table

ROW_HEIGHT_UM = 2.72
SITE_WIDTH_UM = 0.46
SITE_AREA_UM2 = ROW_HEIGHT_UM * SITE_WIDTH_UM  # 1.2512 um2


def tt16_of_cell(cell: Dict) -> int:
    """16-bit truth table of a Liberty cell with at most 4 inputs (pins in order = A..D)."""
    pins = tuple(cell['inputs'])
    k = len(pins)
    t = eval_cell_truth_table(cell['function'], pins)
    return sum(1 << i for i in range(16) if (t >> (i & ((1 << k) - 1))) & 1)


def _features(cost: Dict) -> List[float]:
    return [1.0, float(cost['transistors']), float(max(0, cost['stages'] - 1))]


def _least_squares(X: List[List[float]], y: List[float]) -> List[float]:
    """Solves the normal equations (X^T X) b = X^T y by Gauss-Jordan elimination."""
    n = len(X[0])
    A = [[sum(r[i] * r[j] for r in X) for j in range(n)] + [sum(r[i] * yy for r, yy in zip(X, y))]
         for i in range(n)]
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(A[r][c]))
        A[c], A[piv] = A[piv], A[c]
        for r in range(n):
            if r != c:
                f = A[r][c] / A[c][c]
                A[r] = [a - f * b for a, b in zip(A[r], A[c])]
    return [A[i][n] / A[i][i] for i in range(n)]


class AreaModel:
    """Width-in-sites model fitted to HD x1 cells."""

    def __init__(self, lib_path: str = "given/hd_usable.lib"):
        self.rows: List[Dict] = []
        for c in parse_hd_library(lib_path):
            if not c['name'].endswith('_1') or not 1 <= len(c['inputs']) <= 4:
                continue
            cost = cmos_cost(tt16_of_cell(c))
            self.rows.append({
                "cell": c['name'],
                "inputs": len(c['inputs']),
                "transistors": cost['transistors'],
                "stages": cost['stages'],
                "construction": cost['construction'],
                "sites": round(c['area'] / SITE_AREA_UM2),
                "area_um2": c['area'],
            })
        X = [_features(r) for r in self.rows]
        y = [float(r['sites']) for r in self.rows]
        self.coef = _least_squares(X, y)
        for r, x in zip(self.rows, X):
            r['predicted_sites'] = sum(a * b for a, b in zip(self.coef, x))
            r['error_sites'] = r['predicted_sites'] - r['sites']

    def sites(self, cost: Dict) -> int:
        """Estimated width in whole sites (rounded up)."""
        raw = sum(a * b for a, b in zip(self.coef, _features(cost)))
        return max(1, math.ceil(raw - 1e-9))

    def area(self, cost: Dict) -> float:
        """Estimated area in um2."""
        return round(self.sites(cost) * SITE_AREA_UM2, 4)

    def error_summary(self) -> Dict[str, Dict[str, float]]:
        """Mean and max absolute error, in sites and %, per group."""
        out = {}
        groups = {"single-stage": [r for r in self.rows if r['stages'] == 1],
                  "multi-stage": [r for r in self.rows if r['stages'] > 1],
                  "all": self.rows}
        for g, rows in groups.items():
            if not rows:
                continue
            errs = [abs(r['error_sites']) for r in rows]
            pct = [abs(r['error_sites']) / r['sites'] * 100 for r in rows]
            out[g] = {"cells": len(rows), "mae_sites": sum(errs) / len(errs),
                      "max_sites": max(errs), "mape_pct": sum(pct) / len(pct)}
        return out

    def write_report(self, csv_path: str = "results/area_model.csv",
                     md_path: str = "results/area_model.md") -> None:
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(self.rows[0].keys()))
            w.writeheader()
            for r in self.rows:
                w.writerow({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()})
        c0, c1, c2 = self.coef
        summ = self.error_summary()
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write("# Area Model Fitted to HD x1 Cells\n\n")
            f.write("Least-squares fit of the width in sites (0.46 um x 2.72 um = 1.2512 um2 per site) "
                    "on every single-output combinational `_1` cell of HD with 1 to 4 inputs, "
                    "with transistor and stage counts from `src/cmos_cost.py` "
                    "(at most 3 transistors in series per stage).\n\n")
            f.write(f"**sites = {c0:.3f} + {c1:.3f} x transistors + {c2:.3f} x (stages - 1)**, "
                    "rounded up to a whole site for a new cell.\n\n")
            f.write("| Group | Cells | Mean abs. error (sites) | Max abs. error (sites) | Mean abs. error (%) |\n")
            f.write("|---|---|---|---|---|\n")
            for g, s in summ.items():
                f.write(f"| {g} | {s['cells']} | {s['mae_sites']:.2f} | {s['max_sites']:.2f} | {s['mape_pct']:.1f}% |\n")
            f.write("\n## Cell by cell\n\n")
            f.write("| Cell | Inputs | Transistors | Stages | Construction | HD sites | Model sites | Error |\n")
            f.write("|---|---|---|---|---|---|---|---|\n")
            for r in sorted(self.rows, key=lambda r: (r['stages'] > 1, r['cell'])):
                f.write(f"| `{r['cell']}` | {r['inputs']} | {r['transistors']} | {r['stages']} | "
                        f"{r['construction']} | {r['sites']} | {r['predicted_sites']:.2f} | {r['error_sites']:+.2f} |\n")


if __name__ == "__main__":
    m = AreaModel()
    m.write_report()
    print("coefficients:", [round(c, 3) for c in m.coef])
    for g, s in m.error_summary().items():
        print(g, s)
