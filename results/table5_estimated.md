# Table 5 (first version, estimated areas)

Baseline: `given/hd_reduced.lib` (189 cells). Extended: the baseline plus 10 new cells with estimated areas (`libs/hd_extended_est.lib`). Commands of section 2; equivalence by ABC `dsec` of every mapped netlist against the design before ABC (logs in `results/logs/`).

| Design | Script | Baseline (um2) | With new cells (um2) | Reduction | New-cell instances | Equivalence |
|---|---|---|---|---|---|---|
| cpu8 | A | 4,221.5 | 4,150.2 | +1.69% | 4 | pass |
| cpu8 | B | 4,259.1 | 4,247.8 | +0.26% | 2 | pass |
| dsp8 | A | 5,795.6 | 5,865.6 | -1.21% | 6 | pass |
| dsp8 | B | 6,040.8 | 6,005.8 | +0.58% | 20 | pass |
| arlet6502 | A | 9,330.2 | 9,305.2 | +0.27% | 12 | pass |
| arlet6502 | B | 9,572.9 | 9,560.4 | +0.13% | 11 | pass |
| uart_apb | A | 12,719.7 | 12,663.4 | +0.44% | 6 | pass |
| uart_apb | B | 13,057.5 | 13,057.5 | +0.00% | 4 | pass |
| risc8 | A | 28,147.0 | 27,906.8 | +0.85% | 22 | pass |
| risc8 | B | 28,133.2 | 28,282.1 | -0.53% | 60 | pass |
| fir10 | A | 26,494.2 | 26,509.2 | -0.06% | 10 | pass |
| fir10 | B | 29,015.3 | 28,587.4 | +1.48% | 205 | pass |

## Best of both scripts

| Design | Baseline best (um2) | With new cells best (um2) | Reduction |
|---|---|---|---|
| cpu8 | 4,221.5 | 4,150.2 | +1.69% |
| dsp8 | 5,795.6 | 5,865.6 | -1.21% |
| arlet6502 | 9,330.2 | 9,305.2 | +0.27% |
| uart_apb | 12,719.7 | 12,663.4 | +0.44% |
| risc8 | 28,133.2 | 27,906.8 | +0.80% |
| fir10 | 26,494.2 | 26,509.2 | -0.06% |
| **Total (required designs)** | **86,694.4** | **86,400.4** | **+0.34%** |

## New cells in the extended library

| Cell | Truth table | Function | Est. area (um2) | Instances (A) | Instances (B) |
|---|---|---|---|---|---|
| `dd2_g5__f011f_1` | `0x011F` | `!((C&D)|((A|B)&(C|D)))` | 10.0096 | 0 | 17 |
| `dd2_g5__f000b_1` | `0x000B` | `!(C|(D|(!A&B)))` | 8.7584 | 0 | 178 |
| `dd2_g5__f001f_1` | `0x001F` | `!(D|(C&(A|B)))` | 7.5072 | 59 | 88 |
| `dd2_g5__f82eb_1` | `0x82EB` | `!((!A&D)|((!A|D)&((B|C)&(!B|!C))))` | 16.2656 | 0 | 0 |
| `dd2_g5__f002b_1` | `0x002B` | `!(D|((!A|B)&(C|(!A&B))))` | 11.2608 | 0 | 1 |
| `dd2_g5__f80a8_1` | `0x80A8` | `!(!(A&((B&C)|(!D&(B|C)))))` | 12.5120 | 0 | 1 |
| `dd2_g5__f0ee0_1` | `0x0EE0` | `!(!((A|B)&((C|D)&(!C|!D))))` | 13.7632 | 0 | 0 |
| `dd2_g5__fa8fe_1` | `0xA8FE` | `!(!((A&!D)|((A|!D)&(B|C))))` | 12.5120 | 0 | 11 |
| `dd2_g5__f00eb_1` | `0x00EB` | `!(D|(!A&((B|C)&(!B|!C))))` | 13.7632 | 1 | 6 |
| `dd2_g5__f0009_1` | `0x0009` | `!(C|!(!D&((A&B)|(!A&!B))))` | 15.0144 | 0 | 0 |
