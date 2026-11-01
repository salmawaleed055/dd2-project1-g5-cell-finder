"""
Compares the redundancy checker on given/hd_usable.lib and on the full HD
Liberty (Option 2 handout, section 5, asks for all drives and all kinds).

The flow classifies against hd_usable.lib, which every machine has through
`make setup`.  This script shows that the full Liberty gives the same class
for every 4-input function, so the choice does not change any result.

    PDK_ROOT=~/.ciel python3 src/check_full_hd.py
"""

import os
import sys
from typing import Set

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from src.classification import depends_on_all_4, get_p_class
from src.redundancy import RedundancyChecker, parse_hd_library

USABLE_LIB = "given/hd_usable.lib"
FULL_LIB_REL = "sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"
REPORT = "results/full_hd_check.md"


def main() -> int:
    full_lib = os.path.join(os.environ.get("PDK_ROOT", os.path.expanduser("~/.ciel")), FULL_LIB_REL)
    usable_cells = parse_hd_library(USABLE_LIB)
    full_cells = parse_hd_library(full_lib)
    usable, full = RedundancyChecker(USABLE_LIB), RedundancyChecker(full_lib)

    not_exists = [c["name"] for c in full_cells if full.classify_hd_cell_dict(c) != "Exists"]
    classes: Set[int] = {get_p_class(tt)[0] for tt in range(1 << 16) if depends_on_all_4(tt)}
    changed = [rep for rep in sorted(classes) if usable.classify(rep) != full.classify(rep)]

    with open(REPORT, 'w', encoding='utf-8') as f:
        f.write("# Redundancy Check: hd_usable.lib against the Full HD Liberty\n\n")
        f.write("| Measure | Value |\n|---|---|\n")
        f.write(f"| Single-output combinational cells in `hd_usable.lib` | {len(usable_cells)} |\n")
        f.write(f"| Single-output combinational cells in the full Liberty | {len(full_cells)} |\n")
        f.write(f"| Full-Liberty cells not classified as Exists | {len(not_exists)} |\n")
        f.write(f"| 4-input classes compared | {len(classes):,} |\n")
        f.write(f"| Classes whose Table 3 class changes | {len(changed)} |\n")
    print(f"{len(classes)} classes compared, {len(changed)} change; written to {REPORT}")
    return 0 if not changed and not not_exists else 1


if __name__ == "__main__":
    sys.exit(main())
