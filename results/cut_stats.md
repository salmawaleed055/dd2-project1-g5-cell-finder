# Cut and Class Statistics Before and After ABC Restructuring

Section 9.2 Deliverable: AIG size, number of cuts, and number of equivalence classes before and after ABC restructuring (`strash; dch; strash`).
Every enumerated cut across all 6 designs (186,065 original cuts and 149,061 restructured cuts) passed 100% exhaustive simulation verification across all $2^k$ input combinations.

## 1. All K-Feasible Cuts ($1 \le k \le 4$)

| Design | Orig ANDs | Orig Cuts | Orig P-Classes | Orig P+N_out | Orig NPN | After ABC ANDs | After ABC Cuts | After ABC P-Classes | After ABC P+N_out | After ABC NPN |
|---|---|---|---|---|---|---|---|---|---|---|
| `cpu8` | 932 | 7,021 | 223 | 181 | 58 | 849 | 6,052 | 199 | 168 | 52 |
| `dsp8` | 1,661 | 13,261 | 257 | 198 | 51 | 1,293 | 10,733 | 228 | 186 | 52 |
| `arlet6502` | 2,464 | 20,184 | 295 | 199 | 54 | 2,091 | 16,725 | 262 | 188 | 49 |
| `uart_apb` | 3,550 | 18,734 | 197 | 151 | 39 | 1,770 | 11,133 | 127 | 103 | 29 |
| `risc8` | 5,485 | 42,979 | 268 | 189 | 55 | 4,876 | 37,010 | 234 | 168 | 42 |
| `fir10` | 8,173 | 83,886 | 262 | 209 | 59 | 6,390 | 67,408 | 245 | 198 | 57 |
| **Total / Union** | **22,265** | **186,065** | **499** | **328** | **83** | **17,269** | **149,061** | **451** | **303** | **78** |

## 2. Strict 4-Input Non-Degenerate Cuts ($k = 4$, depending on all 4 inputs)

In the universe of $2^{16} = 65,536$ four-variable truth tables, $64,594$ depend on all 4 inputs, partitioning into **3,904 P-classes** (input permutations), **1,988 P+N_out classes** (input permutations + output inversion, Section 4 Step 3), and **208 NPN classes**.

| Design | Orig 4-Input Cuts | Orig 4-Input P-Classes | Orig 4-Input P+N_out | Orig 4-Input NPN | After ABC 4-Input Cuts | After ABC 4-Input P-Classes | After ABC 4-Input P+N_out | After ABC 4-Input NPN |
|---|---|---|---|---|---|---|---|---|
| `cpu8` | 3,382 | 179 | 149 | 46 | 2,860 | 160 | 140 | 41 |
| `dsp8` | 6,591 | 214 | 171 | 41 | 5,411 | 187 | 158 | 41 |
| `arlet6502` | 10,412 | 243 | 169 | 43 | 8,556 | 221 | 160 | 38 |
| `uart_apb` | 7,634 | 157 | 125 | 28 | 4,603 | 102 | 83 | 20 |
| `risc8` | 20,735 | 217 | 159 | 43 | 17,803 | 190 | 141 | 31 |
| `fir10` | 45,914 | 220 | 177 | 47 | 37,449 | 209 | 170 | 46 |
| **Total / Union** | **94,668** | **434** | **293** | **69** | **76,682** | **393** | **270** | **67** |
