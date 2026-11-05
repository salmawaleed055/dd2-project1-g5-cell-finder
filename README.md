# Project 1, Option 2: Finding Cells Worth Adding

CSCE 3304 Digital Design II - Fall 2026 · Final submission (tag `final`)

## 1. Group
Salma Elmarakby (900232658), Mikhael Khalil (900232633), Marina Mikhael (900233146) · Option 2 · AI used as a development aid

## 2. Quick start
Tools: Yosys 0.70+201 (git 0ad867ab5, with its bundled ABC), Icarus Verilog 14.0 (devel), OpenSTA 2.5.0, Python 3.12, the SKY130 PDK (`sky130A`, installed with ciel). Every number in `results/` and in the reports comes from one clean run on these versions (Ubuntu 24.04 under WSL2).

```bash
export PDK_ROOT=~/.ciel   # where ciel installed sky130A
make setup     # < 1 min: links given/ (student pack) and pdk/ (PDK_ROOT/sky130A)
make check     # < 1 min: Yosys, ABC, Icarus, OpenSTA, the PDK files, the two given libraries
make test      # < 1 min: unit tests, Table 4 self-test, and every broken case
make all       # ~ 13 min: the whole flow, steps 1 to 12 of handout section 4
make demo IN=<design.v or name>   # ~ 1 min: the whole flow on one design (interview demo)
```

OpenSTA without root: `conda create -p ~/eda-sta -c litex-hub -c conda-forge openroad` provides `~/eda-sta/bin/sta`, which the flow finds (or set `STA_BIN`). Without OpenSTA, `make all` still runs and leaves the delay table unmeasured. `results/curve.png` needs `matplotlib` in the Python that runs the flow (`make all PYTHON=/usr/bin/python3` when OSS CAD Suite's own Python comes first on PATH).

## 3. What the tool does
The tool finds the small functions that synthesized designs compute again and again, checks which of them the SKY130 HD library already has, proposes cells for the rest, writes a Liberty file with them, and measures what they do to area and delay when Yosys and ABC map the designs. Its steps, in the order `make all` runs them:
1. Synthesize each required design to an AIG, and restructure it with ABC (`strash; dch; strash`).
2. Enumerate every cut of up to 4 inputs with its truth table, and simulate every cut on all its inputs.
3. Classify the truth tables up to input order (P), input order and output inversion (P+N<sub>out</sub>), and NPN.
4. Cost every class in CMOS stages, inverters and transistors, with at most 3 in series per stage.
5. Check every class against HD (handout Table 3), with the self-test against Table 4.
6. Fit an area model to HD's x1 cells and report its error.
7. Rank the candidates by estimated saving. (The baseline mapping of step 9 runs before this step, because the ranking needs its areas.)
8. Write one cell request per candidate (overview, Appendix A) and the extended Liberty file.
9. Map every design with and without the new cells, scripts A and B, and check every netlist with ABC `dsec` (or `cec` without flip-flops).
10. Select the final set greedily by remapping (at most 10 cells), and write Table 5 for it.
11. Read real cells from cell responses, validate them, and remeasure with them.
12. Make the most-used new cell 30% smaller and remap.

Then the cell-by-cell curve, SPM and the multiplier with their gate-level testbenches, pic16/p16c5x against risc8, and the worst delay of every mapping from OpenSTA.

## 4. Commands
| Command | Input | Output |
|---|---|---|
| `make setup` | `PDK_ROOT`, the student pack next to the repository | Links `given/`, `pdk/`; working folders |
| `make check` | Tools on PATH, `pdk/`, `given/` | Versions and file checks; exit 1 if anything required is missing |
| `make test` | `tests/`, `tests/broken/` | Unit tests and broken cases; exit 1 on any failure |
| `make all` | `given/designs/`, `given/*.lib`, `designs/tutorials/` | Everything in `results/`, `libs/`, `cells/requests/` |
| `make demo IN=<file>` | A design name of handout Table 2, or any `.v` file (top found automatically) | Steps 1–4 printed; `results/demo/<design>.md` with its classes, Table 5 rows (both scripts, dsec) and worst delays |
| `make clean` | | Removes `build/` and Python caches |
| `python src/run_step.py 1` | `given/designs/*.v` | `results/aigs/`, `results/aig_stats.md` |
| `python src/run_step.py 2 / 3 / 4 [file.aag]` | An AIGER file | Cuts with the simulation check / class counts / CMOS costs |
| `python src/run_step.py cut_stats` | `results/aigs/` | `results/cut_stats.md`, `results/redundancy_report.md` |
| `python src/run_step.py 5` | `given/hd_usable.lib` | `results/table4_self_test.md` |
| `python src/run_step.py table1` | Designs, both libraries | `results/table1.md` |
| `python src/run_step.py hd_classes` | `given/hd_usable.lib` | `results/hd_classes.md` |
| `python src/run_step.py 6` | `given/hd_usable.lib` | `results/area_model.md` |
| `python src/run_step.py 9b` | Designs, `given/hd_reduced.lib` | Baseline mappings with dsec, `results/table5_baseline*.json` |
| `python src/run_step.py 7` | AIGs, baseline areas | `results/candidates.md/.csv` |
| `python src/run_step.py 8` | `results/candidates.csv` | `libs/hd_extended_est.lib` (top 10), `cells/requests/` |
| `python src/run_step.py 9` | `libs/hd_extended_est.lib` | `results/table5_estimated.md` (CP2 Table 5, top 10 by rank) |
| `python src/run_step.py 10` | Candidates, baseline | `results/greedy.md`, `results/final_set.json`, `libs/hd_extended_final_est.lib`, `results/table5_final_est.md` |
| `python src/run_step.py 11` | `cells/responses/*.json` and their Liberty files | `results/real_cells.md`; with accepted cells `libs/hd_extended_final_real.lib`, `results/table5_final_real.md`, `results/curve_real.csv` |
| `python src/run_step.py curve` | `results/final_set.json` | `results/curve.md`, `results/curve_est.csv`, `results/curve.png` |
| `python src/run_step.py 12` | Final library | `results/sensitivity_30pct.md` |
| `python src/run_step.py gls` | `designs/tutorials/` | `results/gls.md` (SPM, multiplier: dsec/cec and testbenches) |
| `python src/run_step.py extra` | pic16, p16c5x | `results/isa_designs.md` |
| `python src/run_step.py delay` | Mapped netlists | `results/delay.md` (OpenSTA) |
| `python src/check_full_hd.py` | Full HD Liberty from the PDK | `results/full_hd_check.md` |
| `python report/build_pdf.py` | `report/*.md` | `report/report.pdf`, `report/ai_report.pdf` (Edge/Chrome headless) |

## 5. Layout
- `src/`: the tool. CP1: `aig.py`, `cut_enumerator.py`, `classification.py`, `redundancy.py`, `extract_aigs.py`, `cut_stats.py`, `reproduce_table1.py`, `hd_classes.py`. CP2: `cmos_cost.py`, `area_model.py`, `candidates.py`, `liberty_writer.py`, `table5.py`, `equivalence.py`, `netlist_repair.py`, `cp2_flow.py`. Final: `final_flow.py`, `responses.py`, `sta.py`. `run_step.py` runs each step; `runner.py` finds and runs the tools.
- `tests/`: unit tests; `tests/broken/`: the broken cases.
- `designs/tutorials/`: SPM (Tutorial 4) and the multiplier (Tutorial 2) with their testbenches.
- `results/`: every table, CSV, log and netlist the reports use; `results/demo/` holds the rehearsal demo on x18.
- `libs/`: the Liberty files the tool writes (CP2 top 10, final set, 30% variant) and the new-cell Verilog models.
- `cells/requests/`: one Appendix A request per candidate; `cells/responses/`: where cell responses go.
- `ai/`: AI use and mistakes logs for CP1, CP2 and final.
- `report/`: `report.md/.pdf`, `ai_report.md/.pdf`, and `build_pdf.py`.
- `docs/interface/`: the Appendix A request and response examples.

## 6. Results
- **AIGs, cuts, classes**: `results/aig_stats.md`, `results/cut_stats.md`. 335,126 cuts over the six designs, all passing the simulation check; 4-input classes after ABC: 393 P, 270 P+N<sub>out</sub>, 67 NPN.
- **Table 1**: `results/table1.md`. Reduced vs usable library within 0.15% for every design and script.
- **HD class table**: `results/hd_classes.md`. 83 single-output families, 24 four-input P-classes.
- **Table 4 self-test**: `results/table4_self_test.md`. All 264 HD cells Exist; all 9 reference counts reproduced.
- **Redundancy report**: `results/redundancy_report.md`, `results/candidates.md`. Of 393 classes: 18 Exists, 20 Exists with an inverter, 23 Contained, 332 New.
- **Area model**: `results/area_model.md`. sites = 1.985 + 0.451·T + 0.308·(stages−1); mean error 0.77 sites (12.9%) over 61 x1 HD cells.
- **Ranked candidates**: `results/candidates.md`. 375 kept, 244 with a positive estimated saving.
- **Final set**: `results/greedy.md`. 9 cells kept out of 30 tried; 4 of the 9 are never instantiated in the final mappings (mapping noise).
- **Table 5, estimated areas**: `results/table5_final_est.md`. Every mapping passes dsec; best-of-both total over the required designs **+0.08%** (85,602.1 → 85,535.8 um2); fir10 +0.27%, risc8 −0.07%.
- **Cell-by-cell curve**: `results/curve.md`, `results/curve.png`.
- **30% experiment**: `results/sensitivity_30pct.md`. `dd2_g5__f000b_1` 30% smaller: total reduction 0.70% instead of 0.08%.
- **Delay**: `results/delay.md`. Worst path of every mapping from OpenSTA.
- **SPM and the multiplier**: `results/gls.md`. dsec/cec and the tutorial testbenches pass on every library and script.
- **risc8, pic16, p16c5x**: `results/isa_designs.md`. All three use the same two cells most (`0x000B`, `0xA888`).
- **Real cells**: `results/real_cells.md`. No response received yet; see Limitations.
- **CP2 Table 5 (top 10 by rank)**: `results/table5_estimated.md`, kept for reference.

## 7. Tests
`make test` runs:
- `tests/test_aig.py`: AIGER parsing, indexing, simulation.
- `tests/test_cuts.py`: cut enumeration with the exhaustive simulation of every cut. Broken: `tests/broken/test_broken_cut_tt.py` (one truth-table bit flipped must be caught).
- `tests/test_redundancy.py`: all 264 HD cells come out Exists; the 9 counts of Table 4. Broken: `tests/broken/test_broken_redundancy.py` (nand4_1 claimed New must fail).
- `tests/test_cp2.py`: CMOS costs of textbook gates, the area model, the Liberty writer (Yosys imports 189 + N), pin repair, cpu8 mapping passes dsec. Broken: `tests/broken/test_broken_liberty.py` (a malformed Liberty file Yosys must reject), `tests/broken/test_broken_cp2.py` (cpu8 with nand2 swapped for nor2 must fail dsec; a new cell with the wrong function must be flagged), `tests/broken/test_broken_cec.py` (ABC must find two netlists inequivalent).
- `tests/test_final.py`: greedy selection keeps only improving cells and stops at 10; the Liberty function parser agrees with HD's functions and reads the full operator set; a correct cell response is accepted; the 30% Liberty edit loads in Yosys; new-cell Verilog models match their truth tables on all 16 inputs; SPM passes its testbench. Broken: `tests/broken/test_broken_final.py` (responses with status fail, a wrong function, or two cell groups are rejected; SPM with one cell swapped makes `SPM_tb` report wrong products; the multiplier with one cell swapped fails `cec`; a candidate that raises the area is dropped).

## 8. AI use
`AGENTS.md` · `ai/use_log.md`, `ai/use_log_cp2.md`, `ai/use_log_final.md` · `ai/mistakes_log.md`, `ai/mistakes_log_cp2.md`, `ai/mistakes_log_final.md` · `report/ai_report.pdf`

## 9. Limitations
- **Real cells are not measured yet.** The cell generator for three-student Option 2 groups had not been received when the final results were produced, so Table 5 with real areas, the real-area curve and the real-area 30% experiment are missing. Step 11 is implemented and tested: put each response in `cells/responses/<cell>.json` with its Liberty file and run `python src/run_step.py 11`, then `curve`, `12`, `gls` and `delay`.
- The saving (0.08%) is the size of ABC's reaction to a changed library: 4 of the 9 kept cells are never instantiated, and the 30% experiment changes the result nine-fold. The area model has a 12.9% mean error.
- New cells carry placeholder capacitance and scalar timing; their delays are indicative.
- The greedy tries the 30 best-ranked candidates in one pass.
- Areas depend on the Yosys build (CP2 measured +0.34% on 0.70+190, +0.05% on 0.70+201; `results/rerun_yosys_0.70_201/`).
- Yosys 0.70 writes some mapped cell pins under internal signal names; `src/netlist_repair.py` repairs them, and every repaired netlist must pass the equivalence check.

## 10. Third-party files
| File | Source | Licence |
|---|---|---|
| `libs/*.lib` (contain `given/hd_reduced.lib`) | Course student pack, built from the SkyWater `sky130_fd_sc_hd` Liberty | Apache-2.0 |
| `designs/tutorials/spm/` (SPM, CSADD, TCMP, SPM_tb) | Course Tutorial 4 (M. Shalan) | Apache-2.0 (notice in each file) |
| `designs/tutorials/mul/` (mul, mul_tb, mul_exhaustive_tb) | Course Tutorial 2 (M. Shalan) | Course material |
| `results/netlists/`, `results/aigs/`, `results/demo/` (generated from `given/designs/`, not committed) | Course student pack, from the sift repository | Each design's own notice (BSD, GPL-2, LGPL-2.1 or the author's own) |
| `docs/interface/`, starting Makefile, README and log layouts | Course student pack, `repo_template/` | Course material |
