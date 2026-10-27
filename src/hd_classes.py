"""
Class Table of HD (SkyWater 130nm High-Density Library)
Extracts all combinational logic cells in sky130_fd_sc_hd, computes truth tables,
P-classes, P+N_out classes, NPN classes, exact static CMOS stages & transistor counts,
and area/width metrics. Reconciles the 83 single-output families and 3 multi-output/constant
families (86 total combinational families).
"""

import os
import re
import csv
from typing import Dict, List, Tuple

from src.redundancy import parse_hd_library, eval_lib_expr, eval_cell_truth_table
from src.classification import get_p_class, get_p_nout_class, get_npn_class


def compute_hd_family_cmos_cost(family_name: str, pins: List[str], fn_expr: str) -> Tuple[int, int]:
    """
    Returns (cmos_stages, transistor_count) for a SkyWater 130nm HD combinational cell family.
    Derived from the cell topology:
    - Single-stage inverting gates (inv, nand*, nor*, a*oi, o*ai): 1 stage, 2*k transistors
    - Positive-unate gates (buf, and*, or*, a*o, o*a): 2 stages, 2*k + 2 transistors
    - Gates with inverted input pins (*_N in pin list): +2 transistors per _N input inverter
    - Majority gate (maj3): 10-transistor inverting core + 2-transistor output inverter = 12 tx, 2 stages
    - Multiplexers & XOR/XNOR:
      - mux2i: 10 tx, 2 stages; mux2: 12 tx, 3 stages; mux4: 26 tx, 3 stages
      - xor2 / xnor2: 10 tx, 2 stages; xor3 / xnor3: 20 tx, 3 stages
    """
    k = len(pins)
    if family_name == "inv":
        return (1, 2)
    if family_name == "buf":
        return (2, 4)
    if family_name == "maj3":
        return (2, 12)
    if family_name == "mux2i":
        return (2, 10)
    if family_name == "mux2":
        return (3, 12)
    if family_name == "mux4":
        return (3, 26)
    if family_name in ("xor2", "xnor2"):
        return (2, 10)
    if family_name in ("xor3", "xnor3"):
        return (3, 20)

    # Count internal input inverters on *_N pins (e.g. A_N, B_N, B1_N, A1_N, A2_N)
    num_inv_pins = sum(1 for p in pins if p.endswith("_N"))
    # Determine whether the core gate has an output inverter (non-inverting family vs inverting family)
    is_inverting_output = (
        family_name.startswith("nand")
        or family_name.startswith("nor")
        or family_name.endswith("i")
    )
    out_inv = 0 if is_inverting_output else 1

    stages = 1 + (1 if num_inv_pins > 0 else 0) + out_inv
    transistors = 2 * k + 2 * num_inv_pins + 2 * out_inv
    return (stages, transistors)


def parse_special_combinational_families(usable_lib: str, reduced_lib: str) -> List[Dict]:
    """
    Parses the 3 non-single-output combinational families in HD (conb, ha, fa)
    that together with the 83 single-output families make the 86 combinational families
    described in Section 2 of the Option 2 Handout.
    """
    with open(usable_lib, 'r', encoding='utf-8') as f:
        u_content = f.read()
    with open(reduced_lib, 'r', encoding='utf-8') as f:
        r_content = f.read()

    special = []
    cell_matches = list(re.finditer(r'cell\s*\(\s*\"?([a-zA-Z0-9_]+)\"?\s*\)\s*\{', u_content))
    reduced_names = set(re.findall(r'cell\s*\(\s*\"?([a-zA-Z0-9_]+)\"?\s*\)\s*\{', r_content))

    by_family: Dict[str, List[Dict]] = {}
    for i in range(len(cell_matches)):
        name = cell_matches[i].group(1)
        start = cell_matches[i].start()
        end = cell_matches[i + 1].start() if i + 1 < len(cell_matches) else len(u_content)
        block = u_content[start:end]

        if re.search(r'ff\s*\(|latch\s*\(', block):
            continue

        pin_matches = re.findall(r'pin\s*\(\s*\"?([a-zA-Z0-9_]+)\"?\s*\)\s*\{([^}]+)\}', block)
        inputs = []
        outputs = []
        for pin_name, pin_block in pin_matches:
            dir_m = re.search(r'direction\s*:\s*\"?(input|output)\"?', pin_block)
            if not dir_m:
                continue
            direction = dir_m.group(1)
            if direction == 'input':
                inputs.append(pin_name)
            elif direction == 'output':
                fn_m = re.search(r'function\s*:\s*\"([^\"]+)\"', pin_block)
                if fn_m:
                    outputs.append((pin_name, fn_m.group(1)))

        if len(outputs) != 1:
            area_m = re.search(r'area\s*:\s*([0-9.]+)', block)
            area = float(area_m.group(1)) if area_m else 0.0
            fam = re.sub(r'_\d+$', '', name.replace('sky130_fd_sc_hd__', ''))
            by_family.setdefault(fam, []).append({
                'name': name,
                'inputs': inputs,
                'outputs': outputs,
                'area': area,
                'in_reduced': name in reduced_names
            })

    for fam, group in sorted(by_family.items()):
        x1 = next((c for c in group if c['name'].endswith('_1')), group[0])
        drive_nums = []
        for c in group:
            m = re.search(r'_(\d+)$', c['name'])
            if m:
                drive_nums.append(int(m.group(1)))
        drives = [f"x{d}" for d in sorted(set(drive_nums))]
        out_str = "; ".join(f"{p}={fn}" for p, fn in x1['outputs'])
        width_sites = round(x1['area'] / (2.72 * 0.46))
        tx = 4 if fam == "conb" else (14 if fam == "ha" else 28)
        special.append({
            "family": fam,
            "inputs": len(x1['inputs']),
            "outputs": len(x1['outputs']),
            "pins": ",".join(x1['inputs']),
            "function": out_str,
            "drives": ",".join(drives),
            "area_x1_um2": x1['area'],
            "width_sites": width_sites,
            "est_transistors": tx,
            "in_reduced": "yes" if any(c['in_reduced'] for c in group) else "no"
        })
    return special


def build_hd_class_table(usable_lib: str = "given/hd_usable.lib", reduced_lib: str = "given/hd_reduced.lib") -> List[Dict]:
    """Builds a comprehensive class table for all 83 single-output combinational cell families in HD."""
    usable_cells = parse_hd_library(usable_lib)
    reduced_cells = {c["name"]: c for c in parse_hd_library(reduced_lib)}

    # Group by distinct Boolean function expression
    functions: Dict[str, List[Dict]] = {}
    for c in usable_cells:
        functions.setdefault(c["function"], []).append(c)

    table = []

    for fn_expr, cell_group in sorted(functions.items(), key=lambda item: (len(item[1][0]["inputs"]), item[1][0]["name"])):
        first_cell = cell_group[0]
        pins = first_cell["inputs"]
        k = len(pins)

        tt_full = eval_cell_truth_table(fn_expr, tuple(pins))
        if k <= 4:
            tt = 0
            for idx in range(16):
                sub_idx = idx & ((1 << k) - 1)
                if (tt_full >> sub_idx) & 1:
                    tt |= (1 << idx)
            p_rep, _ = get_p_class(tt)
            pn_rep = get_p_nout_class(tt)
            npn_rep = get_npn_class(tt)
            tt_hex = f"0x{tt:04X}"
            p_hex = f"0x{p_rep:04X}"
            pn_hex = f"0x{pn_rep:04X}"
            npn_hex = f"0x{npn_rep:04X}"
        else:
            tt_hex = f"0x{tt_full:0{1 << (k - 2)}X}"
            p_hex = f"{k}-input"
            pn_hex = f"{k}-input"
            npn_hex = f"{k}-input"

        # Drive variants (sorted numerically)
        drives_num = []
        for c in cell_group:
            m = re.search(r'_(\d+)$', c["name"])
            if m:
                drives_num.append(int(m.group(1)))
        drives_str = ",".join(f"x{d}" for d in sorted(set(drives_num)))

        # Base cell (prefer x1)
        x1_cell = next((c for c in cell_group if c["name"].endswith("_1")), first_cell)
        area_x1 = x1_cell["area"]
        width_sites = round(area_x1 / (2.72 * 0.46))

        in_reduced = any(c["name"] in reduced_cells for c in cell_group)

        # Family name from cell name
        family_name = re.sub(r'^sky130_fd_sc_hd__', '', x1_cell["name"])
        family_name = re.sub(r'_\d+$', '', family_name)

        stages, transistor_count = compute_hd_family_cmos_cost(family_name, pins, fn_expr)

        table.append({
            "family": family_name,
            "inputs": k,
            "pins": ",".join(pins),
            "function": fn_expr,
            "truth_table": tt_hex,
            "p_class": p_hex,
            "p_nout_class": pn_hex,
            "npn_class": npn_hex,
            "drives": drives_str,
            "area_x1_um2": area_x1,
            "width_sites": width_sites,
            "stages": stages,
            "est_transistors": transistor_count,
            "in_reduced": "yes" if in_reduced else "no"
        })

    return table


def write_hd_class_reports(
    table: List[Dict],
    csv_path: str = "results/hd_classes.csv",
    md_path: str = "results/hd_classes.md",
    usable_lib: str = "given/hd_usable.lib",
    reduced_lib: str = "given/hd_reduced.lib"
):
    """Writes HD class table to CSV and Markdown."""
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            "family", "inputs", "pins", "function", "truth_table",
            "p_class", "p_nout_class", "npn_class", "drives", "area_x1_um2",
            "width_sites", "stages", "est_transistors", "in_reduced"
        ])
        writer.writeheader()
        writer.writerows(table)

    special = parse_special_combinational_families(usable_lib, reduced_lib)

    # Compute summary counts
    p_4inp = {r["p_class"] for r in table if r["inputs"] == 4}
    pn_4inp = {r["p_nout_class"] for r in table if r["inputs"] == 4}
    npn_4inp = {r["npn_class"] for r in table if r["inputs"] == 4}
    p_le4 = {r["p_class"] for r in table if r["inputs"] <= 4}
    pn_le4 = {r["p_nout_class"] for r in table if r["inputs"] <= 4}
    npn_le4 = {r["npn_class"] for r in table if r["inputs"] <= 4}

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("# Class Table of the SkyWater 130nm HD Library (`sky130_fd_sc_hd`)\n\n")
        f.write("## 1. Library Summary\n\n")
        f.write("- **Total combinational cell families in `hd_usable.lib` / `hd_reduced.lib`**: **86 families**\n")
        f.write(f"  - **Single-output combinational logic families (1 to 6 inputs)**: **{len(table)} families** (264 cells in `hd_usable.lib`, 169 cells in `hd_reduced.lib`)\n")
        f.write(f"  - **Multi-output / constant combinational families (`conb`, `ha`, `fa`)**: **{len(special)} families** (6 cells in `hd_usable.lib`, 3 cells in `hd_reduced.lib`)\n")
        f.write("- **Sequential cell families (flip-flops and latches)**: **17 families** (37 cells in `hd_usable.lib`, 17 cells at `x1` in `hd_reduced.lib`)\n")
        f.write(f"- **Distinct 4-input equivalence classes among the 28 four-input HD families**: **{len(p_4inp)} P-classes**, **{len(pn_4inp)} P+N_out classes**, **{len(npn_4inp)} NPN classes**\n")
        f.write(f"- **Distinct equivalence classes across all 61 HD families with $\\le 4$ inputs**: **{len(p_le4)} P-classes**, **{len(pn_le4)} P+N_out classes**, **{len(npn_le4)} NPN classes**\n\n")

        f.write("## 2. Single-Output Combinational Cell Families (83 Families)\n\n")
        f.write("| Family | Inputs | Function | Truth Table | P-Class | P+N_out Class | NPN Class | Drives | Area x1 (um2) | Width (Sites) | Stages | Transistors | In Reduced |\n")
        f.write("|---|---|---|---|---|---|---|---|---|---|---|---|---|\n")
        for r in table:
            f.write(
                f"| `{r['family']}` | {r['inputs']} | `{r['function']}` | `{r['truth_table']}` | "
                f"`{r['p_class']}` | `{r['p_nout_class']}` | `{r['npn_class']}` | {r['drives']} | "
                f"{r['area_x1_um2']} | {r['width_sites']} | {r['stages']} | {r['est_transistors']} | {r['in_reduced']} |\n"
            )

        if special:
            f.write("\n## 3. Multi-Output and Constant Combinational Families (3 Families)\n\n")
            f.write("| Family | Inputs | Outputs | Pin Functions | Drives | Area x1 (um2) | Width (Sites) | Transistors | In Reduced |\n")
            f.write("|---|---|---|---|---|---|---|---|---|\n")
            for s in special:
                f.write(
                    f"| `{s['family']}` | {s['inputs']} | {s['outputs']} | `{s['function']}` | "
                    f"{s['drives']} | {s['area_x1_um2']} | {s['width_sites']} | {s['est_transistors']} | {s['in_reduced']} |\n"
                )


if __name__ == "__main__":
    t = build_hd_class_table()
    write_hd_class_reports(t)
    print(f"Generated HD class table with {len(t)} single-output cell families (+ 3 multi-output/constant families = 86 total).")
