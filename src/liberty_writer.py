"""
Request writer and Liberty writer (Option 2 handout, section 4, step 8, and
section 6).

Each new cell gets
  * a request in the format of Appendix A of the overview
    (cells/requests/<cell>.json, see docs/interface/request_example.json);
  * a Liberty cell group, written inside the library group of hd_reduced.lib
    so units and templates are shared: area from the area model, pins A..D
    with direction and capacitance, output Y with its function and one timing
    arc per input.

Capacitance and timing are placeholders from logical effort (reference 6):
both mapping scripts aim at area, but Yosys's ABC needs the timing groups.
"""

import json
import os
import re
from typing import Dict, List

from src.cmos_cost import NAMES, _sop_cubes
from src.redundancy import eval_lib_expr

PIN_CAP_PF = 0.0024         # about an x1 HD input
TAU_NS = 0.025              # placeholder delay unit per stage


def tt_from_expr(expr: str) -> int:
    """16-bit truth table of a Liberty expression over A..D."""
    return sum(1 << i for i in range(16)
               if eval_lib_expr(expr, {NAMES[v]: (i >> v) & 1 for v in range(4)}))


def liberty_function(tt: int, structure: str) -> str:
    """
    Liberty function of the cell: the cost structure when it evaluates to tt
    (it is checked), otherwise the minimum sum of products.
    """
    if structure and not structure.startswith("tt_") and tt_from_expr(structure) == tt:
        return structure
    cubes = _sop_cubes(tt)
    terms = ["&".join(("" if val >> v & 1 else "!") + NAMES[v]
                      for v in range(4) if care >> v & 1) for care, val in cubes]
    expr = "|".join(f"({t})" for t in terms)
    assert tt_from_expr(expr) == tt
    return expr


def timing_sense(tt: int, v: int) -> str:
    """positive_unate, negative_unate or non_unate of the output in input v."""
    s = 1 << v
    rises = falls = False
    for i in range(16):
        if i & s:
            continue
        a, b = (tt >> i) & 1, (tt >> (i | s)) & 1
        rises |= b > a
        falls |= b < a
    if rises and falls:
        return "non_unate"
    return "positive_unate" if rises else "negative_unate"


def cell_name(rep: int) -> str:
    return f"dd2_g5__f{rep:04x}_1"


def cell_group(c: Dict) -> str:
    """Liberty text of one new cell.  c has name, tt, function, area, stages."""
    d = TAU_NS * (1 + c["stages"])
    lines = [f'  cell ("{c["name"]}") {{', f'    area : {c["area"]:.4f};']
    for p in NAMES:
        lines.append(f'    pin ("{p}") {{ direction : "input"; capacitance : {PIN_CAP_PF}; }}')
    lines += ['    pin ("Y") {', '      direction : "output";',
              f'      function : "{c["function"]}";']
    for v, p in enumerate(NAMES):
        lines += ['      timing () {', f'        related_pin : "{p}";',
                  f'        timing_sense : "{timing_sense(c["tt"], v)}";',
                  f'        cell_rise (scalar) {{ values ("{d * 1.25:.3f}"); }}',
                  f'        cell_fall (scalar) {{ values ("{d:.3f}"); }}',
                  f'        rise_transition (scalar) {{ values ("{d * 1.25:.3f}"); }}',
                  f'        fall_transition (scalar) {{ values ("{d:.3f}"); }}',
                  '      }']
    lines += ['    }', '  }']
    return "\n".join(lines)


def write_liberty(base_lib: str, cells: List[Dict], out_lib: str) -> None:
    """Writes base_lib with the new cell groups added before its final brace."""
    with open(base_lib, 'r', encoding='utf-8') as f:
        text = f.read()
    end = text.rstrip().rfind('}')
    groups = "\n".join(cell_group(c) for c in cells)
    os.makedirs(os.path.dirname(out_lib), exist_ok=True)
    with open(out_lib, 'w', encoding='utf-8') as f:
        f.write(text[:end] + "\n  /* DD2 Project 1 group 5: new cells, estimated areas */\n"
                + groups + "\n}\n")


def write_requests(cells: List[Dict], out_dir: str = "cells/requests") -> List[str]:
    """Writes one Appendix A request per cell; returns the file paths."""
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for i, c in enumerate(cells, 1):
        req = {
            "request_id": f"G5-{i:03d}",
            "name": c["name"],
            "inputs": list(NAMES),
            "output": "Y",
            "expression": c["function"],
            "truth_table": f"0x{c['tt']:04X}",
            "sizing": "hd",
            "estimated_area_um2": round(c["area"], 4),
        }
        p = os.path.join(out_dir, f"{c['name']}.json")
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(req, f, indent=2)
            f.write("\n")
        paths.append(p)
    return paths


def imported_cell_count(yosys_output: str) -> int:
    """Parses 'Imported N cell types' from Yosys read_liberty output."""
    m = re.search(r'Imported (\d+) cell types', yosys_output)
    return int(m.group(1)) if m else -1


def cells_from_candidates(csv_path: str, top_n: int) -> List[Dict]:
    """The top_n kept candidates of results/candidates.csv as cell records."""
    import csv
    cells = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r["kept"] != "True" or len(cells) >= top_n:
                continue
            tt = int(r["p_class"], 16)
            cells.append({"name": cell_name(tt), "tt": tt,
                          "function": liberty_function(tt, r["structure"]),
                          "area": float(r["est_area_um2"]), "stages": int(r["stages"]),
                          "transistors": int(r["transistors"]), "p_class": r["p_class"]})
    return cells


def verify_liberty_cells(lib_path: str, cells: List[Dict]) -> List[str]:
    """
    Re-reads the written Liberty and checks every new cell: present once,
    area as estimated, and its function evaluates to the class truth table.
    Returns a list of problems (empty when the file is right).
    """
    from src.redundancy import parse_hd_library
    found = {c['name']: c for c in parse_hd_library(lib_path) if c['name'].startswith("dd2_g5__")}
    problems = []
    for c in cells:
        got = found.get(c["name"])
        if got is None:
            problems.append(f"{c['name']}: missing")
            continue
        if got['inputs'] != list(NAMES):
            problems.append(f"{c['name']}: pins {got['inputs']}")
        if abs(got['area'] - c['area']) > 1e-3:
            problems.append(f"{c['name']}: area {got['area']} != {c['area']}")
        if tt_from_expr(got['function']) != c['tt']:
            problems.append(f"{c['name']}: function {got['function']} is not 0x{c['tt']:04X}")
    return problems
