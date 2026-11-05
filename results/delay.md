# Worst delay from OpenSTA

Data arrival time of the worst max-delay path of every mapped netlist (`src/sta.py` gives the constraints; logs in `build/sta/`). New cells with estimated areas carry placeholder scalar timing, so their delays are only indicative.

| Design | Library | Script | Area (um2) | Worst arrival (ns) |
|---|---|---|---|---|
| cpu8 | baseline | A | 4,206.5 | 4.0431 |
| cpu8 | baseline | B | 4,259.1 | 4.3511 |
| cpu8 | final_est | A | 4,205.3 | 4.3096 |
| cpu8 | final_est | B | 4,244.1 | 4.6265 |
| dsp8 | baseline | A | 5,846.9 | 5.3211 |
| dsp8 | baseline | B | 6,040.8 | 6.1952 |
| dsp8 | final_est | A | 5,846.9 | 5.3211 |
| dsp8 | final_est | B | 6,065.8 | 5.6683 |
| arlet6502 | baseline | A | 9,310.2 | 6.4867 |
| arlet6502 | baseline | B | 9,572.9 | 7.1697 |
| arlet6502 | final_est | A | 9,301.4 | 6.4664 |
| arlet6502 | final_est | B | 9,549.2 | 7.0647 |
| uart_apb | baseline | A | 12,655.9 | 5.584 |
| uart_apb | baseline | B | 13,057.5 | 4.2471 |
| uart_apb | final_est | A | 12,648.4 | 5.5838 |
| uart_apb | final_est | B | 13,063.8 | 4.2192 |
| risc8 | baseline | A | 28,170.8 | 23.0924 |
| risc8 | baseline | B | 28,133.2 | 24.1833 |
| risc8 | final_est | A | 28,153.3 | 23.1196 |
| risc8 | final_est | B | 28,313.4 | 22.2497 |
| fir10 | baseline | A | 25,449.4 | 6.6718 |
| fir10 | baseline | B | 29,015.3 | 7.6561 |
| fir10 | final_est | A | 25,380.6 | 6.8451 |
| fir10 | final_est | B | 28,543.6 | 7.1472 |

## Best-of-both mapping of each design

| Design | Library | Script chosen (smaller area) | Area (um2) | Worst arrival (ns) |
|---|---|---|---|---|
| cpu8 | baseline | A | 4,206.5 | 4.0431 |
| cpu8 | final_est | A | 4,205.3 | 4.3096 |
| dsp8 | baseline | A | 5,846.9 | 5.3211 |
| dsp8 | final_est | A | 5,846.9 | 5.3211 |
| arlet6502 | baseline | A | 9,310.2 | 6.4867 |
| arlet6502 | final_est | A | 9,301.4 | 6.4664 |
| uart_apb | baseline | A | 12,655.9 | 5.584 |
| uart_apb | final_est | A | 12,648.4 | 5.5838 |
| risc8 | baseline | B | 28,133.2 | 24.1833 |
| risc8 | final_est | A | 28,153.3 | 23.1196 |
| fir10 | baseline | A | 25,449.4 | 6.6718 |
| fir10 | final_est | A | 25,380.6 | 6.8451 |
