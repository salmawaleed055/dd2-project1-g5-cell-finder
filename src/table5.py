"""
Mapping and measuring with and without the new cells (Option 2 handout,
section 4, step 9, and section 7).

Every design is mapped with the commands of section 2 (the same as
given/scripts/map.sh) on the baseline hd_reduced.lib and on the extended
library, with script A and script B.  For every mapping the tool keeps

  * the netlist (results/netlists/) and the Yosys log (results/logs/);
  * the chip area, the sequential area and the new-cell instances from
    `stat -liberty`;
  * the equivalence check against the design before ABC (src/equivalence.py).

Table 5 reports the same-script reduction and the best-of-both reduction.
"""

import csv
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional

from src.equivalence import netlist_to_aig, run_cec, write_ff_models
from src.netlist_repair import liberty_pins, repair_netlist
from src.runner import runner

SCRIPTS = {
    "A": "+strash;dch,-f;amap;topo",
    "B": "+strash;&get,-n;&dch,-f;&nf,-R,1000;&put",
}

DESIGNS = [
    {"name": "cpu8", "top": "cpu8"},
    {"name": "dsp8", "top": "dsp8"},
    {"name": "arlet6502", "top": "cpu"},
    {"name": "uart_apb", "top": "uart_apb_master"},
    {"name": "risc8", "top": "cpu"},
    {"name": "fir10", "top": "fir10"},
]

NETLIST_DIR = "results/netlists"
LOG_DIR = "results/logs"
WORK_DIR = "build/map"


def map_design(name: str, top: str, lib: str, lib_tag: str, script: str,
               check: bool = True) -> Dict:
    """Maps one design on one library with one script, then checks it."""
    for d in (NETLIST_DIR, LOG_DIR, WORK_DIR):
        os.makedirs(d, exist_ok=True)
    tag = f"{name}_{lib_tag}_{script}"
    pre_v = f"{WORK_DIR}/{tag}_pre.v"
    raw_v = f"{WORK_DIR}/{tag}_raw.v"
    net_v = f"{NETLIST_DIR}/{tag}.v"
    log = f"{LOG_DIR}/{tag}_map.log"
    ys = (
        f"read_verilog given/designs/{name}.v\n"
        f"synth -flatten -top {top}\n"
        f"dfflibmap -liberty {lib}\n"
        f"abc -liberty {lib} -script {SCRIPTS[script]}\n"
        "opt_clean -purge\n"
        f"tee -o {log}.stat stat -liberty {lib}\n"
        f"write_verilog -noattr {raw_v}\n"
    )
    res = runner.run_cmd(["yosys", "-l", log, "-q", "-p", ys.replace("\n", "; ")])
    if res.returncode != 0:
        raise RuntimeError(f"mapping {tag} failed:\n{res.stderr[-2000:]}")
    # The reference for the equivalence check comes from a separate run with
    # the same synth and dfflibmap: writing a netlist inside the mapping run,
    # before abc, renames internal signals and changes ABC's result.
    res = runner.run_cmd(["yosys", "-q", "-p",
                          f"read_verilog given/designs/{name}.v; synth -flatten -top {top}; "
                          f"dfflibmap -liberty {lib}; write_verilog -noattr {pre_v}"])
    if res.returncode != 0:
        raise RuntimeError(f"reference netlist of {tag} failed:\n{res.stderr[-2000:]}")
    with open(f"{log}.stat", 'r', encoding='utf-8') as f:
        stat = f.read()
    os.remove(f"{log}.stat")
    area = float(re.search(r"Chip area for module .*?:\s*([0-9.]+)", stat).group(1))
    seq = re.search(r"sequential elements:\s*([0-9.]+)", stat)
    seq_area = float(seq.group(1)) if seq else 0.0
    new_cells = {m.group(2): int(m.group(1))
                 for m in re.finditer(r"^\s*(\d+)\s+\S+\s+(dd2_g5__\w+)", stat, re.M)}

    with open(raw_v, 'r', encoding='utf-8') as f:
        netlist, alias = repair_netlist(f.read(), liberty_pins(lib))
    with open(net_v, 'w', encoding='utf-8') as f:
        f.write(netlist)

    row = {"design": name, "library": lib_tag, "script": script,
           "area": round(area, 4), "seq_area": round(seq_area, 4),
           "comb_area": round(area - seq_area, 4),
           "new_cell_instances": sum(new_cells.values()), "new_cells": new_cells,
           "repaired_pins": len(alias), "cec": "not run"}
    if check:
        ff_v = f"{WORK_DIR}/ff_models_{lib_tag}.v"
        if not os.path.exists(ff_v):
            write_ff_models(lib, ff_v)
        ff_cells = write_ff_models(lib, os.devnull)
        gold, gate = f"{WORK_DIR}/{tag}_gold.aig", f"{WORK_DIR}/{tag}_gate.aig"
        netlist_to_aig(pre_v, top, lib, ff_v, ff_cells, gold)
        netlist_to_aig(net_v, top, lib, ff_v, ff_cells, gate)
        ok, out = run_cec(gold, gate)
        with open(f"{LOG_DIR}/{tag}_cec.log", 'w', encoding='utf-8') as f:
            f.write(out)
        row["cec"] = "pass" if ok else "FAIL"
    return row


def map_all(lib: str, lib_tag: str, check: bool = True, jobs: int = 4) -> List[Dict]:
    """Maps every required design with both scripts on one library."""
    os.makedirs(WORK_DIR, exist_ok=True)
    write_ff_models(lib, f"{WORK_DIR}/ff_models_{lib_tag}.v")
    tasks = [(d["name"], d["top"], lib, lib_tag, s, check) for d in DESIGNS for s in SCRIPTS]
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        rows = list(ex.map(lambda t: map_design(*t), tasks))
    for r in rows:
        print(f"  {r['design']:10s} {lib_tag:9s} script {r['script']}: {r['area']:10.2f} um2, "
              f"{r['new_cell_instances']} new-cell instances, cec {r['cec']}")
    return rows


def write_baseline(rows: List[Dict], path: str = "results/table5_baseline.json") -> None:
    """Baseline areas per design, used by the candidate ranking."""
    out = {}
    for r in rows:
        d = out.setdefault(r["design"], {})
        d[r["script"]] = {"area": r["area"], "comb_area": r["comb_area"]}
    for d, v in out.items():
        best = min(("A", "B"), key=lambda s: v[s]["area"])
        v["best_script"] = best
        v["best_comb_area"] = v[best]["comb_area"]
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2)


def write_table5(base: List[Dict], ext: List[Dict], cells: List[Dict], title: str,
                 csv_path: str = "results/table5_estimated.csv",
                 md_path: str = "results/table5_estimated.md") -> None:
    """Writes Table 5 with the same-script and best-of-both reductions."""
    idx = {(r["design"], r["script"]): r for r in base}
    rows = []
    for e in ext:
        b = idx[(e["design"], e["script"])]
        rows.append({
            "design": e["design"], "script": e["script"],
            "baseline_um2": b["area"], "with_new_cells_um2": e["area"],
            "reduction_pct": round((b["area"] - e["area"]) / b["area"] * 100, 3),
            "new_cell_instances": e["new_cell_instances"],
            "new_cells": ";".join(f"{k}:{v}" for k, v in sorted(e["new_cells"].items())),
            "equivalence": "pass" if b["cec"] == "pass" and e["cec"] == "pass" else
                           f"baseline {b['cec']}, extended {e['cec']}",
        })
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    designs = [d["name"] for d in DESIGNS]
    best = []
    for d in designs:
        bb = min(r["baseline_um2"] for r in rows if r["design"] == d)
        be = min(r["with_new_cells_um2"] for r in rows if r["design"] == d)
        best.append((d, bb, be))
    tb = sum(x[1] for x in best)
    te = sum(x[2] for x in best)

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(f"# {title}\n\n")
        f.write(f"Baseline: `given/hd_reduced.lib` (189 cells). Extended: the baseline plus "
                f"{len(cells)} new cells with estimated areas (`libs/hd_extended_est.lib`). "
                "Commands of section 2; equivalence by ABC `dsec` of every mapped netlist "
                "against the design before ABC (logs in `results/logs/`).\n\n")
        f.write("| Design | Script | Baseline (um2) | With new cells (um2) | Reduction | "
                "New-cell instances | Equivalence |\n|---|---|---|---|---|---|---|\n")
        for r in rows:
            f.write(f"| {r['design']} | {r['script']} | {r['baseline_um2']:,.1f} | "
                    f"{r['with_new_cells_um2']:,.1f} | {r['reduction_pct']:+.2f}% | "
                    f"{r['new_cell_instances']} | {r['equivalence']} |\n")
        f.write("\n## Best of both scripts\n\n")
        f.write("| Design | Baseline best (um2) | With new cells best (um2) | Reduction |\n|---|---|---|---|\n")
        for d, bb, be in best:
            f.write(f"| {d} | {bb:,.1f} | {be:,.1f} | {(bb - be) / bb * 100:+.2f}% |\n")
        f.write(f"| **Total (required designs)** | **{tb:,.1f}** | **{te:,.1f}** | "
                f"**{(tb - te) / tb * 100:+.2f}%** |\n\n")
        f.write("## New cells in the extended library\n\n")
        f.write("| Cell | Truth table | Function | Est. area (um2) | Instances (A) | Instances (B) |\n"
                "|---|---|---|---|---|---|\n")
        for c in cells:
            na = sum(e["new_cells"].get(c["name"], 0) for e in ext if e["script"] == "A")
            nb = sum(e["new_cells"].get(c["name"], 0) for e in ext if e["script"] == "B")
            f.write(f"| `{c['name']}` | `0x{c['tt']:04X}` | `{c['function']}` | {c['area']:.4f} | {na} | {nb} |\n")
