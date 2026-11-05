# Table 5 (first version, estimated areas)

Baseline: `given/hd_reduced.lib` (189 cells). Extended: the baseline plus 10 new cells with estimated areas (`libs/hd_extended_est.lib`). Commands of section 2; equivalence by ABC `dsec` of every mapped netlist against the design before ABC (logs in `results/logs/`).

| Design | Script | Baseline (um2) | With new cells (um2) | Reduction | New-cell instances | Equivalence |
|---|---|---|---|---|---|---|
| cpu8 | A | 4,206.5 | 4,199.0 | +0.18% | 1 | pass |
| cpu8 | B | 4,259.1 | 4,256.6 | +0.06% | 5 | pass |
| dsp8 | A | 5,846.9 | 5,815.6 | +0.54% | 10 | pass |
| dsp8 | B | 6,040.8 | 5,997.0 | +0.72% | 26 | pass |
| arlet6502 | A | 9,310.2 | 9,326.4 | -0.17% | 12 | pass |
| arlet6502 | B | 9,572.9 | 9,561.7 | +0.12% | 11 | pass |
| uart_apb | A | 12,655.9 | 12,640.9 | +0.12% | 4 | pass |
| uart_apb | B | 13,057.5 | 13,057.5 | +0.00% | 4 | pass |
| risc8 | A | 28,170.8 | 28,150.7 | +0.07% | 17 | pass |
| risc8 | B | 28,133.2 | 28,277.1 | -0.51% | 64 | pass |
| fir10 | A | 25,449.4 | 25,428.1 | +0.08% | 12 | pass |
| fir10 | B | 29,015.3 | 28,578.7 | +1.50% | 212 | pass |

## Best of both scripts

| Design | Baseline best (um2) | With new cells best (um2) | Reduction |
|---|---|---|---|
| cpu8 | 4,206.5 | 4,199.0 | +0.18% |
| dsp8 | 5,846.9 | 5,815.6 | +0.53% |
| arlet6502 | 9,310.2 | 9,326.4 | -0.17% |
| uart_apb | 12,655.9 | 12,640.9 | +0.12% |
| risc8 | 28,133.2 | 28,150.7 | -0.06% |
| fir10 | 25,449.4 | 25,428.1 | +0.08% |
| **Total (required designs)** | **85,602.1** | **85,560.8** | **+0.05%** |

## New cells in the extended library

| Cell | Truth table | Function | Est. area (um2) | Instances (A) | Instances (B) |
|---|---|---|---|---|---|
| `dd2_g5__f011f_1` | `0x011F` | `!((C&D)|((A|B)&(C|D)))` | 10.0096 | 0 | 15 |
| `dd2_g5__f001f_1` | `0x001F` | `!(D|(C&(A|B)))` | 7.5072 | 50 | 101 |
| `dd2_g5__f000b_1` | `0x000B` | `!(C|(D|(!A&B)))` | 8.7584 | 6 | 175 |
| `dd2_g5__f82eb_1` | `0x82EB` | `!((!A&D)|((!A|D)&((B|C)&(!B|!C))))` | 16.2656 | 0 | 3 |
| `dd2_g5__f002b_1` | `0x002B` | `!(D|((!A|B)&(C|(!A&B))))` | 11.2608 | 0 | 0 |
| `dd2_g5__f80a8_1` | `0x80A8` | `!(!(A&((B&C)|(!D&(B|C)))))` | 12.5120 | 0 | 0 |
| `dd2_g5__fa8fe_1` | `0xA8FE` | `!(!((A&!D)|((A|!D)&(B|C))))` | 12.5120 | 0 | 14 |
| `dd2_g5__f0ee0_1` | `0x0EE0` | `!(!((A|B)&((C|D)&(!C|!D))))` | 13.7632 | 0 | 0 |
| `dd2_g5__f00eb_1` | `0x00EB` | `!(D|(!A&((B|C)&(!B|!C))))` | 13.7632 | 0 | 7 |
| `dd2_g5__f28be_1` | `0x28BE` | `!((!A&D)|((!A|D)&((B&C)|(!B&!C))))` | 16.2656 | 0 | 7 |
