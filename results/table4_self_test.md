# Redundancy Checker Self-Test against Handout Table 4

## 1. Table 4 Reference Count Verification

- **All 264 single-output combinational cells in `hd_usable.lib` fed as candidates**: **100% classified as `Exists`**.
- **Total non-degenerate 4-input Boolean functions**: $64,594$, partitioned into **3,904 P-classes** under $S_4$ input permutations.

| Group | Reference Count | Implemented Tool Count | Status |
|---|---|---|---|
| Exists | 24 | 24 | MATCH |
| Exists with an inverter | 20 | 20 | MATCH |
| Contained | 38 | 38 | MATCH |
| New | 3,822 | 3,822 | MATCH |
| New, and one static CMOS stage | 9 | 9 | MATCH |
| New, one stage, <= 3 in series and <= 12 tx | 5 | 5 | MATCH |
| One stage with every input used once (<= 3 in series) | 8 (6 Exist, 2 Contained) | 8 (6 Exist, 2 Contained) | MATCH |

## 2. The 9 Single-Stage Static CMOS `New` Classes

| P-Class | Synthesized 1-Stage Expression | Literals | Transistors | NMOS Series | PMOS Series | <= 3 Series & <= 12 Tx |
|---|---|---|---|---|---|---|
| `0x0017` | `!(A|((B&C)|(D&(B|C))))` | 6 | 12 | 2 | 4 | **NO** |
| `0x0117` | `!((A&B)|((C&D)|((A|B)&(C|D))))` | 8 | 16 | 2 | 4 | **NO** |
| `0x011F` | `!((C|D)&(A|(B|(C&D))))` | 6 | 12 | 3 | 3 | **YES** |
| `0x013F` | `!((A|(B|C))&(D|(B&C)))` | 6 | 12 | 3 | 3 | **YES** |
| `0x017F` | `!((A&(B&C))|(D&(A|(B|C))))` | 7 | 14 | 3 | 4 | **NO** |
| `0x037F` | `!((A&(B&C))|(D&(B|C)))` | 6 | 12 | 3 | 3 | **YES** |
| `0x077F` | `!((C|D)&((A&B)|(C&D)))` | 6 | 12 | 3 | 2 | **YES** |
| `0x177F` | `!((A|B)&((C|D)&((A&B)|(C&D))))` | 8 | 16 | 4 | 2 | **NO** |
| `0x17FF` | `!(D&((A&B)|(C&(A|B))))` | 6 | 12 | 3 | 3 | **YES** |

## 3. The 8 Simplest Single-Stage Cells (Every Input Used Once, <= 3 in Series)

| P-Class | Synthesized Read-Once Expression | NMOS Series | PMOS Series | Redundancy Class | Matched HD Cell |
|---|---|---|---|---|---|
| `0x0007` | `!(C|(D|(A&B)))` | 2 | 3 | **Exists** | `sky130_fd_sc_hd__a211oi_1` |
| `0x001F` | `!(D|(C&(A|B)))` | 2 | 3 | **Contained** | `sky130_fd_sc_hd__a221oi_1` |
| `0x007F` | `!(D|(A&(B&C)))` | 3 | 2 | **Exists** | `sky130_fd_sc_hd__a31oi_1` |
| `0x01FF` | `!(D&(A|(B|C)))` | 2 | 3 | **Exists** | `sky130_fd_sc_hd__o31ai_1` |
| `0x0357` | `!((A|D)&(B|C))` | 2 | 2 | **Exists** | `sky130_fd_sc_hd__o22ai_1` |
| `0x0777` | `!((A&B)|(C&D))` | 2 | 2 | **Exists** | `sky130_fd_sc_hd__a22oi_1` |
| `0x07FF` | `!(D&(C|(A&B)))` | 3 | 2 | **Contained** | `sky130_fd_sc_hd__a32oi_1` |
| `0x1FFF` | `!(C&(D&(A|B)))` | 3 | 2 | **Exists** | `sky130_fd_sc_hd__o211ai_1` |
