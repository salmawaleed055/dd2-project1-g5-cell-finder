# Table 1: Area of Required Designs on Usable vs Reduced HD Library ($\mu\text{m}^2$)

Synthesized with Yosys + ABC using the exact commands of Section 2 (`given/scripts/map.sh`):
- **Script A**: `+strash;dch,-f;amap;topo` (ABC's area-oriented structural mapper)
- **Script B**: `+strash;&get,-n;&dch,-f;&nf,-R,1000;&put` (ABC's functional cut mapper with relaxed delay target)

## 1. Reproduced Table 1 (Measured with Yosys 0.70 / OSS CAD Suite)

| Design | Script A, usable HD | Script A, reduced HD | Diff A (%) | Script B, usable HD | Script B, reduced HD | Diff B (%) |
|---|---|---|---|---|---|---|
| `cpu8` | 4,195.3 | 4,221.5 | +0.63% | 4,265.3 | 4,259.1 | -0.15% |
| `dsp8` | 5,723.0 | 5,795.6 | +1.27% | 6,040.8 | 6,040.8 | +0.00% |
| `arlet6502` | 9,308.9 | 9,330.2 | +0.23% | 9,559.2 | 9,572.9 | +0.14% |
| `uart_apb` | 12,687.2 | 12,719.7 | +0.26% | 13,057.5 | 13,057.5 | +0.00% |
| `risc8` | 27,864.2 | 28,147.0 | +1.01% | 28,122.0 | 28,133.2 | +0.04% |
| `fir10` | 25,355.6 | 26,494.2 | +4.49% | 29,015.3 | 29,015.3 | +0.00% |

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
> Largest difference between the reduced (189 cells) and usable (307 cells) library: **4.49%** (handout threshold: 0.5%). Above the threshold: cpu8 A, dsp8 A, risc8 A, fir10 A.
