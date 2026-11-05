# Table 5 (final set, estimated areas)

Baseline: `given/hd_reduced.lib` (189 cells). Extended: the baseline plus 9 new cells of the final set with estimated areas (`libs/hd_extended_final_est.lib`). Commands of section 2; equivalence by ABC `dsec` of every mapped netlist against the design before ABC (logs in `results/logs/`).

| Design | Script | Baseline (um2) | With new cells (um2) | Reduction | New-cell instances | Equivalence |
|---|---|---|---|---|---|---|
| cpu8 | A | 4,206.5 | 4,205.3 | +0.03% | 0 | pass |
| cpu8 | B | 4,259.1 | 4,244.1 | +0.35% | 0 | pass |
| dsp8 | A | 5,846.9 | 5,846.9 | +0.00% | 1 | pass |
| dsp8 | B | 6,040.8 | 6,065.8 | -0.41% | 6 | pass |
| arlet6502 | A | 9,310.2 | 9,301.4 | +0.09% | 1 | pass |
| arlet6502 | B | 9,572.9 | 9,549.2 | +0.25% | 18 | pass |
| uart_apb | A | 12,655.9 | 12,648.4 | +0.06% | 2 | pass |
| uart_apb | B | 13,057.5 | 13,063.8 | -0.05% | 1 | pass |
| risc8 | A | 28,170.8 | 28,153.3 | +0.06% | 2 | pass |
| risc8 | B | 28,133.2 | 28,313.4 | -0.64% | 33 | pass |
| fir10 | A | 25,449.4 | 25,380.6 | +0.27% | 24 | pass |
| fir10 | B | 29,015.3 | 28,543.6 | +1.63% | 171 | pass |

## Best of both scripts

| Design | Baseline best (um2) | With new cells best (um2) | Reduction |
|---|---|---|---|
| cpu8 | 4,206.5 | 4,205.3 | +0.03% |
| dsp8 | 5,846.9 | 5,846.9 | +0.00% |
| arlet6502 | 9,310.2 | 9,301.4 | +0.09% |
| uart_apb | 12,655.9 | 12,648.4 | +0.06% |
| risc8 | 28,133.2 | 28,153.3 | -0.07% |
| fir10 | 25,449.4 | 25,380.6 | +0.27% |
| **Total (required designs)** | **85,602.1** | **85,535.8** | **+0.08%** |

## New cells in the extended library

| Cell | Truth table | Function | Est. area (um2) | Instances (A) | Instances (B) |
|---|---|---|---|---|---|
| `dd2_g5__f000b_1` | `0x000B` | `!(C|(D|(!A&B)))` | 8.7584 | 2 | 191 |
| `dd2_g5__f0ee0_1` | `0x0EE0` | `!(!((A|B)&((C|D)&(!C|!D))))` | 13.7632 | 0 | 0 |
| `dd2_g5__f00eb_1` | `0x00EB` | `!(D|(!A&((B|C)&(!B|!C))))` | 13.7632 | 0 | 0 |
| `dd2_g5__f009f_1` | `0x009F` | `!(D|(C&((A|B)&(!A|!B))))` | 12.5120 | 9 | 5 |
| `dd2_g5__feee8_1` | `0xEEE8` | `!(!((A&B)|((A|B)&(C|D))))` | 11.2608 | 0 | 11 |
| `dd2_g5__f008e_1` | `0x008E` | `!(D|((!A|!B)&(C|(!A&!B))))` | 12.5120 | 0 | 0 |
| `dd2_g5__f00be_1` | `0x00BE` | `!(D|(!A&((B&C)|(!B&!C))))` | 13.7632 | 0 | 0 |
| `dd2_g5__fa888_1` | `0xA888` | `!(!(A&(B|(C&D))))` | 8.7584 | 17 | 9 |
| `dd2_g5__f006f_1` | `0x006F` | `!(D|(C&((A&B)|(!A&!B))))` | 12.5120 | 2 | 13 |
