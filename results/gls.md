# SPM and the multiplier: mapping, equivalence and gate-level testbenches

SPM (Tutorial 4) and the 8x8 multiplier (Tutorial 2), mapped with the commands of section 2 on the baseline and on the extended libraries. Every netlist is checked with ABC `dsec` against the design before ABC, and simulated with the tutorials' self-checking testbenches on the PDK's cell models (zero delay, as Tutorial 4's `make gls`); new cells use the behavioural models generated from their Liberty functions (`libs/new_cells_*.v`). Logs: `results/logs/<design>_<library>_<script>_<testbench>.log`.

| Design | Library | Script | Area (um2) | New-cell instances | Equivalence | Testbench | Result |
|---|---|---|---|---|---|---|---|
| spm | baseline | A | 2,869.00 | 0  | pass | `SPM_tb` | pass |
| spm | baseline | B | 2,907.79 | 0  | pass | `SPM_tb` | pass |
| spm | final_est | A | 2,869.00 | 0  | pass | `SPM_tb` | pass |
| spm | final_est | B | 2,907.79 | 0  | pass | `SPM_tb` | pass |
| mul | baseline | A | 1,737.92 | 0  | pass | `mul_tb` | pass |
| mul | baseline | A | 1,737.92 | 0  | pass | `mul_exhaustive_tb` | pass |
| mul | baseline | B | 1,964.38 | 0  | pass | `mul_tb` | pass |
| mul | baseline | B | 1,964.38 | 0  | pass | `mul_exhaustive_tb` | pass |
| mul | final_est | A | 1,734.16 | 0  | pass | `mul_tb` | pass |
| mul | final_est | A | 1,734.16 | 0  | pass | `mul_exhaustive_tb` | pass |
| mul | final_est | B | 1,911.83 | 0  | pass | `mul_tb` | pass |
| mul | final_est | B | 1,911.83 | 0  | pass | `mul_exhaustive_tb` | pass |
