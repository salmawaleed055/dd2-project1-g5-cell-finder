# Greedy selection of the final set (handout section 4, step 10)

Candidates tried, in rank order: the 30 best-ranked of `results/candidates.csv` with a positive estimated saving. A candidate is kept only if the total best-of-both area of the six required designs drops (estimated areas; trial mappings in `build/greedy/`, log in `results/greedy_log.csv`). At most 10 cells.

- Baseline best-of-both total (`given/hd_reduced.lib`): **85,602.10 um2**
- After the final set of 9 cells: **85,535.79 um2** (+0.08%)
- Remapped with the equivalence check: 85,535.79 um2 (`results/table5_final_est.md`)
- Candidates tried: 30, kept: 9

| Trial | Cell | Rank | Occurrences | Est. area | Est. saving | Total after (um2) | Gain (um2) | Instances A | Instances B | Kept |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `dd2_g5__f011f_1` | 1 | 294 | 10.01 | 3,076.7 | 85,602.10 | +0.00 | 0 | 6 | no |
| 2 | `dd2_g5__f001f_1` | 2 | 1,177 | 7.51 | 2,972.7 | 85,605.85 | -3.75 | 48 | 90 | no |
| 3 | `dd2_g5__f000b_1` | 3 | 1,477 | 8.76 | 2,880.3 | 85,590.84 | +11.26 | 3 | 190 | **yes** |
| 4 | `dd2_g5__f82eb_1` | 4 | 254 | 16.27 | 2,827.0 | 85,590.84 | +0.00 | 0 | 7 | no |
| 5 | `dd2_g5__f002b_1` | 5 | 295 | 11.26 | 2,714.5 | 85,617.11 | -26.28 | 0 | 1 | no |
| 6 | `dd2_g5__f80a8_1` | 6 | 291 | 12.51 | 2,310.1 | 85,617.11 | -26.28 | 0 | 0 | no |
| 7 | `dd2_g5__fa8fe_1` | 7 | 284 | 12.51 | 2,244.1 | 85,590.84 | +0.00 | 0 | 14 | no |
| 8 | `dd2_g5__f0ee0_1` | 8 | 624 | 13.76 | 2,056.7 | 85,579.58 | +11.26 | 0 | 0 | **yes** |
| 9 | `dd2_g5__f00eb_1` | 9 | 407 | 13.76 | 1,691.3 | 85,555.80 | +23.77 | 0 | 1 | **yes** |
| 10 | `dd2_g5__f28be_1` | 10 | 139 | 16.27 | 1,507.3 | 85,555.80 | +0.00 | 0 | 2 | no |
| 11 | `dd2_g5__f00fe_1` | 11 | 930 | 8.76 | 1,412.7 | 85,570.82 | -15.01 | 0 | 2 | no |
| 12 | `dd2_g5__f9990_1` | 12 | 424 | 13.76 | 1,402.5 | 85,555.80 | +0.00 | 0 | 2 | no |
| 13 | `dd2_g5__f009f_1` | 13 | 307 | 12.51 | 1,365.9 | 85,552.05 | +3.75 | 7 | 19 | **yes** |
| 14 | `dd2_g5__f02ab_1` | 14 | 146 | 11.26 | 1,346.0 | 85,559.56 | -7.51 | 0 | 16 | no |
| 15 | `dd2_g5__f0009_1` | 15 | 641 | 15.01 | 1,294.6 | 85,572.07 | -20.02 | 0 | 0 | no |
| 16 | `dd2_g5__feee8_1` | 16 | 140 | 11.26 | 1,290.7 | 85,549.55 | +2.50 | 0 | 9 | **yes** |
| 17 | `dd2_g5__f00ab_1` | 17 | 630 | 8.76 | 1,290.2 | 85,594.59 | -45.04 | 71 | 17 | no |
| 18 | `dd2_g5__f008e_1` | 18 | 160 | 12.51 | 1,262.7 | 85,548.30 | +1.25 | 0 | 0 | **yes** |
| 19 | `dd2_g5__f088a_1` | 19 | 155 | 12.51 | 1,224.9 | 85,548.30 | +0.00 | 0 | 1 | no |
| 20 | `dd2_g5__f0017_1` | 20 | 109 | 10.01 | 1,143.7 | 85,554.55 | -6.26 | 0 | 1 | no |
| 21 | `dd2_g5__f00bf_1` | 21 | 1,731 | 8.76 | 1,077.6 | 85,555.80 | -7.51 | 4 | 2 | no |
| 22 | `dd2_g5__f077f_1` | 22 | 98 | 10.01 | 1,025.2 | 85,552.05 | -3.75 | 0 | 14 | no |
| 23 | `dd2_g5__fe88e_1` | 23 | 90 | 16.27 | 1,005.9 | 85,548.30 | +0.00 | 0 | 0 | no |
| 24 | `dd2_g5__fa880_1` | 24 | 108 | 11.26 | 998.0 | 85,548.30 | +0.00 | 0 | 0 | no |
| 25 | `dd2_g5__f00be_1` | 25 | 190 | 13.76 | 965.1 | 85,547.05 | +1.25 | 1 | 0 | **yes** |
| 26 | `dd2_g5__f0990_1` | 26 | 234 | 20.02 | 933.3 | 85,547.05 | +0.00 | 0 | 0 | no |
| 27 | `dd2_g5__f0006_1` | 27 | 445 | 15.01 | 908.6 | 85,562.06 | -15.01 | 0 | 0 | no |
| 28 | `dd2_g5__f0999_1` | 28 | 171 | 12.51 | 774.3 | 85,562.06 | -15.01 | 0 | 0 | no |
| 29 | `dd2_g5__fa888_1` | 29 | 924 | 8.76 | 766.7 | 85,538.29 | +8.76 | 17 | 9 | **yes** |
| 30 | `dd2_g5__f006f_1` | 30 | 163 | 12.51 | 721.5 | 85,535.79 | +2.50 | 2 | 13 | **yes** |

## Kept cells that the final mappings never use

4 of the 9 kept cells have no instance in any final mapping: `dd2_g5__f0ee0_1`, `dd2_g5__f00eb_1`, `dd2_g5__f008e_1`, `dd2_g5__f00be_1`. Their gain was measured, but it does not come from the cell: adding a cell to the Liberty changes the library ABC builds its supergates and choices from, so the mapping of the rest of the design changes too. These gains are mapping noise of the size of one or two HD cells, and a smaller set without them is expected to give a similar total.

## Frequency against saving

The most frequent candidate that did not save area is `dd2_g5__f00bf_1` (class `0x00BF`, 1,731 cut occurrences, rank 21). Added to the cells already chosen, ABC used it 4 times with script A and 2 times with script B, and the total changed by +7.51 um2. Where ABC used it, the logic around it was covered differently and the total did not drop: a cut that is frequent in the AIG is not a cut the mapper should take, because cuts overlap and the cell's area is paid per instance.
