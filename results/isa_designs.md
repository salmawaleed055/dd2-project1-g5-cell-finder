# risc8, pic16 and p16c5x: one instruction set, the same new cells?

The three designs implement the PIC16C5x instruction set. They are mapped with the commands of section 2 on the baseline and on the final library (dsec on every mapping), and the cuts of their restructured AIGs are counted for each final cell's class.

| Design | Library | Script | Area (um2) | Reduction | New-cell instances | Equivalence |
|---|---|---|---|---|---|---|
| risc8 | baseline | A | 28,170.8 | +0.00% | 0 | pass |
| risc8 | baseline | B | 28,133.2 | +0.00% | 0 | pass |
| risc8 | final_est | A | 28,153.3 | +0.06% | 2 | pass |
| risc8 | final_est | B | 28,313.4 | -0.64% | 33 | pass |
| pic16 | baseline | A | 30,417.9 | +0.00% | 0 | pass |
| pic16 | baseline | B | 30,349.1 | +0.00% | 0 | pass |
| pic16 | final_est | A | 30,417.9 | +0.00% | 11 | pass |
| pic16 | final_est | B | 30,397.9 | -0.16% | 41 | pass |
| p16c5x | baseline | A | 29,285.6 | +0.00% | 0 | pass |
| p16c5x | baseline | B | 31,181.2 | +0.00% | 0 | pass |
| p16c5x | final_est | A | 29,290.6 | -0.02% | 2 | pass |
| p16c5x | final_est | B | 31,233.7 | -0.17% | 49 | pass |

## Instances of each final cell (estimated areas, scripts A + B) and cut occurrences of its class

| Cell | risc8 instances | risc8 cuts | pic16 instances | pic16 cuts | p16c5x instances | p16c5x cuts |
|---|---|---|---|---|---|---|
| `dd2_g5__f000b_1` | 29 | 315 | 41 | 346 | 41 | 597 |
| `dd2_g5__f0ee0_1` | 0 | 10 | 0 | 6 | 0 | 2 |
| `dd2_g5__f00eb_1` | 0 | 12 | 0 | 1 | 0 | 1 |
| `dd2_g5__f009f_1` | 1 | 2 | 2 | 17 | 2 | 11 |
| `dd2_g5__feee8_1` | 1 | 2 | 0 | 1 | 0 | 5 |
| `dd2_g5__f008e_1` | 0 | 3 | 1 | 1 | 1 | 5 |
| `dd2_g5__f00be_1` | 0 | 2 | 0 | 5 | 0 | 5 |
| `dd2_g5__fa888_1` | 3 | 101 | 5 | 130 | 4 | 184 |
| `dd2_g5__f006f_1` | 1 | 6 | 3 | 0 | 3 | 0 |
