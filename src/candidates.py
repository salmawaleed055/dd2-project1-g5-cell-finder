"""
Candidate classification, costing, redundancy filtering and ranking
(Option 2 handout, section 4, steps 3 to 7).

For every required design the cuts of the restructured AIG (after ABC
`strash; dch`, which is what both mapping scripts start from) are enumerated.
Every 4-input cut that depends on all its inputs is one occurrence of its
class (up to input order).  Each class is

  * costed by src/cmos_cost.py and given an estimated area by the fitted
    area model (src/area_model.py);
  * checked against HD (src/redundancy.py, Table 3) and kept if New, or if
    Exists-with-an-inverter / Contained but estimated smaller than the HD
    cell (+ inverter) it matches;
  * ranked by estimated saving.

Estimated saving of a class, summed over designs d and occurrences o:

    saving = sum_o ( rate_d * cone(o) - area_new )

where cone(o) is the number of AIG AND nodes inside the cut and rate_d is
the combinational area per AND node of design d in its baseline mapping
(best of scripts A and B on hd_reduced.lib).  rate_d * cone(o) is the area
the occurrence's logic costs today.  The ranking is a guess: cuts overlap and
share logic, so occurrences of one class are counted once per root node, but
logic shared between cuts is counted in each of them.
"""

import csv
import json
import os
from typing import Dict, List

from src.aig import parse_aag
from src.area_model import AreaModel
from src.classification import depends_on_all_4, get_p_class, get_p_nout_class, get_npn_class
from src.cmos_cost import cmos_cost
from src.cut_enumerator import CutEnumerator
from src.redundancy import RedundancyChecker

DESIGNS = ["cpu8", "dsp8", "arlet6502", "uart_apb", "risc8", "fir10"]
INV_AREA_UM2 = 3.7536  # sky130_fd_sc_hd__inv_1


def cone_size(aig, root: int, leaves) -> int:
    """Number of AND nodes between the cut leaves and the root (inclusive)."""
    leaves = set(leaves)
    seen = set()
    stack = [root]
    while stack:
        v = stack.pop()
        if v in seen or v in leaves or v not in aig.and_nodes:
            continue
        seen.add(v)
        l0, l1 = aig.and_nodes[v]
        stack.append(l0 >> 1)
        stack.append(l1 >> 1)
    return len(seen)


def collect_occurrences(aag_path: str) -> Dict[int, Dict[str, int]]:
    """{P-class rep: {'occurrences': roots, 'cone_ands': sum of cone sizes}} of one AIG."""
    aig = parse_aag(aag_path)
    cuts = CutEnumerator(aig, max_cut_size=4, max_cuts_per_node=None).enumerate_cuts()
    out: Dict[int, Dict[str, int]] = {}
    for node, node_cuts in cuts.items():
        seen_here = set()
        for cut in node_cuts:
            if len(cut.inputs) != 4 or not depends_on_all_4(cut.truth_table):
                continue
            rep, _ = get_p_class(cut.truth_table)
            if rep in seen_here:
                continue  # one occurrence per class and root node
            seen_here.add(rep)
            e = out.setdefault(rep, {"occurrences": 0, "cone_ands": 0})
            e["occurrences"] += 1
            e["cone_ands"] += cone_size(aig, node, cut.inputs)
    return out


def rank_candidates(baseline_path: str = "results/table5_baseline.json",
                    aig_dir: str = "results/aigs",
                    lib_full: str = "given/hd_usable.lib") -> List[Dict]:
    """Builds the candidate table, ranked by estimated saving (largest first)."""
    with open(baseline_path, 'r', encoding='utf-8') as f:
        baseline = json.load(f)
    model = AreaModel(lib_full)
    checker = RedundancyChecker(lib_full)

    per_class: Dict[int, Dict] = {}
    rates = {}
    for d in DESIGNS:
        aag = os.path.join(aig_dir, f"{d}_dch.aag")
        occ = collect_occurrences(aag)
        n_ands = parse_aag(aag).num_ands
        rates[d] = baseline[d]["best_comb_area"] / n_ands
        for rep, e in occ.items():
            c = per_class.setdefault(rep, {"occ": {}, "cone": {}})
            c["occ"][d] = e["occurrences"]
            c["cone"][d] = e["cone_ands"]

    rows = []
    for rep, c in per_class.items():
        cost = cmos_cost(rep)
        est_area = model.area(cost)
        cat, hd_cell, desc, hd_area = checker.classify_with_details(rep)
        if cat == "Exists":
            keep, why = False, "HD has it"
        elif cat == "Exists with an inverter":
            keep = est_area < hd_area + INV_AREA_UM2
            why = f"est. {est_area:.2f} vs HD cell + inverter {hd_area + INV_AREA_UM2:.2f}"
        elif cat == "Contained":
            keep = est_area < hd_area
            why = f"est. {est_area:.2f} vs containing HD cell {hd_area:.2f}"
        else:
            keep, why = True, "not in HD"
        replaced = sum(rates[d] * c["cone"][d] for d in c["occ"])
        occurrences = sum(c["occ"].values())
        saving = replaced - occurrences * est_area
        rows.append({
            "p_class": f"0x{rep:04X}",
            "p_nout_class": f"0x{get_p_nout_class(rep):04X}",
            "npn_class": f"0x{get_npn_class(rep):04X}",
            "redundancy_class": cat,
            "matched_hd_cell": hd_cell,
            "kept": keep,
            "keep_reason": why,
            "occurrences": occurrences,
            "designs": len(c["occ"]),
            "mean_cone_ands": round(sum(c["cone"].values()) / occurrences, 2),
            "stages": cost["stages"],
            "inverters": cost["inverters"],
            "transistors": cost["transistors"],
            "construction": cost["construction"],
            "structure": cost["expression"],
            "est_sites": model.sites(cost),
            "est_area_um2": est_area,
            "replaced_area_um2": round(replaced, 2),
            "est_saving_um2": round(saving, 2),
            **{f"occ_{d}": c["occ"].get(d, 0) for d in DESIGNS},
        })
    rows.sort(key=lambda r: (not r["kept"], -r["est_saving_um2"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i if r["kept"] else ""
    return rows


def write_candidate_reports(rows: List[Dict], top_n: int,
                            csv_path: str = "results/candidates.csv",
                            md_path: str = "results/candidates.md") -> None:
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=["rank"] + [k for k in rows[0] if k != "rank"])
        w.writeheader()
        w.writerows(rows)
    kept = [r for r in rows if r["kept"]]
    counts: Dict[str, List[int]] = {}
    for r in rows:
        k = counts.setdefault(r["redundancy_class"], [0, 0])
        k[0] += 1
        k[1] += int(r["kept"])
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("# Ranked Candidates (estimated areas)\n\n")
        f.write("4-input classes (up to input order) of the restructured AIGs of the 6 required designs, "
                "costed, checked against HD, and ranked by estimated saving "
                "(`src/candidates.py` explains the formula).\n\n")
        f.write("| Table 3 class | Classes found | Kept as candidates |\n|---|---|---|\n")
        for k in ("Exists", "Exists with an inverter", "Contained", "New"):
            a, b = counts.get(k, [0, 0])
            f.write(f"| {k} | {a} | {b} |\n")
        f.write(f"| **Total** | **{len(rows)}** | **{len(kept)}** |\n\n")
        positive = [r for r in kept if r["est_saving_um2"] > 0]
        f.write(f"Candidates with a positive estimated saving: **{len(positive)}**. "
                f"The top {top_n} go into the first extended Liberty.\n\n")
        f.write("| Rank | P-class | Table 3 | Occurrences | Designs | Mean cone ANDs | Stages | Transistors | "
                "Est. sites | Est. area (um2) | Replaced area (um2) | Est. saving (um2) | Structure |\n")
        f.write("|---|---|---|---|---|---|---|---|---|---|---|---|---|\n")
        for r in kept[:40]:
            f.write(f"| {r['rank']} | `{r['p_class']}` | {r['redundancy_class']} | {r['occurrences']:,} | "
                    f"{r['designs']} | {r['mean_cone_ands']} | {r['stages']} | {r['transistors']} | "
                    f"{r['est_sites']} | {r['est_area_um2']:.2f} | {r['replaced_area_um2']:,.1f} | "
                    f"{r['est_saving_um2']:,.1f} | `{r['structure']}` |\n")
        f.write(f"\nThe full list ({len(rows)} classes, including the dropped ones and why) is in "
                "`results/candidates.csv`.\n")
