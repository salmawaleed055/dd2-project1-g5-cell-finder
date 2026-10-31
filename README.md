# Project 1, Option 2: Finding Cells Worth Adding

CSCE 3304 Digital Design II - Fall 2026  
Milestone 2 (Checkpoint 2, Tag `cp2`)

## 1. Group
Salma Elmarakby, Mikhael Khalil, Marina Mikhael · Option 2 · AI used as a development aid

## 2. Quick start
Tools: Yosys 0.70+201 (with bundled ABC), Icarus Verilog 13.0, Python 3.11+

```bash
make setup     # < 1 min: creates directories and links PDK and given files
make check     # < 1 min: verifies tool versions and required library availability
make test      # < 1 min: runs unit tests, simulation cut verifier, Table 4 self-test, and broken cases
make all       # ~ 6 min: Milestone 1 flow, then area model, ranking, extended Liberty, mapping with cec, Table 5
```

## 3. What the tool does
Option 2 builds an automated EDA tool that discovers recurring small logic functions (up to 4-input cuts) in synthesized designs, checks whether the SkyWater 130nm High-Density (`sky130_fd_sc_hd`) standard-cell library already provides them, costs candidate classes by CMOS stages, inverters, and transistors (with at most 3 transistors in series per stage), estimates physical area, and measures chip area savings when remapping benchmark designs using Yosys and ABC.
The tool operates in structured, reproducible steps:
1. Synthesizes RTL designs to AIGs (`synth -flatten`, `async2sync`, `dffunmap`, `aigmap`, `write_aiger`) and restructures them using ABC (`strash; dch; strash`).
2. Enumerates all non-dominated K-feasible cuts ($K \le 4$) in topological order, computes exact 16-bit truth tables, and exhaustively verifies 100% of cuts by gate-level simulation across all $2^k$ input valuations.
3. Classifies truth tables into permutation + output inversion equivalence classes (P+$N_{\text{out}}$ classes), input permutation classes (P-classes), and NPN classes.
4. Costs candidate classes by CMOS stage count, inverter count, and transistor count (with at most 3 transistors in series in any stage).
5. Checks candidates against the full HD library, categorizing them into Table 3 redundancy classes (`Exists`, `Exists with an inverter`, `Contained`, `New`), and verifies the checker against all 264 combinational HD cells and all 9 reference counts of Table 4.

## 4. Commands
| Command | Input | Output |
|---|---|---|
| `make setup` | None | Workspace directories, links to `pdk` and `given/` |
| `make check` | Tool paths, PDK | Tool versions and library sanity validation |
| `make test` | `tests/` and `tests/broken/` | Regression test results, broken case rejection checks |
| `make all` | Benchmark designs in `given/designs/` | Complete Milestone 1 outputs in `results/` and `build/aigs/` |
| `make demo IN=<design>` | Design name, `.v` file, or `.aag` file | AIG extraction, cut enumeration, 100% simulation check, classification, and costing |
| `python src/run_step.py 6` | `given/hd_usable.lib` | `results/area_model.md/.csv` (area model fitted to HD x1 cells) |
| `python src/run_step.py 9b` | Designs, `given/hd_reduced.lib` | Baseline mappings + dsec, `results/table5_baseline.json`, `results/netlists/`, `results/logs/` |
| `python src/run_step.py 7` | `results/aigs/*_dch.aag`, baseline | `results/candidates.md/.csv` (classified, costed, redundancy-checked, ranked) |
| `python src/run_step.py 8` | `results/candidates.csv` | `libs/hd_extended_est.lib`, `cells/requests/*.json` (Yosys must import 189 + N cells) |
| `python src/run_step.py 9` | Extended Liberty | Extended mappings + dsec, `results/table5_estimated.md/.csv` |
| `make clean` | None | Cleans `build/` artifacts and Python cache directories |
| `python src/run_step.py 1` | `given/designs/*.v` | `build/aigs/*`, `results/aigs/*`, `results/aig_stats.md`, `results/aig_stats.csv` |
| `python src/run_step.py 2 [file]` | `.aag` AIGER file | Cut enumeration and 100% exhaustive simulation verification |
| `python src/run_step.py 3 [file]` | `.aag` AIGER file | P+$N_{\text{out}}$, P-class, and NPN classification counts |
| `python src/run_step.py 4 [file]` | `.aag` AIGER file | CMOS stage, inverter, and transistor costing (at most 3 in series) |
| `python src/run_step.py 5` | `given/hd_usable.lib` | Redundancy classification and `results/table4_self_test.md` |
| `python src/run_step.py cut_stats` | `build/aigs/*.aag` | `results/cut_stats.md`, `results/cut_stats.csv`, `results/redundancy_report.md` |
| `python src/run_step.py table1` | Designs & Liberty libs | `results/table1.md`, `results/table1.csv` |
| `python src/run_step.py hd_classes` | `given/hd_usable.lib` | `results/hd_classes.md`, `results/hd_classes.csv` |

## 5. Layout
- `src/`: Core Python tool implementation (AIG parser, cut enumerator, classification, CMOS cost & redundancy checker, runners)
- `tests/`: Automated unit and integration tests (`test_aig.py`, `test_cuts.py`, `test_redundancy.py`)
- `tests/broken/`: Deliberately broken test cases that the check scripts must reject
- `results/`: Output markdown and CSV deliverables for all required milestone tables, logs, and extracted AIGs (`results/aigs/`)
- `build/`: Working synthesis and restructured AIGER files (`_orig.aag`, `_dch.aag`) and temporary scripts
- `libs/`: Extended Liberty files (for Checkpoints 2 and 3)
- `cells/`: Cell response and request definitions
- `ai/`: AI use logs (`use_log.md`) and caught mistakes logs (`mistakes_log.md`)
- `report/`: Technical report and AI report source files and PDFs

## 6. Results
- **AIG Statistics & ABC Restructuring**: `results/aig_stats.md` and `results/aigs/` (Original vs restructured AND nodes across all 6 required designs; `cpu8`: 932 $\to$ 849 ANDs, 82 FFs)
- **Cut & Class Comparison**: `results/cut_stats.md` (186,065 original cuts and 149,061 restructured cuts verified 100% by simulation; 499 P-classes, 328 P+$N_{\text{out}}$ classes, 83 NPN classes across all cuts; 434 P-classes, 293 P+$N_{\text{out}}$ classes, 69 NPN classes for strict 4-input cuts)
- **Table 1 Reproduced**: `results/table1.md` (Chip area in $\mu\text{m}^2$ across usable and reduced HD library with Scripts A and B; script B differs by at most 0.15%; script A differs by up to 4.49% (fir10) on Yosys 0.70, above the handout's 0.5% expectation, see Limitations)
- **Class Table of HD**: `results/hd_classes.md` (83 single-output combinational families + 3 multi-output/constant families `conb`, `ha`, `fa` = 86 combinational families; 24 four-input P-classes, 12 P+$N_{\text{out}}$ classes, 4 NPN classes)
- **Table 4 Self-Test**: `results/table4_self_test.md` (100% first-principles match with all 9 reference counts across the 3,904 four-input classes: 24 Exists, 20 Exists with inverter, 38 Contained, 3,822 New, 9 one-stage New, 5 one-stage $\le 3$-series $\le 12$-tx New, 8 read-once simplest cells = 6 Exists + 2 Contained)
- **Candidate Redundancy Report**: `results/redundancy_report.md` (All 497 distinct 4-input candidate P-classes discovered across the 6 designs, original and restructured AIGs together, with their Table 3 class, matched HD cell, occurrence counts, and CMOS cost)

- **Area model (CP2)**: `results/area_model.md` (sites = 1.985 + 0.451·T + 0.308·(stages−1); mean error 0.77 sites, 12.9%, over 61 HD x1 cells)
- **Ranked candidates (CP2)**: `results/candidates.md` (393 classes from the restructured AIGs only, which both mapping scripts start from; 375 kept after Table 3 rules, 251 with positive estimated saving; top 10 in the Liberty)
- **First Table 5, estimated areas (CP2)**: `results/table5_estimated.md` (24 mappings, all pass ABC `dsec`; best-of-both total −0.34%)

## 7. Tests
`make test` executes comprehensive automated tests and verifies all broken cases:
- `tests/test_aig.py`: Validates AIGER format parsing, node indexing, topological sorting, and simulation.
- `tests/test_cuts.py`: Verifies K-feasible cut enumeration and exhaustively simulates all $2^k$ truth table combinations against the AIG logic cone.
- `tests/test_redundancy.py`: Verifies that 100% of all 264 single-output combinational HD cells (1 to 6 inputs) flag as `Exists`, and verifies all 9 rows of Table 4.
- `tests/broken/test_broken_cut_tt.py`: Deliberately corrupts a cut's truth table bit; verified that `verify_cut()` catches the mismatch and raises `CutVerificationError`.
- `tests/broken/test_broken_redundancy.py`: Feeds an installed HD cell (`nand4_1`, `0x7FFF`) to the redundancy checker; verifies that any claim of being `New` fails.
- `tests/broken/test_broken_liberty.py`: Feeds a malformed Liberty file with syntax errors to Yosys `read_liberty`; verifies that Yosys rejects it with a non-zero exit code.
- `tests/test_cp2.py`: CMOS costing of textbook gates, area model, Liberty writer (Yosys imports 189 + N), netlist pin repair, cpu8 mapping passes `dsec`.
- `tests/broken/test_broken_cp2.py`: a mapped cpu8 netlist with one nand2 swapped for nor2 must fail `dsec`; a new cell with the wrong function must be flagged by the Liberty check.
- `tests/broken/test_broken_cec.py`: Runs ABC `cec` on functionally inequivalent netlists; verifies that ABC detects non-equivalence.

## 8. AI use
- Rules and constraints: `AGENTS.md`
- AI prompts, tool assistance, and verification: `ai/use_log.md`
- Caught errors and analysis: `ai/mistakes_log.md`
- Detailed retrospective report: `report/ai_report.pdf`

## 9. Limitations
- Checkpoint 2 uses estimated areas; real cells (step 11), the greedy final set (step 10), the cell-by-cell curve and the 30% experiment are Checkpoint 3.
- Yosys 0.70 writes some mapped cell pins under internal signal names; `src/netlist_repair.py` repairs them and `dsec` checks every repaired netlist.
- On Yosys 0.70+190, script A on the reduced library costs up to 4.49% more than on the usable library (`results/table1.md`); script B stays within 0.15%.
