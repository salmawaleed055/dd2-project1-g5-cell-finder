# The 30% experiment (handout section 4, step 12)

The new cell with the most instances in the final mappings is made 30% smaller in the Liberty file, and every required design is remapped with both scripts (dsec on every mapping). ABC sees only the numbers in the Liberty, so this shows how much the result depends on the area estimate.

## Estimated areas: `dd2_g5__f000b_1` at 6.1309 um2 (`libs/hd_extended_final_est_30pct.lib`)

| Design | Script | Area (um2) | With the cell 30% smaller (um2) | Change | Instances | Instances (30% smaller) | Equivalence |
|---|---|---|---|---|---|---|---|
| cpu8 | A | 4,205.3 | 4,193.9 | -0.27% | 0 | 11 | pass |
| cpu8 | B | 4,244.1 | 4,233.9 | -0.24% | 0 | 11 | pass |
| dsp8 | A | 5,846.9 | 5,684.5 | -2.78% | 0 | 78 | pass |
| dsp8 | B | 6,065.8 | 5,973.5 | -1.52% | 1 | 58 | pass |
| arlet6502 | A | 9,301.4 | 9,279.9 | -0.23% | 1 | 62 | pass |
| arlet6502 | B | 9,549.2 | 9,524.6 | -0.26% | 1 | 36 | pass |
| uart_apb | A | 12,648.4 | 12,653.4 | +0.04% | 1 | 30 | pass |
| uart_apb | B | 13,063.8 | 13,067.3 | +0.03% | 0 | 2 | pass |
| risc8 | A | 28,153.3 | 28,109.8 | -0.15% | 0 | 157 | pass |
| risc8 | B | 28,313.4 | 27,851.1 | -1.63% | 29 | 375 | pass |
| fir10 | A | 25,380.6 | 25,341.3 | -0.15% | 0 | 34 | pass |
| fir10 | B | 28,543.6 | 28,110.2 | -1.52% | 160 | 174 | pass |

Best-of-both total: baseline 85,602.1 um2; final set 85,535.8 um2 (+0.08%); with `dd2_g5__f000b_1` 30% smaller 85,004.0 um2 (+0.70%).

