#!/bin/bash
# Step 1 of the Option 2 handout: write each required design as an AIG.
# build/aig/<name>.aag      ASCII AIGER after synth (for our own parser)
# build/aig/<name>.aig      binary AIGER after synth (for ABC)
# build/aig/<name>_abc.aig  binary AIGER after ABC restructuring (comb; strash; dch; strash)
set -u
cd "$(dirname "$0")/.."
mkdir -p build/aig results
CSV=results/aig_sizes.csv
echo "design,flipflops,and_nodes_raw,and_nodes_after_abc" > $CSV

andcount() {  # file.aig -> number of AND nodes, as ABC counts them
  yosys-abc -c "read_aiger $1; comb; strash; print_stats" 2>&1 \
    | grep -oE 'and *= *[0-9]+' | grep -oE '[0-9]+' | tail -1
}

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
    write_aiger build/aig/$name.aig
  " 2> build/aig/$name.warn
  yosys-abc -c "read_aiger build/aig/$name.aig; comb; strash; dch; strash; write_aiger -s build/aig/${name}_abc.aig" \
    > build/aig/$name.abc.log 2>&1
  ff=$(grep -oE '[0-9]+' build/aig/$name.ff.txt | tail -1)
  raw=$(head -1 build/aig/$name.aag | awk '{print $6}')
  abc=$(andcount build/aig/${name}_abc.aig)
  echo "$name,$ff,$raw,$abc" | tee -a $CSV
done
