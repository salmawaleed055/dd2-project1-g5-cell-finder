#!/bin/bash
# Step 1 of the Option 2 handout: write each required design as an AIG.
# Outputs: build/aig/<name>.aag (after synth) and build/aig/<name>_abc.aag (after ABC strash;dch).
set -u
cd "$(dirname "$0")/.."
mkdir -p build/aig results
CSV=results/aig_sizes.csv
echo "design,flipflops,and_nodes_raw,and_nodes_after_abc" > $CSV

for d in cpu8:cpu8 dsp8:dsp8 arlet6502:cpu uart_apb:uart_apb_master risc8:cpu fir10:fir10; do
  name=${d%%:*}; top=${d##*:}
  yosys -q -l build/aig/$name.log -p "
    read_verilog given/designs/$name.v
    synth -flatten -top $top
    async2sync
    dffunmap
    tee -o build/aig/$name.ff.txt select -count t:\$_DFF_*
    aigmap
    write_aiger -ascii build/aig/$name.aag
  "
  yosys-abc -q -c "read_aiger build/aig/$name.aag; strash; dch; strash; write_aiger -s build/aig/${name}_abc.aig" 2>/dev/null
  ff=$(grep -oE '[0-9]+' build/aig/$name.ff.txt | tail -1)
  raw=$(head -1 build/aig/$name.aag | awk '{print $6}')
  abc=$(yosys-abc -q -c "read_aiger build/aig/${name}_abc.aig; print_stats" 2>/dev/null | grep -oE 'and *= *[0-9]+' | grep -oE '[0-9]+')
  echo "$name,$ff,$raw,$abc" | tee -a $CSV
done
