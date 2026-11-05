"""
Checkpoint 3 flow: steps 10 to 12 of handout section 4, and the measurements
of section 7.

    python src/run_step.py 10     greedy selection of the final set (estimated areas)
    python src/run_step.py 11     real cells from cell responses, Table 5 with real areas
    python src/run_step.py 12     the 30% experiment
    python src/run_step.py curve  the cell-by-cell curve (CSV and PNG)
    python src/run_step.py delay  worst delay of every mapping with OpenSTA
    python src/run_step.py gls    SPM and the multiplier: mapping, dsec and testbenches
    python src/run_step.py extra  pic16 and p16c5x: do they favour risc8's cells?

All of them need the outputs of steps 6 to 9 (`make all` runs them first).

Greedy selection (step 10).  The candidates are taken in the order of the
ranking of step 7.  Each one is added to the cells already chosen, every
required design is remapped with both scripts on hd_reduced.lib plus those
cells, and the candidate is kept only if the total best-of-both area of the
required designs drops.  The selection stops after MAX_CELLS cells or when
the POOL best-ranked candidates have all been tried.  The trial mappings only
need areas, so they skip the equivalence check; the final set is then mapped
again with the check, and the two totals must agree (ABC is deterministic).
"""

import csv
import json
import os
import sys
from typing import Callable, Dict, List, Optional, Tuple

from src.cp2_flow import BASE_LIB, BASE_ROWS
from src.liberty_writer import (cells_from_candidates, imported_cell_count,
                                liberty_function, verify_liberty_cells, verilog_models,
                                write_liberty, write_requests)
from src.responses import cell_groups, collect_real_cells, write_real_liberty
from src.runner import runner
from src.table5 import DESIGNS, best_of_both, map_all, map_design, write_table5

POOL = 30
MAX_CELLS = 10
MIN_GAIN_UM2 = 0.001          # below this, a change in total area is float noise

FINAL_SET = "results/final_set.json"
EST_LIB = "libs/hd_extended_final_est.lib"
REAL_LIB = "libs/hd_extended_final_real.lib"
EST_ROWS = "results/table5_final_est_rows.json"
REAL_ROWS = "results/table5_final_real_rows.json"
GREEDY_DIR = "build/greedy"
PDK_VERILOG = "pdk/libs.ref/sky130_fd_sc_hd/verilog"

# SPM (Tutorial 4) and the multiplier (Tutorial 2), with their testbenches.
TUTORIAL_DESIGNS = [
    {"name": "spm", "top": "SPM",
     "src": "designs/tutorials/spm/SPM.v designs/tutorials/spm/CSADD.v designs/tutorials/spm/TCMP.v",
     "benches": [("SPM_tb", "designs/tutorials/spm/SPM_tb.v")]},
    {"name": "mul", "top": "mul",
     "src": "designs/tutorials/mul/mul.v",
     "benches": [("mul_tb", "designs/tutorials/mul/mul_tb.v"),
                 ("mul_exhaustive_tb", "designs/tutorials/mul/mul_exhaustive_tb.v")]},
]
# The other implementations of risc8's instruction set (handout, section 9.3).
ISA_DESIGNS = [
    {"name": "pic16", "top": "PIC16C5x"},
    {"name": "p16c5x", "top": "P16C5x"},
]


# ---------------------------------------------------------------- helpers
def _load_json(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _save_json(obj, path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, indent=1)


def _write_csv(rows: List[Dict], path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    keys: List[str] = []
    for r in rows:
        keys += [k for k in r if k not in keys]
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def _check_liberty(lib: str, n_new: int) -> None:
    """Yosys must import 189 + n_new cell types (handout, section 6)."""
    res = runner.run_cmd(["yosys", "-p", f"read_liberty -lib {lib}"])
    n = imported_cell_count(res.stdout)
    print(f"Yosys: Imported {n} cell types from {lib} (expected {189 + n_new})")
    if n != 189 + n_new:
        sys.exit(1)


def _require_cec(rows: List[Dict]) -> None:
    bad = [f"{r['design']} {r['library']} {r['script']}" for r in rows if r["cec"] != "pass"]
    if bad:
        print("Equivalence check FAILED for: " + ", ".join(bad))
        sys.exit(1)


def _total(rows: List[Dict]) -> float:
    return round(sum(best_of_both(rows).values()), 4)


def final_cells() -> List[Dict]:
    """The final set chosen by step 10, in the order it was chosen."""
    return _load_json(FINAL_SET)["cells"]


def real_lib_cells() -> Optional[List[Dict]]:
    """Cells of the real-area library, or None when no real cell was accepted."""
    path = "results/real_cells.json"
    if not os.path.exists(path) or not os.path.exists(REAL_LIB):
        return None
    acc = [r for r in _load_json(path) if r["status"] == "accepted"]
    return acc or None


# ---------------------------------------------------------------- step 10
def greedy_select(pool: List[Dict], evaluate: Callable[[List[Dict]], Tuple[float, Dict]],
                  base_total: float, max_cells: int = MAX_CELLS,
                  min_gain: float = MIN_GAIN_UM2) -> Tuple[List[Dict], List[Dict]]:
    """
    Handout section 4, step 10.  evaluate(cells) maps every required design
    with the given new cells and returns (total best-of-both area, details).
    Returns (chosen cells in order, one log record per trial).
    """
    chosen: List[Dict] = []
    log: List[Dict] = []
    current = base_total
    for c in pool:
        if len(chosen) >= max_cells:
            break
        total, detail = evaluate(chosen + [c])
        gain = current - total
        keep = gain > min_gain
        log.append({"trial": len(log) + 1, "cell": c["name"], "p_class": c["p_class"],
                    "rank": c["rank"], "occurrences": c["occurrences"],
                    "est_area_um2": c["area"], "est_saving_um2": c["est_saving_um2"],
                    "total_before_um2": round(current, 4), "total_after_um2": round(total, 4),
                    "gain_um2": round(gain, 4), "kept": keep, **detail})
        print(f"  trial {len(log):2d}: {c['name']} (rank {c['rank']}): total {total:,.2f} um2, "
              f"gain {gain:+.2f} -> {'KEEP' if keep else 'drop'}")
        if keep:
            chosen.append(c)
            current = total
    return chosen, log


def _trial_evaluator() -> Callable[[List[Dict]], Tuple[float, Dict]]:
    """Evaluates a set of new cells by mapping the required designs without dsec."""
    counter = [0]

    def evaluate(cells: List[Dict]) -> Tuple[float, Dict]:
        counter[0] += 1
        tag = f"g{counter[0]:02d}"
        lib = f"{GREEDY_DIR}/{tag}.lib"
        write_liberty(BASE_LIB, cells, lib)
        rows = map_all(lib, tag, check=False, netlist_dir=f"{GREEDY_DIR}/netlists",
                       log_dir=f"{GREEDY_DIR}/logs", quiet=True)
        best = best_of_both(rows)
        new = cells[-1]["name"]
        detail = {f"best_{d}": round(a, 2) for d, a in best.items()}
        detail["new_cell_instances_A"] = sum(r["new_cells"].get(new, 0) for r in rows if r["script"] == "A")
        detail["new_cell_instances_B"] = sum(r["new_cells"].get(new, 0) for r in rows if r["script"] == "B")
        return round(sum(best.values()), 4), detail

    return evaluate


def step_10() -> None:
    base = _load_json(BASE_ROWS)
    base_total = _total(base)
    pool = [c for c in cells_from_candidates("results/candidates.csv", POOL)
            if c["est_saving_um2"] > 0]
    os.makedirs(GREEDY_DIR, exist_ok=True)
    print(f"Greedy selection over the {len(pool)} best-ranked candidates; "
          f"baseline best-of-both total {base_total:,.2f} um2")
    chosen, log = greedy_select(pool, _trial_evaluator(), base_total)
    _write_csv(log, "results/greedy_log.csv")
    _save_json({"baseline_total_um2": base_total, "pool": len(pool),
                "cells": chosen, "curve": [base_total] + [r["total_after_um2"] for r in log if r["kept"]]},
               FINAL_SET)
    if not chosen:
        print("No candidate lowers the total area: the final set is empty.")
        _write_greedy_report(base_total, pool, chosen, log, None, [])
        return

    write_liberty(BASE_LIB, chosen, EST_LIB)
    problems = verify_liberty_cells(EST_LIB, chosen)
    if problems:
        print("\n".join(problems))
        sys.exit(1)
    _check_liberty(EST_LIB, len(chosen))
    write_requests(chosen)
    verilog_models(chosen, "libs/new_cells_est.v")

    print("Final set, estimated areas: mapping every required design with dsec")
    ext = map_all(EST_LIB, "final_est")
    _save_json(ext, EST_ROWS)
    write_table5(base, ext, chosen, "Table 5 (final set, estimated areas)",
                 csv_path="results/table5_final_est.csv", md_path="results/table5_final_est.md",
                 lib_desc=f"new cells of the final set with estimated areas (`{EST_LIB}`)")
    _require_cec(ext)
    final_total = _total(ext)
    _write_greedy_report(base_total, pool, chosen, log, final_total, ext)
    if abs(final_total - log_last_total(log)) > MIN_GAIN_UM2:
        print(f"Final mapping total {final_total} differs from the greedy total {log_last_total(log)}")
        sys.exit(1)


def log_last_total(log: List[Dict]) -> float:
    kept = [r for r in log if r["kept"]]
    return kept[-1]["total_after_um2"] if kept else log[0]["total_before_um2"]


def _write_greedy_report(base_total: float, pool: List[Dict], chosen: List[Dict],
                         log: List[Dict], final_total: Optional[float], ext: List[Dict]) -> None:
    with open("results/greedy.md", 'w', encoding='utf-8') as f:
        f.write("# Greedy selection of the final set (handout section 4, step 10)\n\n")
        f.write(f"Candidates tried, in rank order: the {len(pool)} best-ranked of "
                "`results/candidates.csv` with a positive estimated saving. A candidate is kept only "
                "if the total best-of-both area of the six required designs drops "
                f"(estimated areas; trial mappings in `build/greedy/`, log in `results/greedy_log.csv`). "
                f"At most {MAX_CELLS} cells.\n\n")
        f.write(f"- Baseline best-of-both total (`given/hd_reduced.lib`): **{base_total:,.2f} um2**\n")
        if chosen:
            last = log_last_total(log)
            f.write(f"- After the final set of {len(chosen)} cells: **{last:,.2f} um2** "
                    f"({(base_total - last) / base_total * 100:+.2f}%)\n")
        if final_total is not None:
            f.write(f"- Remapped with the equivalence check: {final_total:,.2f} um2 "
                    f"(`results/table5_final_est.md`)\n")
        f.write(f"- Candidates tried: {len(log)}, kept: {len(chosen)}\n\n")
        f.write("| Trial | Cell | Rank | Occurrences | Est. area | Est. saving | Total after (um2) | "
                "Gain (um2) | Instances A | Instances B | Kept |\n"
                "|---|---|---|---|---|---|---|---|---|---|---|\n")
        for r in log:
            f.write(f"| {r['trial']} | `{r['cell']}` | {r['rank']} | {r['occurrences']:,} | "
                    f"{r['est_area_um2']:.2f} | {r['est_saving_um2']:,.1f} | {r['total_after_um2']:,.2f} | "
                    f"{r['gain_um2']:+.2f} | {r['new_cell_instances_A']} | {r['new_cell_instances_B']} | "
                    f"{'**yes**' if r['kept'] else 'no'} |\n")
        unused = [c["name"] for c in chosen
                  if not any(r["new_cells"].get(c["name"], 0) for r in ext)]
        if unused:
            f.write("\n## Kept cells that the final mappings never use\n\n")
            f.write(f"{len(unused)} of the {len(chosen)} kept cells have no instance in any final mapping: "
                    + ", ".join(f"`{n}`" for n in unused) + ". Their gain was measured, but it does not "
                    "come from the cell: adding a cell to the Liberty changes the library ABC builds its "
                    "supergates and choices from, so the mapping of the rest of the design changes too. "
                    "These gains are mapping noise of the size of one or two HD cells, and a smaller "
                    "set without them is expected to give a similar total.\n")
        dropped = [r for r in log if not r["kept"]]
        if dropped:
            freq = max(dropped, key=lambda r: r["occurrences"])
            f.write("\n## Frequency against saving\n\n")
            f.write(f"The most frequent candidate that did not save area is `{freq['cell']}` "
                    f"(class `{freq['p_class']}`, {freq['occurrences']:,} cut occurrences, rank {freq['rank']}). "
                    f"Added to the cells already chosen, ABC used it {freq['new_cell_instances_A']} times with "
                    f"script A and {freq['new_cell_instances_B']} times with script B, and the total changed by "
                    f"{-freq['gain_um2']:+.2f} um2. ")
            if freq["new_cell_instances_A"] + freq["new_cell_instances_B"] == 0:
                f.write("Its cuts exist in the AIG, but the mappers found cheaper covers of the same logic "
                        "with HD cells, so the cell was never instantiated.\n")
            else:
                f.write("Where ABC used it, the logic around it was covered differently and the total "
                        "did not drop: a cut that is frequent in the AIG is not a cut the mapper "
                        "should take, because cuts overlap and the cell's area is paid per instance.\n")


# ---------------------------------------------------------------- step 11
def step_11() -> None:
    cells = final_cells()
    recs = collect_real_cells(cells)
    _save_json([{k: v for k, v in r.items() if k != "text"} for r in recs], "results/real_cells.json")
    accepted = [r for r in recs if r["status"] == "accepted"]
    with open("results/real_cells.md", 'w', encoding='utf-8') as f:
        f.write("# Real cells (handout section 4, step 11)\n\n")
        f.write("Each request of the final set (`cells/requests/`) is answered by a response in "
                "`cells/responses/<cell>.json` (overview, Appendix A). A response is used only if its "
                "status is pass, its Liberty file holds exactly one cell group with the requested name and "
                "pins, and its function equals the requested truth table (`src/responses.py`).\n\n")
        f.write("| Cell | Estimated area (um2) | Real area (um2) | Status | Problems |\n|---|---|---|---|---|\n")
        for r in recs:
            real = f"{r['area']:.4f}" if r["area"] else "-"
            f.write(f"| `{r['name']}` | {r['est_area']:.4f} | {real} | {r['status']} | "
                    f"{'; '.join(r['problems']) or '-'} |\n")
        if not accepted:
            f.write("\nNo response has been accepted yet, so Table 5 with real areas, the real-area curve "
                    "and the real-area 30% experiment are not measured. They are produced by "
                    "`python src/run_step.py 11` as soon as the responses are in `cells/responses/`.\n")
    print(f"{len(accepted)} of {len(cells)} real cells accepted (results/real_cells.md)")
    if os.path.exists(REAL_LIB):
        os.remove(REAL_LIB)
    if not accepted:
        return

    write_real_liberty(BASE_LIB, accepted, REAL_LIB)
    _check_liberty(REAL_LIB, len(accepted))
    real_cells = [dict(c, area=r["area"]) for c in cells for r in accepted if r["name"] == c["name"]]
    verilog_models(real_cells, "libs/new_cells_real.v")
    base = _load_json(BASE_ROWS)
    ext = map_all(REAL_LIB, "final_real")
    _save_json(ext, REAL_ROWS)
    write_table5(base, ext, real_cells, "Table 5 (final set, real cells)",
                 csv_path="results/table5_final_real.csv", md_path="results/table5_final_real.md",
                 lib_desc=f"real cells of the final set (`{REAL_LIB}`)", area_label="Real area (um2)")
    _require_cec(ext)

    # The cell-by-cell curve with real areas: add the accepted cells one at a
    # time, in the order the greedy selection chose them.
    curve = [{"cells": 0, "cell": "baseline", "total_um2": _total(base)}]
    for k in range(1, len(accepted) + 1):
        lib = f"{GREEDY_DIR}/real_{k}.lib"
        write_real_liberty(BASE_LIB, accepted[:k], lib)
        rows = map_all(lib, f"real{k}", check=False, netlist_dir=f"{GREEDY_DIR}/netlists",
                       log_dir=f"{GREEDY_DIR}/logs", quiet=True)
        curve.append({"cells": k, "cell": accepted[k - 1]["name"], "total_um2": _total(rows)})
    _write_csv(curve, "results/curve_real.csv")


# ---------------------------------------------------------------- curve
def step_curve() -> None:
    fs = _load_json(FINAL_SET)
    est = [{"cells": 0, "cell": "baseline", "total_um2": fs["baseline_total_um2"]}]
    for i, (c, t) in enumerate(zip(fs["cells"], fs["curve"][1:]), 1):
        est.append({"cells": i, "cell": c["name"], "total_um2": t})
    _write_csv(est, "results/curve_est.csv")
    series = {"estimated areas": est}
    if os.path.exists("results/curve_real.csv") and real_lib_cells():
        with open("results/curve_real.csv", 'r', encoding='utf-8') as f:
            series["real cells"] = [dict(r, cells=int(r["cells"]), total_um2=float(r["total_um2"]))
                                    for r in csv.DictReader(f)]
    with open("results/curve.md", 'w', encoding='utf-8') as f:
        f.write("# Cell-by-cell curve\n\nTotal best-of-both area of the six required designs after "
                "adding the final cells one at a time, in the order the tool chose them.\n\n")
        for label, rows in series.items():
            f.write(f"## {label.capitalize()}\n\n| Cells | Cell added | Total (um2) | Reduction |\n"
                    "|---|---|---|---|\n")
            b = rows[0]["total_um2"]
            for r in rows:
                f.write(f"| {r['cells']} | `{r['cell']}` | {r['total_um2']:,.2f} | "
                        f"{(b - r['total_um2']) / b * 100:+.2f}% |\n")
            f.write("\n")
        f.write("Plot: `results/curve.png`.\n")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed: results/curve.png not drawn (the CSV and markdown are written)")
        return
    fig, ax = plt.subplots(figsize=(7, 4))
    for (label, rows), style in zip(series.items(), ("o-", "s--")):
        ax.plot([r["cells"] for r in rows], [r["total_um2"] for r in rows], style, label=label)
    ax.set_xlabel("new cells added (in the order chosen)")
    ax.set_ylabel("total best-of-both area (um$^2$)")
    ax.set_title("Six required designs, hd_reduced.lib plus the final cells")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig("results/curve.png", dpi=150)
    print("results/curve.png written")


# ---------------------------------------------------------------- step 12
def scaled_liberty(lib: str, cell: str, factor: float, out_lib: str) -> float:
    """Copies lib with the area of one cell multiplied by factor; returns the new area."""
    import re
    with open(lib, 'r', encoding='utf-8') as f:
        text = f.read()
    groups = dict(cell_groups(text))
    old = groups[cell]
    area = float(re.search(r'\barea\s*:\s*([0-9.eE+-]+)', old).group(1))
    new_area = round(area * factor, 4)
    new = re.sub(r'\barea\s*:\s*[0-9.eE+-]+', f"area : {new_area:.4f}", old, count=1)
    with open(out_lib, 'w', encoding='utf-8') as f:
        f.write(text.replace(old, new))
    return new_area


def _sensitivity(lib: str, rows_path: str, label: str, tag: str) -> Dict:
    rows = _load_json(rows_path)
    count: Dict[str, int] = {}
    for r in rows:
        for c, n in r["new_cells"].items():
            count[c] = count.get(c, 0) + n
    cell = max(count, key=count.get)
    out_lib = f"libs/hd_extended_final_{tag}_30pct.lib"
    new_area = scaled_liberty(lib, cell, 0.7, out_lib)
    small = map_all(out_lib, f"{tag}30")
    _require_cec(small)
    base = _load_json(BASE_ROWS)
    idx = {(r["design"], r["script"]): r for r in small}
    table = []
    for r in rows:
        s = idx[(r["design"], r["script"])]
        table.append({"design": r["design"], "script": r["script"], "area_um2": r["area"],
                      "area_30pct_um2": s["area"],
                      "change_pct": round((s["area"] - r["area"]) / r["area"] * 100, 3),
                      "instances": r["new_cells"].get(cell, 0),
                      "instances_30pct": s["new_cells"].get(cell, 0), "cec": s["cec"]})
    return {"label": label, "cell": cell, "new_area": new_area, "lib": out_lib, "rows": table,
            "base_total": _total(base), "total": _total(rows), "total_30": _total(small)}


def step_12() -> None:
    runs = [_sensitivity(EST_LIB, EST_ROWS, "estimated areas", "est")]
    if real_lib_cells():
        runs.append(_sensitivity(REAL_LIB, REAL_ROWS, "real cells", "real"))
    _write_csv([dict(r, library=run["label"], cell=run["cell"]) for run in runs for r in run["rows"]],
               "results/sensitivity_30pct.csv")
    with open("results/sensitivity_30pct.md", 'w', encoding='utf-8') as f:
        f.write("# The 30% experiment (handout section 4, step 12)\n\n")
        f.write("The new cell with the most instances in the final mappings is made 30% smaller in the "
                "Liberty file, and every required design is remapped with both scripts (dsec on every "
                "mapping). ABC sees only the numbers in the Liberty, so this shows how much the result "
                "depends on the area estimate.\n\n")
        for run in runs:
            f.write(f"## {run['label'].capitalize()}: `{run['cell']}` at {run['new_area']:.4f} um2 "
                    f"(`{run['lib']}`)\n\n")
            f.write("| Design | Script | Area (um2) | With the cell 30% smaller (um2) | Change | "
                    "Instances | Instances (30% smaller) | Equivalence |\n|---|---|---|---|---|---|---|---|\n")
            for r in run["rows"]:
                f.write(f"| {r['design']} | {r['script']} | {r['area_um2']:,.1f} | {r['area_30pct_um2']:,.1f} | "
                        f"{r['change_pct']:+.2f}% | {r['instances']} | {r['instances_30pct']} | {r['cec']} |\n")
            b, t, t3 = run["base_total"], run["total"], run["total_30"]
            f.write(f"\nBest-of-both total: baseline {b:,.1f} um2; final set {t:,.1f} um2 "
                    f"({(b - t) / b * 100:+.2f}%); with `{run['cell']}` 30% smaller {t3:,.1f} um2 "
                    f"({(b - t3) / b * 100:+.2f}%).\n\n")
    print("results/sensitivity_30pct.md written")


# ---------------------------------------------------------------- delay
def step_delay() -> None:
    from src.sta import find_sta, worst_delay
    if find_sta() is None:
        print("WARNING: OpenSTA not found (sta or openroad on PATH, or STA_BIN): delay not measured")
        return
    libs = [("baseline", BASE_LIB)]
    if os.path.exists(EST_LIB):
        libs.append(("final_est", EST_LIB))
    if real_lib_cells():
        libs.append(("final_real", REAL_LIB))
    designs = [{"name": d["name"], "top": d["top"]} for d in DESIGNS]
    rows = []
    for d in designs:
        for tag, lib in libs:
            for s in ("A", "B"):
                net = f"results/netlists/{d['name']}_{tag}_{s}.v"
                if not os.path.exists(net):
                    continue
                r = worst_delay(net, d["top"], lib, "build/sta")
                rows.append({"design": d["name"], "library": tag, "script": s,
                             "worst_arrival_ns": r["arrival_ns"], "worst_slack_ns": r["slack_ns"],
                             "clocks": " ".join(r["clocks"])})
                print(f"  {d['name']:10s} {tag:10s} {s}: worst arrival {r['arrival_ns']} ns")
    _write_csv(rows, "results/delay.csv")
    area = {}
    for path, tag in ((BASE_ROWS, "baseline"), (EST_ROWS, "final_est"), (REAL_ROWS, "final_real")):
        if os.path.exists(path):
            for r in _load_json(path):
                area[(r["design"], tag, r["script"])] = r["area"]
    with open("results/delay.md", 'w', encoding='utf-8') as f:
        f.write("# Worst delay from OpenSTA\n\n")
        f.write("Data arrival time of the worst max-delay path of every mapped netlist "
                "(`src/sta.py` gives the constraints; logs in `build/sta/`). New cells with estimated "
                "areas carry placeholder scalar timing, so their delays are only indicative.\n\n")
        f.write("| Design | Library | Script | Area (um2) | Worst arrival (ns) |\n|---|---|---|---|---|\n")
        for r in rows:
            a = area.get((r["design"], r["library"], r["script"]))
            f.write(f"| {r['design']} | {r['library']} | {r['script']} | "
                    f"{a:,.1f} | {r['worst_arrival_ns']} |\n" if a else
                    f"| {r['design']} | {r['library']} | {r['script']} | - | {r['worst_arrival_ns']} |\n")
        f.write("\n## Best-of-both mapping of each design\n\n"
                "| Design | Library | Script chosen (smaller area) | Area (um2) | Worst arrival (ns) |\n"
                "|---|---|---|---|---|\n")
        for d in designs:
            for tag, _ in libs:
                cand = [r for r in rows if r["design"] == d["name"] and r["library"] == tag
                        and (d["name"], tag, r["script"]) in area]
                if not cand:
                    continue
                r = min(cand, key=lambda r: area[(d["name"], tag, r["script"])])
                f.write(f"| {d['name']} | {tag} | {r['script']} | {area[(d['name'], tag, r['script'])]:,.1f} | "
                        f"{r['worst_arrival_ns']} |\n")


# ---------------------------------------------------------------- gls
def run_testbench(tb_top: str, tb_file: str, netlist: str, models: Optional[str],
                  work: str = "build/gls") -> Tuple[bool, str]:
    """
    Compiles a testbench with a mapped netlist and the PDK's cell models
    (as Tutorial 4's `make gls`: no SDF, every specify delay 0) and runs it.
    Passes only if vvp exits with 0 and prints PASS.
    """
    os.makedirs(work, exist_ok=True)
    exe = f"{work}/{os.path.splitext(os.path.basename(netlist))[0]}_{tb_top}"
    srcs = [tb_file, netlist, f"{PDK_VERILOG}/primitives.v", f"{PDK_VERILOG}/sky130_fd_sc_hd.v"]
    if models:
        srcs.append(models)
    res = runner.run_cmd(["iverilog", "-s", tb_top, "-o", exe] + srcs)
    if res.returncode != 0:
        return False, res.stdout + res.stderr
    res = runner.run_cmd(["vvp", "-n", os.path.basename(exe)], cwd=work)
    out = res.stdout + res.stderr
    return res.returncode == 0 and "PASS" in out and "FAIL" not in out, out


def _lib_sets() -> List[Tuple[str, str, Optional[str]]]:
    libs = [("baseline", BASE_LIB, None)]
    if os.path.exists(EST_LIB):
        libs.append(("final_est", EST_LIB, "libs/new_cells_est.v"))
    if real_lib_cells():
        libs.append(("final_real", REAL_LIB, "libs/new_cells_real.v"))
    return libs


def step_gls() -> None:
    rows = []
    for d in TUTORIAL_DESIGNS:
        for tag, lib, models in _lib_sets():
            for s in ("A", "B"):
                m = map_design(d["name"], d["top"], lib, tag, s, src=d["src"])
                for tb_top, tb_file in d["benches"]:
                    ok, out = run_testbench(tb_top, tb_file, f"results/netlists/{d['name']}_{tag}_{s}.v",
                                            models)
                    with open(f"results/logs/{d['name']}_{tag}_{s}_{tb_top}.log", 'w', encoding='utf-8') as f:
                        f.write(out)
                    rows.append({"design": d["name"], "library": tag, "script": s, "area_um2": m["area"],
                                 "new_cell_instances": m["new_cell_instances"],
                                 "new_cells": ";".join(f"{k}:{v}" for k, v in sorted(m["new_cells"].items())),
                                 "cec": m["cec"], "testbench": tb_top, "gls": "pass" if ok else "FAIL"})
                    print(f"  {d['name']:4s} {tag:10s} {s}: {m['area']:9.2f} um2, cec {m['cec']}, "
                          f"{tb_top} {'pass' if ok else 'FAIL'}")
    _write_csv(rows, "results/gls.csv")
    with open("results/gls.md", 'w', encoding='utf-8') as f:
        f.write("# SPM and the multiplier: mapping, equivalence and gate-level testbenches\n\n")
        f.write("SPM (Tutorial 4) and the 8x8 multiplier (Tutorial 2), mapped with the commands of section 2 "
                "on the baseline and on the extended libraries. Every netlist is checked with ABC `dsec` "
                "against the design before ABC, and simulated with the tutorials' self-checking testbenches "
                "on the PDK's cell models (zero delay, as Tutorial 4's `make gls`); new cells use the "
                "behavioural models generated from their Liberty functions (`libs/new_cells_*.v`). "
                "Logs: `results/logs/<design>_<library>_<script>_<testbench>.log`.\n\n")
        f.write("| Design | Library | Script | Area (um2) | New-cell instances | Equivalence | Testbench | Result |\n"
                "|---|---|---|---|---|---|---|---|\n")
        for r in rows:
            f.write(f"| {r['design']} | {r['library']} | {r['script']} | {r['area_um2']:,.2f} | "
                    f"{r['new_cell_instances']} {('(' + r['new_cells'] + ')') if r['new_cells'] else ''} | "
                    f"{r['cec']} | `{r['testbench']}` | {r['gls']} |\n")
    bad = [r for r in rows if r["gls"] != "pass" or r["cec"] != "pass"]
    if bad:
        print("Gate-level check FAILED: " + ", ".join(f"{r['design']} {r['library']} {r['script']} "
                                                       f"{r['testbench']}" for r in bad))
        sys.exit(1)


# ---------------------------------------------------------------- extra designs
def step_extra() -> None:
    """Maps pic16 and p16c5x and compares the new cells they use with risc8's."""
    from src.candidates import collect_occurrences
    from src.extract_aigs import extract_single_design
    rows = []
    for tag, lib, _ in _lib_sets():
        rows += map_all(lib, tag, designs=ISA_DESIGNS)
    _require_cec(rows)
    for path, tag in ((BASE_ROWS, "baseline"), (EST_ROWS, "final_est"), (REAL_ROWS, "final_real")):
        if os.path.exists(path) and any(r["library"] == tag for r in rows):
            rows += [r for r in _load_json(path) if r["design"] == "risc8"]
    _save_json(rows, "results/isa_designs_rows.json")

    cells = final_cells()
    occ = {}
    for d in [{"name": "risc8", "top": "cpu"}] + ISA_DESIGNS:
        dch = f"build/aigs/{d['name']}_dch.aag"
        if not os.path.exists(dch):
            alt = f"results/aigs/{d['name']}_dch.aag"
            dch = alt if os.path.exists(alt) else extract_single_design(d["name"], top=d["top"])[1]
        occ[d["name"]] = collect_occurrences(dch)

    names = ["risc8"] + [d["name"] for d in ISA_DESIGNS]
    with open("results/isa_designs.md", 'w', encoding='utf-8') as f:
        f.write("# risc8, pic16 and p16c5x: one instruction set, the same new cells?\n\n")
        f.write("The three designs implement the PIC16C5x instruction set. They are mapped with the "
                "commands of section 2 on the baseline and on the final library (dsec on every mapping), "
                "and the cuts of their restructured AIGs are counted for each final cell's class.\n\n")
        f.write("| Design | Library | Script | Area (um2) | Reduction | New-cell instances | Equivalence |\n"
                "|---|---|---|---|---|---|---|\n")
        base = {(r["design"], r["script"]): r["area"] for r in rows if r["library"] == "baseline"}
        for r in sorted(rows, key=lambda r: (names.index(r["design"]), r["library"], r["script"])):
            b = base[(r["design"], r["script"])]
            f.write(f"| {r['design']} | {r['library']} | {r['script']} | {r['area']:,.1f} | "
                    f"{(b - r['area']) / b * 100:+.2f}% | {r['new_cell_instances']} | {r['cec']} |\n")
        f.write("\n## Instances of each final cell (estimated areas, scripts A + B) and cut occurrences "
                "of its class\n\n| Cell | " + " | ".join(f"{n} instances | {n} cuts" for n in names) +
                " |\n" + "|---" * (1 + 2 * len(names)) + "|\n")
        for c in cells:
            vals = []
            for n in names:
                inst = sum(r["new_cells"].get(c["name"], 0) for r in rows
                           if r["design"] == n and r["library"] == "final_est")
                vals += [str(inst), f"{occ[n].get(c['tt'], {}).get('occurrences', 0):,}"]
            f.write(f"| `{c['name']}` | " + " | ".join(vals) + " |\n")
    print("results/isa_designs.md written")


# ---------------------------------------------------------------- demo
def detect_top(src: str, sv: bool) -> str:
    """Top module of a Verilog source, as Yosys's `hierarchy -auto-top` picks it."""
    import re
    res = runner.run_cmd(["yosys", "-p", f"read_verilog {'-sv ' if sv else ''}{src}; hierarchy -auto-top"])
    m = re.search(r"Automatically selected \\?(\S+) as design top module", res.stdout)
    if not m:
        raise RuntimeError(f"cannot find the top module of {src}:\n{res.stdout[-1000:]}{res.stderr[-1000:]}")
    return m.group(1)


def demo(target: str, dch_aag: Optional[str]) -> None:
    """
    The interview demo (overview, section 3): the design's own classes, then
    the design mapped with and without the final cells, both scripts, with
    dsec, and its worst delay.  Writes results/demo/<design>.md.
    """
    from src.candidates import collect_occurrences
    from src.extract_aigs import ALL_KNOWN_DESIGNS
    from src.redundancy import RedundancyChecker

    clean = target.strip().replace("\\", "/")
    name = os.path.splitext(os.path.basename(clean))[0]
    if name in ALL_KNOWN_DESIGNS and not os.path.isfile(clean):
        info = ALL_KNOWN_DESIGNS[name]
        src, top, sv = info["file"], info["top"], info["sv"]
    elif os.path.isfile(clean) and clean.endswith((".v", ".sv")):
        src, sv = clean, clean.endswith(".sv")
        top = detect_top(src, sv)
    else:
        print(f"Demo mapping needs a Verilog design; {target} is not one. Steps 1 to 4 only.")
        return
    if real_lib_cells():
        lib_tag, lib, cells = "final_real", REAL_LIB, real_lib_cells()
    elif os.path.exists(EST_LIB):
        lib_tag, lib, cells = "final_est", EST_LIB, final_cells()
    else:
        print("No final library yet: run `make all` first. Steps 1 to 4 only.")
        return
    out_dir = "results/demo"
    os.makedirs(out_dir, exist_ok=True)

    print(f"\n=== Demo: {name} (top {top}) mapped on {BASE_LIB} and {lib} ===")
    final_tts = {int(c["tt"]) for c in final_cells()}
    classes = []
    if dch_aag and os.path.exists(dch_aag):
        checker = RedundancyChecker("given/hd_usable.lib")
        occ = collect_occurrences(dch_aag)
        for rep, e in sorted(occ.items(), key=lambda kv: -kv[1]["occurrences"])[:15]:
            cat, hd_cell, _, _ = checker.classify_with_details(rep)
            classes.append((rep, e["occurrences"], cat, hd_cell, rep in final_tts))
        print(f"{len(occ)} four-input classes in the restructured AIG; the most frequent:")
        for rep, n, cat, hd_cell, fin in classes:
            print(f"  0x{rep:04X}: {n:6,} cuts, {cat:24s} {hd_cell or '':28s} {'(final cell)' if fin else ''}")

    design = [{"name": name, "top": top, "src": src, "sv": sv}]
    nd, ld = f"{out_dir}/netlists", f"{out_dir}/logs"
    base = map_all(BASE_LIB, "baseline", designs=design, netlist_dir=nd, log_dir=ld)
    ext = map_all(lib, lib_tag, designs=design, netlist_dir=nd, log_dir=ld)
    delays = {}
    from src.sta import find_sta, worst_delay
    if find_sta():
        for r, l in [(r, BASE_LIB) for r in base] + [(r, lib) for r in ext]:
            d = worst_delay(f"{nd}/{name}_{r['library']}_{r['script']}.v", top, l, "build/sta")
            delays[(r["library"], r["script"])] = d["arrival_ns"]

    bb, be = min(r["area"] for r in base), min(r["area"] for r in ext)
    with open(f"{out_dir}/{name}.md", 'w', encoding='utf-8') as f:
        f.write(f"# Demo: {name}\n\nSource `{src}`, top `{top}`. Baseline `{BASE_LIB}`; extended `{lib}` "
                f"({len(cells)} new cells). Commands of section 2; dsec on every mapping; netlists and logs "
                f"in `{out_dir}/`.\n\n")
        f.write("| Script | Baseline (um2) | With new cells (um2) | Reduction | New-cell instances | "
                "Equivalence | Worst arrival, baseline (ns) | Worst arrival, new cells (ns) |\n"
                "|---|---|---|---|---|---|---|---|\n")
        for b, e in zip(base, ext):
            eq = "pass" if b["cec"] == e["cec"] == "pass" else f"baseline {b['cec']}, extended {e['cec']}"
            f.write(f"| {b['script']} | {b['area']:,.1f} | {e['area']:,.1f} | "
                    f"{(b['area'] - e['area']) / b['area'] * 100:+.2f}% | {e['new_cell_instances']} "
                    f"{', '.join(f'{k}:{v}' for k, v in sorted(e['new_cells'].items()))} | {eq} | {delays.get(('baseline', b['script']))} | "
                    f"{delays.get((lib_tag, e['script']))} |\n")
        f.write(f"\nBest of both: {bb:,.1f} um2 -> {be:,.1f} um2 ({(bb - be) / bb * 100:+.2f}%).\n")
        if classes:
            f.write("\n## Most frequent 4-input classes of the restructured AIG\n\n"
                    "| P-class | Cuts | Table 3 class | HD cell | In the final set |\n|---|---|---|---|---|\n")
            for rep, n, cat, hd_cell, fin in classes:
                f.write(f"| `0x{rep:04X}` | {n:,} | {cat} | {hd_cell or '-'} | {'yes' if fin else ''} |\n")
    print(f"Best of both: {bb:,.1f} um2 -> {be:,.1f} um2 ({(bb - be) / bb * 100:+.2f}%)")
    print(f"Written to {out_dir}/{name}.md")
    _require_cec(base + ext)
