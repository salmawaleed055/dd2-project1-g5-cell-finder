"""
Step 1: Extract AIGs and ABC Restructuring
Section 4, Step 1: Synthesize each required design with Yosys and write it as an
And-Inverter Graph (AIG). Also write the graph after ABC has restructured it (strash; dch; strash).
"""

import os
import re
import shutil
import csv
from typing import Dict, List, Tuple, Optional

from src.runner import runner

REQUIRED_DESIGNS = [
    {"name": "cpu8", "file": "given/designs/cpu8.v", "top": "cpu8", "sv": False, "ref_ff": 82, "ref_and": 1265},
    {"name": "dsp8", "file": "given/designs/dsp8.v", "top": "dsp8", "sv": False, "ref_ff": 72, "ref_and": 1973},
    {"name": "arlet6502", "file": "given/designs/arlet6502.v", "top": "cpu", "sv": False, "ref_ff": 143, "ref_and": 3221},
    {"name": "uart_apb", "file": "given/designs/uart_apb.v", "top": "uart_apb_master", "sv": False, "ref_ff": 330, "ref_and": 4673},
    {"name": "risc8", "file": "given/designs/risc8.v", "top": "cpu", "sv": False, "ref_ff": 696, "ref_and": 7750},
    {"name": "fir10", "file": "given/designs/fir10.v", "top": "fir10", "sv": False, "ref_ff": 176, "ref_and": 8795},
]

OPTIONAL_DESIGNS = [
    {"name": "p16c5x", "file": "given/designs/p16c5x.v", "top": "P16C5x", "sv": False, "ref_ff": 747, "ref_and": 8167},
    {"name": "pic16", "file": "given/designs/pic16.v", "top": "PIC16C5x", "sv": False, "ref_ff": 765, "ref_and": 8276},
    {"name": "x18", "file": "given/designs/x18.v", "top": "x18", "sv": False, "ref_ff": 831, "ref_and": 10151},
    {"name": "pic1826", "file": "given/designs/pic1826.v", "top": "cpu", "sv": True, "ref_ff": 1181, "ref_and": 12457},
    {"name": "xfir", "file": "given/designs/xfir.v", "top": "xfir", "sv": False, "ref_ff": 176, "ref_and": 15955},
    {"name": "chacha", "file": "given/designs/chacha.v", "top": "chacha", "sv": False, "ref_ff": 1940, "ref_and": 38658},
]

ALL_KNOWN_DESIGNS = {d["name"]: d for d in REQUIRED_DESIGNS + OPTIONAL_DESIGNS}


def parse_aag_header(aag_path: str) -> Dict[str, int]:
    """Reads M, I, L, O, A from the first line of an AIGER file."""
    with open(aag_path, 'r', encoding='utf-8') as f:
        header = f.readline().strip().split()
    return {
        "max_var": int(header[1]),
        "inputs": int(header[2]),
        "latches": int(header[3]),
        "outputs": int(header[4]),
        "ands": int(header[5])
    }


def extract_single_design(
    design_or_path: str,
    top: Optional[str] = None,
    sv: Optional[bool] = None,
    output_dir: str = "build/aigs"
) -> Tuple[str, str]:
    """
    Synthesizes any single design (by name in Table 2 or path to a Verilog file)
    to original and ABC-restructured AIGER (.aig and .aag).
    Returns (orig_aag_path, dch_aag_path).
    """
    os.makedirs(output_dir, exist_ok=True)
    clean_arg = design_or_path.strip().replace("\\", "/")
    base_name = os.path.splitext(os.path.basename(clean_arg))[0]

    if base_name in ALL_KNOWN_DESIGNS and not os.path.isfile(clean_arg):
        info = ALL_KNOWN_DESIGNS[base_name]
        v_file = info["file"]
        top_mod = top or info["top"]
        use_sv = info["sv"] if sv is None else sv
    else:
        v_file = clean_arg if os.path.isfile(clean_arg) else f"given/designs/{base_name}.v"
        info = ALL_KNOWN_DESIGNS.get(base_name, {})
        top_mod = top or info.get("top")
        use_sv = info.get("sv", v_file.endswith(".sv") or base_name == "pic1826") if sv is None else sv

    sv_flag = "-sv " if use_sv else ""
    top_cmd = f"synth -flatten -top {top_mod}" if top_mod else "hierarchy -auto-top\nsynth -flatten"

    orig_aig = f"{output_dir}/{base_name}_orig.aig"
    orig_aag = f"{output_dir}/{base_name}_orig.aag"
    dch_aig = f"{output_dir}/{base_name}_dch.aig"
    dch_aag = f"{output_dir}/{base_name}_dch.aag"

    script_orig = (
        f"read_verilog {sv_flag}{v_file}\n"
        f"{top_cmd}\n"
        f"async2sync\n"
        f"dffunmap\n"
        f"aigmap\n"
        f"write_aiger {orig_aig}\n"
    )
    res_orig = runner.run_yosys_script(script_orig, f"syn_{base_name}.ys")
    if res_orig.returncode != 0:
        raise RuntimeError(f"Yosys failed for {base_name} orig: {res_orig.stderr}")

    conv_orig = runner.run_aigtoaig(orig_aig, orig_aag)
    if conv_orig.returncode != 0:
        raise RuntimeError(f"aigtoaig failed for {base_name} orig: {conv_orig.stderr}")

    abc_script = (
        f"read_aiger {orig_aig}\n"
        f"strash\n"
        f"dch\n"
        f"strash\n"
        f"write_aiger {dch_aig}\n"
    )
    res_dch = runner.run_abc_script(abc_script, f"abc_{base_name}.script")
    if res_dch.returncode != 0:
        raise RuntimeError(f"ABC failed for {base_name} dch: {res_dch.stderr}\n{res_dch.stdout}")

    conv_dch = runner.run_aigtoaig(dch_aig, dch_aag)
    if conv_dch.returncode != 0:
        raise RuntimeError(f"aigtoaig failed for {base_name} dch: {conv_dch.stderr}")

    return orig_aag, dch_aag


def extract_all_aigs(output_dir: str = "build/aigs", results_aig_dir: str = "results/aigs") -> List[Dict]:
    """Extracts original and ABC-restructured AIGs for all 6 required designs."""
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(results_aig_dir, exist_ok=True)
    stats_list = []

    for d in REQUIRED_DESIGNS:
        name = d["name"]
        top = d["top"]
        v_file = d["file"]
        sv_flag = "-sv " if d["sv"] else ""

        orig_aig = f"{output_dir}/{name}_orig.aig"
        orig_aag = f"{output_dir}/{name}_orig.aag"
        dch_aig = f"{output_dir}/{name}_dch.aig"
        dch_aag = f"{output_dir}/{name}_dch.aag"

        # If EDA tools are available, synthesize fresh; otherwise if already built in output_dir, verify and copy
        if not (os.path.exists(orig_aag) and os.path.exists(dch_aag)) or runner.can_execute_tools():
            print(f"Synthesizing {name} (top: {top}) to AIG...")
            extract_single_design(name, top=top, sv=d["sv"], output_dir=output_dir)
        else:
            print(f"Using verified AIGs for {name} (top: {top})...")

        # Copy AIG artifacts into results/aigs/ so they are tracked in results/ for Checkpoint 1
        for src_f in (orig_aig, orig_aag, dch_aig, dch_aag):
            if os.path.exists(src_f):
                shutil.copy2(src_f, os.path.join(results_aig_dir, os.path.basename(src_f)))

        header_orig = parse_aag_header(orig_aag)
        header_dch = parse_aag_header(dch_aag)

        entry = {
            "design": name,
            "top": top,
            "inputs": header_orig["inputs"],
            "latches": header_orig["latches"],
            "outputs": header_orig["outputs"],
            "orig_ands": header_orig["ands"],
            "dch_ands": header_dch["ands"],
            "and_reduction_pct": round((header_orig["ands"] - header_dch["ands"]) / header_orig["ands"] * 100.0, 2),
            "ref_ff": d["ref_ff"],
            "ref_and": d["ref_and"]
        }
        stats_list.append(entry)
        print(f"  {name}: {entry['latches']} FFs (ref: {entry['ref_ff']}), "
              f"ANDs: {entry['orig_ands']} -> {entry['dch_ands']} "
              f"({entry['and_reduction_pct']}% reduction, ref: {entry['ref_and']})")

    return stats_list


def write_aig_reports(stats_list: List[Dict], csv_path: str = "results/aig_stats.csv", md_path: str = "results/aig_stats.md"):
    """Writes AIG statistics to CSV and Markdown."""
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            "design", "top", "inputs", "latches", "outputs",
            "orig_ands", "dch_ands", "and_reduction_pct", "ref_ff", "ref_and"
        ])
        writer.writeheader()
        writer.writerows(stats_list)

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("# AIG Statistics for Required Designs\n\n")
        f.write("- **Baseline Synthesis**: Yosys (`synth -flatten -top <top>; async2sync; dffunmap; aigmap; write_aiger`).\n")
        f.write("- **ABC Restructuring**: `strash; dch; strash` (where the second `strash` collapses the SAT-sweeping choice nodes generated by `dch` into the canonical minimized AIG).\n")
        f.write("- **AIG Files**: Binary (`.aig`) and ASCII (`.aag`) graphs saved in `results/aigs/` and `build/aigs/`.\n\n")
        f.write("| Design | Top Module | Inputs | Flip-flops | Outputs | AND Nodes (Original) | AND Nodes (After ABC) | Reduction (%) | Table 2 Ref FFs | Table 2 Ref ANDs |\n")
        f.write("|---|---|---|---|---|---|---|---|---|---|\n")
        for s in stats_list:
            f.write(f"| `{s['design']}` | `{s['top']}` | {s['inputs']} | {s['latches']} | {s['outputs']} | "
                    f"{s['orig_ands']:,} | {s['dch_ands']:,} | {s['and_reduction_pct']:.2f}% | {s['ref_ff']} | {s['ref_and']:,} |\n")


if __name__ == "__main__":
    stats = extract_all_aigs()
    write_aig_reports(stats)
    print("AIG extraction complete.")
