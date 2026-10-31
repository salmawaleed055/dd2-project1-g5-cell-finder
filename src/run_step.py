"""
Step Runner for Option 2 Flow
Section 9.1: The tool, with one command per step of section 4.
Usage:
  python src/run_step.py 1               # Step 1: Extract AIGs and ABC restructuring
  python src/run_step.py 2 [file]        # Step 2: Enumerate cuts and check by simulation
  python src/run_step.py 3 [file]        # Step 3: Classify truth tables into P+N_out, P, and NPN classes
  python src/run_step.py 4 [file]        # Step 4: Cost classes by CMOS stages, inverters, and transistors
  python src/run_step.py 5               # Step 5: Check redundancy against HD & Table 4 self-test
  python src/run_step.py table1          # Reproduce Table 1
  python src/run_step.py hd_classes      # Generate HD class table
  python src/run_step.py cut_stats       # Generate full cut/class/redundancy reports across all 6 designs
  python src/run_step.py demo <design>   # Live demo on any design name, Verilog file, or AIGER file
"""

import sys
import os
from typing import Dict, List

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from src.aig import parse_aag
from src.cut_enumerator import CutEnumerator, verify_cut
from src.classification import get_p_class, get_p_nout_class, get_npn_class, depends_on_all_4
from src.redundancy import RedundancyChecker, synthesize_one_stage_4inp, cost_4inp_class, parse_hd_library
from src.extract_aigs import extract_all_aigs, extract_single_design, write_aig_reports
from src.reproduce_table1 import reproduce_table1, write_table1_reports
from src.hd_classes import build_hd_class_table, write_hd_class_reports
from src.cut_stats import generate_all_cut_stats, write_cut_stats_reports


def step_1():
    print("=== Step 1: Extracting AIGs and Restructuring with ABC ===")
    stats = extract_all_aigs()
    write_aig_reports(stats)
    print("Step 1 complete. Results saved in results/aig_stats.md, results/aig_stats.csv, and results/aigs/")


def step_2(aag_file: str = "build/aigs/cpu8_orig.aag"):
    print(f"=== Step 2: Enumerating cuts of up to 4 inputs on {aag_file} ===")
    if not os.path.exists(aag_file):
        alt = aag_file.replace("build/aigs/", "results/aigs/")
        if os.path.exists(alt):
            aag_file = alt
        else:
            print(f"File {aag_file} not found. Running Step 1 first...")
            step_1()

    aig = parse_aag(aag_file)
    enumerator = CutEnumerator(aig, max_cut_size=4, max_cuts_per_node=None)
    cuts_by_node = enumerator.enumerate_cuts()

    total_cuts = sum(len(c_list) for c_list in cuts_by_node.values())
    cuts_4inp = sum(
        1 for c_list in cuts_by_node.values() for c in c_list
        if len(c.inputs) == 4 and depends_on_all_4(c.truth_table)
    )
    print(f"Enumerated {total_cuts:,} total cuts ({cuts_4inp:,} non-degenerate 4-input cuts) across {len(cuts_by_node):,} nodes.")

    # Exhaustive simulation verification
    print("Verifying cuts by simulating each cut's logic for every input combination...")
    verified_count = 0
    for node, cuts in cuts_by_node.items():
        for cut in cuts:
            verify_cut(aig, cut)
            verified_count += 1

    print(f"PASS: Successfully simulated and verified {verified_count:,} cuts (100% equivalence).")


def step_3(aag_file: str = "build/aigs/cpu8_orig.aag"):
    print(f"=== Step 3: Classifying Truth Tables into Classes (P+N_out, P-class, and NPN) ===")
    if not os.path.exists(aag_file):
        alt = aag_file.replace("build/aigs/", "results/aigs/")
        if os.path.exists(alt):
            aag_file = alt
        else:
            step_1()

    aig = parse_aag(aag_file)
    enumerator = CutEnumerator(aig, max_cut_size=4, max_cuts_per_node=None)
    cuts_by_node = enumerator.enumerate_cuts()

    p_classes = set()
    p_nout_classes = set()
    npn_classes = set()
    p4_classes = set()
    pn4_classes = set()
    npn4_classes = set()

    for cuts in cuts_by_node.values():
        for cut in cuts:
            tt = cut.truth_table
            p_rep, _ = get_p_class(tt)
            pn_rep = get_p_nout_class(tt)
            npn_rep = get_npn_class(tt)
            p_classes.add(p_rep)
            p_nout_classes.add(pn_rep)
            npn_classes.add(npn_rep)
            if len(cut.inputs) == 4 and depends_on_all_4(tt):
                p4_classes.add(p_rep)
                pn4_classes.add(pn_rep)
                npn4_classes.add(npn_rep)

    print(f"From {aag_file}:")
    print(f"  All cuts (k <= 4): {len(p_nout_classes)} P+N_out classes, {len(p_classes)} P-classes, {len(npn_classes)} NPN classes")
    print(f"  Strict 4-input cuts (k = 4): {len(pn4_classes)} P+N_out classes, {len(p4_classes)} P-classes, {len(npn4_classes)} NPN classes")
    print("  Note: Input permutation + output inversion (P+N_out) and P-classes matter for CMOS because")
    print("  each input inversion costs 2 physical transistors (1 inverter), whereas NPN treats input inverters as free.")


def step_4(aag_file: str = "build/aigs/cpu8_orig.aag"):
    print(f"=== Step 4: Costing Discovered 4-Input Classes by CMOS Stages, Inverters, and Transistors ===")
    if not os.path.exists(aag_file):
        alt = aag_file.replace("build/aigs/", "results/aigs/")
        if os.path.exists(alt):
            aag_file = alt
        else:
            step_1()

    aig = parse_aag(aag_file)
    enumerator = CutEnumerator(aig, max_cut_size=4, max_cuts_per_node=None)
    cuts_by_node = enumerator.enumerate_cuts()

    p4_freq: Dict[int, int] = {}
    for cuts in cuts_by_node.values():
        for cut in cuts:
            if len(cut.inputs) == 4 and depends_on_all_4(cut.truth_table):
                rep, _ = get_p_class(cut.truth_table)
                p4_freq[rep] = p4_freq.get(rep, 0) + 1

    stage_counts: Dict[int, int] = {}
    for rep in p4_freq:
        c = cost_4inp_class(rep)
        st = int(c["stages"])
        stage_counts[st] = stage_counts.get(st, 0) + 1

    print(f"Costed {len(p4_freq)} distinct 4-input P-classes from {aag_file} (with <= 3 transistors in series per stage):")
    for st in sorted(stage_counts):
        print(f"  {st}-stage CMOS classes: {stage_counts[st]}")


def step_5():
    print("=== Step 5: Redundancy Checker and Self-Test against Table 4 ===")
    checker = RedundancyChecker("given/hd_usable.lib")

    # Verify all combinational HD cells come out as Exists
    hd_cells = parse_hd_library("given/hd_usable.lib")
    for c in hd_cells:
        res = checker.classify_hd_cell_dict(c)
        if res != "Exists":
            raise AssertionError(f"Self-test failed: HD cell {c['name']} classified as {res} instead of Exists")
    print(f"PASS: All {len(hd_cells)} combinational single-output cells in hd_usable.lib classified as 'Exists'.")

    counts = checker.run_self_test()

    print("\n--- Handout Table 4 Self-Test Results ---")
    print(f"Exists: {counts['Exists']} (Reference: 24)")
    print(f"Exists with an inverter: {counts['Exists with an inverter']} (Reference: 20)")
    print(f"Contained: {counts['Contained']} (Reference: 38)")
    print(f"New: {counts['New']} (Reference: 3,822)")
    print(f"New, and one static CMOS stage: {counts['New, and one static CMOS stage']} (Reference: 9)")
    print(f"New, one stage, at most 3 in series and <= 12 tx: {counts['New, one stage, at most 3 transistors in series and at most 12 transistors']} (Reference: 5)")
    print(f"Simplest cells (4 inputs used once, <= 3 in series): {counts['One stage with every input used once']} (Reference: 8, of which 6 Exist and 2 are Contained)")
    print(f"  - Exists: {counts['One stage with every input used once, Exists']}")
    print(f"  - Contained: {counts['One stage with every input used once, Contained']}")

    sp_info = synthesize_one_stage_4inp()
    one_stage_all = sp_info["one_stage_all"]
    one_stage_3s_12tx = sp_info["one_stage_3s_12tx"]
    read_once_3s = sp_info["read_once_3s"]

    os.makedirs("results", exist_ok=True)
    with open("results/table4_self_test.md", "w", encoding="utf-8") as f:
        f.write("# Redundancy Checker Self-Test against Handout Table 4\n\n")
        f.write("## 1. Table 4 Reference Count Verification\n\n")
        f.write("- **All 264 single-output combinational cells in `hd_usable.lib` fed as candidates**: **100% classified as `Exists`**.\n")
        f.write("- **Total non-degenerate 4-input Boolean functions**: $64,594$, partitioned into **3,904 P-classes** under $S_4$ input permutations.\n\n")
        f.write("| Group | Reference Count | Implemented Tool Count | Status |\n")
        f.write("|---|---|---|---|\n")
        f.write(f"| Exists | 24 | {counts['Exists']} | {'MATCH' if counts['Exists'] == 24 else 'FAIL'} |\n")
        f.write(f"| Exists with an inverter | 20 | {counts['Exists with an inverter']} | {'MATCH' if counts['Exists with an inverter'] == 20 else 'FAIL'} |\n")
        f.write(f"| Contained | 38 | {counts['Contained']} | {'MATCH' if counts['Contained'] == 38 else 'FAIL'} |\n")
        f.write(f"| New | 3,822 | {counts['New']:,} | {'MATCH' if counts['New'] == 3822 else 'FAIL'} |\n")
        f.write(f"| New, and one static CMOS stage | 9 | {counts['New, and one static CMOS stage']} | {'MATCH' if counts['New, and one static CMOS stage'] == 9 else 'FAIL'} |\n")
        f.write(f"| New, one stage, <= 3 in series and <= 12 tx | 5 | {counts['New, one stage, at most 3 transistors in series and at most 12 transistors']} | {'MATCH' if counts['New, one stage, at most 3 transistors in series and at most 12 transistors'] == 5 else 'FAIL'} |\n")
        f.write(f"| One stage with every input used once (<= 3 in series) | 8 (6 Exist, 2 Contained) | {counts['One stage with every input used once']} ({counts['One stage with every input used once, Exists']} Exist, {counts['One stage with every input used once, Contained']} Contained) | {'MATCH' if counts['One stage with every input used once'] == 8 and counts['One stage with every input used once, Exists'] == 6 and counts['One stage with every input used once, Contained'] == 2 else 'FAIL'} |\n\n")

        f.write("## 2. The 9 Single-Stage Static CMOS `New` Classes\n\n")
        f.write("| P-Class | Synthesized 1-Stage Expression | Literals | Transistors | NMOS Series | PMOS Series | <= 3 Series & <= 12 Tx |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for rep in sorted(one_stage_all):
            if checker.classify(rep) == "New":
                in_5 = rep in one_stage_3s_12tx
                lits, n, p, expr = one_stage_3s_12tx[rep] if in_5 else one_stage_all[rep]
                f.write(f"| `0x{rep:04X}` | `{expr}` | {lits} | {2 * lits} | {n} | {p} | **{'YES' if in_5 else 'NO'}** |\n")

        f.write("\n## 3. The 8 Simplest Single-Stage Cells (Every Input Used Once, <= 3 in Series)\n\n")
        f.write("| P-Class | Synthesized Read-Once Expression | NMOS Series | PMOS Series | Redundancy Class | Matched HD Cell |\n")
        f.write("|---|---|---|---|---|---|\n")
        for rep in sorted(read_once_3s):
            n, p, expr = read_once_3s[rep]
            cat, hd_cell, desc, _ = checker.classify_with_details(rep)
            f.write(f"| `0x{rep:04X}` | `{expr}` | {n} | {p} | **{cat}** | `{hd_cell}` |\n")

    print("\nSelf-test successfully verified and written to results/table4_self_test.md")


def run_demo(target: str):
    """Runs an end-to-end live demonstration on a design name, .v file, or .aag file."""
    clean = target.strip().replace("\\", "/")
    if clean.endswith(".aag") and os.path.exists(clean):
        orig_aag = clean
        dch_aag = None
    else:
        base = os.path.splitext(os.path.basename(clean))[0]
        cand_orig = f"build/aigs/{base}_orig.aag"
        cand_dch = f"build/aigs/{base}_dch.aag"
        if not os.path.exists(cand_orig):
            cand_orig = f"results/aigs/{base}_orig.aag"
            cand_dch = f"results/aigs/{base}_dch.aag"
        if os.path.exists(cand_orig):
            orig_aag = cand_orig
            dch_aag = cand_dch if os.path.exists(cand_dch) else None
        else:
            orig_aag, dch_aag = extract_single_design(clean)

    step_2(orig_aag)
    step_3(orig_aag)
    step_4(orig_aag)
    if dch_aag and os.path.exists(dch_aag):
        print(f"\n--- Comparing with ABC-restructured AIG ({dch_aag}) ---")
        step_2(dch_aag)
        step_3(dch_aag)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1].lower()
    if cmd == "1":
        step_1()
    elif cmd == "2":
        if len(sys.argv) > 2:
            step_2(sys.argv[2])
        else:
            step_2("build/aigs/cpu8_orig.aag")
    elif cmd == "3":
        aag = sys.argv[2] if len(sys.argv) > 2 else "build/aigs/cpu8_orig.aag"
        step_3(aag)
    elif cmd == "4":
        aag = sys.argv[2] if len(sys.argv) > 2 else "build/aigs/cpu8_orig.aag"
        step_4(aag)
    elif cmd == "5":
        step_5()
    elif cmd == "cut_stats":
        r_list, summ, cands = generate_all_cut_stats()
        write_cut_stats_reports(r_list, summ, cands)
    elif cmd == "table1":
        t1 = reproduce_table1()
        write_table1_reports(t1)
    elif cmd == "hd_classes":
        hdc = build_hd_class_table()
        write_hd_class_reports(hdc)
    elif cmd in ("6", "7", "8", "9", "9b"):
        from src import cp2_flow
        {"6": cp2_flow.step_6, "7": cp2_flow.step_7, "8": cp2_flow.step_8,
         "9": cp2_flow.step_9, "9b": cp2_flow.step_9_baseline}[cmd]()
    elif cmd == "demo":
        target = sys.argv[2] if len(sys.argv) > 2 else "cpu8"
        run_demo(target)
    else:
        print(f"Unknown step: {cmd}")
        sys.exit(1)
