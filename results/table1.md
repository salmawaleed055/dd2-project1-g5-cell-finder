# Table 1: Area of Required Designs on Usable vs Reduced HD Library ($\mu\text{m}^2$)

Synthesized with Yosys + ABC using the exact commands of Section 2 (`given/scripts/map.sh`):
- **Script A**: `+strash;dch,-f;amap;topo` (ABC's area-oriented structural mapper)
- **Script B**: `+strash;&get,-n;&dch,-f;&nf,-R,1000;&put` (ABC's functional cut mapper with relaxed delay target)

## 1. Reproduced Table 1 (Measured with Yosys 0.70 / OSS CAD Suite)

| Design | Script A, usable HD | Script A, reduced HD | Diff A (%) | Script B, usable HD | Script B, reduced HD | Diff B (%) |
|---|---|---|---|---|---|---|
| `cpu8` | 4,206.5 | 4,206.5 | +0.00% | 4,265.3 | 4,259.1 | -0.15% |
| `dsp8` | 5,843.1 | 5,846.9 | +0.06% | 6,040.8 | 6,040.8 | +0.00% |
| `arlet6502` | 9,303.9 | 9,310.2 | +0.07% | 9,559.2 | 9,572.9 | +0.14% |
| `uart_apb` | 12,655.9 | 12,655.9 | +0.00% | 13,057.5 | 13,057.5 | +0.00% |
| `risc8` | 28,168.3 | 28,170.8 | +0.01% | 28,122.0 | 28,133.2 | +0.04% |
| `fir10` | 25,449.4 | 25,449.4 | +0.00% | 29,015.3 | 29,015.3 | +0.00% |

## 2. Handout Table 1 Reference (Yosys 0.33)

| Design | Ref Script A, usable | Ref Script A, reduced | Ref Script B, usable | Ref Script B, reduced |
|---|---|---|---|---|
| `cpu8` | 4,186.5 | 4,186.5 | 4,367.9 | 4,359.2 |
| `dsp8` | 5,928.2 | 5,928.2 | 6,217.2 | 6,214.7 |
| `arlet6502` | 9,654.3 | 9,701.8 | 9,954.5 | 9,995.8 |
| `uart_apb` | 12,948.7 | 12,948.7 | 13,180.1 | 13,180.1 |
| `risc8` | 28,265.9 | 28,263.4 | 27,501.4 | 27,511.4 |
| `fir10` | 25,968.7 | 25,968.7 | 29,055.4 | 29,055.4 |

> [!NOTE]
> Across all six required designs, the reduced HD library (`hd_reduced.lib`, 189 cells) costs at most **0.14%** in area compared to the usable HD library (`hd_usable.lib`, 307 cells), well within the handout's $\le 0.5\%$ threshold. This confirms that drive reduction does not penalize baseline area and establishes `hd_reduced.lib` as a clean baseline.
