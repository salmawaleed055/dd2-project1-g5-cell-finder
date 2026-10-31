# Area Model Fitted to HD x1 Cells

Least-squares fit of the width in sites (0.46 um x 2.72 um = 1.2512 um2 per site) on every single-output combinational `_1` cell of HD with 1 to 4 inputs, with transistor and stage counts from `src/cmos_cost.py` (at most 3 transistors in series per stage).

**sites = 1.985 + 0.451 x transistors + 0.308 x (stages - 1)**, rounded up to a whole site for a new cell.

| Group | Cells | Mean abs. error (sites) | Max abs. error (sites) | Mean abs. error (%) |
|---|---|---|---|---|
| single-stage | 13 | 0.56 | 0.79 | 13.6% |
| multi-stage | 48 | 0.83 | 3.91 | 12.7% |
| all | 61 | 0.77 | 3.91 | 12.9% |

## Cell by cell

| Cell | Inputs | Transistors | Stages | Construction | HD sites | Model sites | Error |
|---|---|---|---|---|---|---|---|
| `sky130_fd_sc_hd__a211oi_1` | 4 | 8 | 1 | one complex gate | 6 | 5.59 | -0.41 |
| `sky130_fd_sc_hd__a21oi_1` | 3 | 6 | 1 | one complex gate | 4 | 4.69 | +0.69 |
| `sky130_fd_sc_hd__a22oi_1` | 4 | 8 | 1 | one complex gate | 6 | 5.59 | -0.41 |
| `sky130_fd_sc_hd__a31oi_1` | 4 | 8 | 1 | one complex gate | 5 | 5.59 | +0.59 |
| `sky130_fd_sc_hd__inv_1` | 1 | 2 | 1 | one complex gate | 3 | 2.89 | -0.11 |
| `sky130_fd_sc_hd__nand2_1` | 2 | 4 | 1 | one complex gate | 3 | 3.79 | +0.79 |
| `sky130_fd_sc_hd__nand3_1` | 3 | 6 | 1 | one complex gate | 4 | 4.69 | +0.69 |
| `sky130_fd_sc_hd__nor2_1` | 2 | 4 | 1 | one complex gate | 3 | 3.79 | +0.79 |
| `sky130_fd_sc_hd__nor3_1` | 3 | 6 | 1 | one complex gate | 4 | 4.69 | +0.69 |
| `sky130_fd_sc_hd__o211ai_1` | 4 | 8 | 1 | one complex gate | 6 | 5.59 | -0.41 |
| `sky130_fd_sc_hd__o21ai_1` | 3 | 6 | 1 | one complex gate | 4 | 4.69 | +0.69 |
| `sky130_fd_sc_hd__o22ai_1` | 4 | 8 | 1 | one complex gate | 5 | 5.59 | +0.59 |
| `sky130_fd_sc_hd__o31ai_1` | 4 | 8 | 1 | one complex gate | 6 | 5.59 | -0.41 |
| `sky130_fd_sc_hd__a211o_1` | 4 | 10 | 2 | complex gate + output inverter | 7 | 6.80 | -0.20 |
| `sky130_fd_sc_hd__a21bo_1` | 3 | 8 | 2 | two gates + nand2/nor2 | 8 | 5.90 | -2.10 |
| `sky130_fd_sc_hd__a21boi_1` | 3 | 8 | 2 | one complex gate | 6 | 5.90 | -0.10 |
| `sky130_fd_sc_hd__a21o_1` | 3 | 8 | 2 | complex gate + output inverter | 6 | 5.90 | -0.10 |
| `sky130_fd_sc_hd__a22o_1` | 4 | 10 | 2 | complex gate + output inverter | 7 | 6.80 | -0.20 |
| `sky130_fd_sc_hd__a2bb2o_1` | 4 | 12 | 2 | one complex gate | 8 | 7.70 | -0.30 |
| `sky130_fd_sc_hd__a2bb2oi_1` | 4 | 12 | 2 | one complex gate | 7 | 7.70 | +0.70 |
| `sky130_fd_sc_hd__a31o_1` | 4 | 10 | 2 | complex gate + output inverter | 7 | 6.80 | -0.20 |
| `sky130_fd_sc_hd__and2_1` | 2 | 6 | 2 | complex gate + output inverter | 5 | 5.00 | -0.00 |
| `sky130_fd_sc_hd__and2b_1` | 2 | 6 | 2 | one complex gate | 6 | 5.00 | -1.00 |
| `sky130_fd_sc_hd__and3_1` | 3 | 8 | 2 | complex gate + output inverter | 5 | 5.90 | +0.90 |
| `sky130_fd_sc_hd__and3b_1` | 3 | 8 | 2 | two gates + nand2/nor2 | 7 | 5.90 | -1.10 |
| `sky130_fd_sc_hd__and4_1` | 4 | 12 | 2 | two gates + nand2/nor2 | 7 | 7.70 | +0.70 |
| `sky130_fd_sc_hd__and4b_1` | 4 | 10 | 2 | two gates + nand2/nor2 | 8 | 6.80 | -1.20 |
| `sky130_fd_sc_hd__and4bb_1` | 4 | 12 | 3 | two gates + nand2/nor2 | 10 | 8.01 | -1.99 |
| `sky130_fd_sc_hd__buf_1` | 1 | 4 | 2 | one complex gate | 3 | 4.10 | +1.10 |
| `sky130_fd_sc_hd__maj3_1` | 3 | 12 | 2 | complex gate + output inverter | 8 | 7.70 | -0.30 |
| `sky130_fd_sc_hd__mux2_1` | 3 | 12 | 3 | complex gate + output inverter | 9 | 8.01 | -0.99 |
| `sky130_fd_sc_hd__mux2i_1` | 3 | 10 | 2 | one complex gate | 8 | 6.80 | -1.20 |
| `sky130_fd_sc_hd__nand2b_1` | 2 | 6 | 2 | one complex gate | 5 | 5.00 | -0.00 |
| `sky130_fd_sc_hd__nand3b_1` | 3 | 8 | 2 | one complex gate | 6 | 5.90 | -0.10 |
| `sky130_fd_sc_hd__nand4_1` | 4 | 14 | 3 | two gates + nand2/nor2 + output inverter | 5 | 8.91 | +3.91 |
| `sky130_fd_sc_hd__nand4b_1` | 4 | 12 | 3 | two gates + nand2/nor2 + output inverter | 7 | 8.01 | +1.01 |
| `sky130_fd_sc_hd__nand4bb_1` | 4 | 12 | 3 | two gates + nand2/nor2 | 9 | 8.01 | -0.99 |
| `sky130_fd_sc_hd__nor2b_1` | 2 | 6 | 2 | one complex gate | 5 | 5.00 | -0.00 |
| `sky130_fd_sc_hd__nor3b_1` | 3 | 8 | 2 | one complex gate | 6 | 5.90 | -0.10 |
| `sky130_fd_sc_hd__nor4_1` | 4 | 14 | 3 | two-level + output inverter | 5 | 8.91 | +3.91 |
| `sky130_fd_sc_hd__nor4b_1` | 4 | 12 | 3 | two gates + nand2/nor2 + output inverter | 7 | 8.01 | +1.01 |
| `sky130_fd_sc_hd__nor4bb_1` | 4 | 12 | 3 | two gates + nand2/nor2 | 8 | 8.01 | +0.01 |
| `sky130_fd_sc_hd__o211a_1` | 4 | 10 | 2 | complex gate + output inverter | 8 | 6.80 | -1.20 |
| `sky130_fd_sc_hd__o21a_1` | 3 | 8 | 2 | complex gate + output inverter | 6 | 5.90 | -0.10 |
| `sky130_fd_sc_hd__o21ba_1` | 3 | 8 | 2 | two gates + nand2/nor2 | 8 | 5.90 | -2.10 |
| `sky130_fd_sc_hd__o21bai_1` | 3 | 8 | 2 | one complex gate | 6 | 5.90 | -0.10 |
| `sky130_fd_sc_hd__o22a_1` | 4 | 10 | 2 | complex gate + output inverter | 7 | 6.80 | -0.20 |
| `sky130_fd_sc_hd__o2bb2a_1` | 4 | 12 | 2 | one complex gate | 8 | 7.70 | -0.30 |
| `sky130_fd_sc_hd__o2bb2ai_1` | 4 | 12 | 2 | one complex gate | 7 | 7.70 | +0.70 |
| `sky130_fd_sc_hd__o31a_1` | 4 | 10 | 2 | complex gate + output inverter | 7 | 6.80 | -0.20 |
| `sky130_fd_sc_hd__or2_1` | 2 | 6 | 2 | complex gate + output inverter | 5 | 5.00 | -0.00 |
| `sky130_fd_sc_hd__or2b_1` | 2 | 6 | 2 | one complex gate | 6 | 5.00 | -1.00 |
| `sky130_fd_sc_hd__or3_1` | 3 | 8 | 2 | complex gate + output inverter | 5 | 5.90 | +0.90 |
| `sky130_fd_sc_hd__or3b_1` | 3 | 8 | 2 | two gates + nand2/nor2 | 7 | 5.90 | -1.10 |
| `sky130_fd_sc_hd__or4_1` | 4 | 12 | 2 | two-level | 6 | 7.70 | +1.70 |
| `sky130_fd_sc_hd__or4b_1` | 4 | 10 | 2 | two gates + nand2/nor2 | 8 | 6.80 | -1.20 |
| `sky130_fd_sc_hd__or4bb_1` | 4 | 12 | 3 | two gates + nand2/nor2 | 9 | 8.01 | -0.99 |
| `sky130_fd_sc_hd__xnor2_1` | 2 | 12 | 2 | one complex gate | 7 | 7.70 | +0.70 |
| `sky130_fd_sc_hd__xnor3_1` | 3 | 34 | 3 | two-level | 18 | 17.93 | -0.07 |
| `sky130_fd_sc_hd__xor2_1` | 2 | 12 | 2 | one complex gate | 7 | 7.70 | +0.70 |
| `sky130_fd_sc_hd__xor3_1` | 3 | 34 | 3 | two-level | 19 | 17.93 | -1.07 |
