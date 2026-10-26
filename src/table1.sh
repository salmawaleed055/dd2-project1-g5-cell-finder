#!/bin/bash
# Reproduce Table 1 of the Option 2 handout: 6 designs x {usable,reduced} x {A,B}.
# Writes the raw lines to results/table1_raw.txt and a table to results/table1.csv.
set -u
cd "$(dirname "$0")/.."
mkdir -p results
OUT_RAW=results/table1_raw.txt
OUT_CSV=results/table1.csv
: > "$OUT_RAW"
echo "design,script_A_usable,script_A_reduced,script_B_usable,script_B_reduced" > "$OUT_CSV"

DESIGNS="cpu8:cpu8 dsp8:dsp8 arlet6502:cpu uart_apb:uart_apb_master risc8:cpu fir10:fir10"

area() {  # design top lib script
  given/scripts/map.sh "given/designs/$1.v" "$2" "$3" "$4" | tee -a "$OUT_RAW" \
    | grep "Chip area" | awk '{print $NF}'
}

for d in $DESIGNS; do
  name=${d%%:*}; top=${d##*:}
  echo "== $name ($top)" >> "$OUT_RAW"
  aU=$(area "$name" "$top" given/hd_usable.lib  A)
  aR=$(area "$name" "$top" given/hd_reduced.lib A)
  bU=$(area "$name" "$top" given/hd_usable.lib  B)
  bR=$(area "$name" "$top" given/hd_reduced.lib B)
  echo "$name,$aU,$aR,$bU,$bR" | tee -a "$OUT_CSV"
done
yosys -V > results/table1_versions.txt
